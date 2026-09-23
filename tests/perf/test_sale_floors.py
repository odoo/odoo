from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from . import _bench
from ._bench import ServerClock, StatementCounter, measure


@pytest.fixture(scope="module")
def env(sale_db):
    import odoo
    from odoo.modules.registry import Registry

    registry = Registry(sale_db)
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        cr.transaction.default_env = env
        yield env
        cr.rollback()


@pytest.fixture(scope="module")
def counter():
    with StatementCounter().on() as counter:
        yield counter


@pytest.fixture(scope="module")
def order_factory(env):
    product = env["product.product"].create(
        {"name": "perf product", "list_price": 10, "type": "consu"}
    )
    customer = env["res.partner"].create({"name": "perf customer"})
    env.flush_all()

    def make():
        order = env["sale.order"].create(
            {
                "partner_id": customer.id,
                "line_ids": [
                    (0, 0, {"product_id": product.id, "product_qty": 2})
                    for _ in range(3)
                ],
            }
        )
        env.flush_all()
        return order

    return make


def test_sale_order_create(env, counter, order_factory, check):
    readings = measure(order_factory, counter, repeat=10)
    check("sale_order_create_3_lines", readings)


def test_sale_order_create_confirm(env, counter, order_factory, check):
    def cycle():
        order = order_factory()
        order.action_confirm()
        env.flush_all()

    readings = measure(cycle, counter, repeat=10)
    check("sale_order_create_confirm", readings)


def test_partner_create_on_sale_set(env, counter, check):
    partner = env["res.partner"]
    readings = measure(
        lambda: (partner.create({"name": "b"}), env.flush_all()), counter, repeat=50
    )
    check("partner_create_one_sale_set", readings)


def test_sale_order_entry_as_salesman(env, counter, check):
    # what a user's order costs the server: the form's onchanges for a customer
    # and three lines, the save and the confirmation, as a salesman under access
    # rules. Measured 2026-09-22 through a real browser, onchange was 43 % of an
    # order entry's server time and nothing else held it to a number
    from odoo.tests import Form
    from odoo.tests.common import freeze_time, new_test_user

    user = new_test_user(
        env,
        login="perf_salesman",
        groups="sale.group_sale_salesman,stock.group_stock_user",
    )
    product = env["product.product"].create(
        {"name": "perf entry product", "list_price": 10, "type": "consu"}
    )
    customer = env["res.partner"].create({"name": "perf entry customer"})
    env.flush_all()
    salesman_env = env(user=user.id)

    def entry():
        form = Form(salesman_env["sale.order"])
        form.partner_id = customer
        for _ in range(3):
            with form.line_ids.new() as line:
                line.product_id = product
        order = form.save()
        frozen.tick(timedelta(seconds=1))
        order.action_confirm()
        salesman_env.flush_all()

    clock = ServerClock()
    clock.wrap(
        type(salesman_env["sale.order"]),
        "get_views",
        "onchange",
        "web_save",
        "web_read",
        "action_confirm",
    )
    clock.wrap(type(salesman_env["sale.order.line"]), "onchange")
    # the confirmation rewrites date_order to now, and whether that differs
    # from the create's decides whether one more UPDATE is flushed. Patching
    # fields.Datetime.now does not reach date_order's default, which holds the
    # function itself, so the create read the wall clock and the count was 314
    # or 315 by whether the iteration fell in the pinned second. A frozen
    # clock reaches both, and the tick makes every confirmation a second
    # later than its order, as a user's is; the server clock reads real time
    try:
        with freeze_time(
            datetime.combine(datetime.now().date(), time(12)),
            ignore=[_bench.__name__],
        ) as frozen:
            readings = measure(entry, counter, repeat=2, clock=clock)
    finally:
        clock.unwrap()
    check("sale_order_entry_as_salesman", readings)
