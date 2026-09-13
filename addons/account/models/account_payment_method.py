from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountPaymentMethod(models.Model):
    _name = "account.payment.method"
    _description = "Payment Method"

    name = fields.Char(
        translate=True,
        required=True,
    )
    code = fields.Char(required=True)
    payment_type = fields.Selection(
        selection=[("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True,
    )

    _name_code_unique = models.Constraint(
        "unique (code, payment_type)",
        "The combination code/payment type already exists!",
    )

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        payment_methods = super().create(vals_list)
        methods_info = self._get_payment_method_information()
        return self._auto_link_payment_methods(payment_methods, methods_info)

    def _auto_link_payment_methods(self, payment_methods, methods_info):
        multi_methods = payment_methods.filtered(
            lambda method: methods_info.get(method.code, {}).get("mode") == "multi"
        )
        journals_per_code = self._get_journals_per_payment_method_code(
            set(multi_methods.mapped("code"))
        )
        self.env["account.payment.channel"].create(
            [
                {
                    "name": method.name,
                    "payment_method_id": method.id,
                    "journal_id": journal.id,
                }
                for method in multi_methods
                for journal in journals_per_code[method.code]
            ]
        )
        return payment_methods

    def _get_journals_per_payment_method_code(self, codes):
        Journal = self.env["account.journal"]
        return {
            code: Journal.search(self._get_domain_payment_method(code))
            for code in codes
        }

    @api.model
    def _get_domain_payment_method(self, code, with_currency=True, with_country=True):
        if not code:
            return Domain.TRUE
        information = self._get_payment_method_information().get(code)
        journal_types = information.get("type", ("bank", "cash", "credit"))
        domain = Domain("type", "in", journal_types)

        if with_currency and (currency_ids := information.get("currency_ids")):
            domain &= (
                Domain("currency_id", "=", False)
                & Domain("company_id.currency_id", "in", currency_ids)
            ) | Domain("currency_id", "in", currency_ids)

        if with_country and (country_id := information.get("country_id")):
            domain &= Domain("company_id.account_fiscal_country_id", "=", country_id)

        _debug.logic(
            "payment_method_domain_built",
            code=code,
            journal_types=journal_types,
            currency_filtered=bool(with_currency and information.get("currency_ids")),
            country_filtered=bool(with_country and information.get("country_id")),
        )
        return domain

    @api.model
    def _get_payment_method_information(self):
        return {
            "manual": {"mode": "multi", "type": ("bank", "cash", "credit")},
        }

    @api.model
    def _get_sdd_payment_method_code(self):
        return []

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        self.env["account.payment.channel"].search(
            [("payment_method_id", "in", self.ids)]
        ).unlink()
        return super().unlink()
