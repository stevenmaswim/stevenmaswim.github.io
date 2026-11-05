"""The only new Python in the demo: a thin layer between the page and the engine.

The engine in demo/orderbook/ is the unchanged code from the order-book repo.
Everything here returns JSON strings, so the JavaScript side stays simple.
"""

import json
import random

from orderbook import MatchingEngine, OrderType, Side

engine = MatchingEngine()
rng = random.Random(42)


def submit(side: str, kind: str, qty: int, price: float | None = None) -> str:
    """Submit one order. Errors from the engine come back as {"error": ...}."""
    try:
        order, fills = engine.submit(
            Side[side],
            OrderType[kind],
            int(qty),
            price=None if kind == "MARKET" else round(float(price), 2),
        )
    except (ValueError, KeyError) as exc:
        return json.dumps({"error": str(exc)})
    return json.dumps({
        "id": order.order_id,
        "status": order.status.value,
        "filled": order.filled,
        "remaining": order.remaining,
        "fills": [[t.price, t.quantity] for t in fills],
    })


def random_order() -> str:
    """Same mix as the repo's demo traders: 90% limit orders priced 99.50-100.50."""
    side = "BUY" if rng.random() < 0.5 else "SELL"
    qty = rng.randint(1, 100)
    if rng.random() < 0.90:
        return submit(side, "LIMIT", qty, rng.randint(9950, 10050) / 100)
    return submit(side, "MARKET", qty)


def warm_up(n: int = 400) -> None:
    """Fill the book so the first view is not empty."""
    for _ in range(n):
        random_order()


def state(levels: int = 8) -> str:
    snap = engine.depth_snapshot(levels)
    trades = engine.trades()
    return json.dumps({
        "bids": snap["bids"],
        "asks": snap["asks"],
        "best_bid": engine.best_bid(),
        "best_ask": engine.best_ask(),
        "orders": len(engine.orders()),
        "trade_count": len(trades),
        "trades": [[t.trade_id, t.price, t.quantity] for t in trades[-10:]][::-1],
    })


def reset() -> None:
    global engine, rng
    engine = MatchingEngine()
    rng = random.Random(42)
