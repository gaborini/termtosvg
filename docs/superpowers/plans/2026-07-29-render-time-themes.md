# Render-time colour themes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `termtosvg render` pick a colour palette independently of the SVG template, via a `--theme` option that accepts a built-in name, a palette file, or `auto` to read the palette out of the cast file.

**Architecture:** A new `termtosvg/theme.py` turns a theme argument into a palette dict keyed by the CSS class names the renderer already emits (`foreground`, `background`, `color0`–`color15`). `anim.py` writes those colours into a new `<style id="generated-theme">` appended inside the template's `<defs>`, which lands after the template's own `<style id="user-style">` and therefore wins at equal CSS specificity. Nothing is substituted, so template rules that are not colours survive.

**Tech Stack:** Python 3.10+, lxml for SVG, argparse for the CLI, `unittest` for tests, ruff for linting.

## Global Constraints

- Python floor is 3.10; `requires-python = ">=3.10"`.
- With no `--theme` argument, output must be **byte-identical** to the current tree. The 267-artifact baseline is the oracle.
- `user-style` must never be overwritten: `progress_bar` keeps `@keyframes progress-bar-animation` and `#progress-bar` there, and `window_frame_js` keeps `#play-button`, `#pause-button`, `#wide_track`, `#track`, `#slider_button`, `#timer`.
- The colour surface is exactly 18 class names: `foreground`, `background`, `color0` … `color15`.
- Theme argument resolution order is fixed: literal `auto`, then built-in name, then file path.
- An 8-entry palette emits rules for `color0`–`color7` only; `color8`–`color15` are left to the template.
- `--theme` goes on the `render` sub-command and the implicit record-and-render form. Never on `record`.
- `--theme` is long-only. No short flag.
- Existing public signatures keep working: `render_animation(frames, geometry, filename, template)` and `timed_frames(records, ...) -> (geometry, frames)` must remain callable exactly as they are today.
- Line length 100, single quotes, `ruff check .` must pass.
- Commit with `git -c user.email=17881088+gaborini@users.noreply.github.com` — the repo's configured address is blocked by GitHub's email privacy protection.

---

### Task 1: Palette extraction and CSS generation

**Files:**
- Create: `termtosvg/theme.py`
- Test: `termtosvg/tests/test_theme.py`
- Modify: `termtosvg/tests/suite.py` (register the new TestCase)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `COLOR_KEYS: list[str]`, `AUTO: str`, `class ThemeError(Exception)`, `palette_from_template(template: bytes) -> dict[str, str]`, `theme_css(palette: dict[str, str]) -> str`.

- [ ] **Step 1: Write the failing test**

Create `termtosvg/tests/test_theme.py`:

```python
import json
import tempfile
import unittest

from termtosvg import config, theme
from termtosvg.asciicast import AsciiCastV2Theme


class TestTheme(unittest.TestCase):
    def test_palette_from_template(self):
        templates = config.default_templates()

        # Every bundled template declares the full 18-colour surface
        for name in sorted(templates):
            with self.subTest(template=name):
                palette = theme.palette_from_template(templates[name])
                self.assertEqual(set(palette), set(theme.COLOR_KEYS))
                for key, colour in palette.items():
                    self.assertRegex(colour, r'^#[0-9a-fA-F]{6}$', key)

    def test_palette_from_template_known_values(self):
        templates = config.default_templates()
        palette = theme.palette_from_template(templates['dracula'])
        self.assertEqual(palette['foreground'], '#e9e9f4')
        self.assertEqual(palette['background'], '#282936')
        self.assertEqual(palette['color1'], '#ea51b2')

    def test_palette_from_template_failures(self):
        with self.assertRaises(theme.ThemeError):
            theme.palette_from_template(b'this is not svg at all')

        # Well-formed SVG with no user-style element
        no_style = b'<svg xmlns="http://www.w3.org/2000/svg"><defs/></svg>'
        with self.assertRaises(theme.ThemeError):
            theme.palette_from_template(no_style)

    def test_theme_css_orders_and_formats_rules(self):
        css = theme.theme_css({'foreground': '#ffffff', 'color0': '#000000'})
        self.assertIn('.foreground {fill: #ffffff;}', css)
        self.assertIn('.color0 {fill: #000000;}', css)
        # foreground comes first in COLOR_KEYS, so it comes first in the output
        self.assertLess(css.index('.foreground'), css.index('.color0'))

    def test_theme_css_omits_absent_colours(self):
        # An 8-colour palette must leave color8..color15 to the template
        palette = {f'color{i}': '#010203' for i in range(8)}
        css = theme.theme_css(palette)
        self.assertIn('.color7', css)
        self.assertNotIn('.color8', css)
        self.assertNotIn('.foreground', css)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest termtosvg.tests.test_theme -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'termtosvg.theme'`

