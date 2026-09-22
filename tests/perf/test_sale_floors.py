from __future__ import annotations

import pytest

from ._bench import StatementCounter, python_ms
from .conftest import check, requires_pg

pytestmark = requires_pg


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


def test_sale_order_create(env, counter, order_factory):
    ms, statements = python_ms(order_factory, counter, repeat=10)
    check("sale_order_create_3_lines", {"statements": statements, "python_ms": ms})


def test_sale_order_create_confirm(env, counter, order_factory):
    def cycle():
        order = order_factory()
        order.action_confirm()
        env.flush_all()

    ms, statements = python_ms(cycle, counter, repeat=10)
    check("sale_order_create_confirm", {"statements": statements, "python_ms": ms})


def test_partner_create_on_sale_set(env, counter):
    partner = env["res.partner"]
    ms, statements = python_ms(
        lambda: (partner.create({"name": "b"}), env.flush_all()), counter, repeat=50
    )
    check("partner_create_one_sale_set", {"statements": statements, "python_ms": ms})
