# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from collections import defaultdict
from datetime import date

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare

from odoo.addons.l10n_ec_edi.models.account_tax import L10N_EC_TAXSUPPORTS
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_TAX_HAVEN_OR_LOWER_TAX_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_SUBJECT_WITHHOLD_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_DOUBLE_TAXATION_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WITHHOLD_FOREIGN_REGIME


class L10nEcWizardAccountWithhold(models.TransientModel):
    _name = 'l10n_ec.wizard.account.withhold'
    _description = 'Withhold Wizard'
    _check_company_auto = True

    partner_id = fields.Many2one(related='related_invoice_ids.partner_id')
    # Technical field used to decide if it is local or foreign purchase, and hide/show options
    partner_country_code = fields.Char(related='related_invoice_ids.commercial_partner_id.country_id.code')
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        compute='_compute_journal', readonly=False, store=True,
        required=True, precompute=True,
        check_company=True,
    )
    document_number = fields.Char(string='Document Number')
    manual_document_number = fields.Boolean(
        compute='_compute_manual_document_number',
        string='Manual Number',
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(related='related_invoice_ids.company_id', store=True)
    # Needed for withhold_subtotals widget
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Currency',
    )
    # Technical field to limit elegible invoices related to this withhold
    related_invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string="Invoices",
        readonly=True,
    )
    related_invoices_count = fields.Integer(
        string='Related Invoice Count',
        compute='_compute_related_invoices_fields',
    )
    # Technical field to limit elegible journals and taxes
    withhold_type = fields.Selection(
        selection=[
            ('out_withhold', "Sales Withhold"),
            ('in_withhold', "Purchase Withhold"),
        ],
        compute='_compute_related_invoices_fields',
    )
    withhold_line_ids = fields.One2many(
        comodel_name='l10n_ec.wizard.account.withhold.line',
        inverse_name='wizard_id',
        compute='_compute_withhold_lines', readonly=False, store=True,
        string="Withhold Lines",
    )
    # Subtotals
    withhold_subtotals = fields.Json(
        compute='_compute_withhold_subtotals',
        help="Sales/Purchases subtotals, and total",
    )
    # Foreign purchase fields
    foreign_regime = fields.Selection(
        selection=L10N_EC_WITHHOLD_FOREIGN_REGIME,
        string="Foreign Fiscal Regime",
    )

    # ===== DEFAULT GET: calculate initial fields and lines =====

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if 'related_invoice_ids' in fields_list:
            if self._context.get('active_model') != 'account.move' or not self._context.get('active_ids'):
                raise UserError(_('Withholds must be created from an invoice.'))
            invoices = self.env['account.move'].browse(self._context['active_ids'])
            self._validate_invoices_data_on_open(invoices)
            result['related_invoice_ids'] = [Command.set(invoices.ids)]
        return result

    def _prepare_withhold_line_data(self, invoice):
        withhold_data = []
        # Calculate tax_details grouped for the (profit, VAT) withholds
        profit_grouped, vat_grouped = invoice._get_profit_vat_tax_grouped_details()

        for group, base_key in [(profit_grouped, 'base_amount'), (vat_grouped, 'tax_amount')]:
            for tax_details in group['tax_details'].values():
                if tax_details['withhold_tax']:
                    tax_amount, _dummy = self.env['l10n_ec.wizard.account.withhold.line']._tax_compute_all_helper(
                        tax_details[base_key], tax_details['withhold_tax'])
                    withhold_data.append({
                        'invoice_id': invoice._origin.id,
                        'base': tax_details[base_key],
                        'tax_id': tax_details['withhold_tax'].id,
                        'taxsupport_code': tax_details['tax_support'],
                        'amount': tax_amount,
                    })
        return withhold_data

    #  ===== COMPUTE & ONCHANGE METHODS =====

    @api.depends('related_invoice_ids')
    def _compute_withhold_lines(self):
        for wiz in self:
            # Computes suggested withhold lines for purchase withholds
            if wiz.related_invoice_ids[0].move_type != 'in_invoice':
                wiz.related_invoice_ids = []
                continue

            withhold_lines = []
            invoice = wiz.related_invoice_ids[0]
            withhold_data = self._prepare_withhold_line_data(invoice)
            for data in withhold_data:
                withhold_lines.append(Command.create(data))
            wiz.withhold_line_ids = withhold_lines

    @api.depends('related_invoice_ids')
    def _compute_journal(self):
        for wizard in self:
            withhold = 'in_withhold' if wizard.related_invoice_ids[0].move_type == 'in_invoice' else 'out_withhold'
            withhold_journal = self.env['account.journal'].search([
                ('l10n_ec_withhold_type', '=', withhold),
                ('company_id', '=', wizard.related_invoice_ids[0].company_id.id)],
                limit=1)
            wizard.journal_id = withhold_journal.id

    @api.depends('related_invoice_ids')
    def _compute_related_invoices_fields(self):
        for wizard in self:
            wizard.related_invoices_count = len(wizard.related_invoice_ids)
            wizard.withhold_type = 'in_withhold' if wizard.related_invoice_ids[0].move_type == 'in_invoice' else 'out_withhold'

    @api.depends('journal_id')
    def _compute_manual_document_number(self):
        for wizard in self:
            wizard.manual_document_number = wizard.journal_id.l10n_ec_withhold_type == 'out_withhold'
            if wizard.journal_id.l10n_ec_withhold_type == 'in_withhold':
                # manual when there are not any posted entry with journal
                count = self.env['account.move'].search([
                    ('journal_id', '=', wizard.journal_id.id),
                    ('state', 'in', ['posted', 'cancel'])
                ], limit=1)
                wizard.manual_document_number = not count

    @api.onchange('document_number')
    def _onchange_document_number(self):
        wth_doc_type = self.env.ref("l10n_ec.ec_dt_07")  # Withhold (Comprobante de Retencion)
        doc_number = wth_doc_type._format_document_number(self.document_number)
        if self.document_number != doc_number:
            self.document_number = doc_number

    @api.depends('withhold_line_ids.tax_id', 'withhold_line_ids.amount', 'withhold_line_ids.base')
    def _compute_withhold_subtotals(self):
        def line_dict(withhold_line):
            return {
                'tax_group': withhold_line.tax_id.tax_group_id,
                'amount': withhold_line.amount,
                'base': withhold_line.base,
            }

        for wizard in self:
            lines = wizard.withhold_line_ids.mapped(line_dict)
            wizard.withhold_subtotals = self.env['account.move']._l10n_ec_withhold_subtotals_dict(
                wizard.company_id.currency_id, lines
            )

    # ===== MOVE CREATION METHODS =====

    def action_create_and_post_withhold(self):
        # Withhold validation
        self._validate_withhold_data_on_post()

        # Withhold creation
        vals = self._prepare_withhold_header()
        total_lines = self._prepare_withhold_move_lines()
        vals['line_ids'] = [Command.create(vals) for vals in total_lines]
        withhold = self.env['account.move'].create(vals)
        withhold.action_post()

        # Withhold/Invoice Lines RECONCILIATION
        invoices = withhold.line_ids.mapped("l10n_ec_withhold_invoice_id")
        for inv in invoices:
            wh_reconc = withhold.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                    and l.l10n_ec_withhold_invoice_id == inv)
            inv_reconc = inv.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled)
            (wh_reconc + inv_reconc).reconcile()

        return withhold

    def _prepare_withhold_header(self):
        invoices = self.withhold_line_ids.mapped('invoice_id')
        invoice_date = invoices[0].invoice_date
        last_day_of_month = calendar.monthrange(invoice_date.year, invoice_date.month)[1]
        last_date_in_withhold = date(invoice_date.year, invoice_date.month, last_day_of_month)

        # for the recognition of withhold taxes at the time of recognition of the invoice and invoice taxes
        # and for ensuring proper result in the 103 report, an "orphan" withhold (withhout its base) might result otherwise
        vals = {
            'date': min(self.date, last_date_in_withhold),
            'l10n_ec_withhold_date': self.date,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'move_type': 'entry',
            'l10n_ec_withhold_foreign_regime': self.foreign_regime,
        }

        name_key = 'ref' if self.withhold_type == 'out_withhold' else 'name'
        if self.document_number:
            vals[name_key] = f"Ret {self.document_number}"
        return vals

    @api.model
    def _get_move_line_default_values(self, line, price, debit_wh_type):
        return {
            'partner_id': self.partner_id.commercial_partner_id.id,
            'quantity': 1.0,
            'price_unit': price,
            'debit': price if self.withhold_type == debit_wh_type else 0.0,
            'credit': price if self.withhold_type != debit_wh_type else 0.0,
            'tax_base_amount': 0.0,
            'display_type': 'product',
            'l10n_ec_withhold_invoice_id': line.invoice_id.id,
            'l10n_ec_code_taxsupport': line.taxsupport_code,
        }

    def _prepare_withhold_move_lines(self):
        total_per_invoice = defaultdict(lambda: [0, self.env['l10n_ec.wizard.account.withhold.line']])
        total_lines = []

        # 1. Create the base line (and its counterpart to cancel out) for every withhold line.  Tax lines will be created automatically.
        for line in self.withhold_line_ids:
            dummy, account = line._tax_compute_all_helper(1.0, line.tax_id)
            total_per_invoice[line.invoice_id][0] += line.amount
            total_per_invoice[line.invoice_id][1] = line

            nice_base_label_elements = []
            if line.tax_id.l10n_ec_code_base:
                nice_base_label_elements.append(line.tax_id.l10n_ec_code_base)
            nice_base_label_elements.append("{:.2f}%".format(abs(line.tax_id.amount)))
            nice_base_label_elements.append(line.invoice_id.name)
            nice_base_label = ", ".join(nice_base_label_elements)
            vals_base_line = {
                **self._get_move_line_default_values(line, line.base, 'in_withhold'),
                'name': 'Base Ret: ' + nice_base_label,
                'tax_ids': [Command.set(line.tax_id.ids)],
                'account_id': account,
            }
            total_lines.append(vals_base_line)

            vals_base_line_counterpart = {
                **self._get_move_line_default_values(line, line.base, 'out_withhold'),  # Counterpart 0 operation
                'name': 'Base Ret Cont: ' + nice_base_label,
                'account_id': account,
            }
            total_lines.append(vals_base_line_counterpart)

        # 2. Payable/Receivable line
        # One line for each invoice linked with it
        for invoice, (amount, line) in total_per_invoice.items():
            if self.currency_id.compare_amounts(amount, 0) > 0:
                account = self._get_partner_account(self.partner_id, self.withhold_type)
                vals = {
                    **self._get_move_line_default_values(line, amount, 'in_withhold'),
                    'name': _('Withhold on: %s', invoice.name),
                    'account_id': account.id,
                }
                total_lines.append(vals)
        return total_lines

    def _get_partner_account(self, partner, withhold_type):
        partner = partner.with_company(self.company_id)
        if withhold_type == 'out_withhold':
            return partner.property_account_receivable_id
        return partner.property_account_payable_id

    # ===== MOVE VALIDATION METHODS =====

    @api.model
    def _validate_invoices_data_on_open(self, invoices):
        # Let's test the source invoices for misuse before showing the withhold wizard
        MAP_INVOICE_TYPE_PARTNER_TYPE = {
            'out_invoice': 'customer',
            'out_refund': 'customer',
            'in_invoice': 'supplier',
            'in_refund': 'supplier',
        }
        invoice_months = set()
        for invoice in invoices:
            errors = []
            if invoice.state != 'posted':
                errors.append(_("Withholds can only be created for posted invoices."))
                continue
            invoice_months.add((invoice.invoice_date.month, invoice.invoice_date.year))
            if not invoice.l10n_ec_sri_payment_id and self.withhold_type != 'in_withhold':
                errors.append(_("The SRI Payment Method must be set."))
            if len(invoice_months) > 1:
                errors.append(_("All invoices must be from the same month."))
            if invoice.state != 'posted':
                errors.append(_("The invoice needs to be posted. "))
            if invoice.commercial_partner_id != invoices[0].commercial_partner_id:
                errors.append(_("Some documents belong to different partners"))
            if not invoice.commercial_partner_id.country_id:
                errors.append(_("You must set a Country for Partner: %s", invoice.commercial_partner_id.name))
            if MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type]:
                errors.append(_("Can't mix supplier and customer documents in the same withhold"))
            if (len(invoices) > 1 or invoice.l10n_ec_withhold_ids.filtered(lambda w: w.state == 'posted')) and invoice.move_type == 'in_invoice':
                # We only allow one posted supplier withhold over one single supplier invoice
                errors.append(_("Multiple invoices are only supported in customer withholds"))
            if not invoice.l10n_ec_show_add_withhold:
                errors.append(_("The selected document type does not support withholds."))
            if invoice.move_type == 'out_invoice' and invoice.commercial_partner_id._l10n_ec_get_identification_type() != 'ruc':
                errors.append(_("For recording a withhold the selected partner should have a RUC"))
            if errors:
                errors.append('')
                errors.append(_("For invoice: %s", invoice.name))
        if errors:
            raise ValidationError('\n'.join(errors))

    def _validate_withhold_data_on_post(self):
        """
        Validations that apply only on withhold post, other validations should be on method _validate_invoices_data()
        """
        if not self.withhold_line_ids:
            raise ValidationError(_("You must input at least one withhold line"))

        error = self._validate_helper_for_foreign_tax_codes()
        if any(self.date < i.invoice_date for i in self.related_invoice_ids):
            error += _("The withhold can not have an earlier date than its invoice(s)")
        if error:
            raise ValidationError(error)

    def _validate_helper_for_foreign_tax_codes(self):
        # validates all taxes are of the same type: domestic taxes, foreign taxes, etc
        error = ''
        if not self.foreign_regime:
            return error
        tax_codes = self.withhold_line_ids.mapped('tax_id').filtered(lambda t: t.tax_group_id.l10n_ec_type == 'withhold_income_purchase').mapped('l10n_ec_code_base')
        credit_card_codes = []
        if self.related_invoice_ids.l10n_ec_sri_payment_id.code in ['01', '16', '19']:
            credit_card_codes = ['332']
        valid_foreign_codes = L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES + L10N_EC_WTH_FOREIGN_TAX_HAVEN_OR_LOWER_TAX_CODES + credit_card_codes
        valid_tax_haven_and_lower_codes = L10N_EC_WTH_FOREIGN_TAX_HAVEN_OR_LOWER_TAX_CODES + credit_card_codes
        valid_double_taxation_codes = L10N_EC_WTH_FOREIGN_DOUBLE_TAXATION_CODES + credit_card_codes
        valid_subject_codes = L10N_EC_WTH_FOREIGN_SUBJECT_WITHHOLD_CODES + credit_card_codes

        if self.foreign_regime == '01' and any(tax not in valid_foreign_codes for tax in tax_codes):
            error += _("You have selected a 'Regular' regime but used taxes from 'Fiscal paradise' or 'Preferential tax' "
                       "regime, please select a tax from: %s\n", ', '.join(valid_foreign_codes))
        elif self.foreign_regime != '01' and any(tax not in valid_tax_haven_and_lower_codes for tax in tax_codes):
            error += _("You have selected a 'Fiscal paradise' or 'Preferential tax' regime but used taxes from 'Regular' "
                       "regime, please select a tax from: %s\n", ', '.join(valid_tax_haven_and_lower_codes))
        if len({tax in valid_double_taxation_codes for tax in tax_codes}) > 1:
            error += _("You have selected at least one 'Double taxation withhold' type tax, but mixed with taxes from "
                       "other types.\n The valid 'Double taxation withhold' type taxes are: %s.\n",
                       ', '.join(valid_double_taxation_codes))
        if len({tax in valid_subject_codes for tax in tax_codes}) > 1:
            error += _("You have selected at least one 'Foreign payment subject to withhold in application of the legal "
                       "norm' type of tax, but mixed with other types.\n The valid 'Foreign payment subject to withhold' "
                       "type taxes are: %s.\n", ', '.join(valid_subject_codes))
        return error


