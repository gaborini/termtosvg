"""termtosvg — record terminal sessions as lightweight SVG animations."""

# Single source of truth for the version. Read at build time by setuptools
# (see `[tool.setuptools.dynamic]` in pyproject.toml) and at runtime by the
# `--version` flag. A plain literal is used rather than importlib.metadata so
# that starting termtosvg costs no metadata lookup — see the note in config.py
# about guarding startup time.
__version__ = "1.4.0"

__all__ = ["__version__"]
