import base64
from datetime import timedelta

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def is_sample_action_available(self):
        return bool(self.env.ref("base.res_partner_2", raise_if_not_found=False))

    @_debug.perf.timed
    def action_create_vendor_bill(self):
        _debug.lifecycle("action_create_vendor_bill", records=self)
        context = dict(self.env.context)
        purchase_journal = self.browse(context.get("default_journal_id")).filtered(
            lambda journal: journal.type == "purchase"
        ) or self.search([("type", "=", "purchase")], limit=1)
        partner = self.env.ref("base.res_partner_2", raise_if_not_found=False)
        _debug.logic(
            "sample_bill_inputs",
            journal=purchase_journal,
            journal_from_context=bool(context.get("default_journal_id")),
            partner=partner,
        )
        if not purchase_journal:
            raise UserError(
                self._prepare_no_journal_error_msg(
                    self.env.company.display_name, ["purchase"]
                )
            )
        if not partner:
            raise UserError(
                _(
                    "You may only use samples in demo mode, try uploading one of your invoices instead."
                )
            )
        context["default_move_type"] = "in_invoice"
        invoice_date = fields.Date.today() - timedelta(days=12)
        company = purchase_journal.company_id
        default_expense_account = company.account_config_id.expense_account_id
        ref = "DE%s" % invoice_date.strftime("%Y%m")
        bill = (
            self.env["account.move"]
            .with_context(default_extract_state="done")
            .create(
                {
                    "move_type": "in_invoice",
                    "partner_id": partner.id,
                    "ref": ref,
                    "invoice_date": invoice_date,
                    "invoice_date_due": invoice_date + timedelta(days=30),
                    "journal_id": purchase_journal.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "[FURN_8999] Three-Seat Sofa",
                                "account_id": purchase_journal.default_account_id.id
                                or default_expense_account.id,
                                "quantity": 5,
                                "price_unit": 1500,
                            }
                        ),
                        Command.create(
                            {
                                "name": "[FURN_8220] Four Person Desk",
                                "account_id": purchase_journal.default_account_id.id
                                or default_expense_account.id,
                                "quantity": 5,
                                "price_unit": 2350,
                            }
                        ),
                    ],
                }
            )
        )
        _debug.pipeline(
            "sample_bill_created",
            move=bill,
            journal=purchase_journal,
            company=company,
        )
        bill.message_post(
            attachment_ids=self._render_sample_bill_attachment(
                company, ref, invoice_date
            ).ids
        )
        return {
            "name": _("Bills"),
            "res_id": bill.id,
            "view_mode": "form",
            "res_model": "account.move",
            "views": [[False, "form"]],
            "type": "ir.actions.act_window",
            "context": context,
        }

    @_debug.perf.timed
    def _render_sample_bill_attachment(self, company, ref, invoice_date):
        if _debug.logic.enabled and (
            tools.config["test_enable"] or modules.module.current_test
        ):
            _debug.logic("sample_pdf_skipped", reason="test_mode", company=company)
        if tools.config["test_enable"] or modules.module.current_test:
            return self.env["ir.attachment"]
        address = [
            part
            for part in [
                company.street,
                company.street2,
                " ".join(x for x in [company.state_id.name, company.zip] if x),
                company.country_id.name,
            ]
            if part
        ]
        html = self.env["ir.qweb"]._render(
            "account.bill_preview",
            {
                "company_name": company.name,
                "company_street_address": address,
                "invoice_name": "Invoice " + ref,
                "invoice_ref": ref,
                "invoice_date": invoice_date,
                "invoice_due_date": invoice_date + timedelta(days=30),
            },
        )
        IrReport = self.env["ir.actions.report"]
        bodies, _res_ids, specific_paperformat_args = IrReport._prepare_weasyprint_html(
            html
        )
        with _debug.perf("sample_pdf_render", cr=self.env.cr, company=company):
            content = IrReport._render_html_to_pdf(
                bodies, specific_paperformat_args=specific_paperformat_args
            )
        _debug.pipeline("sample_pdf_ready", company=company, size=len(content))
        return self.env["ir.attachment"].create(
            {
                "type": "binary",
                "name": "INV-%s-0001.pdf" % invoice_date.strftime("%Y-%m"),
                "res_model": "mail.compose.message",
                "datas": base64.encodebytes(content),
            }
        )
