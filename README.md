# personal-site

Steven Ma's personal site. Simple and quiet: plain HTML and one CSS file. No framework, no build step, no JavaScript.

## Preview

    open index.html

Or serve it, so links behave exactly as they will online:

    python3 -m http.server 8000    # then open http://localhost:8000

## Walkthrough

- `index.html` is the home page: name and nav on the left, About, Experience and Projects on the right. Each entry is one `<li class="item">`.
- `projects/*.html` and `work/txdot.html` are the write-ups. Each one follows the same order: the problem, what was built, the decisions, the results. That order is what an interviewer walks through, so each page doubles as interview notes.
- `style.css` holds every visual rule. The colours are the five variables at the top. Dark mode swaps them in the `prefers-color-scheme` block. Change a colour there, never inline.
- `.thumb-todo` (home) and `.figure-todo` (write-ups) boxes are placeholders. Replace each with `<img src="../img/name.png" alt="...">` inside the same `<figure>`, and add a `<figcaption>`.
- `.nojekyll` tells GitHub Pages to serve the files as they are.

## Editing the pixel icons

    python3 tools/pixel_icons.py    # grids live in the script; writes img/icons/*.svg

Each icon is a 16x16 grid of `#` (ink), `-` (paper fill) and `.` (transparent). Show them at 16 or 32 px only, so every pixel stays square.

## Regenerating the link-preview image

    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
      --virtual-time-budget=5000 --window-size=1200,630 --screenshot="$PWD/img/og.png" "file://$PWD/index.html"

Run it from this folder after any change to the top of the home page. Update the "Last updated" date in `index.html` at the same time.

## Regenerating the market chart

    python3 tools/make_market_chart.py    # reads tools/tes_lgd_2026-08-29.csv, writes img/market-tes-lgd.svg

The CSV was pulled read-only from the platform's archived SQLite snapshot; the query is in the script's docstring.

## Adding a project

1. Copy `projects/market-data.html` to `projects/<name>.html`.
2. Keep the four headings. Fill them from the newest résumé variant only.
3. Add one `.entry` block to `index.html` under Projects.

## Live

https://stevenmaswim.github.io/
