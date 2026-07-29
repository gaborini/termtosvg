# Changelog
## Version 1.4.1 (2026-07-29)

* **Fix a crash on recordings with a bright background colour.** pyte 0.8.2
  ships `BG_AIXTERM[105] = 'bfightmagenta'`, a typo for `'brightmagenta'`.
  Rendering raised `ValueError: Invalid background color` as soon as a character
  cell was actually painted with a bright magenta background — SGR 105 — which no
  user could work around. termtosvg now rebuilds both AIXTERM tables from its own
  colour names, the same stance it already takes for `FG_BG_256`. Present in every
  release before this one.


## Version 1.4.0 (2026-07-29)

* **Add `--theme` to choose colours independently of the template.** Previously
  the palette and the terminal chrome were welded together in a template file,
  which is why sixteen templates ship with substantial overlap. `--theme` accepts
  the name of a built-in template to borrow its palette, a path to a JSON palette
  file, or `auto` to use the palette stored in the recording.
* Honour the `theme` attribute of asciicast files when `--theme auto` is given.
  The attribute was previously parsed and validated but never used for rendering,
  so asciinema recordings had their colours silently discarded.
* Themes are written to a new `<style id="generated-theme">` element appended
  after the template's own `user-style`, rather than replacing it. Two bundled
  templates keep non-colour rules there — `progress_bar` its bar animation and
  `window_frame_js` its player controls — and those keep working.
* Rendering without `--theme` is unchanged: all 267 reference artifacts remain
  byte-identical.


## Version 1.3.0 (2026-07-29)

* **Add a `termtosvg-ng` command alongside `termtosvg`.** Both names run the same
  program. The package installs as `termtosvg-ng`, so being able to invoke it by
  that name removes the mismatch; `termtosvg` is kept because renaming it would
  break every existing script, tutorial and distro package that calls it.
* Usage and help text now reflect the name the program was invoked under, instead
  of always claiming to be `termtosvg`. Output for `termtosvg` itself is
  unchanged, and `python -m termtosvg` still reports the canonical name.


## Version 1.2.0 (2026-07-29)

Compatibility and maintenance release. The command line interface, the template
format and the generated SVG output are unchanged: all 16 bundled templates
render byte-identical animations to 1.1.0.

* **Published on PyPI as `termtosvg-ng`.** The `termtosvg` distribution name
  belongs to the original author and still serves 1.1.0. Install with
  `pip install termtosvg-ng`; the import package and the installed command remain
  `termtosvg`, and no code looks the distribution name up at runtime.

* **Fix startup failure on Python 3.12 and later.** `pkg_resources` is no longer
  shipped by setuptools, and it was imported at module scope, so every command —
  `record`, `render` and even `--version` — failed with `ModuleNotFoundError`.
  The version is now read from `termtosvg.__version__`.
* Require Python >= 3.10; test against 3.10 through 3.14.
* Replace deprecated APIs: `isinstance()` against `typing` aliases now uses
  `collections.abc`, and lxml's removed-in-future `Element.getchildren()` is gone.
* Move packaging to `pyproject.toml` (PEP 621). The `termtosvg` command is now a
  console entry point rather than an installed script; the command name and
  behaviour are the same.
* Replace the Travis pipeline with GitHub Actions, and publish to PyPI through
  trusted publishing instead of a stored token.
* Fix two silent test defects: `test__read_v1_records` zipped over a JSON
  *string*, truncating the comparison to its characters and passing even if no
  records were decoded; `test_default_templates` asserted nothing at all.


## Version 1.1.0 (2020-01-18)

