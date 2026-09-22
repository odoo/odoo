from __future__ import annotations

import re
import subprocess
import sys
import time

import pytest

from ._bench import StatementCounter, measure
from .conftest import ADDONS_PATH, REPO_ROOT


@pytest.fixture(scope="module")
def env(base_db):
    import odoo
    from odoo.modules.registry import Registry

    registry = Registry(base_db)
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        cr.transaction.default_env = env
        yield env
        cr.rollback()


@pytest.fixture(scope="module")
def counter():
    with StatementCounter().on() as counter:
        yield counter


def test_partner_create_one(env, counter, check):
    partner = env["res.partner"]
    readings = measure(
        lambda: (partner.create({"name": "b"}), env.flush_all()), counter, repeat=50
    )
    check("partner_create_one", readings)


def test_partner_create_batch(env, counter, check):
    partner = env["res.partner"]
    readings = measure(
        lambda: (
            partner.create([{"name": f"b{i}"} for i in range(1000)]),
            env.flush_all(),
        ),
        counter,
        repeat=1,
        rounds=3,
    )
    check("partner_create_batch_1000", readings)


def test_partner_write_loop(env, counter, check):
    partners = env["res.partner"].create([{"name": f"w{i}"} for i in range(1000)])
    env.flush_all()
    tick = [0]

    def loop():
        tick[0] += 1
        for record in partners:
            record.ref = f"r{tick[0]}"
        env.flush_all()

    readings = measure(loop, counter, repeat=1, rounds=3)
    check("partner_write_loop_1000", readings)


def test_partner_write_batch(env, counter, check):
    partners = env["res.partner"].create([{"name": f"v{i}"} for i in range(1000)])
    env.flush_all()
    tick = [0]

    def batch():
        tick[0] += 1
        partners.write({"ref": f"b{tick[0]}"})
        env.flush_all()

    readings = measure(batch, counter, repeat=1, rounds=3)
    check("partner_write_batch_1000", readings)


def test_partner_search_fetch(env, counter, check):
    env["res.partner"].create([{"name": f"s{i}"} for i in range(1000)])
    env.flush_all()

    def fetch():
        env.invalidate_all()
        return env["res.partner"].search_fetch(
            [("name", "like", "s")], ["name", "email"], limit=1000
        )

    readings = measure(fetch, counter, repeat=5)
    check("partner_search_fetch_1000", readings)


def test_registry_warm_load(base_db, check):
    seconds = []
    for _ in range(3):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "odoo-bin"),
                "--addons-path",
                ADDONS_PATH,
                "-d",
                base_db,
                "--stop-after-init",
                "--no-http",
                "--log-level",
                "info",
            ],
            capture_output=True,
            text=True,
            timeout=600,
            check=True,
        )
        match = re.search(r"Registry loaded in ([0-9.]+)s", proc.stdout + proc.stderr)
        assert match, proc.stderr[-2000:]
        seconds.append(float(match.group(1)))
    check("registry_warm_load_base", {"seconds": round(min(seconds), 3)})


def test_in_memory_floor(check):
    from odoo import api, fields, models
    from odoo.orm.model_test_env import model_test_env

    class Plain(models.Model):
        _name = "perf.plain"
        _module = "perf"
        _description = "perf floor"
        name = fields.Char()
        value = fields.Integer()

    attrs = {
        "_name": "perf.computed",
        "_module": "perf",
        "_description": "perf floor",
        "name": fields.Char(),
        "value": fields.Integer(),
    }
    for i in range(16):

        def make(i):
            @api.depends("value")
            def compute(self):
                for record in self:
                    record[f"c{i}"] = record.value + i

            return compute

        attrs[f"c{i}"] = fields.Integer(compute=f"_compute_c{i}", store=True)
        attrs[f"_compute_c{i}"] = make(i)
    Computed = type("Computed", (models.Model,), attrs)

    def create_one_us(env, model, n=300):
        m = env[model]
        m.create({"name": "warm", "value": 1})
        env.flush_all()
        start = time.perf_counter()
        for i in range(n):
            m.create({"name": f"r{i}", "value": i})
            env.flush_all()
        return (time.perf_counter() - start) / n * 1e6

    with model_test_env(Plain, Computed) as env:
        plain = min(create_one_us(env, "perf.plain") for _ in range(3))
        computed = min(create_one_us(env, "perf.computed") for _ in range(3))
    check(
        "in_memory_floor",
        {
            "create_one_us": round(plain),
            "per_stored_compute_us": round((computed - plain) / 16, 1),
        },
    )
