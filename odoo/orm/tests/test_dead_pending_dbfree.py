from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.tools.misc import PENDING

_MOD = "test_dead_pending_dbfree"


class Partial(models.Model):
    _name = "dpd.partial"
    _module = _MOD
    _description = "stored computes that leave records unassigned"
    _log_access = False

    mode = fields.Char()
    alpha = fields.Integer(compute="_compute_alpha", store=True, readonly=False)
    beta = fields.Integer(compute="_compute_beta", store=True, readonly=False)

    @api.depends("mode")
    def _compute_alpha(self):
        self.filtered(lambda record: record.mode == "force").alpha = 1

    @api.depends("mode")
    def _compute_beta(self):
        self.filtered(lambda record: record.mode == "force").beta = 2


def _marker(record, fname):
    return record._fields[fname]._get_cache(record.env).get(record.id, "<absent>")


def test_one_fetch_answers_every_unassigned_field():
    with model_test_env(Partial) as env:
        record = env["dpd.partial"].create({"mode": "leave"})
        assert _marker(record, "beta") is PENDING
        env.flush_all()
        # the compute ran and assigned nothing: the marker is stale
        assert _marker(record, "beta") is PENDING
        assert record.alpha == 0
        # the row that answered alpha carries beta too, as on PostgreSQL
        assert _marker(record, "beta") == 0
        assert record.beta == 0


def test_a_pending_write_and_a_rescheduled_compute_survive_a_fetch():
    with model_test_env(Partial) as env:
        record = env["dpd.partial"].create({"mode": "leave"})
        env.flush_all()
        env.invalidate_all()
        record.alpha = 42
        record.beta
        assert record.alpha == 42
        env.invalidate_all()
        record.alpha
        record.mode = "force"
        assert (record.alpha, record.beta) == (1, 2)
