"""Colour themes applied when rendering

A theme is a mapping from the CSS class names the renderer emits onto colours:
'foreground', 'background' and 'color0' through 'color15'.

Templates declare their palette inside a <style id="user-style"> element, which
is also where template authors keep rules that have nothing to do with colour
(the progress bar animation, the JavaScript player controls). A theme is
therefore emitted as a separate element rather than replacing that one.
"""

import io
import re

from lxml import etree

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