* Allow invocation through runpy (issue [#111](https://github.com/nbedos/termtosvg/issues/111))


## Version 1.0.0 (2019-11-16)

* Add more templates that follow the standard color palette for terminal colors. Change default template to 'powershell'. (issue [#105](https://github.com/nbedos/termtosvg/issues/105))


## Version 0.9.0 (2019-07-06)

* Switch from SMIL animations to animations created via CSS or the Web Animations API (issues [#75](https://github.com/nbedos/termtosvg/issues/75),
[#86](https://github.com/nbedos/termtosvg/issues/86),
[#94](https://github.com/nbedos/termtosvg/issues/94))
* Add CLI option `--loop-delay` for customization of the delay between two loops of the animation ([issue #95](https://github.com/nbedos/termtosvg/issues/95))
* Fix text length computation involving wide Unicode characters ([issue #96](https://github.com/nbedos/termtosvg/issues/96))
* Fix invalid type restriction for the timeout parameter of asciicast v2 headers ([issue #97](https://github.com/nbedos/termtosvg/issues/97))


## Version 0.8.0 (2019-01-20)

* Implement still frame rendering ([issue #50](https://github.com/nbedos/termtosvg/issues/50))
* Properly handle zero width characters ([issue #89](https://github.com/nbedos/termtosvg/issues/89))
* Remove unused options for record CLI subcommand (min & max-frame-duration)

## Version 0.7.0 (2018-12-09)

* Add --command CLI option ([issue #83](https://github.com/nbedos/termtosvg/issues/83), [pull request #84](https://github.com/nbedos/termtosvg/pull/84))
* Add unit tests to package ([pull request #77](https://github.com/nbedos/termtosvg/pull/77))
* Move termtosvg-template man page from section 1 to 5 ([issue #80](https://github.com/nbedos/termtosvg/issues/80))

## Version 0.6.0 (2018-11-04)

* Add base16-default-dark color theme ([pull request #57](https://github.com/nbedos/termtosvg/pull/57))
* Add manual pages in groff format ([issue #53](https://github.com/nbedos/termtosvg/issues/53))
* Add support for italic, underscore and strikethrough style attributes (pull requests
[#60](https://github.com/nbedos/termtosvg/pull/60) and [#62](https://github.com/nbedos/termtosvg/pull/62))
* Add --min-frame-duration command line option ([issue #33](https://github.com/nbedos/termtosvg/issues/33))
* Add --max-frame-duration command line option
* Remove unused --verbose command line option
* Reduce file size by optimizing the use of SVG attributes


## Version 0.5.0 (2018-08-05)

* Add support for hidden cursors
* Add support for SVG templates (custom color themes, terminal UI, animation controls...) as
discussed in [issue #53](https://github.com/nbedos/termtosvg/issues/53)
* Remove --font and --theme options, as well as the termtosvg.ini configuration file
* Fix select() deadlock on BSD and macOS ([issue #18](https://github.com/nbedos/termtosvg/issues/18))


## Version 0.4.0 (2018-07-08)

* Add support for rendering recordings in asciicast v1 format ([issue #15](https://github.com/nbedos/termtosvg/issues/15))
* Add support for bold text rendering ([pull request #35](https://github.com/nbedos/termtosvg/pull/35))
* Use temporary file for logging ([issue #12](https://github.com/nbedos/termtosvg/issues/12))


## Version 0.3.0 (2018-07-02)

* Add support for a font option ([pull request #3](https://github.com/nbedos/termtosvg/pull/3))
* Drop support for color information gathering from Xresources (fixes [issues #5](https://github.com/nbedos/termtosvg/issues/5) and [#6](https://github.com/nbedos/termtosvg/issues/6))
* Add configuration file in INI format for defining preferred font and color theme, and for adding or modifying color themes


## Version 0.2.2 (2018-06-25)

* Prevent crash when no Xresources string can be retrieved from the Xserver ([issue #2](https://github.com/nbedos/termtosvg/issues/2))


## Version 0.2.1 (2018-06-25)

* Fallback to non bright colors when using an 8 color palette ([issue #1](https://github.com/nbedos/termtosvg/issues/1))


## Version 0.2.0 (2018-06-24)

* Add support for the asciicast v2 recording format
* Add subcommands for independently recording the terminal session and rendering the SVG animations


## Version 0.1.0 (2018-06-16)
Initial release!
