import unittest

from termtosvg import config


class TestConf(unittest.TestCase):
    def test_default_templates(self):
        templates = config.default_templates()

        # One template per declared name, keyed without the '.svg' suffix
        expected_names = {name.removesuffix('.svg')
                          for name in config.DEFAULT_TEMPLATES_NAMES}
        self.assertEqual(set(templates), expected_names)

        # Every template must have been found in the package data and be
        # readable SVG bytes rather than an empty or missing resource
        for name, template in templates.items():
            with self.subTest(template=name):
                self.assertIsInstance(template, bytes)
                self.assertIn(b'<svg', template)

    def test_validate_geometry(self):
        self.assertEqual(config.validate_geometry('82x19'), (82, 19))
        self.assertEqual(config.validate_geometry('82X19'), (82, 19))

        for invalid in ['0x19', '82x0', '-1x19', '82', 'axb', '', '1x2x3']:
            with self.subTest(case=invalid), self.assertRaises(ValueError):
                config.validate_geometry(invalid)
