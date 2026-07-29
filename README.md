# termtosvg

**Record a terminal session and get a standalone SVG animation you can drop into any web page.**

No video encoding, no player to embed, no JavaScript. The output is a single
vector file where the text is still text.

[![CI](https://github.com/gaborini/termtosvg/actions/workflows/ci.yml/badge.svg)](https://github.com/gaborini/termtosvg/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/termtosvg-ng.svg)](https://pypi.org/project/termtosvg-ng/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)

Maintained by **[Gabor Lepsenyi](https://gaborl.hu)** · [gaborl.hu](https://gaborl.hu)

![Example](./docs/examples/awesome_window_frame_powershell.svg)

- 🖼️ [Gallery of examples](https://nbedos.github.io/termtosvg/pages/examples.html)
- 🎨 [Gallery of templates](https://nbedos.github.io/termtosvg/pages/templates.html)
- 📖 [Manual page](man/termtosvg.md) · [Writing templates](man/termtosvg-templates.md)

---

## Why SVG

The animation above is a **26-second session at 82×19 characters, in 50 KB**. That
is one file, and the properties that come with it are not available from a
screen recording:

| | |
|---|---|
| **The text is real text** | Readers can select, copy and search the commands in your demo. Search engines index them. |
| **Resolution independent** | Vector output stays crisp on a 4K display and at any zoom level. There is no "recorded at the wrong size" problem. |
| **Themeable after the fact** | Colours are CSS classes, not baked pixels. Restyle a finished animation by editing its stylesheet. |
| **Self-contained** | One `.svg` file. No player script, no external assets, no network requests. Works from `file://`. |
| **Diff-friendly enough to commit** | Plain XML in your repository, embedded with a relative Markdown link. |

## Installation

termtosvg runs on Linux, macOS and the BSDs, and requires **Python 3.10 or later**.

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install termtosvg-ng
```

Three equivalent ways to run it — use whichever reads best to you:

```shell
termtosvg          # the historical command name
termtosvg-ng       # matches the name you installed
python3 -m termtosvg
```

> [!IMPORTANT]
> **Why the install name carries `-ng`.** The plain `termtosvg` name on PyPI
> belongs to the original author and last shipped **1.1.0** in January 2020. That
> release predates the removal of `pkg_resources` from setuptools, so on Python
> 3.12 and later it fails at import with `ModuleNotFoundError: No module named
> 'pkg_resources'` — every command, `--version` included, dies immediately.
> `termtosvg-ng` is the same tool with that fixed.
>
> The `termtosvg` command is kept so that existing scripts, tutorials and distro
> packaging continue to work unchanged. The import package is `termtosvg` as well.

<details>
<summary><b>Installing straight from source</b></summary>

```shell
pip install git+https://github.com/gaborini/termtosvg.git@develop
```

</details>

<details>
<summary><b>OS packages maintained by the community</b></summary>

These package the original `termtosvg` distribution, so they carry 1.1.0 and the
caveat above applies to them.

| OS | Repository | Command |
|---|---|---|
| Arch Linux | [extra/termtosvg](https://archlinux.org/packages/extra/any/termtosvg/) | `pacman -S termtosvg` |
| FreeBSD | [graphics/py-termtosvg](https://www.freshports.org/graphics/py-termtosvg) | |
| Gentoo | [media-gfx/termtosvg](https://packages.gentoo.org/packages/media-gfx/termtosvg) | `emerge media-gfx/termtosvg` |
| macOS | [Homebrew](https://formulae.brew.sh/formula/termtosvg) | `brew install termtosvg` |
| NixOS | [nixpkgs](https://github.com/NixOS/nixpkgs/blob/master/pkgs/tools/misc/termtosvg/) | |
| OpenBSD | [graphics/termtosvg](https://github.com/openbsd/ports/tree/master/graphics/termtosvg) | |

</details>

## Quick start

Start recording. You land in a subshell — type as you normally would.

```console
$ termtosvg
Recording started, enter "exit" command or Control-D to end
```

Leave the shell to finish:

```console
$ exit
Recording ended, file is /tmp/termtosvg_exp5nsr4.svg
```

Open it in a browser to watch it, then embed it with a relative link:

```markdown
![My demo](./demo.svg)
```

## How it works

termtosvg separates *capturing* from *drawing*, which is what makes the output
editable and reproducible:

```
                  ┌──────────────┐                   ┌──────────────┐
   your shell ──► │    record    │ ──► .cast file ──► │    render    │ ──► .svg
                  └──────────────┘   (asciicast v2)   └──────────────┘
                                            ▲                ▲
                                     hand-editable      SVG template
                                     timings & text     (theme + chrome)
```

Running `termtosvg` with no sub-command does both in one pass. Splitting them is
useful because the intermediate `.cast` file is plain text: you can fix a typo,
retime a pause, or re-render the same recording with a different theme without
performing the session again.

```shell
termtosvg record demo.cast          # capture only
termtosvg render demo.cast out.svg  # draw, as often as you like
```

Because `render` reads the [asciicast](https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md)
format (v1 and v2), it also renders **recordings made with
[asciinema](https://asciinema.org/)**.

## Command line reference

Three forms. The default records *and* renders in one go:

```
termtosvg [output_path] [-c COMMAND] [-D DELAY] [-g GEOMETRY] [-m MIN_DURATION]
          [-M MAX_DURATION] [-s] [-t TEMPLATE] [-v] [-h]

termtosvg record [output_path] [-c COMMAND] [-g GEOMETRY] [-v] [-h]

termtosvg render input_file [output_path] [-D DELAY] [-m MIN_DURATION]
                 [-M MAX_DURATION] [-s] [-t TEMPLATE] [-h]
```

Not every option applies to every form — `render` takes its geometry from the
recording, so it has no `-g`:

| Option | Default | default form | `record` | `render` | What it does |
|---|---|:-:|:-:|:-:|---|
| `-c, --command COMMAND` | `$SHELL`, else `sh` | ✅ | ✅ | — | Program to record, with arguments: `-c 'ipython --pprint'`. |
| `-g, --screen-geometry COLSxROWS` | your terminal, else `80x24` | ✅ | ✅ | — | Screen size to record at, e.g. `82x19`. |
| `-t, --template TEMPLATE` | `powershell` | ✅ | — | ✅ | Built-in name (see below) or a path to your own template. |
| `-m, --min-frame-duration MS` | `1` | ✅ | — | ✅ | Merge frames shorter than this. Raise it to shrink output from commands that redraw constantly. |
| `-M, --max-frame-duration MS` | none¹ | ✅ | — | ✅ | Clamp long pauses, so thinking time does not stall the animation. |
| `-D, --loop-delay MS` | `1000` | ✅ | — | ✅ | Pause before the animation loops. |
| `-s, --still-frames` | off | ✅ | — | ✅ | Write one SVG per frame into a directory instead of one animation. |
| `-v, --version` | | ✅ | ✅ | — | Print the version. |
| `-h, --help` | | ✅ | ✅ | ✅ | Print usage. |

¹ Unless the recording's header carries `idle_time_limit`, which is then used.

Durations accept a bare integer or an `ms` suffix — `-m 17` and `-m 17ms` are the
same. `output_path` is optional everywhere; a temporary file is generated when it
is omitted (a *directory*, with `--still-frames`).

## Templates

A template supplies the colour theme, the font, any window chrome, and how the
animation is driven. Pass one by name with `-t`:

| Template | Look | Animation |
|---|---|:-:|
| `powershell` *(default)* | Windows PowerShell palette | CSS |
| `base16_default_dark` | Base16 default dark | CSS |
| `dracula` | Dracula | CSS |
| `gjm8` | Understated dark, no chrome | CSS |
| `gjm8_single_loop` | `gjm8`, plays once instead of looping | CSS |
| `gjm8_play` | `gjm8` with a play-icon drawn over the screen | CSS |
| `progress_bar` | Adds a progress bar tracking the animation | CSS |
| `putty` | PuTTY palette | CSS |
| `solarized_dark` / `solarized_light` | Solarized | CSS |
| `terminal_app` | macOS Terminal.app | CSS |
| `ubuntu` | Ubuntu terminal | CSS |
| `xterm` | xterm palette | CSS |
| `window_frame` | Adds a terminal window frame | CSS |
| `window_frame_powershell` | Window frame, PowerShell palette | CSS |
| `window_frame_js` | Window frame with play/pause buttons | **JavaScript** |

### Embedding, and one caveat worth knowing

Fifteen of the sixteen templates animate through pure CSS, so they play when
loaded as an ordinary image — including from a Markdown `![...]()` in a GitHub
README.

`window_frame_js` is the exception: its play/pause controls need JavaScript, and
browsers do not execute scripts inside an SVG loaded via `<img>`. Embed that one
with `<object>` or `<iframe>`, or link to the file directly:

```html
<object type="image/svg+xml" data="demo.svg"></object>
```

Writing your own template is documented in
[termtosvg-templates(5)](man/termtosvg-templates.md). The shipped templates under
[`termtosvg/data/templates/`](termtosvg/data/templates) are the best starting
point — copy one and edit its palette.

## Recipes

```shell
# Record a specific program instead of a shell
termtosvg -c 'ipython --pprint' demo.svg

# Pin the geometry so the animation is not tied to your window size
termtosvg -g 82x19 demo.svg

# Tame a chatty command: coalesce sub-17ms frames, cap pauses at 2s
termtosvg -m 17 -M 2000 demo.svg

# Re-theme an existing recording — no need to perform it again
termtosvg render demo.cast dracula.svg -t dracula

# Render someone else's asciinema recording
termtosvg render downloaded.cast out.svg

# Still frames, e.g. to pick a thumbnail
termtosvg render demo.cast frames/ --still-frames

# Two seconds of breathing room between loops
termtosvg -D 2000 demo.svg
```

## Compatibility

| | |
|---|---|
| **Python** | 3.10 – 3.14 |
| **Operating systems** | Linux, macOS, FreeBSD, OpenBSD (anything with a POSIX pty) |
| **Not supported** | Windows, which has no `pty` module. WSL works. |
| **Dependencies** | [pyte](https://github.com/selectel/pyte) (terminal emulation), [lxml](https://lxml.de/) (SVG), [wcwidth](https://github.com/jquast/wcwidth) (wide-character widths) |

Windows *shells* can still be recorded — the `powershell` template exists for
styling such recordings — but termtosvg itself must run on a POSIX host.

## Development

```shell
make install   # editable install with dev extras
make tests     # unit tests with coverage
make lint      # ruff
make build     # sdist + wheel into dist/
make html      # regenerate the example gallery
```

`make lint` runs `ruff check`. The formatter is intentionally *not* enforced;
see the note in [`pyproject.toml`](pyproject.toml) for why.

Rendering is deterministic, which makes it easy to prove a change did not alter
output: render the casts in [`docs/examples/casts/`](docs/examples/casts) before
and after, and compare bytes.

Bug reports and pull requests are welcome at
[github.com/gaborini/termtosvg](https://github.com/gaborini/termtosvg/issues).

## Maintainer

**[Gabor Lepsenyi](https://gaborl.hu)** — [gaborl.hu](https://gaborl.hu) ·
[github.com/gaborini](https://github.com/gaborini)

Licensed under the [BSD 3-Clause License](LICENSE).

<sub>Originally created by Nicolas Bedos, who wrote the recorder, the rendering
engine and the template system. Copyright is retained as required by the
license.</sub>