- [ ] **Step 3: Write minimal implementation**

Create `termtosvg/theme.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest termtosvg.tests.test_theme -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Register the new TestCase in the aggregate suite**

Edit `termtosvg/tests/suite.py` — add the import alongside the others and the name to `__all__`:

```python
from termtosvg.tests.test_term import TestTerm
from termtosvg.tests.test_theme import TestTheme

__all__ = [
    'TestAnim',
    'TestAsciicast',
    'TestConf',
    'TestMain',
    'TestTerm',
    'TestTheme',
]
```

- [ ] **Step 6: Verify the whole suite still passes and lint is clean**

Run: `python -m unittest termtosvg.tests.suite` then `ruff check .`
Expected: OK, and "All checks passed!"

- [ ] **Step 7: Commit**

```bash
git add termtosvg/theme.py termtosvg/tests/test_theme.py termtosvg/tests/suite.py
git -c user.email=17881088+gaborini@users.noreply.github.com commit -m "Add palette extraction and theme CSS generation

Templates already carry their palette as 18 CSS rules in user-style, so built-in
palettes need no new data file and cannot drift from the templates."
```

---

### Task 2: Resolving a `--theme` argument

**Files:**
- Modify: `termtosvg/theme.py`
- Test: `termtosvg/tests/test_theme.py`

**Interfaces:**
- Consumes: `COLOR_KEYS`, `AUTO`, `ThemeError`, `palette_from_template` from Task 1.
- Produces: `palette_from_cast_theme(theme) -> dict[str, str]`, `palette_from_file(path: str) -> dict[str, str]`, `resolve(value: str, templates: dict[str, bytes]) -> str | dict[str, str]`. `resolve` returns the string `AUTO` unchanged when given `"auto"`, otherwise a palette dict.

- [ ] **Step 1: Write the failing test**

Append to `termtosvg/tests/test_theme.py` inside `class TestTheme`:

```python
    def test_palette_from_cast_theme(self):
        cast_theme = AsciiCastV2Theme(
            fg='#839496', bg='#002b36',
            palette=':'.join([f'#00000{i}' for i in range(8)]),
        )
        palette = theme.palette_from_cast_theme(cast_theme)
        self.assertEqual(palette['foreground'], '#839496')
        self.assertEqual(palette['background'], '#002b36')
        self.assertEqual(palette['color0'], '#000000')
        self.assertEqual(palette['color7'], '#000007')
        # An 8-colour theme must not invent the bright half
        self.assertNotIn('color8', palette)

    def test_palette_from_file(self):
        data = {'fg': '#ffffff', 'bg': '#000000',
                'palette': ':'.join(['#111111'] * 8)}
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as handle:
            json.dump(data, handle)
            path = handle.name
        palette = theme.palette_from_file(path)
        self.assertEqual(palette['foreground'], '#ffffff')
        self.assertEqual(palette['color3'], '#111111')

        # A whole cast header is accepted too, so a theme can be lifted from one
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as handle:
            json.dump({'version': 2, 'width': 80, 'height': 24, 'theme': data}, handle)
            header_path = handle.name
        self.assertEqual(theme.palette_from_file(header_path)['foreground'], '#ffffff')

    def test_palette_from_file_failures(self):
        cases = [
            ('not json', 'nonsense'),
            ('not an object', '[1, 2, 3]'),
            ('missing attributes', json.dumps({'fg': '#ffffff'})),
            ('invalid colour', json.dumps({'fg': 'xxxxxxx', 'bg': '#000000',
                                           'palette': ':'.join(['#111111'] * 8)})),
            ('short palette', json.dumps({'fg': '#ffffff', 'bg': '#000000',
                                          'palette': '#111111'})),
        ]
        for case, content in cases:
            with self.subTest(case=case):
                with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as handle:
                    handle.write(content)
                    path = handle.name
                with self.assertRaises(theme.ThemeError):
                    theme.palette_from_file(path)

        with self.subTest(case='missing file'):
            with self.assertRaises(theme.ThemeError):
                theme.palette_from_file('/nonexistent/theme.json')

    def test_resolve_order(self):
        templates = config.default_templates()

        # 'auto' is a keyword and is passed through for the caller to handle
        self.assertEqual(theme.resolve('auto', templates), theme.AUTO)

        # A built-in name wins over any same-named file in the working directory
        self.assertEqual(theme.resolve('dracula', templates),
                        theme.palette_from_template(templates['dracula']))

        # Anything else is a path
        with self.assertRaises(theme.ThemeError):
            theme.resolve('definitely-not-a-template', templates)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest termtosvg.tests.test_theme -v`
Expected: FAIL with `AttributeError: module 'termtosvg.theme' has no attribute 'palette_from_cast_theme'`

- [ ] **Step 3: Write minimal implementation**

Add to `termtosvg/theme.py` — extend the imports at the top:

```python
import io
import json
import re

