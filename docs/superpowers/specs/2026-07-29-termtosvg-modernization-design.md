# termtosvg modernization — design

**Date:** 2026-07-29
**Status:** approved

## Problem

The project was last touched in June 2020 and declares `python_requires='>=3.5'`.
On a current interpreter it does not merely warn — it fails to start at all.

Measured on Python 3.14.4, fresh virtualenv, `pip install .`:

```
ModuleNotFoundError: No module named 'pkg_resources'
  termtosvg/main.py:9  import pkg_resources
```

`pkg_resources` is no longer shipped by setuptools (verified absent in
setuptools 83.0.0). Because `main.py` imports it at module scope, every entry
point dies: `--version`, `record`, `render`, and `python -m termtosvg`.

The rendering engine itself is healthy. With `pkg_resources` stubbed out, the
full pipeline runs clean against current dependencies (lxml 6.1.1, pyte 0.8.2,
wcwidth 0.8.2) and all 25 unit tests pass on Python 3.14. The rot is confined
to the edges: packaging, CI, and a handful of deprecated API calls.

## Goal

Bring the project to current-era standards without altering what it does.

## Invariants

"Preserve functionality" is treated as measurable, not aspirational.

1. **The CLI surface is unchanged.** Same three sub-commands (implicit,
   `record`, `render`), same eight options with identical short and long names,
   same defaults (`--template powershell`, `-m 1`, `-D 1000`, no `-M` cap), same
   `$SHELL` fallback, same `python -m termtosvg` entry.
2. **Generated SVG output is byte-identical.** This is the primary regression
   oracle. See Verification.
3. **Template contract is untouched.** The 16 bundled templates and the
   `termtosvg` XML namespace (`template_settings`, `screen_geometry`) stay as
   they are, so user-authored templates keep working.

## Non-goals

- No new features, no CLI additions.
- No pytest migration. The 25 `unittest` tests pass; swapping runners is churn
  without benefit.
- No mypy / full static typing. Type hints go on public functions only.
- No `pathlib` rewrite of the `pty`/`fcntl`/`termios` layer, where raw file
  descriptors are the point.
- No rewrite of `docs/` site content beyond link and pipeline updates.

## Design

### Source changes

| File | Change | Rationale |
| --- | --- | --- |
| `main.py` | drop `pkg_resources`, read `termtosvg.__version__` | The blocker. A module-level literal is used rather than `importlib.metadata` because `config.py` already documents that startup cost is guarded — `pkg_resources` alone added 150 ms. A literal costs nothing. |
| `asciicast.py` | `typing.Iterable` → `collections.abc.Iterable` | `isinstance()` against `typing` aliases is deprecated. |
| `term.py` | `typing.Iterator` → `collections.abc.Iterator`; delegate with `yield from` | Same deprecation; `yield from` also preserves the generator's return value. |
| `anim.py` | `Element.getchildren()` → `list(element)` | Deprecated in lxml and slated for removal. Still functional on 6.1.1, but it is a timed bomb. |
| all | `.format()` → f-strings; type hints on public functions | Readability. Private helpers are left unannotated to keep the diff bounded. |
| `config.py` | keep `pkgutil.get_data` | `importlib.resources` would be slower here. The existing startup-time trade-off is deliberate engineering, not rot. |

### Packaging

`setup.py` and `MANIFEST.in` are replaced by a PEP 621 `pyproject.toml` on the
**setuptools** backend. Hatchling was considered and rejected: this package is
built by distro packagers (Arch, FreeBSD, Gentoo, NixOS, Homebrew) and
setuptools is the lowest-friction choice for them.

- `requires-python = ">=3.10"`; classifiers for 3.10 through 3.14.
- `scripts/termtosvg` becomes `[project.scripts] termtosvg = "termtosvg.main:main"`.
  The command name is identical; only the mechanism modernizes.
- Package data (templates, DTD) declared via `[tool.setuptools.package-data]`.
- Version lives in exactly one place: a literal in `termtosvg/__init__.py`, read
  by `dynamic = ["version"]`.
- `1.1.0` → `1.2.0`. The Python floor raise and the entry-point change justify a
  minor bump.
- New `.gitignore` — the repo currently has none.

### CI/CD

`.travis.yml` is deleted. Travis is effectively dead for open source, and the
file additionally carries three expired encrypted credentials that have no
business sitting in the repository.

- `ci.yml` — matrix of ubuntu + macos across Python 3.10–3.14; ruff, unittest,
  coverage.
- `release.yml` — on tag: `python -m build`, publish to PyPI via **trusted
  publishing** (no stored API token), attach man pages to the GitHub release.
- `pages.yml` — build the Pelican gallery and deploy with current
  `actions/deploy-pages`.
- `pylint` → `ruff` for both linting and formatting, configured in `pyproject.toml`.
- `Makefile` refreshed: `python setup.py sdist` → `python -m build`.

### README

Tone is upstream-neutral: the document describes termtosvg as a tool and does
not editorialize about fork status. Nicolas Bedos is credited factually in a
Credits section. The upstream "no longer maintained" banner is removed because
it describes a different repository; no maintenance promise replaces it.

Badges point at URLs that actually resolve for this repository, since a badge
aimed at an archived repo would render broken.

Substantive information gains over the current README:

- A complete CLI reference table with defaults. The current README has none and
  defers entirely to the man page.
- A "why SVG rather than GIF" section — the project's real differentiator:
  selectable text, roughly an order of magnitude smaller files, crisp at any
  zoom, no JavaScript required.
- Template gallery with inline previews.
- Workflow recipes: rendering asciinema casts, still frames, embedding in a
  README.
- Compatibility table, distro package table, development setup.

One structural note: this spec lives under `docs/`, which is the root of the
gh-pages site. `docs/superpowers/` is therefore excluded from the Pages
workflow so specs are not published to the public site.

## Verification

Ordering matters. The baseline is captured from unmodified code *before* any
edit lands.

1. **Baseline** — 267 artifacts rendered from the pristine tree: 5 example casts
   x 16 built-in templates (80 animations), still-frame output for two
   templates, and three non-default `--min/--max/--loop-delay` combinations to
   exercise the frame-coalescing paths. Recorded as a SHA-256 manifest.
2. **Oracle validity** — the renderer was confirmed deterministic: two
   independent runs of the baseline produced 267/267 byte-identical files. Byte
   comparison is therefore a trustworthy signal rather than a source of false
   alarms.
3. **Post-change** — regenerate all 267 artifacts and diff against the manifest.
   Any mismatch is a defect, not an acceptable variation.
4. **Tests** — 25/25 unit tests green.
5. **Install** — clean virtualenv, `pip install .`, then `termtosvg --version`
   and a real render must succeed with no setuptools present.
