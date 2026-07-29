# Render-time colour themes — design

**Date:** 2026-07-29
**Status:** approved

## Problem

Colour and terminal chrome are currently welded together. The only way to change
an animation's palette is to author or pick a whole SVG template, which is why
the project ships sixteen of them with substantial overlap — `powershell`,
`window_frame_powershell` and `window_frame` differ mostly in chrome, not colour.

Meanwhile the machinery for a palette already exists and is unused.
`AsciiCastV2Theme` validates a foreground colour, a background colour and an 8-
or 16-entry palette, rejecting malformed hex. Nothing consumes it: `record()`
always emits `theme=None`, and `timed_frames()` reads only `width`, `height` and
`idle_time_limit` from the header. An asciinema recording that carries its own
theme has that theme silently discarded.

## Goal

Make colour selectable at render time, independently of the template, without
changing any existing output.

## Findings that constrain the design

These were measured against the current tree, not assumed.

1. **The palette lives in `user-style`, and that element holds more than
   colour.** Template structure is:

   ```
   <svg id="terminal">
     <defs>
       <style id="generated-style">   written by termtosvg (font, keyframes)
       <style id="user-style">        template palette + template's own rules
     <svg id="screen">
   ```

   `progress_bar` additionally keeps `@keyframes progress-bar-animation` and
   `#progress-bar` in `user-style`; `window_frame_js` keeps `#play-button`,
   `#pause-button`, `#wide_track`, `#track`, `#slider_button` and `#timer` there.
   Overwriting `user-style` would therefore break the progress bar and the
   JavaScript player controls. The theme must be appended, not substituted.

2. **All 16 templates expose the same 18-rule colour surface** —
   `.color0`–`.color15`, `.foreground`, `.background` — and a regex extraction
   yields 18/18 from every one of them. The built-in palettes are already in the
   repository; no new data file is needed.

3. **Three of the five example casts carry a theme** (`awesome`, `colors`,
   `unittest`, all Solarized dark). Honouring cast themes by default would
   therefore shift 48 of the 80 baseline animations and silently recolour the
   published gallery on the next Pages deploy. This is what makes opt-in the
   right default rather than a matter of taste.

## Design

### Injection

A new element is appended immediately after `user-style` inside `<defs>`:

```
<style id="generated-theme">   only the colour rules
```

Being last in document order, it wins over `user-style` at equal specificity.
The ID-based rules noted in finding 1 have higher specificity and are unaffected.

### Command line

`--theme` is added to the `render` sub-command and to the implicit
record-and-render form, mirroring how `-t/--template` is already wired. It is not
added to `record`, which renders nothing.

The option is long-only. `-t` already means template, and a `-T` shorthand for a
neighbouring colour concept is too easy to mistype into the wrong one.

| Form | Meaning |
| --- | --- |
| `--theme dracula` | name of a built-in palette |
| `--theme ./mine.json` | palette file |
| `--theme auto` | take the palette from the cast header |

Built-in names are the sixteen template names; the palette is extracted from that
template's `user-style` at run time, so it cannot drift from the template.

The argument is resolved in a fixed order, so the meaning of a given string never
depends on the working directory: the literal `auto` first, then a built-in name,
then a file path. This mirrors `validate_template`, which already prefers a
built-in template name over a same-named file on disk. A file that happens to be
called `auto` or `dracula` must therefore be given with a path separator, for
example `./dracula`.

The file format is the asciicast `theme` object — `fg`, `bg`, and `palette` as a
colon-separated list — because `AsciiCastV2Theme` already validates exactly that
shape, and it lets a theme object be copied straight out of a `.cast` header.

### Precedence

```
explicit --theme  >  --theme auto (cast header)  >  template palette
```

With no `--theme`, nothing changes. That is what keeps the 267-artifact
byte-identity result and the published gallery's colours intact.

### Edge cases

- **`--theme auto` on a cast with no theme:** warn on stderr and fall back to the
  template palette. Failing hard would be hostile to batch use; falling back
  silently would hide that the request was not honoured.
- **8-colour palette:** emit rules for `color0`–`color7`, `foreground` and
  `background` only, leaving `color8`–`color15` to the template. Synthesising
  bright variants would be guesswork.
- **Unknown name that is also not a readable file:** error listing the valid
  built-in names.

### Code placement

A new module, `termtosvg/theme.py`, with three independently testable functions:

- `palette_from_template(template: bytes) -> dict` — extract from `user-style`
- `palette_from_theme(theme: AsciiCastV2Theme) -> dict` — from the cast/file shape
- `theme_css(palette: dict) -> str` — render the rules

`anim.py` gains only the insertion of the `generated-theme` element. The module is
separate because `anim.py` is already ~660 lines and theme handling is its own
responsibility.

## Non-goals

- No new palette data files; built-in palettes come from the templates.
- No synthesised bright colours for 8-entry palettes.
- No change to the template format or to `template_settings`.
- No `--theme` on `record`.

## Verification

1. **With no `--theme`, all 267 baseline artifacts stay byte-identical.** This is
   the primary test: it is what proves the feature is genuinely opt-in.
2. `--theme dracula` on a given template produces the same colours as the
   `dracula` template does, with the original template's chrome preserved.
3. `--theme auto` on the three theme-carrying casts produces Solarized colours.
4. The non-colour rules in `progress_bar` and `window_frame_js` survive theme
   injection. This was the riskiest point in the design and gets an explicit test.
5. Themed output still validates against the SVG 1.1 DTD.
6. Unit tests for extraction, parsing, validation failure modes, and the
   8-colour path.