from lxml import etree

from termtosvg.asciicast import AsciiCastError, AsciiCastV2Theme
```

and append these functions:

```python
def palette_from_cast_theme(cast_theme) -> dict[str, str]:
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


def resolve(value: str, templates: dict[str, bytes]):
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest termtosvg.tests.test_theme -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Verify lint and the full suite**

Run: `ruff check .` then `python -m unittest termtosvg.tests.suite`
Expected: "All checks passed!" and OK

- [ ] **Step 6: Commit**

```bash
git add termtosvg/theme.py termtosvg/tests/test_theme.py
git -c user.email=17881088+gaborini@users.noreply.github.com commit -m "Resolve --theme arguments to palettes

Reuses AsciiCastV2Theme for validation so palette files and cast headers accept
exactly the same shape. Resolution order is fixed - auto, built-in name, then
path - so an argument's meaning does not depend on the working directory."
```

---

### Task 3: Inject the theme into rendered SVG

**Files:**
- Modify: `termtosvg/anim.py` (imports; `render_animation`, `render_still_frames`, `_render_preparation`; new `_add_theme`)
- Test: `termtosvg/tests/test_anim.py`

**Interfaces:**
- Consumes: `theme_css` from Task 1.
- Produces: `render_animation(frames, geometry, filename, template, cell_width=CELL_WIDTH, cell_height=CELL_HEIGHT, palette=None)` and `render_still_frames(frames, geometry, directory, template, cell_width=CELL_WIDTH, cell_height=CELL_HEIGHT, palette=None)`. `palette` is a dict as produced by Task 1/2, or `None` to leave the template's colours alone.

- [ ] **Step 1: Write the failing test**

Append to `termtosvg/tests/test_anim.py` inside `class TestAnim`:

First extend the module-level imports of `termtosvg/tests/test_anim.py` — it
already imports `io`, `itertools`, `tempfile`, `unittest`, `etree`, `anim` and
`term`, but not these two:

```python
from termtosvg import anim, config, term, theme
```

Then add the tests:

```python
    def test_render_animation_with_palette(self):
        templates = config.default_templates()
        frames = [term.TimedFrame(0, 1000, {0: {0: anim.CharacterCell('a')}})]
        palette = {'foreground': '#abcdef', 'color1': '#123456'}

        _, filename = tempfile.mkstemp(prefix='termtosvg_test_', suffix='.svg')
        anim.render_animation(frames, (80, 24), filename, templates['gjm8'],
                              palette=palette)

        with open(filename, 'rb') as svg_file:
            root = etree.parse(svg_file).getroot()

        generated = root.find(f'.//{{{anim.SVG_NS}}}defs/'
                              f'{{{anim.SVG_NS}}}style[@id="generated-theme"]')
        self.assertIsNotNone(generated)
        self.assertIn('.foreground {fill: #abcdef;}', generated.text)
        self.assertIn('.color1 {fill: #123456;}', generated.text)

        # The theme element must come after user-style so it wins on specificity
        defs = root.find(f'.//{{{anim.SVG_NS}}}defs')
        ids = [child.get('id') for child in defs]
        self.assertLess(ids.index('user-style'), ids.index('generated-theme'))

    def test_render_animation_palette_preserves_template_rules(self):
        # The riskiest part of theming: user-style holds rules that are not
        # colours, and those must survive. window_frame_js keeps its player
        # controls there and progress_bar keeps its bar animation.
        templates = config.default_templates()
        frames = [term.TimedFrame(0, 1000, {0: {0: anim.CharacterCell('a')}})]

        expected = {
            'window_frame_js': ['#play-button', '#pause-button', '#slider_button'],
            'progress_bar': ['progress-bar-animation', '#progress-bar'],
        }
        for name, needles in expected.items():
            with self.subTest(template=name):
                _, filename = tempfile.mkstemp(prefix='termtosvg_test_', suffix='.svg')
                anim.render_animation(frames, (80, 24), filename, templates[name],
                                      palette={'foreground': '#abcdef'})
                with open(filename, 'rb') as svg_file:
                    root = etree.parse(svg_file).getroot()
                user_style = root.find(f'.//{{{anim.SVG_NS}}}defs/'
                                       f'{{{anim.SVG_NS}}}style[@id="user-style"]')
                self.assertIsNotNone(user_style)
                for needle in needles:
                    self.assertIn(needle, user_style.text)

    def test_render_animation_without_palette_adds_no_theme_element(self):
        templates = config.default_templates()
        frames = [term.TimedFrame(0, 1000, {0: {0: anim.CharacterCell('a')}})]
        _, filename = tempfile.mkstemp(prefix='termtosvg_test_', suffix='.svg')
        anim.render_animation(frames, (80, 24), filename, templates['gjm8'])

        with open(filename, 'rb') as svg_file:
            root = etree.parse(svg_file).getroot()
        self.assertIsNone(root.find(f'.//{{{anim.SVG_NS}}}style[@id="generated-theme"]'))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest termtosvg.tests.test_anim -v`
