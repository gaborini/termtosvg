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
            ('palette not a string', json.dumps({'fg': '#ffffff', 'bg': '#000000',
                                                 'palette': 42})),
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
