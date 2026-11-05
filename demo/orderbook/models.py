"""Order and Trade models. Pure data — no book logic lives here."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    order_id: int
    side: Side
    order_type: OrderType
    quantity: int
    price: float | None = None  # None for MARKET orders
    status: OrderStatus = OrderStatus.NEW
    filled: int = 0
    cancelled_qty: int = 0
    seq: int | None = None  # assigned by the book at accept time; heap tie-break
    timestamp: float = field(default_factory=time.time)

    @property
    def remaining(self) -> int:
        return self.quantity - self.filled - self.cancelled_qty

    @property
    def is_active(self) -> bool:
        return (
            self.status in (OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED)
            and self.remaining > 0
        )


@dataclass(frozen=True)
class Trade:
    trade_id: int
    maker_id: int
    taker_id: int
    price: float
    quantity: int
    timestamp: float