Expected: FAIL with `TypeError: render_animation() got an unexpected keyword argument 'palette'`

- [ ] **Step 3: Write minimal implementation**

In `termtosvg/anim.py`, add the import near the other project imports:

```python
from termtosvg.theme import theme_css
```

Add `_add_theme` immediately above `_render_preparation`:

```python
def _add_theme(root, palette):
    """Append a style element that overrides the template's palette

    Appended to "defs" rather than replacing the template's "user-style"
    element: template authors keep rules there that have nothing to do with
    colour, such as the progress bar animation and the JavaScript player
    controls, and those must survive. Being last in document order, these rules
    win over the template's at equal specificity, while the template's
    higher-specificity ID selectors are untouched.
    """
    defs = root.find(f'.//{{{SVG_NS}}}defs')
    if defs is None:
        raise TemplateError('Missing "defs" element in template')

    style = etree.SubElement(defs, 'style', attrib={'id': 'generated-theme'})
    style.text = etree.CDATA(f'\n{theme_css(palette)}\n        ')
    return root
```

Change `render_animation`, `render_still_frames` and `_render_preparation`:

```python
def render_animation(frames, geometry, filename, template,
                     cell_width: int = CELL_WIDTH, cell_height: int = CELL_HEIGHT,
                     palette=None) -> None:
    root = _render_preparation(geometry, template, cell_width, cell_height, palette)
    _, screen_height = geometry
    root = _render_animation(screen_height, frames, root, cell_width, cell_height)

    with open(filename, 'wb') as output_file:
        output_file.write(etree.tostring(root))


def render_still_frames(frames, geometry, directory, template,
                        cell_width: int = CELL_WIDTH, cell_height: int = CELL_HEIGHT,
                        palette=None) -> None:
    root = _render_preparation(geometry, template, cell_width, cell_height, palette)

    frame_generator = _render_still_frames(frames, root, cell_width, cell_height)
    for frame_count, frame_root in enumerate(frame_generator):
        filename = os.path.join(directory, f'termtosvg_{frame_count:05}.svg')
        with open(filename, 'wb') as output_file:
            output_file.write(etree.tostring(frame_root))


def _render_preparation(geometry, template, cell_width, cell_height, palette=None):
    # Read header record and add the corresponding information to the SVG
    root = resize_template(template, geometry, cell_width, cell_height)
    if palette:
        _add_theme(root, palette)
    svg_screen_tag = _find_screen(root)

    for child in list(svg_screen_tag):
        svg_screen_tag.remove(child)
    svg_screen_tag.append(BG_RECT_TAG)

    return root
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest termtosvg.tests.test_anim -v`
Expected: PASS, all tests including the three new ones

- [ ] **Step 5: Confirm the no-theme path is still byte-identical**

Run:
```bash
PYTHONPATH=. python /path/to/scratchpad/baseline.py /tmp/after_task3
(cd /tmp/after_task3 && find . -type f -name '*.svg' | sort | xargs shasum -a 256) > /tmp/after_task3.sha256
diff /path/to/scratchpad/baseline.sha256 /tmp/after_task3.sha256 && echo IDENTICAL
```
Expected: `IDENTICAL` — 267 files unchanged, because `palette` defaults to `None`.

- [ ] **Step 6: Confirm themed output is still valid SVG**

