import unittest

from termtosvg import config, theme


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
