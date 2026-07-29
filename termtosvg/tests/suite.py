"""Aggregate every TestCase into one module so that the whole suite can be run
with `python -m unittest termtosvg.tests.suite`.

The imports below look unused but are not: unittest collects TestCase classes
from this module's namespace. `__all__` documents that they are re-exports.
"""

from termtosvg.tests.test_anim import TestAnim
from termtosvg.tests.test_asciicast import TestAsciicast
from termtosvg.tests.test_config import TestConf
from termtosvg.tests.test_main import TestMain
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