Run:
```bash
PYTHONPATH=. python -c "
from termtosvg import anim, config, term, theme
templates = config.default_templates()
frames = [term.TimedFrame(0, 1000, {0: {0: anim.CharacterCell('a')}})]
palette = theme.palette_from_template(templates['dracula'])
anim.render_animation(frames, (80, 24), '/tmp/themed.svg', templates['gjm8'], palette=palette)
anim.validate_svg('/tmp/themed.svg')
print('themed output validates against the SVG 1.1 DTD')
"
```
Expected: the success line, no exception.

- [ ] **Step 7: Commit**

```bash
git add termtosvg/anim.py termtosvg/tests/test_anim.py
git -c user.email=17881088+gaborini@users.noreply.github.com commit -m "Emit a theme override style element when a palette is given

Appended after the template's user-style rather than replacing it, because two
templates keep non-colour rules there: progress_bar its bar animation, and
window_frame_js its player controls. A test asserts those survive.

With no palette the element is not emitted at all, so the 267-artifact baseline
stays byte-identical."
```

---

### Task 4: Wire up the `--theme` command line option

**Files:**
- Modify: `termtosvg/main.py` (imports; `parse`; `render_subcommand`; `record_render_subcommand`; `main`)
- Test: `termtosvg/tests/test_main.py`

**Interfaces:**
- Consumes: `theme.resolve`, `theme.AUTO`, `theme.palette_from_cast_theme` from Tasks 1–2; the `palette=` keyword from Task 3.
- Produces: `args.theme` on the implicit and `render` parsers, holding `None`, the string `AUTO`, or a palette dict.

- [ ] **Step 1: Write the failing test**

Add to `termtosvg/tests/test_main.py` inside `class TestMain`, and extend `test_cases` with the new argument forms:

```python
    def test_theme_option(self):
        templates = {'plain': b'', 'dracula': b''}

        # 'auto' is passed through for main() to resolve against the cast header
        _, args = termtosvg.main.parse(
            args=['render', 'input_filename', '--theme', 'auto'],
            templates=templates, default_template='plain', default_geometry='48x95',
            default_min_dur=2, default_max_dur=None, default_cmd='sh',
            default_loop_delay=1000,
        )
        self.assertEqual(args.theme, termtosvg.theme.AUTO)

        # Absent by default, so rendering is unaffected
        _, args = termtosvg.main.parse(
            args=['render', 'input_filename'],
            templates=templates, default_template='plain', default_geometry='48x95',
            default_min_dur=2, default_max_dur=None, default_cmd='sh',
            default_loop_delay=1000,
        )
        self.assertIsNone(args.theme)

    def test_theme_rejected_by_record(self):
        # record renders nothing, so --theme must not be accepted there
        with self.assertRaises(SystemExit):
            termtosvg.main.parse(
                args=['record', '--theme', 'auto'],
                templates={'plain': b''}, default_template='plain',
                default_geometry='48x95', default_min_dur=2, default_max_dur=None,
                default_cmd='sh', default_loop_delay=1000,
            )
```

Add `import termtosvg.theme` to the imports at the top of the test file, and append these entries to `test_cases`:

```python
        ['--theme', 'auto'],
        ['render', 'input_filename', '--theme', 'auto'],
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest termtosvg.tests.test_main -v`
Expected: FAIL with `AttributeError: 'Namespace' object has no attribute 'theme'`

- [ ] **Step 3: Write minimal implementation**

In `termtosvg/main.py`, add to the imports:

```python
import termtosvg.theme
```

In `parse`, add a theme parser next to `template_parser`:

```python
    theme_parser = argparse.ArgumentParser(add_help=False)
    theme_parser.add_argument(
        '--theme',
        help=('override the color palette of the template. THEME may be "auto" '
              'to use the palette recorded in the cast file, the name of one of '
              f'the default templates ({", ".join(templates)}), or the path to a '
              'JSON file with "fg", "bg" and "palette" attributes.'),
        type=lambda name: termtosvg.theme.resolve(name, templates),
        default=None,
        metavar='THEME'
    )
```

Add `theme_parser` to the parents of the main parser and of the `render` parser, leaving `record` alone:

```python
    parser = argparse.ArgumentParser(
        prog=prog,
        parents=[command_parser, loop_delay_parser, geometry_parser, min_duration_parser,
                 max_duration_parser, still_frames_parser, template_parser, theme_parser],
        usage=USAGE,
        epilog=EPILOG
    )
```

```python
            parser = argparse.ArgumentParser(
                prog=prog,
                description='render an asciicast recording as an SVG animation',
                parents=[loop_delay_parser,  min_duration_parser,
                         max_duration_parser, still_frames_parser, template_parser,
                         theme_parser],
                usage=RENDER_USAGE
            )
```

