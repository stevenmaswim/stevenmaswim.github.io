"""MatchingEngine: thread-safe facade over OrderBook.

ONE coarse RLock around submit(), cancel(), and every read that must be
consistent. book.py stays lock-free single-threaded logic. Rationale:
correctness first, then measure — the lock is not the bottleneck at this
throughput, and a coarse lock is honest under the GIL.
"""
from __future__ import annotations

import itertools
import threading

from .book import OrderBook
from .models import Order, OrderType, Side, Trade


class MatchingEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._book = OrderBook()
        self._trades: list[Trade] = []
        self._order_ids = itertools.count(1)

    # ------------------------------------------------------------------ #
    # Write API
    # ------------------------------------------------------------------ #

    def submit(
        self,
        side: Side,
        order_type: OrderType,
        quantity: int,
        price: float | None = None,
    ) -> tuple[Order, list[Trade]]:
        """Submit an order; returns (order, trades executed on arrival)."""
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError(f"quantity must be a positive int, got {quantity!r}")
        if order_type is OrderType.LIMIT:
            if price is None or price <= 0:
                raise ValueError(f"LIMIT order requires a positive price, got {price!r}")
        elif price is not None:
            raise ValueError("MARKET order must not carry a price")
        # Order-id and seq assignment must be atomic with book insertion: if
        # another thread interleaved between id/seq assignment and the heap
        # push, seq order would no longer match insertion order and FIFO time
        # priority would break.
        with self._lock:
            order = Order(
                order_id=next(self._order_ids),
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
            )
            trades = self._book.submit(order)
            self._trades.extend(trades)
            return order, trades

    def cancel(self, order_id: int) -> bool:
        with self._lock:
            return self._book.cancel(order_id)

    # ------------------------------------------------------------------ #
    # Read API (consistent under the same lock)
    # ------------------------------------------------------------------ #

    def order(self, order_id: int) -> Order | None:
        with self._lock:
            return self._book.orders.get(order_id)

    def orders(self) -> list[Order]:
        with self._lock:
            return list(self._book.orders.values())

    def trades(self) -> list[Trade]:
        with self._lock:
            return list(self._trades)

    def best_bid(self) -> float | None:
        with self._lock:
            return self._book.best_bid()

    def best_ask(self) -> float | None:
        with self._lock:
            return self._book.best_ask()

    def spread(self) -> float | None:
        with self._lock:
            return self._book.spread()

    def mid_price(self) -> float | None:
        with self._lock:
            return self._book.mid_price()

    def depth_snapshot(self, levels: int = 5) -> dict[str, list[tuple[float, int]]]:
        with self._lock:
            return self._book.depth_snapshot(levels)
