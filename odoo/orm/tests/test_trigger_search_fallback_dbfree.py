from unittest import mock

from odoo import api, fields, models
from odoo.orm.domain import Domain, ids_selected_without_query
from odoo.orm.model_test_env import model_test_env

_MOD = "test_trigger_search_fallback"


class Invoice(models.Model):
    _name = "tsf.invoice"
    _module = _MOD
    _description = "invoice"
    _log_access = False

    state = fields.Char(default="open")
    payment_id = fields.Many2one("tsf.payment")


class Payment(models.Model):
    _name = "tsf.payment"
    _module = _MOD
    _description = "payment"
    _log_access = False

    name = fields.Char()
    invoice_ids = fields.Many2many(
        "tsf.invoice", compute="_compute_invoice_ids", search="_search_invoice_ids"
    )
    state = fields.Char(compute="_compute_state", store=True)

    def _compute_invoice_ids(self):
        for payment in self:
            payment.invoice_ids = self.env["tsf.invoice"].search(
                [("payment_id", "=", payment.id)]
            )

    def _search_invoice_ids(self, operator, value):
        invoices = self.env["tsf.invoice"].browse(value)
        return [("id", "in", invoices.payment_id.ids)]

    @api.depends("invoice_ids.state")
    def _compute_state(self):
        for payment in self:
            states = set(payment.invoice_ids.mapped("state"))
            payment.state = "paid" if states and states == {"paid"} else "open"


def test_an_id_set_domain_is_answered_without_a_query():
    with model_test_env(Invoice, Payment) as env:
        model = env["tsf.payment"]
        selected = ids_selected_without_query(
            Domain("id", "in", [3, 1]).optimize_full(model)
        )
        assert selected is not None and set(selected) == {3, 1}
        assert ids_selected_without_query(Domain.FALSE) is not None
        assert not ids_selected_without_query(Domain.FALSE)
        assert ids_selected_without_query(Domain("name", "=", "x")) is None
        assert ids_selected_without_query(Domain("id", "in", [1, "x"])) is None


def test_a_search_defined_dependency_marks_the_records_without_searching():
    with model_test_env(Invoice, Payment) as env:
        payment = env["tsf.payment"].create({"name": "p"})
        invoice = env["tsf.invoice"].create({"payment_id": payment.id})
        env.flush_all()
        assert payment.state == "open"

        with mock.patch.object(
            type(env["tsf.payment"]), "search", autospec=True
        ) as search:
            invoice.state = "paid"
            env.flush_all()
        assert search.call_count == 0
        assert payment.state == "paid"


def test_a_search_defined_dependency_with_no_referrer_marks_nothing():
    with model_test_env(Invoice, Payment) as env:
        payment = env["tsf.payment"].create({"name": "p"})
        orphan = env["tsf.invoice"].create({})
        env.flush_all()
        payment.state
        orphan.state = "paid"
        env.flush_all()
        assert env.is_to_compute(payment._fields["state"], payment) is False
        assert payment.state == "open"
