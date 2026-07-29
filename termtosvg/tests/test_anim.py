import io
import itertools
import os
import pkgutil
import tempfile
import unittest
from collections import namedtuple

import pyte.screens
from lxml import etree

from termtosvg import anim, config, term, theme

TEMPLATE = pkgutil.get_data('termtosvg', '/data/templates/gjm8.svg')


def line(i):
    chars = []
    for c in f'line{i}':
        chars.append(anim.CharacterCell(c, '#123456', '#789012',
                                        False, False, False, False))
    return dict(enumerate(chars))


class TestAnim(unittest.TestCase):
    def test_from_pyte(self):
        pyte_chars = [
            # Simple mapping
            pyte.screens.Char('A', 'red', 'blue'),
            # Reverse colors
            pyte.screens.Char('B', 'red', 'blue', reverse=True),
            # Bold for foreground -> bright colors
            pyte.screens.Char('C', 'red', 'blue', bold=True),
            # Bold and reverse
            pyte.screens.Char('D', 'red', 'blue', bold=True, reverse=True),
            # Defaults
            pyte.screens.Char('E', 'default', 'default'),
            # Hexadecimal
            pyte.screens.Char('F', '008700', 'ABCDEF'),
            # Bright and bold
            pyte.screens.Char('G', 'brightgreen', 'ABCDEF', bold=True),
            # Italics
            pyte.screens.Char('H', 'red', 'blue', italics=True),
            # Underscore
            pyte.screens.Char('I', 'red', 'blue', underscore=True),
            # Strikethrough
            pyte.screens.Char('J', 'red', 'blue', strikethrough=True),
        ]

        char_cells = [
            anim.CharacterCell('A', 'color1', 'color4'),
            anim.CharacterCell('B', 'color4', 'color1'),
            anim.CharacterCell('C', 'color9', 'color4', bold=True),
            anim.CharacterCell('D', 'color4', 'color9', bold=True),
            anim.CharacterCell('E', 'foreground', 'background'),
            anim.CharacterCell('F', '#008700', '#ABCDEF'),
            anim.CharacterCell('G', 'color10', '#ABCDEF', bold=True),
            anim.CharacterCell('H', 'color1', 'color4', italics=True),
            anim.CharacterCell('I', 'color1', 'color4', underscore=True),
            anim.CharacterCell('J', 'color1', 'color4', strikethrough=True),
        ]

        for pyte_char, cell_char in zip(pyte_chars, char_cells, strict=True):
            with self.subTest(case=pyte_char):
                self.assertEqual(anim.CharacterCell.from_pyte(pyte_char), cell_char)

    def test__render_line_bg_colors_xml(self):
        cell_width = 8
        screen_line = {
            0: anim.CharacterCell('A', 'black', 'red'),
            1: anim.CharacterCell('A', 'black', 'red'),
            3: anim.CharacterCell('A', 'black', 'red'),
            4: anim.CharacterCell('A', 'black', 'blue'),
            6: anim.CharacterCell('A', 'black', 'blue'),
            7: anim.CharacterCell('A', 'black', 'blue'),
            8: anim.CharacterCell('A', 'black', 'green'),
            9: anim.CharacterCell('A', 'black', 'red'),
            10: anim.CharacterCell('A', 'black', 'red'),
            11: anim.CharacterCell('A', 'black', '#123456'),
        }

        rectangles = anim._render_line_bg_colors(screen_line=screen_line,
                                                 height=0,
                                                 cell_height=1,
                                                 cell_width=cell_width)

        def key(r):
            return r.attrib['x']

        rect_0, rect_3, rect_4, rect_6, rect_8, rect_9, rect_11 = sorted(rectangles, key=key)

        self.assertEqual(rect_0.attrib['x'], '0')
        self.assertEqual(rect_0.attrib['width'], '16')
        self.assertEqual(rect_0.attrib['height'], '1')
        self.assertEqual(rect_0.attrib['class'], 'red')
        self.assertEqual(rect_3.attrib['x'], '24')
        self.assertEqual(rect_3.attrib['width'], '8')
        self.assertEqual(rect_4.attrib['x'], '32')
        self.assertEqual(rect_6.attrib['x'], '48')
        self.assertEqual(rect_6.attrib['width'], '16')
        self.assertEqual(rect_6.attrib['class'], 'blue')
        self.assertEqual(rect_8.attrib['x'], '64')
        self.assertEqual(rect_8.attrib['class'], 'green')
        self.assertEqual(rect_9.attrib['x'], '72')
        self.assertEqual(rect_11.attrib['fill'], '#123456')

    def test__render_characters(self):
        screen_line = {
            0: anim.CharacterCell('A', 'red', 'white'),
            1: anim.CharacterCell('B', 'blue', 'white'),
            2: anim.CharacterCell('C', 'blue', 'white'),
            7: anim.CharacterCell('D', '#00FF00', 'white'),
            8: anim.CharacterCell('E', '#00FF00', 'white'),
            9: anim.CharacterCell('F', '#00FF00', 'white'),
            10: anim.CharacterCell('G', '#00FF00', 'white'),
            20: anim.CharacterCell('H', 'black', 'black', bold=True),
            30: anim.CharacterCell('I', 'black', 'black', italics=True),
            40: anim.CharacterCell('J', 'black', 'black', underscore=True),
            50: anim.CharacterCell('K', 'black', 'black', strikethrough=True),
            60: anim.CharacterCell('L', 'black', 'black', underscore=True, strikethrough=True),
        }

        with self.subTest(case='Content'):
            cell_width = 8
            texts = {t.text: t for t in anim._render_characters(screen_line, cell_width)}

            self.assertEqual(texts['A'].attrib['class'], 'red')
            self.assertEqual(texts['A'].attrib['x'], '0')
            # Style attributes should not appear for normal text
            self.assertNotIn('font-weight', texts['A'].attrib)
            self.assertNotIn('font-style', texts['A'].attrib)
            self.assertNotIn('text-decoration', texts['A'].attrib)
            self.assertEqual(texts['BC'].attrib['class'], 'blue')
            self.assertEqual(texts['BC'].attrib['x'], '8')
            self.assertEqual(texts['DEFG'].attrib['fill'], '#00FF00')
            self.assertEqual(texts['DEFG'].attrib['x'], '56')
            self.assertEqual(texts['H'].attrib['font-weight'], 'bold')
            self.assertEqual(texts['I'].attrib['font-style'], 'italic')
            self.assertIn('underline', texts['J'].attrib['text-decoration'].split())
            self.assertIn('line-through', texts['K'].attrib['text-decoration'].split())
            self.assertIn('underline', texts['L'].attrib['text-decoration'].split())
            self.assertIn('line-through', texts['L'].attrib['text-decoration'].split())

    def test_ConsecutiveWithSameAttributes(self):
        testClass = namedtuple('testClass', ['field1', 'field2'])
        test_cases = [
            (0, testClass('a', 'b')),
            (2, testClass('a', 'b')),
            (3, testClass('a', 'b')),
            (4, testClass('b', 'b')),
            (5, testClass('b', 'a')),
            (10, testClass('c', 'd')),
            (11, testClass('c', 'd')),
        ]

        expected_results = [
            (0, {'field1': 'a', 'field2': 'b'}),
            (2, {'field1': 'a', 'field2': 'b'}),
            (2, {'field1': 'a', 'field2': 'b'}),
            (4, {'field1': 'b', 'field2': 'b'}),
            (5, {'field1': 'b', 'field2': 'a'}),
            (10, {'field1': 'c', 'field2': 'd'}),
            (10, {'field1': 'c', 'field2': 'd'}),
        ]

        key = anim.ConsecutiveWithSameAttributes(['field1', 'field2'])
        for case, result in zip(test_cases, expected_results, strict=True):
            with self.subTest(case=case):
                self.assertEqual(key(case), result)

    def test__render_timed_frame(self):
        frames = [
            term.TimedFrame(1, 1, {
                1: line(1),
            }),
            term.TimedFrame(2, 1, {
                1: line(1),
                2: line(2),
            }),
            term.TimedFrame(3, 1, {
                1: line(1),
                2: line(2),
                3: line(3),
            }),
            term.TimedFrame(4, 1, {
                1: line(1),
                2: line(2),
                3: line(3),
                4: line(4),
            }),
            # Definition reuse
            term.TimedFrame(5, 1, {
                1: line(1),
                2: line(2),
                3: line(3),
                5: line(4),
            }),
        ]

        all_definitions = {}
        for frame in frames:
            _group, new_defs = anim._render_timed_frame(offset=0,
                                                       buffer=frame.buffer,
                                                       cell_width=8,
                                                       cell_height=17,
                                                       definitions={})
            all_definitions.update(new_defs)

        self.assertEqual(len(all_definitions), 4)

    def test_render_animation(self):
        frames = [
            term.TimedFrame(0, 60, {
                0: line(0),
            }),
            term.TimedFrame(60, 60, {
                0: line(0),
                1: line(1),
            }),
            term.TimedFrame(120, 60, {
                2: line(2),
                3: line(3),
            }),
        ]
        _, filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        anim.render_animation(frames, (80, 24), filename, TEMPLATE)
        with open(filename) as f:
            anim.validate_svg(f)

    def test_render_animation_with_palette(self):
        templates = config.default_templates()
        frames = [term.TimedFrame(0, 1000, {0: {0: anim.CharacterCell('a')}})]
        palette = {'foreground': '#abcdef', 'color1': '#123456'}

        _, filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
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
                _, filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
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
        _, filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        anim.render_animation(frames, (80, 24), filename, templates['gjm8'])

        with open(filename, 'rb') as svg_file:
            root = etree.parse(svg_file).getroot()
        self.assertIsNone(root.find(f'.//{{{anim.SVG_NS}}}style[@id="generated-theme"]'))

    def test_aixterm_colour_names_are_all_known(self):
        # pyte 0.8.2 ships BG_AIXTERM[105] = 'bfightmagenta', a typo for
        # 'brightmagenta'. from_pyte rejects any name it does not know, so a
        # recording using a bright background crashed the renderer.
        for mapping in (pyte.graphics.FG_AIXTERM, pyte.graphics.BG_AIXTERM):
            for code, colour in mapping.items():
                with self.subTest(code=code):
                    self.assertIn(colour, anim.NAMED_COLORS)

    def test_bright_background_renders(self):
        # \033[100m .. \033[107m are the bright backgrounds; 105 is the one that
        # used to raise ValueError('Invalid background color')
        for offset in range(8):
            with self.subTest(code=100 + offset):
                screen = pyte.Screen(4, 1)
                stream = pyte.Stream(screen)
                stream.feed(f'\033[{100 + offset}mX')
                cell = anim.CharacterCell.from_pyte(screen.buffer[0][0])
                self.assertEqual(cell.background_color, f'color{8 + offset}')

    def test_bright_foreground_renders(self):
        for offset in range(8):
            with self.subTest(code=90 + offset):
                screen = pyte.Screen(4, 1)
                stream = pyte.Stream(screen)
                stream.feed(f'\033[{90 + offset}mX')
                cell = anim.CharacterCell.from_pyte(screen.buffer[0][0])
                self.assertEqual(cell.color, f'color{8 + offset}')

    def test_themed_output_validates_against_dtd(self):
        # A theme adds a <style> element, and the SVG 1.1 DTD requires a 'type'
        # attribute on it. Without that the output parses fine but fails
        # validation, so assert it here rather than relying on a manual check.
        templates = config.default_templates()
        frames = [term.TimedFrame(0, 1000, {0: {0: anim.CharacterCell('a')}})]
        palette = theme.palette_from_template(templates['dracula'])

        for name in ['gjm8', 'window_frame', 'progress_bar', 'window_frame_js']:
            with self.subTest(template=name):
                _, filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
                anim.render_animation(frames, (80, 24), filename, templates[name],
                                      palette=palette)
                with open(filename) as svg_file:
                    anim.validate_svg(svg_file)

    def test_render_still_frames_with_palette(self):
        templates = config.default_templates()
        frames = [term.TimedFrame(0, 1000, {0: {0: anim.CharacterCell('a')}})]
        palette = theme.palette_from_template(templates['dracula'])

        directory = tempfile.mkdtemp(prefix='termtosvg_')
        anim.render_still_frames(frames, (80, 24), directory, templates['gjm8'],
                                 palette=palette)

        with open(os.path.join(directory, 'termtosvg_00000.svg'), 'rb') as svg_file:
            root = etree.parse(svg_file).getroot()
        generated = root.find(f'.//{{{anim.SVG_NS}}}style[@id="generated-theme"]')
        self.assertIsNotNone(generated)
        self.assertIn(f'.background {{fill: {palette["background"]};}}', generated.text)

    def test__render_still_frames(self):
        def line(s):
            return dict(enumerate([anim.CharacterCell(c) for c in s]))

        frames = [
            term.TimedFrame(0, 0, {
                1: line('a'),
                2: line('b'),
            }),
            term.TimedFrame(120, 120, {
                2: line('b'),
                3: line('c'),
                4: line('d'),
            }),
            term.TimedFrame(240, 60, {
                2: line('b'),
                3: line('c'),
                4: line('d'),
                5: line('e'),
            }),
            term.TimedFrame(300, 60, {
                2: line('b'),
                3: line('c'),
                4: line('d'),
                5: line('f'),
            }),
        ]

        root = anim._render_preparation((80, 24), TEMPLATE, 9, 17)
        frame_generator = anim._render_still_frames(frames, root, 9, 17)

        def extract_text_content(frame):
            svg_screen_elem = frame.find(f'.//{{{anim.SVG_NS}}}svg[@id="screen"]'
                                         )
            return {elem.text for elem in svg_screen_elem.findall('.//text')}

        expected_texts_by_frame = [
            {'a', 'b'},
            {'b', 'c', 'd'},
            {'b', 'c', 'd', 'e'},
            {'b', 'c', 'd', 'f'},
        ]

        z = itertools.zip_longest(expected_texts_by_frame, frame_generator)
        for count, (texts, frame) in enumerate(z):
            with self.subTest(case=f'Frame #{count}'):
                anim.validate_svg(io.BytesIO(etree.tostring(frame)))
                self.assertEqual(texts, extract_text_content(frame))

    def test__embed_css(self):
        test_cases = [{'animation_duration': None, 'timings': {1: 100, 2: 200}},
                      {'animation_duration': 42, 'timings': {12: 100, 33: 200}} ]
        for args in test_cases:
            with self.subTest(case=args['animation_duration']):
                tree = etree.parse(io.BytesIO(TEMPLATE))
                root = tree.getroot()
                anim._embed_css(root, **args)
                assert b'{{' not in etree.tostring(root)

    def test_validate_svg(self):
        failure_test_cases = [
            '',
            '<svg>',
            '</svg>',
            '</svg></a>',
            None
        ]
        for case in failure_test_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    anim.validate_svg(io.StringIO(case))

        success_test_cases = [
            TEMPLATE,
        ]
        for bytes_svg in success_test_cases:
            with io.BytesIO(bytes_svg) as bstream:
                anim.validate_svg(bstream)
