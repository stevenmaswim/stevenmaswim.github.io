# Where the engine code comes from

`demo/orderbook/` is copied unchanged from github.com/stevenmaswim/order-book at commit
`a7e19ca177e8c505721f9cd299e4ae9f709d4073` (2026-07-28): `__init__.py`, `book.py`,
`engine.py`, `models.py`. `display.py` is left out; it only draws charts with matplotlib.

The browser runs these files with Pyodide (CPython compiled to WebAssembly).
`demo/bridge.py` is the only new Python: it calls the engine and returns JSON for the page.

To update after the engine changes, copy the four files again and change the commit above.