Add a helper above `render_subcommand`:

```python
def _resolve_auto_palette(header):
    """Return the palette recorded in a cast header, or None with a warning

    Falling back is deliberate: refusing to render would be hostile in batch use,
    while falling back silently would hide that --theme auto did nothing.
    """
    if header.theme is None:
        logger.warning('--theme auto: this recording carries no theme, '
                       'keeping the colors of the template')
        return None
    return termtosvg.theme.palette_from_cast_theme(header.theme)
```

Replace `render_subcommand` with a version that resolves `auto` from the header. The header is read off the stream and chained back so that `timed_frames` still receives it and its public return shape is untouched:

```python
def render_subcommand(still, template, cast_filename, output_path,
                      min_frame_duration, max_frame_duration, loop_delay,
                      palette=None):
    """Render the animation from an asciicast recording"""
    import itertools

    from termtosvg.asciicast import read_records
    from termtosvg.term import timed_frames

    logger.info('Rendering started')
    asciicast_records = iter(read_records(cast_filename))
    if palette is termtosvg.theme.AUTO:
        header = next(asciicast_records)
        palette = _resolve_auto_palette(header)
        asciicast_records = itertools.chain([header], asciicast_records)

    geometry, frames = timed_frames(asciicast_records, min_frame_duration,
                                    max_frame_duration, loop_delay)
    if still:
        termtosvg.anim.render_still_frames(frames=frames,
                                          geometry=geometry,
                                          directory=output_path,
                                          template=template,
                                          palette=palette)
        logger.info('Rendering ended, SVG frames are located at %s', output_path)
    else:
        termtosvg.anim.render_animation(frames=frames,
                                        geometry=geometry,
                                        filename=output_path,
                                        template=template,
                                        palette=palette)
        logger.info('Rendering ended, SVG animation is %s', output_path)
```

In `record_render_subcommand`, add a `palette=None` parameter, resolve `AUTO` the same way, and pass `palette` through. `record()` always emits `theme=None`, so `--theme auto` there warns and keeps the template colours:

```python
def record_render_subcommand(process_args, still, template, geometry,
                             input_fileno, output_fileno, output_path,
                             min_frame_duration, max_frame_duration,
                             loop_delay, palette=None):
    """Record and render the animation on the fly"""
    import itertools

    from termtosvg.term import TerminalMode, get_terminal_size, record, timed_frames

    logger.info('Recording started, enter "exit" command or Control-D to end')
    if geometry is None:
        columns, lines = get_terminal_size(output_fileno)
    else:
        columns, lines = geometry
    with TerminalMode(input_fileno):
        # Do not write anything to stdout (print, logger...) while in this
        # context manager if the output of the process is set to stdout. We
        # do not want two processes writing to the same terminal.
        asciicast_records = iter(record(process_args, columns, lines, input_fileno,
                                       output_fileno))
        if palette is termtosvg.theme.AUTO:
            header = next(asciicast_records)
            palette = _resolve_auto_palette(header)
            asciicast_records = itertools.chain([header], asciicast_records)

        geometry, frames = timed_frames(asciicast_records, min_frame_duration,
                                        max_frame_duration, loop_delay)

        if still:
            termtosvg.anim.render_still_frames(frames, geometry, output_path,
                                              template, palette=palette)
            end_msg = 'Rendering ended, SVG frames are located at %s'
        else:
            termtosvg.anim.render_animation(frames, geometry, output_path,
                                           template, palette=palette)
            end_msg = 'Rendering ended, SVG animation is %s'

    logger.info(end_msg, output_path)
```

In `main`, pass the parsed theme to both call sites:

```python
        render_subcommand(args.still_frames, args.template, args.input_file,
                          output_path, args.min_frame_duration,
                          args.max_frame_duration, args.loop_delay, args.theme)
```

```python
        record_render_subcommand(process_args, args.still_frames, args.template,
                                 args.screen_geometry, input_fileno,
                                 output_fileno, output_path,
                                 args.min_frame_duration,
                                 args.max_frame_duration,
                                 args.loop_delay, args.theme)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest termtosvg.tests.test_main -v`
Expected: PASS

- [ ] **Step 5: Exercise the option end to end**

