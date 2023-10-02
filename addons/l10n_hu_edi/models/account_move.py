# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError
from functools import lru_cache
from odoo.addons.account.models.account_move import MAX_HASH_VERSION
from odoo.tools import formatLang, float_round

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("l10n_hu_delivery_date", "country_code", "move_type")
    def _compute_l10n_hu_show_delivery_date(self):
        for move in self:
            move.l10n_hu_show_delivery_date = move.l10n_hu_delivery_date and move.is_sale_document()
            if move.country_code == "HU":
                move.l10n_hu_show_delivery_date = move.is_sale_document()

    l10n_hu_delivery_date = fields.Date(
        string="Delivery Date",
        readonly=True,
        store=True,
        states={"draft": [("readonly", False)]},
    )
    l10n_hu_show_delivery_date = fields.Boolean(compute="_compute_l10n_hu_show_delivery_date")

    l10n_hu_payment_mode = fields.Selection(
        [
            ("TRANSFER", "Transfer"),
            ("CASH", "Cash"),
            ("CARD", "Credit/debit card"),
            ("VOUCHER", "Voucher"),
            ("OTHER", "Other"),
        ],
        string="Payment mode",
        help="Hungarian payment mode of the invoice.",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    l10n_hu_invoice_chain = fields.Integer("NAV Invoice Chain Index", readonly=True, copy=False)

    l10n_hu_actual_transaction_id = fields.Many2one(
        "l10n_hu.upload_transaction", string="Upload Transaction", readonly=True, copy=False
    )
    l10n_hu_transaction_ids = fields.One2many(
        "l10n_hu.upload_transaction", "invoice_id", string="Upload Transaction History"
    )

    l10n_hu_currency_rate = fields.Float(
        "Currency rate at post",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Currency rate applied at the moment the invoice is posted",
    )

    l10n_hu_is_demo_invoice = fields.Boolean(compute="_calc_l10n_hu_is_demo_invoice")

    def _l10n_hu_get_invoice_totals_for_report(self):
        self.ensure_one()

        tax_totals = self.tax_totals
        if not isinstance(tax_totals, dict):
            return tax_totals

        tax_totals.update(
            {
                "display_tax_base": True,
                "total_vat_amount_in_huf": 0.0,
            }
        )

        sign = 1.0
        if "refund" in self.move_type:
            sign = -1.0

        if sign < 0:
            tax_totals.update(
                {
                    "amount_total": tax_totals["amount_total"] * sign,
                    "amount_untaxed": tax_totals["amount_untaxed"] * sign,
                }
            )
            tax_totals.update(
                {
                    "formatted_amount_total": formatLang(
                        self.env, tax_totals["amount_total"], currency_obj=self.currency_id
                    ),
                    "formatted_amount_untaxed": formatLang(
                        self.env, tax_totals["amount_untaxed"], currency_obj=self.currency_id
                    ),
                }
            )

            if "formatted_amount_total_rounded" in tax_totals:
                tax_totals.update(
                    {
                        "rounding_amount": tax_totals["rounding_amount"] * sign,
                        "amount_total_rounded": tax_totals["amount_total_rounded"] * sign,
                    }
                )
                tax_totals.update(
                    {
                        "formatted_rounding_amount": formatLang(
                            self.env, tax_totals["rounding_amount"], currency_obj=self.currency_id
                        ),
                        "formatted_amount_total_rounded": formatLang(
                            self.env, tax_totals["amount_total_rounded"], currency_obj=self.currency_id
                        ),
                    }
                )

        for tax_list in tax_totals["groups_by_subtotal"].values():
            for tax in tax_list:
                if sign < 0:
                    tax.update(
                        {
                            "tax_group_amount": tax["tax_group_amount"] * sign,
                            "tax_group_base_amount": tax["tax_group_base_amount"] * sign,
                        }
                    )
                    tax.update(
                        {
                            "formatted_tax_group_amount": formatLang(
                                self.env,
                                tax["tax_group_amount"],
                                currency_obj=self.currency_id,
                            ),
                            "formatted_tax_group_base_amount": formatLang(
                                self.env,
                                tax["tax_group_base_amount"],
                                currency_obj=self.currency_id,
                            ),
                        }
                    )

                if self.currency_id != self.company_id.currency_id:
                    tax.update(
                        {
                            "tax_group_amount_company_currency": float_round(
                                tax["tax_group_amount"] * self.l10n_hu_currency_rate, 0
                            ),
                            "tax_group_base_amount_company_currency": float_round(
                                tax["tax_group_base_amount"] * self.l10n_hu_currency_rate, 0
                            ),
                        }
                    )
                    tax.update(
                        {
                            "formatted_tax_group_amount_company_currency": formatLang(
                                self.env,
                                tax["tax_group_amount_company_currency"],
                                currency_obj=self.company_id.currency_id,
                            ),
                            "formatted_tax_group_base_amount_company_currency": formatLang(
                                self.env,
                                tax["tax_group_base_amount_company_currency"],
                                currency_obj=self.company_id.currency_id,
                            ),
                        }
                    )

                    tax_totals["total_vat_amount_in_huf"] += tax["tax_group_amount_company_currency"]

        tax_totals["formatted_total_vat_amount_in_huf"] = formatLang(
            self.env, tax_totals["total_vat_amount_in_huf"], currency_obj=self.company_id.currency_id
        )

        if sign < 0:
            for subtotal in tax_totals["subtotals"]:
                subtotal.update(
                    {
                        "amount": subtotal["amount"] * sign,
                    }
                )
                subtotal.update(
                    {
                        "formatted_amount": formatLang(self.env, subtotal["amount"], currency_obj=self.currency_id),
                    }
                )

        return tax_totals

    def _calc_l10n_hu_is_demo_invoice(self):
        for invoice in self:
            conn_obj = self.env["l10n_hu.nav_communication"]
            try:
                conn_obj = self.env["l10n_hu.nav_communication"]._get_best_communication(invoice.company_id)
            except UserError:
                pass

            invoice.l10n_hu_is_demo_invoice = (
                not conn_obj or conn_obj.state == "test" or invoice.company_id.l10n_hu_use_demo_mode
            )

    def _recompute_cash_rounding_lines(self):
        super()._recompute_cash_rounding_lines()

        # In Hungary the rounding line should have the ATK tax
        if self.country_code == "HU" and self.invoice_cash_rounding_id:
            if self.invoice_cash_rounding_id.strategy != "add_invoice_line":
                raise UserError(
                    _("For Hungarian accounting compliance only the new line adding cash rounding can be used!")
                )

            rl = self.line_ids.filtered(lambda l: l.display_type == "rounding")
            if rl:
                atk_tax = self.env["account.tax"].search(
                    [
                        ("l10n_hu_tax_type", "=", "VAT-ATK"),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
                if not atk_tax:
                    raise UserError(_("Please create an ATK (outside the scope of the VAT Act) type of tax!"))
                rl.write({"tax_ids": [Command.set([atk_tax.id])]})

    def _get_name_invoice_report(self):
        self.ensure_one()
        return self.country_code == "HU" and "l10n_hu_edi.report_invoice_document" or super()._get_name_invoice_report()

    def _l10n_hu_get_nav_operation(self):
        "Technical field for the NAV Upload"
        self.ensure_one()
        operation = "CREATE"
        if self.move_type == "out_refund" and self.reversed_entry_id:
            operation = "MODIFY"
        return operation

    def _retry_edi_documents_error_hook(self):
        # OVERRIDE
        nav_hun_30 = self.env.ref("l10n_hu_edi.edi_hun_nav_3_0")
        self.filtered(
            lambda m: m._get_edi_document(nav_hun_30).blocking_level == "error"
        ).l10n_hu_actual_transaction_id = None

    @api.depends("l10n_hu_actual_transaction_id.reply_status", "state")
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.state == "posted" and move.l10n_hu_actual_transaction_id:
                if move.l10n_hu_actual_transaction_id.reply_status == "error":
                    move.show_reset_to_draft_button = True
                else:
                    move.show_reset_to_draft_button = False

    def button_draft(self):
        # OVERRIDE
        for move in self:
            if move.l10n_hu_transaction_ids and not move.l10n_hu_actual_transaction_id.reply_status == "error":
                raise UserError(
                    _(
                        "You can't edit the following journal entry %s because an electronic document has already been "
                        "sent to NAV. To edit this entry, you need to create a Credit Note for the invoice and "
                        "create a new invoice.",
                        move.display_name,
                    )
                )

        return super().button_draft()

    def action_reverse(self):
        for move in self.filtered(lambda x: x.country_code == "HU"):
            if move.l10n_hu_actual_transaction_id.reply_status == "error":
                raise UserError(
                    _(
                        "This invoice is rejected by NAV. Instead of creating a reverse, you should set it to "
                        "draft state, correct it and post it again."
                    )
                )
        return super().action_reverse()

    def _get_integrity_hash_fields(self):
        # Hungarian crucial invoice fields:
        # delivery_date, the used currency rate, invoice chain numbering
        val_list = super()._get_integrity_hash_fields()
        hash_version = self._context.get("hash_version", MAX_HASH_VERSION)
        if hash_version > 1:
            val_list += ["l10n_hu_delivery_date", "l10n_hu_currency_rate", "l10n_hu_invoice_chain"]
        return val_list

    def _l10n_hu_edi_fix_fields(self):
        """This method is invoiked *before* the posting of an invoice. It sets various variables, for example delivery date."""
        for invoice in self:
            # Hungarian Invoicing needs to protect the invoices, BUT the implemented hash protection is not good for us.
            # We need to reopen the invoice when we got back an ABORTED mark for the invoice from the NAV.
            if invoice.journal_id.restrict_mode_hash_table:
                raise UserError(_("Hash protection on journal is not compatible with Hungarin Invoicing solution."))

            # Hungarian invoicing only allows you to issue an invoice for today!
            # The field that specifies when the transaction was settled is the delivery date, which can be chosen accordingly.
            if invoice.is_sale_document(include_receipts=True):
                invoice.invoice_date = fields.Date.context_today(invoice)

            # If the delivery date is not setted, than that should be today!
            if not invoice.l10n_hu_delivery_date:
                invoice.l10n_hu_delivery_date = fields.Date.context_today(invoice)

            # For the outgoing invoices store the currency rate
            # Incoming invoice is allowed to auto calculate based on delivery date
            if invoice.is_sale_document(include_receipts=True) or not invoice.l10n_hu_currency_rate:
                invoice.l10n_hu_currency_rate = self.env["res.currency"]._get_conversion_rate(
                    from_currency=invoice.currency_id,
                    to_currency=invoice.company_id.currency_id,
                    company=invoice.company_id,
                    date=invoice.l10n_hu_delivery_date,
                )

            # invoice chain numbering
            if invoice.move_type == "out_invoice":
                if invoice.l10n_hu_invoice_chain != 1:
                    invoice.write({"l10n_hu_invoice_chain": 1})
            elif invoice.move_type == "out_refund":
                other_refunds = invoice.reversed_entry_id.reversal_move_id.filtered(lambda m: m.state == "posted")
                # original (=1) + numbers of previous refunds + 1
                if invoice.l10n_hu_invoice_chain != len(other_refunds) + 2:
                    invoice.write({"l10n_hu_invoice_chain": len(other_refunds) + 2})

            # line numbering
            ln = 1
            round_line = None
            for line in invoice.line_ids:
                if line.display_type == "rounding":
                    round_line = line
                elif line.display_type == "product":
                    if line.l10n_hu_line_number != ln:
                        line.l10n_hu_line_number = ln
                    ln += 1
            # rounding line is the last line
            if round_line:
                if round_line.l10n_hu_line_number != ln:
                    round_line.l10n_hu_line_number = ln

            # remove the previous transaction, so we can do a new upload session
            if invoice.l10n_hu_actual_transaction_id:
                invoice.l10n_hu_actual_transaction_id = False

    def write(self, vals):
        # We need to modify the hungarian invoices *before* the actual posting.
        # Because there is not any method what is adapted inside the _post for this,
        # we need to catch the moment with this hackish code.
        if vals.get("state") == "posted":
            hu_invoices = self.filtered(lambda move: move.state == "draft" and move.country_code == "HU")
            hu_invoices._l10n_hu_edi_fix_fields()

        return super().write(vals)

    def _l10n_hu_get_special_invoice_type(self):
        self.ensure_one()

        if self.move_type == "out_refund":
            return "modification"

        return "normal"


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    # line number inside the invoice. numbering starts with 1
    l10n_hu_line_number = fields.Integer("NAV Line Number", readonly=True, copy=False)

    @api.depends("currency_id", "company_id", "move_id.date", "move_id.l10n_hu_delivery_date")
    def _compute_currency_rate(self):
        """In Hungary, the exchange rate is based on the date of delivery, not the date of issue."""

        @lru_cache()
        def get_rate(from_currency, to_currency, company, date):
            return self.env["res.currency"]._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )

        for line in self:
            if line.move_id.country_code == "HU":
                # for hungary: the date of delivery OR today
                date = line.move_id.l10n_hu_delivery_date or fields.Date.context_today(line)
            else:
                date = line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line)

            if line.currency_id:
                line.currency_rate = get_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=date,
                )
            else:
                line.currency_rate = 1

            # This helps to see the rate during the editing of the invoice record
            if line.move_id.state == "draft":
                line.move_id.l10n_hu_currency_rate = 1.0 / line.currency_rate

    def _get_integrity_hash_fields(self):
        # For hungary the invoice line chain is a crucial and non editable information
        val_list = super()._get_integrity_hash_fields()
        hash_version = self._context.get("hash_version", MAX_HASH_VERSION)
        if hash_version > 1:
            val_list += ["l10n_hu_line_number"]
        return val_list
