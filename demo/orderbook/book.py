"""OrderBook: price-time-priority matching core.

Single-threaded logic only — ALL locking lives in engine.py. Heaps hold
(price_key, seq, order_id) tuples, never Order objects. Bids use a max-heap
via negated price; asks a min-heap. Cancel is lazy deletion: the heap entry
stays and is popped when it surfaces at the top (heapq has no efficient
arbitrary remove).
"""
from __future__ import annotations

import itertools
import time
from heapq import heappop, heappush

from .models import Order, OrderStatus, OrderType, Side, Trade

HeapEntry = tuple[float, int, int]  # (price_key, seq, order_id)


class OrderBook:
    def __init__(self) -> None:
        self.bids: list[HeapEntry] = []  # price_key = -price  → max-heap
        self.asks: list[HeapEntry] = []  # price_key = price   → min-heap
        self.orders: dict[int, Order] = {}
        # Aggregate resting qty per price level, maintained incrementally —
        # depth queries never scan the heaps.
        self.depth: dict[Side, dict[float, int]] = {Side.BUY: {}, Side.SELL: {}}
        self._seq = itertools.count()
        self._trade_ids = itertools.count(1)

    # ------------------------------------------------------------------ #
    # Submit / match
    # ------------------------------------------------------------------ #

    def submit(self, order: Order) -> list[Trade]:
        """Accept an order: match what crosses, rest or cancel the remainder."""
        order.seq = next(self._seq)
        self.orders[order.order_id] = order
        trades = self._match(order)
        if order.remaining > 0:
            if order.order_type is OrderType.LIMIT:
                self._rest(order)
            else:
                # Market leftover has no price to rest at — cancel it.
                order.cancelled_qty = order.quantity - order.filled
                order.status = OrderStatus.CANCELLED
        return trades

    def _match(self, taker: Order) -> list[Trade]:
        opposite = self.asks if taker.side is Side.BUY else self.bids
        trades: list[Trade] = []
        while taker.remaining > 0:
            entry = self._peek_live(opposite)
            if entry is None:
                break
            maker = self.orders[entry[2]]
            assert maker.price is not None  # only limit orders rest
            if not self._crosses(taker, maker.price):
                break
            qty = min(taker.remaining, maker.remaining)
            maker.filled += qty
            taker.filled += qty
            self._decrement_depth(maker.side, maker.price, qty)
            maker.status = (
                OrderStatus.FILLED if maker.remaining == 0 else OrderStatus.PARTIALLY_FILLED
            )
            taker.status = (
                OrderStatus.FILLED if taker.remaining == 0 else OrderStatus.PARTIALLY_FILLED
            )
            # Trade price = resting order's price (taker gets price improvement).
            trades.append(
                Trade(
                    trade_id=next(self._trade_ids),
                    maker_id=maker.order_id,
                    taker_id=taker.order_id,
                    price=maker.price,
                    quantity=qty,
                    timestamp=time.time(),
                )
            )
            if maker.remaining == 0:
                heappop(opposite)  # maker's entry is at the top
        return trades

    @staticmethod
    def _crosses(taker: Order, maker_price: float) -> bool:
        if taker.order_type is OrderType.MARKET:
            return True
        assert taker.price is not None
        if taker.side is Side.BUY:
            return taker.price >= maker_price
        return taker.price <= maker_price

    def _rest(self, order: Order) -> None:
        assert order.price is not None
        key = -order.price if order.side is Side.BUY else order.price
        heap = self.bids if order.side is Side.BUY else self.asks
        assert order.seq is not None
        heappush(heap, (key, order.seq, order.order_id))
        level = self.depth[order.side]
        level[order.price] = level.get(order.price, 0) + order.remaining

    # ------------------------------------------------------------------ #
    # Cancel (lazy deletion)
    # ------------------------------------------------------------------ #

    def cancel(self, order_id: int) -> bool:
        """Cancel a resting order. O(1): flag + depth decrement; the stale
        heap entry is popped later when it surfaces at the top."""
        order = self.orders.get(order_id)
        if order is None or not order.is_active or order.order_type is not OrderType.LIMIT:
            return False
        assert order.price is not None
        self._decrement_depth(order.side, order.price, order.remaining)
        order.cancelled_qty = order.quantity - order.filled
        order.status = OrderStatus.CANCELLED
        return True

    # ------------------------------------------------------------------ #
    # Book views (skip stale heap entries)
    # ------------------------------------------------------------------ #

    def best_bid(self) -> float | None:
        entry = self._peek_live(self.bids)
        return None if entry is None else self.orders[entry[2]].price

    def best_ask(self) -> float | None:
        entry = self._peek_live(self.asks)
        return None if entry is None else self.orders[entry[2]].price

    def spread(self) -> float | None:
        bid, ask = self.best_bid(), self.best_ask()
        if bid is None or ask is None:
            return None
        return ask - bid

    def mid_price(self) -> float | None:
        bid, ask = self.best_bid(), self.best_ask()
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2

    def depth_snapshot(self, levels: int = 5) -> dict[str, list[tuple[float, int]]]:
        """Top-N (price, qty) per side from the incrementally-maintained
        depth dict — no heap scan, no stale entries."""
        bids = sorted(self.depth[Side.BUY].items(), key=lambda kv: -kv[0])[:levels]
        asks = sorted(self.depth[Side.SELL].items(), key=lambda kv: kv[0])[:levels]
        return {"bids": bids, "asks": asks}

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _peek_live(self, heap: list[HeapEntry]) -> HeapEntry | None:
        """Return the top live entry, popping stale (cancelled/filled) ones."""
        while heap:
            entry = heap[0]
            if self.orders[entry[2]].is_active:
                return entry
            heappop(heap)
        return None

    def _decrement_depth(self, side: Side, price: float, qty: int) -> None:
        level = self.depth[side]
        level[price] -= qty
        if level[price] <= 0:
            del level[price]
