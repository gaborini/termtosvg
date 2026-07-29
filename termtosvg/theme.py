"""Colour themes applied when rendering

A theme is a mapping from the CSS class names the renderer emits onto colours:
'foreground', 'background' and 'color0' through 'color15'.

Templates declare their palette inside a <style id="user-style"> element, which
is also where template authors keep rules that have nothing to do with colour
(the progress bar animation, the JavaScript player controls). A theme is
therefore emitted as a separate element rather than replacing that one.
"""

import io
import json
import re

from lxml import etree

from termtosvg.asciicast import AsciiCastError, AsciiCastV2Theme

SVG_NS = 'http://www.w3.org/2000/svg'

# Class names the renderer emits, in the order theme_css writes them out
COLOR_KEYS = ['foreground', 'background'] + [f'color{index}' for index in range(16)]

# Value of --theme meaning "read the palette from the cast file"
AUTO = 'auto'

_USER_STYLE_XPATH = f'.//{{{SVG_NS}}}defs/{{{SVG_NS}}}style[@id="user-style"]'
_COLOUR_RULE = re.compile(
    r'\.(color\d+|foreground|background)\s*\{\s*fill:\s*(#[0-9a-fA-F]{6})\s*;?\s*\}'
)


class ThemeError(Exception):
    pass


def palette_from_template(template: bytes) -> dict[str, str]:
    """Return the colour palette declared by an SVG template"""
    try:
        root = etree.parse(io.BytesIO(template)).getroot()
    except etree.Error as exc:
        raise ThemeError('Invalid template') from exc

    style = root.find(_USER_STYLE_XPATH)
    if style is None:
        raise ThemeError('Template has no <style id="user-style"> element to read colours from')

    palette = dict(_COLOUR_RULE.findall(style.text or ''))
    if not palette:
        raise ThemeError('Template declares no colour rules in its "user-style" element')
    return palette


def theme_css(palette: dict[str, str]) -> str:
    """Return CSS rules that override the palette declared by a template

    Only colours present in `palette` produce a rule, so an 8-colour palette
    leaves color8 through color15 as the template defined them.
    """
    return '\n'.join(f'            .{key} {{fill: {palette[key]};}}'
                     for key in COLOR_KEYS if key in palette)


def palette_from_cast_theme(cast_theme: AsciiCastV2Theme) -> dict[str, str]:
    """Return a palette from an asciicast theme record

    AsciiCastV2Theme has already validated the colours and reduced the palette to
    either 8 or 16 entries, so the entries are taken as they are.
    """
    palette = {'foreground': cast_theme.fg, 'background': cast_theme.bg}
    for index, colour in enumerate(cast_theme.palette.split(':')):
        palette[f'color{index}'] = colour
    return palette


def palette_from_file(path: str) -> dict[str, str]:
    """Return a palette from a JSON file shaped like an asciicast theme

    The file may hold the theme object itself or a whole cast header containing
    one, so a theme can be lifted out of a recording without editing it.
    """
    try:
        with open(path) as theme_file:
            data = json.load(theme_file)
    except OSError as exc:
        raise ThemeError(f'Cannot read theme file "{path}": {exc}') from exc
    except json.JSONDecodeError as exc:
        raise ThemeError(f'Theme file "{path}" is not valid JSON: {exc}') from exc

    if not isinstance(data, dict):
        raise ThemeError(f'Theme file "{path}" must contain a JSON object')

    if isinstance(data.get('theme'), dict):
        data = data['theme']

    missing = {'fg', 'bg', 'palette'} - set(data)
    if missing:
        raise ThemeError(f'Theme file "{path}" is missing attributes: '
                         f'{", ".join(sorted(missing))}')

    try:
        cast_theme = AsciiCastV2Theme(data['fg'], data['bg'], data['palette'])
    except (AsciiCastError, AttributeError) as exc:
        raise ThemeError(f'Invalid theme in "{path}": {exc}') from exc

    return palette_from_cast_theme(cast_theme)


def resolve(value: str, templates: dict[str, bytes]) -> str | dict[str, str]:
    """Turn a --theme argument into a palette

    The order is fixed so that the meaning of an argument never depends on the
    working directory: the literal 'auto' first, then a built-in template name,
    then a file path. A file named like a built-in must be given with a path
    separator, for example './dracula'.

    Returns the string AUTO for 'auto', which the caller resolves against the
    cast header. Returns a palette dict otherwise.
    """
    if value == AUTO:
        return AUTO
    if value in templates:
        return palette_from_template(templates[value])
    return palette_from_file(value)