Run:
```bash
PYTHONPATH=. python -m termtosvg render docs/examples/casts/awesome.cast /tmp/t_dracula.svg -t gjm8 --theme dracula
PYTHONPATH=. python -m termtosvg render docs/examples/casts/awesome.cast /tmp/t_auto.svg -t gjm8 --theme auto
PYTHONPATH=. python -m termtosvg render docs/examples/casts/htop.cast /tmp/t_warn.svg -t gjm8 --theme auto
grep -c 'generated-theme' /tmp/t_dracula.svg /tmp/t_auto.svg
```
Expected: the first two contain a `generated-theme` element; the third prints the "carries no theme" warning on stderr (`htop.cast` has none) and produces no `generated-theme` element.

- [ ] **Step 6: Confirm `--theme dracula` matches the dracula template's colours**

Run:
```bash
PYTHONPATH=. python -c "
from termtosvg import config, theme
templates = config.default_templates()
from lxml import etree
root = etree.parse('/tmp/t_dracula.svg').getroot()
NS = 'http://www.w3.org/2000/svg'
css = root.find(f'.//{{{NS}}}style[@id=\"generated-theme\"]').text
for key, colour in theme.palette_from_template(templates['dracula']).items():
    assert f'.{key} {{fill: {colour};}}' in css, key
print('all 18 dracula colours present in the themed output')
"
```
Expected: the success line.

- [ ] **Step 7: Verify lint, full suite and the byte-identity baseline**

Run: `ruff check .`, `python -m unittest termtosvg.tests.suite`, and the baseline diff from Task 3 Step 5.
Expected: clean lint, OK, and `IDENTICAL`.

- [ ] **Step 8: Commit**

```bash
git add termtosvg/main.py termtosvg/tests/test_main.py
git -c user.email=17881088+gaborini@users.noreply.github.com commit -m "Add a --theme option to render and to the implicit form

Long-only: -t already means template, and a -T shorthand for a neighbouring
colour concept invites picking the wrong one. Not offered on record, which
renders nothing.

Resolving 'auto' needs the cast header, which timed_frames consumes and does not
return. Rather than change that public return shape, the header is read off the
stream and chained back on."
```

---

### Task 5: Document the feature

**Files:**
- Modify: `README.md` (CLI reference table; a themes subsection under Templates; a recipe)
- Modify: `man/termtosvg.md` (OPTIONS; EXAMPLES)
- Modify: `CHANGELOG.md`
- Modify: `termtosvg/__init__.py` (version bump)

- [ ] **Step 1: Add `--theme` to the README CLI reference table**

In the option matrix, immediately after the `-t, --template` row, add:

```markdown
| `--theme THEME` | template's own palette | ✅ | — | ✅ | Override just the colours: `auto` to use the palette stored in the recording, a built-in name, or a path to a JSON palette. |
```

- [ ] **Step 2: Add a themes subsection to the README**

Insert after the template table, before "### Embedding, and one caveat worth knowing":

```markdown
### Colours separately from chrome

A template bundles two independent things: the colour palette and the terminal
chrome (window frame, play button, progress bar). `--theme` lets you vary the
colours without authoring a template, so any palette combines with any chrome:

```shell
termtosvg render demo.cast out.svg -t window_frame --theme dracula
```

`--theme` accepts:

| Value | Meaning |
|---|---|
| a built-in name | the palette from that template, e.g. `--theme solarized_light` |
| `auto` | the palette stored in the recording's own header |
| a path | a JSON file with `fg`, `bg` and `palette` attributes |

`auto` is useful for recordings made with asciinema, which store the terminal's
palette in the cast file. Recordings made by `termtosvg record` do not store one,
so `auto` warns and keeps the template's colours.

A palette file uses the same shape as the asciicast `theme` object, so it can be
copied straight out of a `.cast` header:

```json
{
  "fg": "#839496",
  "bg": "#002b36",
  "palette": "#073642:#dc322f:#859900:#b58900:#268bd2:#d33682:#2aa198:#eee8d5"
}
```

Eight or sixteen colours are both accepted. With eight, the bright half is left
as the template defined it rather than being guessed at.
```

- [ ] **Step 3: Add a recipe to the README**

In the Recipes block, after the "Re-theme an existing recording" line, add:

```shell
# Keep the chrome, swap only the colours
termtosvg render demo.cast out.svg -t window_frame --theme solarized_light

# Use the palette the recording was made with (asciinema casts store one)
termtosvg render downloaded.cast out.svg --theme auto
```

- [ ] **Step 4: Document the option in the man page**

In `man/termtosvg.md`, after the `-t, --template=TEMPLATE` block, add:

