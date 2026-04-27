# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo import _, api, fields, models, Command
from odoo.tools import frozendict, float_round, groupby
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import ValidationError
from datetime import datetime

from odoo.addons.l10n_ec_edi.models.account_tax import L10N_EC_TAXSUPPORTS

L10N_EC_VAT_RATES = {
    5: 5.0,
    2: 12.0,
    10: 13.0,
    3: 14.0,
    4: 15.0,
    0: 0.0,
    6: 0.0,
    7: 0.0,
    8: 8.0,
}
L10N_EC_VAT_SUBTAXES = {
    'vat05': 5,
    'vat08': 8,
    'vat12': 2,
    'vat13': 10,
    'vat14': 3,
    'vat15': 4,
    'zero_vat': 0,
    'not_charged_vat': 6,
    'exempt_vat': 7,
}  # NOTE: non-IVA cases such as ICE and IRBPNR not supported
L10N_EC_VAT_TAX_NOT_ZERO_GROUPS = (
    'vat05',
    'vat08',
    'vat12',
    'vat13',
    'vat14',
    'vat15',
)
L10N_EC_VAT_TAX_ZERO_GROUPS = (
    'zero_vat',
    'not_charged_vat',
    'exempt_vat',
)
L10N_EC_VAT_TAX_GROUPS = tuple(L10N_EC_VAT_TAX_NOT_ZERO_GROUPS + L10N_EC_VAT_TAX_ZERO_GROUPS)  # all VAT taxes
L10N_EC_WITHHOLD_CODES = {
    'withhold_vat_purchase': 2,
    'withhold_income_purchase': 1,
}
L10N_EC_WITHHOLD_VAT_CODES = {
    0.0: 7,  # 0% vat withhold
    10.0: 9,  # 10% vat withhold
    20.0: 10,  # 20% vat withhold
    30.0: 1,  # 30% vat withhold
    50.0: 11, # 50% vat withhold
    70.0: 2,  # 70% vat withhold
    100.0: 3,  # 100% vat withhold
}  # NOTE: non-IVA cases such as ICE and IRBPNR not supported
# Codes from tax report "Form 103", useful for withhold automation:
L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES = ['402', '403', '404', '405', '406', '407', '408', '409', '410', '411', '412', '413', '414', '415', '416', '417', '418', '419', '420', '421', '422', '423']
L10N_EC_WTH_FOREIGN_TAX_HAVEN_OR_LOWER_TAX_CODES = ['424', '425', '426', '427', '428', '429', '430', '431', '432', '433']
L10N_EC_WTH_FOREIGN_NOT_SUBJECT_WITHHOLD_CODES = ['412', '423', '433']
L10N_EC_WTH_FOREIGN_SUBJECT_WITHHOLD_CODES = list(set(L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES) - set(L10N_EC_WTH_FOREIGN_NOT_SUBJECT_WITHHOLD_CODES))
L10N_EC_WTH_FOREIGN_DOUBLE_TAXATION_CODES = ['402', '403', '404', '405', '406', '407', '408', '409', '410', '411', '412']
L10N_EC_WITHHOLD_FOREIGN_REGIME = [('01', '(01) General Regime'), ('02', '(02) Fiscal Paradise'), ('03', '(03) Preferential Tax Regime')]


