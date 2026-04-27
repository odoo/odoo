# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, tools, _
from odoo.exceptions import RedirectWarning
from odoo.osv import expression
from odoo.tools import format_list


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _default_l10n_br_is_nfce(self):
        # NFC-e by default for Brazilian companies. Don't enable in testing mode because it will break l10n_test_pos_qr_payment.
        return not tools.config["test_enable"] and self.env.company.account_fiscal_country_id.code == "BR"

    l10n_br_is_nfce = fields.Boolean(
        "NFC-e", default=_default_l10n_br_is_nfce, help="Brazil: if this is selected, NFC-e will be created for each order."
    )
    l10n_br_invoice_serial = fields.Char(
        "Series",
        copy=False,
        help="Brazil: series number associated with this POS.",
    )

    def _get_available_product_domain(self):
        """Override."""
        res = super()._get_available_product_domain()
        if self.l10n_br_is_nfce:
            return expression.AND(
                [
                    res,
                    [
                        (
                            "taxes_id",
                            "not any",
                            [*self.env["account.tax"]._check_company_domain(self.company_id), ("price_include", "=", False)],
                        ),
                    ],
                ]
            )

        return res

    def _check_before_creating_new_session(self):
        """Override."""
        super()._check_before_creating_new_session()
        if self.l10n_br_is_nfce:
            company = self.company_id
            missing_fields = []
            required_company_fields = ("l10n_br_edi_csc_identifier", "l10n_br_edi_csc_number")
            for field in required_company_fields:
                if not company[field]:
                    missing_fields.append(company._fields[field])

            if missing_fields:
                raise RedirectWarning(
                    _(
                        "You must configure the %(missing_fields)s.",
                        missing_fields=format_list(self.env, [field._description_string(self.env) for field in missing_fields]),
                    ),
                    self.env.ref("account.action_account_config").id,
                    _("Go to Accounting settings"),
                )

            if not self.l10n_br_invoice_serial:
                raise RedirectWarning(
                    _(
                        "You must configure the 'Series' field on point of sale \"%(point_of_sale_name)s\".",
                        point_of_sale_name=self.display_name,
                    ),
                    self.env.ref("point_of_sale.action_pos_configuration").id,
                    _("Go to Point of Sale settings"),
                )

    def _create_journal_and_payment_methods(self, cash_ref=None, cash_journal_vals=None):
        """Override."""
        journal, pm_ids = super()._create_journal_and_payment_methods(cash_ref, cash_journal_vals)
        if self.env.company.account_fiscal_country_id.code == "BR":
            for pm in self.env["pos.payment.method"].browse(pm_ids):
                if pm.type == "cash":
                    pm.l10n_br_payment_method = "01"  # money
                elif pm.type == "bank":
                    pm.l10n_br_payment_method = "16"  # bank deposit
                elif pm.type == "pay_later":
                    pm.l10n_br_payment_method = "90"  # no payment
        return journal, pm_ids
