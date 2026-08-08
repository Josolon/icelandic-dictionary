# Íslenska for Linux and Windows (GoldenDict-ng)

The macOS build is a Dictionary.app bundle. For Linux and Windows the same data
builds as **StarDict**, read by [GoldenDict-ng](https://xiaoyifang.github.io/goldendict-ng/).

You get the same dictionary and, importantly, the same select-a-word-and-look-it-up
workflow macOS gives you natively — GoldenDict calls it **Scan Popup**.

| | |
|---|---|
| Íslenska | 56,382 entries, 529,456 indexed inflected forms |

The indexed forms are BÍN. They are what make this usable at all for Icelandic:
select `hestinum` in a text and you get `hestur`, select `bókanna` and you get
`bók`, select `öbbuðumst` and you get `abbast`. You do not have to work the
lemma out yourself.

## ⚠️ Build it yourself — this one cannot be distributed

The INO lexical data is **CC BY-NC-ND 4.0**. The NoDerivatives clause forbids
distributing converted versions of it, and a StarDict set is a conversion just
as much as a `.dictionary` bundle is. So, exactly as on macOS, there is no
download: you build it on your own machine, for your own use.

`scripts/package_goldendict.sh` deliberately produces a folder rather than a
release zip for that reason. Building it on your Mac and copying the folder to
your own Linux or Windows machine is fine — publishing it is not.

## 1. Build the StarDict set

Follow the main README to fetch the source data and build
`src/IcelandicDictionary.xml`, then:

```bash
./scripts/package_goldendict.sh
```

This writes `dist/goldendict/` — the `.ifo`/`.idx`/`.syn`/`.dict.dz` set plus
`article-style.css`. The body is dictzip-compressed, so the folder is about
20 MB rather than 120 MB.

The build needs nothing but Python 3 — no Dictionary Development Kit, no macOS.
If you have the source data on a Linux box you can build there directly.

## 2. Install GoldenDict-ng

Not the original GoldenDict — the maintained `-ng` fork. Both are packaged
widely; on Linux prefer your distro package or the Flatpak, on Windows use the
installer from the project's releases page.

## 3. Add the dictionary

1. Put `dist/goldendict/` somewhere permanent — the files are read in place,
   not copied.
2. In GoldenDict: **Edit → Dictionaries → Sources → Files → Add…**
3. Select that folder.
4. **Apply**. Indexing takes a minute or two the first time; GoldenDict builds
   its own index cache beside the files.

## 4. Apply the stylesheet

StarDict has no stylesheet slot, so the CSS ships separately. Without it the
entries are readable but unstyled — no paradigm panels, no section headers, no
table borders.

Find your configuration folder:

| OS | Path |
|---|---|
| Linux | `~/.goldendict` or `~/.config/goldendict` |
| Windows | `%APPDATA%\GoldenDict` |
| macOS | `~/Library/Application Support/GoldenDict` |

**Recommended — as an addon style, which leaves your own styling alone:**

Create `styles/Islenska/` in that folder and put `article-style.css` inside it:

```
<config folder>/styles/Islenska/article-style.css
```

Then pick **Islenska** under **Edit → Preferences → Appearances → Style**.

**Alternative:** append the contents of `article-style.css` to the
`article-style.css` sitting directly in the config folder. Everything is scoped
to `.isl-article`, so it will not disturb your other dictionaries — worth
noting, because the class names inside (`.section-block`, `.section-label`)
are generic enough that unscoped they would.

Restart GoldenDict either way — it only reads styles at startup.

The stylesheet includes a dark-mode block via `prefers-color-scheme`, and
shrinks the verb paradigm tables below 520px so they fit popup width.

## 5. Turn on Scan Popup — the Look Up equivalent

**Edit → Preferences → Scan Popup.** Two modes worth knowing:

- **Instant popup** on selection.
- **Scan Flag** — a small icon appears next to your selection and only expands
  into the full article if you click it. Much less intrusive when you are
  reading continuous text.

On **Linux/X11** this is genuinely better than macOS: X11's PRIMARY selection
means merely highlighting a word fires the lookup, with no keystroke at all.

On **Windows** it works from the clipboard via a configurable global hotkey.
Selection-based lookup is reliable; the hover-without-selecting mode is hit or
miss in Chromium- and Electron-based apps.

### If you are on Wayland

Global hotkeys and Scan Flag do not work under native Wayland — the compositor
deliberately withholds the global input access they need. GoldenDict-ng defaults
to native Wayland from 25.12.0 onward for HiDPI reasons, so you may need to opt
out. Their [own Wayland notes](https://xiaoyifang.github.io/goldendict-ng/topic_wayland/)
recommend forcing X11 mode:

```bash
QT_QPA_PLATFORM=xcb goldendict
```

For the Flatpak, set the same variable with Flatseal or `flatpak override`. The
in-window lookup works fine under native Wayland either way — it is only the
select-anywhere-on-screen behaviour that needs XWayland.

## Notes and limitations

- **Icelandic characters.** No fold-stripped duplicates are emitted; GoldenDict
  normalises at search time, so typing `oebbudumst` or `hestinum` without the
  accents still lands on the entry. Selecting real text matches directly.
- **Inline greys.** The generated XML hardcodes `#444`/`#555`/`#666`/`#777` on
  part-of-speech labels and idiom parentheticals. Inline styles beat the
  stylesheet, so the dark-mode block overrides them with `!important`. That is
  the one place the CSS shouts, and it is why the dark theme reads correctly.
- **Disk size.** The body ships as `.dict.dz` — dictzip, which is ordinary gzip
  plus a chunk table that lets GoldenDict seek to a single article instead of
  inflating the whole file. 121 MB becomes 9 MB installed.

## Attribution

Lexical data from Stofnun Árna Magnússonar / CLARIN Iceland (CC BY-NC-ND 4.0).
Morphology from BÍN, Miðeind ehf. — see `CREDITS.md` for BÍN's required verbatim
credit line and the CC BY-SA 4.0 terms. The build scripts are MIT.

## Verifying a build

`scripts/verify_stardict.py` reads a built set back independently of the writer
and checks sort order, offset integrity and UTF-8 validity:

```bash
python3 scripts/verify_stardict.py dist/goldendict/Islenska --lookup hestinum
```

The check that matters is that an *inflected* form resolves, not the lemma.