class L10nEcWizardAccountWithholdLine(models.TransientModel):
    _name = 'l10n_ec.wizard.account.withhold.line'
    _description = "Withhold Wizard Lines"

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string="Invoice",
        compute='_compute_invoice_id', store=True, readonly=False, precompute=True, required=True,
    )
    taxsupport_code = fields.Selection(
        selection=L10N_EC_TAXSUPPORTS,
        string="Tax Support",
        compute='_compute_taxsupport', store=True, readonly=False,
        help="Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS",
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Tax",
    )
    base = fields.Monetary(
        string="Base",
        compute='_compute_base', store=True, readonly=False,
    )
    amount = fields.Monetary(
        string="Amount",
        compute='_compute_amount', store=True, readonly=False,
    )
    company_id = fields.Many2one(related='wizard_id.company_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    wizard_id = fields.Many2one(
        comodel_name='l10n_ec.wizard.account.withhold',
        required=True,
        auto_join=True,
    )
    sequence = fields.Integer(default=10)

    #  ===== Constraints =====

    @api.constrains('taxsupport_code')
    def _check_withhold_lines(self):
        # checks that every line has a taxsupport_code
        if self[0].wizard_id.withhold_type != 'in_withhold':
            return
        taxsupport_codes = self.invoice_id._l10n_ec_get_inv_taxsupports_and_amounts().keys()
        for line in self:
            if not line.taxsupport_code:
                raise ValidationError(_("Every line must have a tax support code"))
            elif line.taxsupport_code not in taxsupport_codes:
                raise ValidationError(_("Tax support %s is not in the tax supports of the original invoice %s", line.taxsupport_code, taxsupport_codes))

    @api.constrains('base', 'amount')
    def _check_amounts(self):
        for line in self:
            precision = line.wizard_id.company_id.currency_id.decimal_places
            if float_compare(line.amount, 0.0, precision_digits=precision) < 0:
                raise ValidationError(_("Negative values are not allowed in amount for withhold lines"))
            if float_compare(line.base, 0.0, precision_digits=precision) <= 0:
                raise ValidationError(_("Negative or zero values are not allowed in base for withhold lines"))

    #  ===== Computes =====

    @api.depends('wizard_id')
    def _compute_invoice_id(self):
        for line in self:
            line.invoice_id = len(line.wizard_id.related_invoice_ids) == 1 and line.wizard_id.related_invoice_ids._origin.id or False

    @api.depends('invoice_id')
    def _compute_taxsupport(self):
        for line in self:
            taxsupport = line.taxsupport_code
            # on purchase withhold sets the tax support when there is only one tax support for the invoice
            if not taxsupport and line.wizard_id.withhold_type == 'in_withhold' and line.invoice_id:
                taxsupports = line.invoice_id._l10n_ec_get_inv_taxsupports_and_amounts()
                if len(taxsupports) == 1:
                    taxsupport = list(taxsupports.keys())[0]  # gets the key from dict
            line.taxsupport_code = taxsupport

    @api.depends('invoice_id', 'taxsupport_code', 'tax_id')
    def _compute_base(self):
        # Suggest a "base amount" according to linked invoice_id and tax type, and "remaining base" not yet used
        withhold_data = defaultdict(list)
        for line in self:
            base = amount_vat = amount_base = 0.0
            if line.invoice_id:
                if line.wizard_id.withhold_type == 'in_withhold' and line.taxsupport_code:
                    tax_supports = line.invoice_id._origin._l10n_ec_get_inv_taxsupports_and_amounts()
                    taxsupportamounts = tax_supports.get(line.taxsupport_code)
                    if taxsupportamounts:
                        amount_base = taxsupportamounts['amount_base']
                        amount_vat = taxsupportamounts['amount_vat']
                else:
                    amount_base = abs(line.invoice_id.amount_untaxed_signed)
                    amount_vat = abs(line.invoice_id.amount_tax_signed)
                if amount_base and line.tax_id:
                    l10n_ec_type = line.tax_id.tax_group_id.l10n_ec_type
                    # Compute previous lines to get previous base, and deduct from suggested base
                    previous_related_lines = line.wizard_id.withhold_line_ids.filtered(
                        lambda r: r.invoice_id == line.invoice_id._origin
                        and r.taxsupport_code == line.taxsupport_code
                        and r.tax_id.tax_group_id.l10n_ec_type == l10n_ec_type
                        and r != line
                    )
                    if previous_related_lines and len(self) == 1:
                        # When user edits a withhold line in the widget, the onchanges creates a new object to
                        # replace line with it, so we temporary have a duplicate with the same base
                        previous_base = sum(previous_related_lines.mapped('base')) - line.base
                    else:
                        previous_base = 0
                    if l10n_ec_type in ('withhold_vat_sale', 'withhold_vat_purchase'):
                        base = amount_vat - previous_base
                    else:
                        base = amount_base - previous_base
            line.base = base

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        # Recomputes amount according to "base amount" and tax percentage
        for line in self:
            tax_amount = 0.0
            if line.tax_id:
                tax_amount, dummy = self._tax_compute_all_helper(line.base, line.tax_id)
            line.amount = tax_amount

    # === Helper methods ====

    @api.model
    def _tax_compute_all_helper(self, base, tax_id):
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = tax_id.compute_all(
            base,
            currency=tax_id.company_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['taxes'][0]['amount']
        tax_amount = abs(tax_amount)  # For ignoring the sign of the percentage on tax configuration
        tax_account_id = taxes_res['taxes'][0]['account_id']
        return tax_amount, tax_account_id