```markdown
##### --theme=THEME
Override the color palette supplied by the template, leaving the rest of the
template alone. THEME may be `auto` to use the palette recorded in the cast file,
the name of one of the default templates to borrow its palette, or the path to a
JSON file with `fg`, `bg` and `palette` attributes in the same form as the
asciicast theme object. Palettes of 8 or 16 colors are accepted; with 8, colors 8
to 15 are left as the template defined them. Recordings made by `termtosvg
record` do not store a theme, so `auto` warns and keeps the template's colors.
```

And in EXAMPLES:

```markdown
Render with a window frame but Dracula colors
```
termtosvg render recording.cast animation.svg -t window_frame --theme dracula
```

Render using the palette stored in an asciinema recording
```
termtosvg render recording.cast animation.svg --theme auto
```
```

- [ ] **Step 5: Bump the version and write the changelog entry**

Set `__version__ = "1.4.0"` in `termtosvg/__init__.py`, and add to the top of `CHANGELOG.md`:

```markdown
## Version 1.4.0 (2026-07-29)

* **Add `--theme` to choose colours independently of the template.** Previously
  the palette and the terminal chrome were welded together in a template file,
  which is why sixteen templates ship with substantial overlap. `--theme` accepts
  the name of a built-in template to borrow its palette, a path to a JSON palette
  file, or `auto` to use the palette stored in the recording.
* Honour the `theme` attribute of asciicast files when `--theme auto` is given.
  The attribute was previously parsed and validated but never used for rendering,
  so asciinema recordings had their colours silently discarded.
* Rendering without `--theme` is unchanged: all 267 reference artifacts remain
  byte-identical.

```

- [ ] **Step 6: Verify the documented commands actually work**

Run each shell snippet added to the README and man page against a real cast:
```bash
PYTHONPATH=. python -m termtosvg render docs/examples/casts/awesome.cast /tmp/d1.svg -t window_frame --theme dracula
PYTHONPATH=. python -m termtosvg render docs/examples/casts/awesome.cast /tmp/d2.svg -t window_frame --theme solarized_light
PYTHONPATH=. python -m termtosvg render docs/examples/casts/awesome.cast /tmp/d3.svg --theme auto
```
Expected: all three succeed and produce non-empty files.

- [ ] **Step 7: Final verification**

Run: `ruff check .`, `python -m unittest termtosvg.tests.suite`, and the 267-artifact baseline diff.
Expected: clean lint, OK, `IDENTICAL`.

- [ ] **Step 8: Commit**

```bash
git add README.md man/termtosvg.md CHANGELOG.md termtosvg/__init__.py
git -c user.email=17881088+gaborini@users.noreply.github.com commit -m "Document --theme and release 1.4.0

Minor bump: this adds functionality and changes nothing existing. Rendering
without --theme stays byte-identical across all 267 reference artifacts."
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
| --- | --- |
| Append `generated-theme` after `user-style`, never overwrite | 3 |
| `user-style` non-colour rules survive | 3, explicit test |
| 18-name colour surface | 1 |
| Built-in palettes extracted from templates, no new data file | 1 |
| `--theme` on render and implicit form, not record | 4, explicit test |
| Long-only option | 4 |
| Three argument forms: name, file, auto | 2 |
| Fixed resolution order (auto, name, path) | 2, explicit test |
| Palette file uses the asciicast theme shape | 2 |
| Precedence: explicit > auto > template | 4 |
| `auto` with no cast theme warns and falls back | 4, verified in Step 5 |
| 8-colour palette leaves color8–15 alone | 1, explicit test |
| Unknown name that is not a file errors | 2, explicit test |
| `theme.py` holds extraction, parsing and CSS generation | 1, 2 |
| No `--theme` means byte-identical output | 3 Step 5, 4 Step 7, 5 Step 7 |
| `--theme dracula` matches the dracula template | 4 Step 6 |
| `auto` gives Solarized on the three theme-carrying casts | 4 Step 5 |
| Themed output validates against the SVG 1.1 DTD | 3 Step 6 |

No gaps.

**Placeholder scan:** No TBD, TODO, "handle errors appropriately", or "similar to Task N". Every code step carries real code.

**Type consistency:** `palette` is a `dict[str, str]` keyed by the names in `COLOR_KEYS` throughout Tasks 1–4. `resolve` returns the string `AUTO` or such a dict; the `AUTO` sentinel is compared with `is` in Task 4 against the same constant defined in Task 1. `palette_from_cast_theme` takes an `AsciiCastV2Theme` in both Task 2 and Task 4. `render_animation`/`render_still_frames` gain the same `palette=None` keyword in Task 3 and are called with it in Task 4.