class AccountMove(models.Model):
    _inherit = "account.move"

    # ===== Authorization number show/edit fields =====
    l10n_show_ec_authorization = fields.Boolean(
        string='Show Authorization',
        compute='_compute_l10n_ec_show_edit_authorization',
        help='Technical field to show "Authorization number" field in the move form.',
    )
    l10n_edit_ec_authorization = fields.Boolean(
        string='Edit Authorization',
        compute='_compute_l10n_ec_show_edit_authorization',
        help='Technical field to edit "Authorization number" field in the move form.',
    )

    # ===== EDI fields =====
    l10n_ec_authorization_number = fields.Char(
        string="Authorization number",
        size=49,
        copy=False, index=True,
        tracking=True,
        help="Ecuador: EDI authorization number (same as access key), set upon posting",
    )
    l10n_ec_authorization_date = fields.Datetime(
        string="Authorization date",
        copy=False, readonly=True, tracking=True,
        help="Ecuador: Date on which government authorizes the document, unset if document is cancelled.",
    )
    l10n_latam_internal_type = fields.Selection(related='l10n_latam_document_type_id.internal_type')

    # ===== WITHHOLD fields =====
    l10n_ec_withhold_type = fields.Selection(related='journal_id.l10n_ec_withhold_type')
    l10n_ec_withhold_date = fields.Date(
        string="Withhold Date",
        readonly=True,
        copy=False,
    )
    # Technical field to show/hide "ADD WITHHOLD" button
    l10n_ec_show_add_withhold = fields.Boolean(
        compute='_compute_l10n_ec_show_add_withhold',
        string="Allow Withhold",
    )
    l10n_ec_withhold_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        string="Withhold Lines",
        copy=False,
        compute='_compute_l10n_ec_withhold_wth_fields',
        help="The withholding lines in a withhold",
    )
    l10n_ec_related_withhold_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='l10n_ec_withhold_invoice_id',
        string="Related withhold lines",
        help="The withhold lines related to this invoice",
    )
    # Technical field for the number of invoices linked to a withhold
    l10n_ec_withhold_origin_invoice_count = fields.Integer(
        compute='_compute_l10n_ec_withhold_wth_fields',
        string="Invoices Count",
    )
    l10n_ec_withhold_ids = fields.Many2many(
        comodel_name='account.move',
        compute='_compute_l10n_ec_withhold_inv_fields',
        string="Withholds",
        help="The withholds related to this invoice",
    )
    # Technical field for the number of invoices linked to this withhold
    l10n_ec_withhold_count = fields.Integer(
        compute='_compute_l10n_ec_withhold_inv_fields',
        string="Withholds Count",
    )
    # Sales/Purchases subtotals, and total widget
    l10n_ec_withhold_subtotals = fields.Json(compute='_compute_l10n_ec_withhold_subtotals')
    l10n_ec_withhold_foreign_regime = fields.Selection(
        selection=L10N_EC_WITHHOLD_FOREIGN_REGIME,
        string="Foreign Fiscal Regime",
    )

    # ==== PURCHASE REIMBURSEMENT ====
    l10n_ec_reimbursement_ids = fields.One2many(
        'l10n_ec.reimbursement',
        'move_id',
        string='Reimbursement Line',
        help='List of purchase invoices used in this reimbursement'
    )

    reimbursement_totals = fields.Binary(
        compute='_compute_l10n_ec_reimbursement_totals',
        exportable=False,
        help='Functional fields to calculate amount totals.'
    )

    # ===== COMPUTE / ONCHANGE / CONSTRAINTS METHODS =====

    @api.depends('l10n_latam_document_type_id', 'l10n_ec_authorization_number', 'journal_id')
    def _compute_l10n_ec_show_edit_authorization(self):
        not_ec_moves = self.filtered(lambda m: m.country_code != 'EC' or not m.l10n_latam_document_type_id) # Not EC documents and documents without a document type
        not_ec_moves = not_ec_moves.filtered(lambda m: not m._l10n_ec_is_withholding()) # Not EC withholds
        not_ec_moves.l10n_show_ec_authorization = False
        not_ec_moves.l10n_edit_ec_authorization = False
        ec_moves = (self - not_ec_moves)
        for move in ec_moves:
            # Always show and edit the authorization number for EC documents
            l10n_show_ec_authorization = True
            l10n_edit_ec_authorization = True
            allow_electronic_document = move.journal_id.type == 'sale' or move.journal_id.l10n_ec_is_purchase_liquidation or move.journal_id.l10n_ec_withhold_type == 'in_withhold'
            if allow_electronic_document and (any(x.code == 'ecuadorian_edi' for x in move.journal_id.edi_format_ids) or move.edi_document_ids):
                # Show authorization number when filled out
                # Do not edit the authorization number when the journal allow electronic invoicing or have an EDI document
                l10n_show_ec_authorization = bool(move.l10n_ec_authorization_number)
                l10n_edit_ec_authorization = False
            elif move.journal_id.l10n_ec_withhold_type == 'out_withhold' or\
                (move.journal_id.type == 'purchase' and move._is_manual_document_number()):
                # Edit and show the autorization number when:
                # - The document it's an out withhold
                # - It's a document with manual authorization
                l10n_edit_ec_authorization = True
            move.l10n_show_ec_authorization = l10n_show_ec_authorization
            move.l10n_edit_ec_authorization = l10n_edit_ec_authorization

    @api.depends('country_code', 'l10n_latam_document_type_id.code', 'l10n_ec_withhold_ids')
    def _compute_l10n_ec_show_add_withhold(self):
        # shows/hide "ADD WITHHOLD" button on invoices
        invoices_ec = self.filtered(lambda inv: inv.country_code == 'EC')
        (self - invoices_ec).l10n_ec_show_add_withhold = False
        for invoice in invoices_ec:
            codes_to_withhold = [
                '01',  # Factura compra
                '02',  # Nota de venta
                '03',  # Liquidacion compra
                '05',  # Nota de Débito
                '08',  # Entradas a espectaculos
                '09',  # Tiquetes
                '11',  # Pasajes
                '12',  # Inst FInancieras
                '20',  # Estado
                '21',  # Carta porte aereo
                '47',  # Nota de crédito de reembolso
                '48',  # Nota de débito de reembolso
            ]
            add_withhold = invoice.country_code == 'EC' and invoice.l10n_latam_document_type_id.code in codes_to_withhold
            invoice.l10n_ec_show_add_withhold = add_withhold

    @api.depends('country_code', 'l10n_ec_withhold_type', 'line_ids.tax_ids', 'line_ids.l10n_ec_withhold_invoice_id')
    def _compute_l10n_ec_withhold_wth_fields(self):
        withholds_ec = self.filtered(lambda wth: wth.country_code == 'EC')
        withholds_not_ec = (self - withholds_ec)
        withholds_not_ec.l10n_ec_withhold_line_ids = False
        withholds_not_ec.l10n_ec_withhold_origin_invoice_count = False
        for withhold in withholds_ec:
            if withhold._l10n_ec_is_withholding():  # fields related to a withhold entry
                withhold.l10n_ec_withhold_line_ids = withhold.line_ids.filtered(lambda l: l.tax_ids)
                withhold.l10n_ec_withhold_origin_invoice_count = len(withhold.line_ids.mapped('l10n_ec_withhold_invoice_id'))
            else:
                withhold.l10n_ec_withhold_line_ids = False
                withhold.l10n_ec_withhold_origin_invoice_count = False

    @api.depends('country_code', 'line_ids.tax_ids.tax_group_id', 'line_ids.l10n_ec_withhold_tax_amount', 'line_ids.balance')
    def _compute_l10n_ec_withhold_subtotals(self):
        def line_dict(withhold_line):
            return {
                'tax_group': withhold_line.tax_ids.tax_group_id,
                'amount': withhold_line.l10n_ec_withhold_tax_amount,
                'base': abs(withhold_line.balance),
            }

        moves_ec = self.filtered(lambda move: move.country_code == 'EC')
        (self - moves_ec).l10n_ec_withhold_subtotals = False
        for move in moves_ec:
            if move.l10n_ec_withhold_type:
                lines = move.l10n_ec_withhold_line_ids.mapped(line_dict)
                move.l10n_ec_withhold_subtotals = self._l10n_ec_withhold_subtotals_dict(move.currency_id, lines)
            else:
                move.l10n_ec_withhold_subtotals = {}

    @api.depends('country_code', 'line_ids')
    def _compute_l10n_ec_withhold_inv_fields(self):
        invoices_ec = self.filtered(lambda inv: inv.country_code == 'EC')
        invoices_not_ec = (self - invoices_ec)
        invoices_not_ec.l10n_ec_withhold_ids = False
        invoices_not_ec.l10n_ec_withhold_count = False

        withhold_invoice_line_data = dict(self.env['account.move.line']._read_group(
            [('l10n_ec_withhold_invoice_id', 'in', invoices_ec.ids)],
            groupby = ['l10n_ec_withhold_invoice_id'],
            aggregates = ['move_id:recordset']
        ))
        for invoice in invoices_ec:
            withhold_ids = False
            withhold_count = False
            if invoice.is_invoice() and withhold_invoice_line_data.get(invoice):
                withhold_ids = withhold_invoice_line_data.get(invoice)
                withhold_count = len(withhold_ids)
            invoice.l10n_ec_withhold_ids = withhold_ids
            invoice.l10n_ec_withhold_count = withhold_count

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number', 'partner_id')
    def _inverse_l10n_latam_document_number(self):
        super()._inverse_l10n_latam_document_number()
        self._l10n_ec_check_number_prefix()

    def write(self, vals):
        out_withholds = self.filtered(lambda m: m.l10n_ec_withhold_type == 'out_withhold' and m.country_code == 'EC')
        out_withholds._l10_ec_check_tax_lock_date(vals)
        return super().write(vals)

    def _l10_ec_check_tax_lock_date(self, vals):
        # Check the locks date for changes in ref field values
        for move in self:
            lock_date = move.company_id._get_user_fiscal_lock_date(move.journal_id)
            if 'ref' in vals and lock_date and move.date <= lock_date:
                raise ValidationError(_("The operation is refused as it would impact an already issued tax statement. "
                                        "Please change the journal entry date or check the fiscal lock date (%s) to proceed."),
                                      format_date(self.env, lock_date))

    @api.depends('l10n_ec_reimbursement_ids.tax_base', 'l10n_ec_reimbursement_ids.tax_amount', 'l10n_ec_reimbursement_ids.tax_id')
    def _compute_l10n_ec_reimbursement_totals(self):
        AccountTax = self.env['account.tax']
        for move in self:
            if move.country_code == 'EC':
                base_lines = [line._prepare_base_line_for_taxes_computation() for line in move.l10n_ec_reimbursement_ids]
                AccountTax._add_tax_details_in_base_lines(base_lines, move.company_id)
                AccountTax._round_base_lines_tax_details(base_lines, move.company_id)
                move.reimbursement_totals = AccountTax._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=move.currency_id,
                    company=move.company_id,
                )
            else:
                move.reimbursement_totals = None

    # ===== BUTTONS =====

    def l10n_ec_add_withhold(self):
        # Launches the withholds wizard linked to selected invoices
        return {
            'name': _("Withhold"),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'l10n_ec.wizard.account.withhold',
            'context': {'active_ids': self.ids, 'active_model': 'account.move'},
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def l10n_ec_action_view_withholds(self):
        # Navigate from the invoice to its withholds
        withhold_ids = self.l10n_ec_withhold_ids.ids
        if len(withhold_ids) == 1:
            return {
                'name': _('Withholding'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': withhold_ids[0],
            }
        else:
            action = self.env["ir.actions.actions"]._for_xml_id('account.action_move_journal_line')
            action['name'] = _("Withholds")
            action['domain'] = f"[('id', 'in', {withhold_ids!r})]"
            return action

    def l10n_ec_action_view_invoices(self):
        # Navigate from the withhold to its invoices
        l10n_ec_withhold_origin_ids = self.line_ids.mapped('l10n_ec_withhold_invoice_id').ids
        if len(l10n_ec_withhold_origin_ids) == 1:
            return {
                'name': _("Invoices"),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': l10n_ec_withhold_origin_ids[0],
            }
        else:
            action_ref = 'account.action_move_out_invoice_type'
            if self.l10n_ec_withhold_type == 'in_withhold':
                action_ref = 'account.action_move_in_invoice_type'
            action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
            action['name'] = _('Invoices')
            action['domain'] = f"[('id', 'in', {l10n_ec_withhold_origin_ids!r})]"
            return action

    def l10n_ec_action_send_withhold(self):
        self.ensure_one()
        template = self.env.ref('l10n_ec_edi.email_template_edi_withhold')
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = {
            **self.env.context,
            'default_model': 'account.move',
            'default_res_ids': self.ids,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'force_email': True,
        }

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'target': 'new',
            'context': ctx,
        }

    def l10n_ec_action_compute_lines_from_reimbursements(self):
        # Compute invoice lines from reimbursements group by product if exists
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('You can only be applied to invoices in draft status.'))
        if self.invoice_line_ids:  # if exists, Remove all lines to recreate the reimbursement lines.
            self.invoice_line_ids = [Command.clear()]

        vals = []
        for reimburs in self.l10n_ec_reimbursement_ids:
            vals.append(
                Command.create({
                    'display_type': 'product',
                    'quantity': 1,
                    'tax_ids': reimburs.tax_id.ids,
                    'price_unit': reimburs.tax_base,
                })
            )
        self.line_ids = vals
        # Update the lines tax because the tax amount in reimbursements is editable. Only occurs when the currency is not foreign.
        #  When move has a foreign currency, it shouldn't have a tax different than 0%, i.e., the tax amount $0.0.
        if self.currency_id == self.company_id.currency_id:
            for tax_id, reimburs_moves in groupby(self.l10n_ec_reimbursement_ids.sorted(lambda l: l.tax_id), lambda i: i.tax_id):
                line = self.line_ids.filtered(lambda l: l.display_type == 'tax' and l.tax_line_id.id == tax_id.id)
                if line:
                    line.debit = sum(r.tax_amount for r in reimburs_moves)

    # ===== OVERRIDES PORTAL WITHHOLD AND PURCHASE LIQUIDATION =====

    def _compute_amount(self):
        # EXTENDS account to properly compute withhold subtotals to be shown in list view, email template, etc.
        withholds = self.filtered(lambda x: x._l10n_ec_is_withholding())
        withholds._l10n_ec_wth_calculate_amount()
        other_moves = self - withholds
        super(AccountMove, other_moves)._compute_amount()

    def _l10n_ec_wth_calculate_amount(self):
        # Sister method to _compute_amount(), withhold subtotals behaves just like payment subtotals
        # Could be computed from the payable lines but also from the withhold lines, we take the second approach
        for withhold in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in withhold.l10n_ec_withhold_line_ids:
                # === Withhold journal entry ===
                total += line.l10n_ec_withhold_tax_amount
                total_currency += line.l10n_ec_withhold_tax_amount

            sign = withhold.direction_sign
            withhold.amount_untaxed = sign * total_untaxed_currency
            withhold.amount_tax = sign * total_tax_currency
            withhold.amount_total = sign * total_currency
            withhold.amount_residual = -sign * total_residual_currency
            withhold.amount_untaxed_signed = -total_untaxed
            withhold.amount_tax_signed = -total_tax
            withhold.amount_total_signed = abs(total) if withhold.move_type == 'entry' else -total
            withhold.amount_residual_signed = total_residual
            withhold.amount_total_in_currency_signed = abs(withhold.amount_total) if withhold.move_type == 'entry' else -(sign * withhold.amount_total)

    def _get_name_invoice_report(self):
        # EXTENDS account_move
        self.ensure_one()
        doc_type_code = self.l10n_latam_document_type_id.code
        if self.l10n_latam_use_documents and self.country_code == 'EC':
            if (self.move_type in ('out_invoice', 'out_refund') and doc_type_code in ['01', '04', '05', '41']) \
                or (self.move_type in ('in_invoice') and doc_type_code in ['03', '41']):
                return 'l10n_ec_edi.report_invoice_document'
        return super(AccountMove, self)._get_name_invoice_report()

    def _is_manual_document_number(self):
        # EXTEND l10n_latam_invoice_document to exclude purchase liquidations and include sales withhold
        self.ensure_one()
        if self.journal_id.company_id.account_fiscal_country_id.code == 'EC':
            if self.journal_id.l10n_ec_is_purchase_liquidation:
                return False
        return super()._is_manual_document_number()

    def _get_l10n_latam_documents_domain(self):
        # EXTENDS l10n_ec
        if not self.journal_id.l10n_ec_is_purchase_liquidation:
            return super()._get_l10n_latam_documents_domain()
        return [('country_id.code', '=', 'EC'), ('internal_type', '=', 'purchase_liquidation')]

    def _l10n_ec_check_number_prefix(self):
        # validates that entity and emission point matches the ones configured in the journal
        to_review = self.filtered(lambda x: x.journal_id.l10n_ec_require_emission and x.l10n_latam_document_type_id
            and x.l10n_latam_document_number and (x.l10n_latam_manual_document_number or not x.highest_name))
        for move in to_review:
            prefix = move.journal_id.l10n_ec_entity + '-' + move.journal_id.l10n_ec_emission
            number = move.l10n_latam_document_type_id._format_document_number(move.l10n_latam_document_number)
            if prefix != number[:7]:
                raise ValidationError(_('Check the document number "%(number)s", the expected prefix is "%(prefix)s".', number=self.l10n_latam_document_number, prefix=prefix))

    def _l10n_ec_check_in_withhold_number_prefix(self):
        # Check the document number only for in withholds
        in_withholds = self.filtered(lambda move: move.journal_id.l10n_ec_withhold_type == 'in_withhold')
        for withhold in in_withholds:
            prefix = 'Ret ' + withhold.journal_id.l10n_ec_entity + '-' + withhold.journal_id.l10n_ec_emission + '-' # The prefix "Ret" is fixed in code
            number = withhold.sequence_prefix
            if prefix != number:
                raise ValidationError(_('Check the document number "%(number)s", the expected prefix is "%(prefix)s".', number=number, prefix=prefix))

    def _l10n_ec_check_in_reimbursements_amounts(self):
        # Check the amount total with reimbursements total. Neither the Sri nor the ATS validate this
        if self.l10n_ec_reimbursement_ids:
            reimbursement_total = sum(self.l10n_ec_reimbursement_ids.mapped('total'))
            if self.currency_id.compare_amounts(self.amount_total, reimbursement_total) != 0:
                raise ValidationError(_("The invoice total (%(total)s) does not match the reimbursement total (%(reim_total)s).", total=self.amount_total, reim_total=reimbursement_total))
            # Check taxsupports used in invoice lines
            taxsupports_used_in_reimburs = set(self.l10n_ec_reimbursement_ids.tax_id.mapped('l10n_ec_code_taxsupport'))
            invoice_taxsupports = set(self.invoice_line_ids.tax_ids.mapped('l10n_ec_code_taxsupport'))
            if not all(taxsupport in invoice_taxsupports for taxsupport in taxsupports_used_in_reimburs):
                raise ValidationError(_("The tax supports used in reimbursements lines must also be in taxes of invoice lines.\nTax supports in reimbursements: %(rec)s",
                                      rec=', '.join(taxsupports_used_in_reimburs)))

    # ===== INVOICE XML GENERATION=====

    def _l10n_ec_get_payment_data(self):
        """ Get payment data for the XML.  """
        payment_data = []
        pay_term_line_ids = self.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
        )
        for line in pay_term_line_ids:
            payment_vals = {
                'payment_code': self.l10n_ec_sri_payment_id.code,
                'payment_total': abs(line.balance),
            }
            payment_vals.update({
                'payment_term': max(((line.date_maturity or self.invoice_date) - self.invoice_date).days, 0) if self.invoice_date else 0,
                'time_unit': "dias",
            })
            payment_data.append(payment_vals)
        return payment_data

    def _l10n_ec_get_invoice_additional_info(self):
        return {
            "Referencia": self.name,  # Reference
            "Vendedor": self.invoice_user_id.name or '',  # Salesperson
            "E-mail": self.invoice_user_id.email or '',
        }

    def _l10n_ec_get_taxes_grouped(self, extra_group='tax_group'):
        self.ensure_one()

        def group_by(base_line, tax_data):
            tax = tax_data['tax']
            code_percentage = L10N_EC_VAT_SUBTAXES[tax.tax_group_id.l10n_ec_type]
            values = {
                'code': self._l10n_ec_map_tax_groups(tax),
                'code_percentage': code_percentage,
                'rate': L10N_EC_VAT_RATES[code_percentage],
            }
            if extra_group == 'tax_group':
                values['tax_group_id'] = tax.tax_group_id.id
            elif extra_group == 'tax_support':
                values['taxsupport'] = tax.l10n_ec_code_taxsupport
            return values

        return self._prepare_edi_tax_details(grouping_key_generator=group_by)

    def _l10n_ec_map_tax_groups(self, tax_id):
        # Maps different tax types (aka groups) to codes for electronic invoicing
        ec_type = tax_id.tax_group_id.l10n_ec_type
        if ec_type in L10N_EC_VAT_TAX_GROUPS:
            return 2
        elif ec_type == 'ice':
            return 3
        elif ec_type == 'irbpnr':
            return 5

    def _l10n_ec_get_invoice_edi_data(self):
        def line_discount(line):
            return line.currency_id.round(line._l10n_ec_prepare_edi_vals_to_export_USD()['price_discount'])

        data = {
            'taxes_data': self._l10n_ec_get_taxes_grouped(),
            'additional_info': self._l10n_ec_get_invoice_additional_info(),
            'discount_total': sum(map(line_discount, self.invoice_line_ids)),
        }
        if self.move_type == 'out_refund':
            data.update({
                'modified_doc': self.reversed_entry_id,
            })
        if self.l10n_latam_document_type_id.internal_type == 'debit_note':
            data.update({
                'modified_doc': self.debit_origin_id,
                'invoice_lines': list(self.invoice_line_ids.filtered(lambda x: x.display_type == 'product')),
            })
        return data

    def _l10n_ec_is_withholding(self):
        return self.country_code == 'EC' and self.l10n_ec_withhold_type in ('in_withhold', 'out_withhold')

    # ===== WITHHOLD XML GENERATION=====

    def _l10n_ec_get_withhold_additional_info(self):
        # Sister method to _l10n_ec_get_invoice_additional_info(), gets an additional info dict
        data = {}
        if self.commercial_partner_id.street or self.commercial_partner_id.street2:
            data = {
                "Direccion": " ".join(filter(None, [self.commercial_partner_id.street, self.commercial_partner_id.street2])),
            }
        if self.commercial_partner_id.email:
            data["Email"] = self.commercial_partner_id.email
        if self.commercial_partner_id.phone:
            data['Telefono'] = self.commercial_partner_id.phone
        return data

    def _l10n_ec_get_withhold_edi_data(self):
        # Computes the data needed for building the withhold xml, to be sent to qweb engine
        self.ensure_one()
        data = {
            'taxsupport_lines': self._l10n_ec_get_withhold_edi_data_lines(),
            'fiscal_period': str(self.date.month).zfill(2) + '/' + str(self.date.year),
            "additional_info": self._l10n_ec_get_withhold_additional_info(),
            'withhold_subtotals': self.l10n_ec_withhold_subtotals,
        }
        return data

    @api.model
    def _l10n_ec_wth_map_tax_code(self, withhold_line):
        # Maps purchase withhold taxes to codes for assembling the EDI document
        code = False
        report_code = False
        l10n_ec_type = withhold_line.tax_ids.tax_group_id.l10n_ec_type
        if l10n_ec_type == 'withhold_income_purchase':
            code = report_code = withhold_line.tax_ids.l10n_ec_code_ats
        elif l10n_ec_type == 'withhold_vat_purchase':
            percentage = abs(withhold_line.tax_ids.amount)
            code = L10N_EC_WITHHOLD_VAT_CODES.get(percentage)
            report_code = withhold_line.tax_ids.l10n_ec_code_applied
        return code, report_code

    def _l10n_ec_wth_get_foreign_data(self):
        """To include in the XML"""
        self.ensure_one()
        foreign_data = {
            'identification': '01',
            'paying_country': 'NA',
            'double_taxation': 'NO',
            'subject_withhold': 'NO',
            'fiscal_payment': '',
            'regime_type': '',
        }
        # This validation is for foreign partners with the field country_code
        if self.commercial_partner_id.country_code != 'EC':
            foreign_data['identification'] = '02'
            taxes = self.line_ids.mapped('tax_ids')
            if taxes:
                foreign_data['paying_country'] = self.commercial_partner_id.country_id.l10n_ec_code_tax_haven or 'NA'
                if any(tax_id.l10n_ec_code_base in L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES for tax_id in taxes):
                    foreign_data['paying_country'] = self.commercial_partner_id.country_id.l10n_ec_code_ats or 'NA'
                if any(tax_id.l10n_ec_code_base in L10N_EC_WTH_FOREIGN_DOUBLE_TAXATION_CODES for tax_id in taxes):
                    foreign_data['double_taxation'] = 'SI'
                foreign_data['subject_withhold'] = 'SI'
                if any(tax_id.l10n_ec_code_base in L10N_EC_WTH_FOREIGN_NOT_SUBJECT_WITHHOLD_CODES for tax_id in taxes):
                    foreign_data['subject_withhold'] = 'NO'
            foreign_data['fiscal_payment'] = 'SI'
            foreign_data['regime_type'] = self.l10n_ec_withhold_foreign_regime
        return foreign_data

    def _l10n_ec_get_withhold_edi_data_lines(self):
        # Withholds has 3 levels, the header, the taxsupports, and its related withholds. As follows:
        # Withhold Header, with withhold number, date, etc.
        # |-- Taxsupports, list of taxsupports affected by the withhold, includes amount subtotals
        #     |-- Withhold lines, includes withhold tax, base, amount
        if not self.l10n_ec_withhold_line_ids:
            return {}
        invoice = self.l10n_ec_withhold_line_ids[0].l10n_ec_withhold_invoice_id  # current version supports only 1 invoice per withhold
        taxsupport_detail = invoice._l10n_ec_get_taxes_grouped(extra_group='tax_support')['tax_details'].values()
        foreign_data = self._l10n_ec_wth_get_foreign_data()
        taxsupport_lines = {}
        for line in self.l10n_ec_withhold_line_ids:
            taxsupport = line.l10n_ec_code_taxsupport
            if not taxsupport_lines.get(taxsupport):
                taxsupport_amount_untaxed = sum(d['base_amount'] for d in taxsupport_detail if d['taxsupport'] == taxsupport)
                taxsupport_amount_total = sum(d['base_amount'] + d['tax_amount'] for d in taxsupport_detail if d['taxsupport'] == taxsupport)
                taxsupport_lines[taxsupport] = {
                    'invoice_taxsupport_code': taxsupport,  # repeated from key, for readibility
                    'invoice_document_type': invoice.l10n_latam_document_type_id.name,
                    'invoice_document_type_code': invoice._l10n_ec_is_purchase_reimbursement() and '41' or invoice.l10n_latam_document_type_id_code,
                    'invoice_document_number': invoice.l10n_latam_document_number.replace('-', '').rjust(15, '0')[-15:],
                    'invoice_document_date': invoice.invoice_date.strftime('%d/%m/%Y'),
                    'invoice_amount_untaxed': taxsupport_amount_untaxed,
                    'invoice_amount_total': taxsupport_amount_total,
                    'invoice_taxes': [d for d in taxsupport_detail if d['taxsupport'] == taxsupport],
                    'withhold_lines': [],  # to be extended below
                    'withhold_lines_count': 0,
                    'invoice_payments': [{'payment_code': invoice.l10n_ec_sri_payment_id.code,
                                          'payment_amount': taxsupport_amount_total}],
                }
                taxsupport_lines[taxsupport].update(foreign_data)
            code, report_code = self._l10n_ec_wth_map_tax_code(line)
            taxsupport_lines[taxsupport]['withhold_lines'].append({
                'tax_type': line.tax_ids.tax_group_id.l10n_ec_type,
                'tax_type_code': L10N_EC_WITHHOLD_CODES.get(line.tax_ids.tax_group_id.l10n_ec_type),
                'tax_code': code,
                'tax_report_code': report_code,
                'tax_base_amount': abs(line.balance),
                'tax_rate': abs(line.tax_ids.amount),  # even if the tax is negative
                'tax_amount': abs(line.l10n_ec_withhold_tax_amount),
            })
            taxsupport_lines[taxsupport]['withhold_lines_count'] += 1
        return list(taxsupport_lines.values())

    def _l10n_ec_get_formas_de_pago(self):
        """Gets the value for the formasDePago key in the XML."""
        self.ensure_one()
        return [self.l10n_ec_sri_payment_id.code]

    # ===== HELPER METHODS FOR WIZARD (Calculate amounts from invoice for withholding) =====

    def _l10n_ec_get_inv_taxsupports_and_amounts(self):
        """ Returns a dict of the base and tax amounts grouped by tax support for this invoice"""
        self.ensure_one()
        taxsupports = {}
        for line in self.line_ids:
            base_tax = line.tax_ids.filtered(lambda t: t.l10n_ec_code_taxsupport)
            taxsupport_code = False
            if line.tax_group_id.l10n_ec_type in L10N_EC_VAT_TAX_GROUPS:
                taxsupport_code = line.tax_line_id.l10n_ec_code_taxsupport
            elif base_tax:
                taxsupport_code = base_tax.l10n_ec_code_taxsupport

            if taxsupport_code:
                taxsupports.setdefault(taxsupport_code, {
                    'amount_base': 0.0,
                    'amount_vat': 0.0,
                })
                if base_tax:
                    sign = -1 if line.move_id.is_inbound() else 1
                    taxsupports[taxsupport_code]['amount_base'] += sign * line.balance
                else:
                    taxsupports[taxsupport_code]['amount_vat'] += abs(line.balance)
        return taxsupports

    def _get_profit_vat_tax_grouped_details(self):
        """ This methods is to return the amounts grouped by tax support and the withhold tax to be applied"""
        # Create a grouped tax method to return profit and vat tax details with _prepare_edi_tax_details method
        self.ensure_one()

        def grouping_function(wth_tax_index, base_line, tax_data):
            line = base_line['record']
            # Should return tuple doc sustento + withholding tax
            tax_support = base_line['tax_ids'].l10n_ec_code_taxsupport
            # Profit withhold logic
            withhold = line._get_suggested_supplier_withhold_taxes()[wth_tax_index]
            return {'tax_support': tax_support,
                    'withhold_tax': withhold}

        # Calculate tax_details grouped for the (profit, VAT) withholds
        return (
            self._prepare_edi_tax_details(grouping_key_generator=partial(grouping_function, 1)),  # profit grouping
            self._prepare_edi_tax_details(grouping_key_generator=partial(grouping_function, 0))  # VAT grouping
        )

    # ===== WITHHOLD TAX SUMMARY WIDGET METHODS =====

    @api.model
    def _l10n_ec_withhold_subtotals_dict(self, currency_id, lines):
        """
        This method returns the information for the tax summary widgets in both the withhold wizard as in the withholding
        itself. That is why the lines are passed as parameter.
        """
        vat_amount, pro_amount, vat_base, pro_base = 0.0, 0.0, 0.0, 0.0
        vat_tax_group, pro_tax_group = None, None
        for line in lines:
            tax_group_id = line['tax_group']
            if tax_group_id:
                if tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase']:
                    vat_tax_group = tax_group_id
                    vat_amount += line['amount']
                    vat_base += line['base']
                elif tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase']:
                    pro_tax_group = tax_group_id
                    pro_amount += line['amount']
                    pro_base += line['base']

        if not (vat_tax_group or pro_tax_group):
            return False  # widget gives errors if no tax groups

        wth_subtotals = {
            'total_amount_currency': vat_amount + pro_amount,
            'allow_tax_edition': False,
            'groups_by_subtotal': {},
            'subtotals_order': [],
            'subtotals': [],
            'display_tax_base': False,
        }

        def add_subtotal(amount, base, currency, key, tax_group):
            # Add a subtotal to the widget
            # We need to add a group_by_subtotal, subtotals and subtotals_order otherwise the widget will crash
            wth_subtotals['groups_by_subtotal'][key] = []
            wth_subtotals['subtotals_order'].append(key)
            wth_subtotals['subtotals'].append({
                'name': key,
                'base_amount_currency': amount,
                'tax_groups': [{
                    'display_base_amount_currency': True,
                    'group_name': tax_group.name,
                    'tax_amount_currency': amount,
                }],
            })

        if vat_tax_group:
            add_subtotal(vat_amount, vat_base, currency_id, _("VAT Withhold"), vat_tax_group)
        if pro_tax_group:
            add_subtotal(pro_amount, pro_base, currency_id, _("Profit Withhold"), pro_tax_group)

        return wth_subtotals

    # ===== EDIs UNIQUE AUTHORIZATION NUMBER GENERATION =====

    def _post(self, soft=True):
        # Company must assign the unique authorization number before sending to SRI, it can be used in offline mode
        moves = super()._post(soft)
        self._l10n_ec_check_in_withhold_number_prefix() # Only for in withholds
        self._l10n_ec_check_in_reimbursements_amounts()
        for move in moves.filtered(lambda m: m.country_code == 'EC'):
            if any(x.code == 'ecuadorian_edi' for x in move.journal_id.edi_format_ids):
                move._l10n_ec_set_authorization_number()
        return moves

    def _l10n_ec_set_authorization_number(self):
        self.ensure_one()
        company = self.company_id
        # NOTE: withholds don't have l10n_latam_document_type_id (WTH journals use separate sequence)
        document_code_sri = '07' if self._l10n_ec_is_withholding() else self.l10n_latam_document_type_id.code
        environment = company.l10n_ec_production_env and '2' or '1'
        serie = self.journal_id.l10n_ec_entity + self.journal_id.l10n_ec_emission
        sequential = self.name.split('-')[2].rjust(9, '0')
        num_filler = '31215214'  # can be any 8 digits, thanks @3cloud !
        emission = '1'  # corresponds to "normal" emission, "contingencia" no longer supported

        if not (document_code_sri and company.partner_id.vat and environment
                and serie and sequential and num_filler and emission):
            return ''

        now_date = (self.l10n_ec_withhold_date if self._l10n_ec_is_withholding() else self.invoice_date).strftime('%d%m%Y')
        key_value = now_date + document_code_sri + company.partner_id.vat + environment + serie + sequential + num_filler + emission
        self.l10n_ec_authorization_number = key_value + str(self._l10n_ec_get_check_digit(key_value))

    @api.model
    def _l10n_ec_get_check_digit(self, key):
        sum_total = sum([int(key[-i - 1]) * (i % 6 + 2) for i in range(len(key))])
        sum_check = 11 - (sum_total % 11)
        if sum_check >= 10:
            sum_check = 11 - sum_check
        return sum_check

    def _l10n_ec_get_reimbursement_common_values(self, move):
        # Get the reimbursements values to show in xml
        reimbursement_total, total_doc_reimbursement, total_tax_reimbursement = 0.0, 0.0, 0.0
        lines_ids = []
        for reimbursement in move.l10n_ec_reimbursement_ids:
            reimbursement_total += reimbursement._get_tax_amounts_converted(reimbursement.total)
            total_doc_reimbursement += reimbursement._get_tax_amounts_converted(reimbursement.tax_base)
            total_tax_reimbursement += reimbursement._get_tax_amounts_converted(reimbursement.tax_amount)
            vat = reimbursement.partner_vat_number
            lines_ids.append({
                'record': reimbursement,
                'supplier_id_type': reimbursement._get_reimbursement_partner_identification_type(),
                'supplier_identification': vat,
                'supplier_country_code': reimbursement.partner_country_id.l10n_ec_code_ats,
                # if the third digit of it's vat is 6 or 9, the supplier type is identified as a company or a natural person
                'supplier_type_edi': '02' if vat[2] in ['6', '9'] else '01',
                'supplier_type_id_code': reimbursement.l10n_latam_document_type_id.code,
                'auth_number': reimbursement.authorization_number or '9999999999',
                'number_vals': reimbursement._get_reimbursement_line_vals(),
            })
        return {
            'lines_ids': lines_ids,
            'reimbursement_total': reimbursement_total,
            'total_doc_reimbursement': total_doc_reimbursement,
            'total_tax_reimbursement': total_tax_reimbursement
        }

    def _l10n_ec_extract_data_from_access_key(self, authorization_number=False):
        """
        Extract the key access fields
                Key acces structure :
                length         field
                8              emission date
                2              document type
                13             vat (RUC)
                1              environment type
                3              shop
                3              Emission point
                9              document number
                8              filler
                1              emission type
                1              verification digit
        """
        access_key = authorization_number or self.l10n_ec_authorization_number
        document_date = datetime.strptime(access_key[0:8], "%d%m%Y").date()
        source_code = access_key[8:10]
        l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
            [('code', '=', source_code),
             ('country_id.code', '=', 'EC')],
            limit=1)
        partner_vat = access_key[10:23]
        partner_id = self.env['res.partner'].search([('vat', '=', partner_vat)], limit=1).commercial_partner_id
        environment_type = access_key[23:24]
        document_number = "-".join([access_key[24:27], access_key[27:30], access_key[30:39]])
        emission_type = access_key[47:48]
        parity = access_key[48:49]  # verification digit
        return {
            'document_date': document_date,
            'source_code': source_code,
            'l10n_latam_document_type_id': l10n_latam_document_type_id,
            'partner_vat': partner_vat,
            'partner_id': partner_id,
            'environment_type': environment_type,
            'document_number': document_number,
            'emission_type': emission_type,
            'parity': parity,
        }

    def _l10n_ec_is_purchase_reimbursement(self):
        return self.l10n_ec_reimbursement_ids and self.is_purchase_document()

    @api.constrains("l10n_ec_reimbursement_ids")
    def _check_l10n_ec_taxsupport_reimbursement_lines(self):
        taxsupports_used = set(self.l10n_ec_reimbursement_ids.tax_id.mapped('l10n_ec_code_taxsupport'))
        if taxsupports_used and len(taxsupports_used) != 1:
            raise ValidationError(
                _("Please ensure all the taxes in reimbursement lines use the same tax support. Creating reimbursement lines with multiple tax supports is not allowed.\n"
                    "Tax supports in reimbursements: %s", ', '.join(taxsupports_used)))


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_ec_withhold_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string="Invoice",
        copy=False,
        ondelete='restrict',
        help="Link the withholding line to its invoice",
    )
    l10n_ec_code_taxsupport = fields.Selection(
        selection=L10N_EC_TAXSUPPORTS,
        string="Tax Support",
        help="Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS",
    )
    l10n_ec_withhold_tax_amount = fields.Monetary(
        string="Withhold Tax Amount",
        compute='_compute_withhold_tax_amount',
    )

    @api.depends('tax_ids')
    def _compute_withhold_tax_amount(self):
        for line in self.filtered('move_id.l10n_ec_withhold_type'):
            currency_rate = line.balance / line.amount_currency if line.amount_currency != 0 else 1
            line.l10n_ec_withhold_tax_amount = line.currency_id.round(
                currency_rate * abs(line.price_total - line.price_subtotal))

    def _get_suggested_supplier_withhold_taxes(self):
        '''
        Returns the VAT and profit withhold tax to be applied on the vendor bill line to calculate a default
        for in the wizard

        For purchases adds prevalence for tax mapping to ease withholds in Ecuador, in the following order:
        For profit withholding tax:
        - If payment type is credit/debit/gift card then only use withhold code 332G (no VAT tax), else:
        - partner_id.taxpayer_type.profit_withhold_tax_id, if not set then
        - product_id profit withhold, if not set then
        - company fallback profit withhold for goods or for services
        For vat withhold tax:
        - If document type is purchase liquidation then withhold 100% from VAT
        - If product is consumable then taxpayer_type vat_goods_withhold_tax_id
        - If product is services or not set then taxpayer_type vat_services_withhold_tax_id
        '''
        self.ensure_one()
        vat_withhold_tax = False
        profit_withhold_tax = False
        taxpayer_type = self.move_id.commercial_partner_id.l10n_ec_taxpayer_type_id
        is_domestic = self.move_id.commercial_partner_id.country_id.code == 'EC'
        product_type = 'services'  # it includes service, event, course and others
        if self.product_id.type == 'consu':
            product_type = 'goods'

        # suggest profit withhold
        if self.move_id.l10n_ec_sri_payment_id.code in ['16', '18', '19']:
            # override all withholds on payments with credit, debit or gift card
            profit_withhold_tax = self.company_id.l10n_ec_withhold_credit_card_tax_id
            return (vat_withhold_tax, profit_withhold_tax)  # no other taxes apply
        elif taxpayer_type.profit_withhold_tax_id:
            profit_withhold_tax = taxpayer_type.profit_withhold_tax_id
        elif self.product_id.l10n_ec_withhold_tax_id:
            profit_withhold_tax = self.product_id.l10n_ec_withhold_tax_id
        elif is_domestic and product_type == 'services':
            profit_withhold_tax = self.company_id.l10n_ec_withhold_services_tax_id
        elif is_domestic and product_type == 'goods':
            profit_withhold_tax = self.company_id.l10n_ec_withhold_goods_tax_id

        # suggest vat withhold
        tax_groups = self.tax_ids.mapped('tax_group_id.l10n_ec_type')
        if set(L10N_EC_VAT_TAX_NOT_ZERO_GROUPS) & set(tax_groups):
            if self.journal_id.l10n_ec_is_purchase_liquidation:
                # law mandates to withhold 100% VAT on purchase liquidations
                vat_withhold_tax = self.env['account.tax'].search([
                    *self.env['account.tax']._check_company_domain(self.company_id),
                    ('tax_group_id.l10n_ec_type', '=', 'withhold_vat_purchase'),
                    ('l10n_ec_code_applied', '=', '731'),  # code for vat withhold 100%
                ])
            elif product_type == 'services':
                vat_withhold_tax = taxpayer_type.vat_services_withhold_tax_id
            else:  # goods
                vat_withhold_tax = taxpayer_type.vat_goods_withhold_tax_id
        return (vat_withhold_tax, profit_withhold_tax)

    def _l10n_ec_prepare_edi_vals_to_export_USD(self):
        results = super()._prepare_edi_vals_to_export()
        currency_rate = self.balance / self.amount_currency if self.amount_currency != 0 else 1

        included_taxes = self.tax_ids.filtered(lambda t: t.price_include)
        if self.quantity and self.discount != 100.0 and included_taxes:
            base_line = self.move_id._prepare_product_base_line_for_taxes_computation(self)
            # We need price unit before discount
            base_line.update({
                'quantity': 1,
                'discount': 0,
            })
            self.env['account.tax']._add_tax_details_in_base_line(base_line, self.company_id, rounding_method='round_globally')
            price_unit = base_line['tax_details']['raw_total_excluded_currency']
        else:
            price_unit = self.price_unit

        return {
            'price_discount': float_round(results['price_discount'] * currency_rate, precision_digits=6),
            'price_unit': float_round(price_unit * currency_rate, precision_digits=6),
        }

    # ============================================
    # Compute overrides when exists purchase reimbursements lines
    # ============================================
    def _compute_name(self):
        amls = self
        if self.move_id._l10n_ec_is_purchase_reimbursement():
            amls = self.filtered(lambda ac: not ac.price_unit)
        super(AccountMoveLine, amls)._compute_name()

    def _compute_product_uom_id(self):
        amls = self
        if self.move_id._l10n_ec_is_purchase_reimbursement():
            amls = self.filtered(lambda ac: not ac.price_unit)
        super(AccountMoveLine, amls)._compute_product_uom_id()

    def _compute_price_unit(self):
        amls = self
        if self.move_id._l10n_ec_is_purchase_reimbursement():
            amls = self.filtered(lambda ac: not ac.price_unit)
        super(AccountMoveLine, amls)._compute_price_unit()

    def _compute_tax_ids(self):
        amls = self
        if self.move_id._l10n_ec_is_purchase_reimbursement():
            amls = self.filtered(lambda ac: not ac.price_unit)
        super(AccountMoveLine, amls)._compute_tax_ids()
