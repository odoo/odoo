# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):

    _inherit = 'account.move'

    @api.model
    def _l10n_ar_get_document_number_parts(self, document_number, document_type_code):
        # import shipments
        if document_type_code in ['66', '67']:
            pos = invoice_number = '0'
        else:
            pos, invoice_number = document_number.split('-')
        return {'invoice_number': int(invoice_number), 'point_of_sale': int(pos)}

    l10n_ar_afip_responsibility_type_id = fields.Many2one(
        'l10n_ar.afip.responsibility.type', string='AFIP Responsibility Type', help='Defined by AFIP to'
        ' identify the type of responsibilities that a person or a legal entity could have and that impacts in the'
        ' type of operations and requirements they need.')

    # Mostly used on reports
    l10n_ar_afip_concept = fields.Selection(
        compute='_compute_l10n_ar_afip_concept', selection='_get_afip_invoice_concepts', string="AFIP Concept",
        help="A concept is suggested regarding the type of the products on the invoice.")
    l10n_ar_afip_service_start = fields.Date(string='AFIP Service Start Date')
    l10n_ar_afip_service_end = fields.Date(string='AFIP Service End Date')

    def _is_manual_document_number(self):
        """ Document number should be manual input by user when the journal use documents and

        * if sales journal and not a AFIP pos (liquido producto case)
        * if purchase journal and not a AFIP pos (regular case of vendor bills)

        All the other cases the number should be automatic set, wiht only one exception, for pre-printed/online AFIP
        POS type, the first numeber will be always set manually by the user and then will be computed automatically
        from there """
        if self.country_code != 'AR':
            return super()._is_manual_document_number()

        # NOTE: There is a corner case where 2 sales documents can have the same number for the same DOC from a
        # different vendor, in that case, the user can create a new Sales Liquido Producto Journal
        return self.l10n_latam_use_documents and self.journal_id.type in ['purchase', 'sale'] and \
            not self.journal_id.l10n_ar_is_pos

    @api.constrains('move_type', 'journal_id')
    def _check_moves_use_documents(self):
        """ Do not let to create not invoices entries in journals that use documents """
        not_invoices = self.filtered(lambda x: x.company_id.account_fiscal_country_id.code == "AR" and x.journal_id.type in ['sale', 'purchase'] and x.l10n_latam_use_documents and not x.is_invoice())
        if not_invoices:
            raise ValidationError(_("The selected Journal can't be used in this transaction, please select one that doesn't use documents as these are just for Invoices."))

    @api.constrains('move_type', 'l10n_latam_document_type_id')
    def _check_invoice_type_document_type(self):
        """ LATAM module define that we are not able to use debit_note or invoice document types in an invoice refunds,
        However for Argentinian Document Type's 99 (internal type = invoice) we are able to used in a refund invoices.

        In this method we exclude the argentinian documents that can be used as invoice and refund from the generic
        constraint """
        docs_used_for_inv_and_ref = self.filtered(
            lambda x: x.country_code == 'AR' and
            x.l10n_latam_document_type_id.code in self._get_l10n_ar_codes_used_for_inv_and_ref() and
            x.move_type in ['out_refund', 'in_refund'])

        super(AccountMove, self - docs_used_for_inv_and_ref)._check_invoice_type_document_type()

    def _get_afip_invoice_concepts(self):
        """ Return the list of values of the selection field. """
        return [('1', 'Products / Definitive export of goods'), ('2', 'Services'), ('3', 'Products and Services'),
                ('4', '4-Other (export)')]

    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id', 'invoice_line_ids.product_id.type', 'journal_id')
    def _compute_l10n_ar_afip_concept(self):
        recs_afip = self.filtered(lambda x: x.company_id.account_fiscal_country_id.code == "AR" and x.l10n_latam_use_documents)
        for rec in recs_afip:
            rec.l10n_ar_afip_concept = rec._get_concept()
        remaining = self - recs_afip
        remaining.l10n_ar_afip_concept = ''

    def _get_concept(self):
        """ Method to get the concept of the invoice considering the type of the products on the invoice """
        self.ensure_one()
        invoice_lines = self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section'))
        product_types = set([x.product_id.type for x in invoice_lines if x.product_id])
        consumable = {'consu'}
        service = set(['service'])
        # on expo invoice you can mix services and products
        expo_invoice = self.l10n_latam_document_type_id.code in ['19', '20', '21']

        # WSFEX 1668 - If Expo invoice and we have a "IVA Liberado – Ley Nº 19.640" (Zona Franca) partner
        # then AFIP concept to use should be type "Others (4)"
        is_zona_franca = self.partner_id.l10n_ar_afip_responsibility_type_id == self.env.ref("l10n_ar.res_IVA_LIB")
        # Default value "product"
        afip_concept = '1'
        if expo_invoice and is_zona_franca:
            afip_concept = '4'
        elif product_types == service:
            afip_concept = '2'
        elif product_types - consumable and product_types - service and not expo_invoice:
            afip_concept = '3'
        return afip_concept

    @api.model
    def _get_l10n_ar_codes_used_for_inv_and_ref(self):
        """ List of document types that can be used as an invoice and refund. This list can be increased once needed
        and demonstrated. As far as we've checked document types of wsfev1 don't allow negative amounts so, for example
        document 61 could not be used as refunds. """
        return ['99', '186', '188', '189', '60']

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.journal_id.company_id.account_fiscal_country_id.code == "AR":
            letters = self.journal_id._get_journal_letter(counterpart_partner=self.partner_id.commercial_partner_id)
            domain += ['|', ('l10n_ar_letter', '=', False), ('l10n_ar_letter', 'in', letters)]
            domain = expression.AND([
                domain or [],
                self.journal_id._get_journal_codes_domain(),
            ])
            if self.move_type in ['out_refund', 'in_refund']:
                domain = ['|', ('code', 'in', self._get_l10n_ar_codes_used_for_inv_and_ref())] + domain
        return domain

    def _check_argentinean_invoice_taxes(self):

        # check vat on companies thats has it (Responsable inscripto)
        for inv in self.filtered(lambda x: x.company_id.l10n_ar_company_requires_vat):
            purchase_aliquots = 'not_zero'
            # we require a single vat on each invoice line except from some purchase documents
            if inv.move_type in ['in_invoice', 'in_refund'] and inv.l10n_latam_document_type_id.purchase_aliquots == 'zero':
                purchase_aliquots = 'zero'
            for line in inv.mapped('invoice_line_ids').filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
                vat_taxes = line.tax_ids.filtered(lambda x: x.tax_group_id.l10n_ar_vat_afip_code)
                if len(vat_taxes) != 1:
                    raise UserError(_("There should be a single tax from the “VAT“ tax group per line, but this is not the case for line “%s”. Please add a tax to this line or check the tax configuration's advanced options for the corresponding field “Tax Group”.", line.name))

                elif purchase_aliquots == 'zero' and vat_taxes.tax_group_id.l10n_ar_vat_afip_code != '0':
                    raise UserError(_('On invoice id “%s” you must use VAT Not Applicable on every line.', inv.id))
                elif purchase_aliquots == 'not_zero' and vat_taxes.tax_group_id.l10n_ar_vat_afip_code == '0':
                    raise UserError(_('On invoice id “%s” you must use a VAT tax that is not VAT Not Applicable', inv.id))

    def _set_afip_service_dates(self):
        for rec in self.filtered(lambda m: m.invoice_date and m.l10n_ar_afip_concept in ['2', '3', '4']):
            if not rec.l10n_ar_afip_service_start:
                rec.l10n_ar_afip_service_start = rec.invoice_date + relativedelta(day=1)
            if not rec.l10n_ar_afip_service_end:
                rec.l10n_ar_afip_service_end = rec.invoice_date + relativedelta(day=1, days=-1, months=+1)

    def _set_afip_responsibility(self):
        """ We save the information about the receptor responsability at the time we validate the invoice, this is
        necessary because the user can change the responsability after that any time """
        for rec in self:
            rec.l10n_ar_afip_responsibility_type_id = rec.commercial_partner_id.l10n_ar_afip_responsibility_type_id.id

    @api.onchange('partner_id')
    def _onchange_afip_responsibility(self):
        if self.company_id.account_fiscal_country_id.code == 'AR' and self.l10n_latam_use_documents and self.partner_id \
           and not self.partner_id.l10n_ar_afip_responsibility_type_id:
            return {'warning': {
                'title': _('Missing Partner Configuration'),
                'message': _('Please configure the AFIP Responsibility for "%s" in order to continue',
                    self.partner_id.name)}}

    @api.onchange('partner_id')
    def _onchange_partner_journal(self):
        """ This method is used when the invoice is created from the sale or subscription """
        expo_journals = ['FEERCEL', 'FEEWS', 'FEERCELP']
        for rec in self.filtered(lambda x: x.company_id.account_fiscal_country_id.code == "AR" and x.journal_id.type == 'sale'
                                 and x.l10n_latam_use_documents and x.partner_id.l10n_ar_afip_responsibility_type_id):
            res_code = rec.partner_id.l10n_ar_afip_responsibility_type_id.code
            domain = [
                *self.env['account.journal']._check_company_domain(rec.company_id),
                ('l10n_latam_use_documents', '=', True),
                ('type', '=', 'sale'),
            ]
            journal = self.env['account.journal']
            msg = False
            if res_code in ['9', '10'] and rec.journal_id.l10n_ar_afip_pos_system not in expo_journals:
                # if partner is foregin and journal is not of expo, we try to change to expo journal
                journal = journal.search(domain + [('l10n_ar_afip_pos_system', 'in', expo_journals)], limit=1)
                msg = _('You are trying to create an invoice for foreign partner but you don\'t have an exportation journal')
            elif res_code not in ['9', '10'] and rec.journal_id.l10n_ar_afip_pos_system in expo_journals:
                # if partner is NOT foregin and journal is for expo, we try to change to local journal
                journal = journal.search(domain + [('l10n_ar_afip_pos_system', 'not in', expo_journals)], limit=1)
                msg = _('You are trying to create an invoice for domestic partner but you don\'t have a domestic market journal')
            if journal:
                rec.journal_id = journal.id
            elif msg:
                # Throw an error to user in order to proper configure the journal for the type of operation
                action = self.env.ref('account.action_account_journal_form')
                raise RedirectWarning(msg, action.id, _('Go to Journals'))

    def _post(self, soft=True):
        ar_invoices = self.filtered(lambda x: x.company_id.account_fiscal_country_id.code == "AR" and x.l10n_latam_use_documents)
        # We make validations here and not with a constraint because we want validation before sending electronic
        # data on l10n_ar_edi
        ar_invoices._check_argentinean_invoice_taxes()
        posted = super()._post(soft=soft)

        posted_ar_invoices = posted & ar_invoices
        posted_ar_invoices._set_afip_responsibility()
        posted_ar_invoices._set_afip_service_dates()
        return posted

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if not default_values_list:
            default_values_list = [{} for move in self]
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'l10n_ar_afip_service_start': move.l10n_ar_afip_service_start,
                'l10n_ar_afip_service_end': move.l10n_ar_afip_service_end,
            })
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number', 'partner_id')
    def _inverse_l10n_latam_document_number(self):
        super()._inverse_l10n_latam_document_number()

        to_review = self.filtered(lambda x: (
            x.journal_id.l10n_ar_is_pos
            and x.l10n_latam_document_type_id
            and x.l10n_latam_document_number
            and (x.l10n_latam_manual_document_number or not x.highest_name)
            and x.l10n_latam_document_type_id.country_id.code == 'AR'
        ))
        for rec in to_review:
            number = rec.l10n_latam_document_type_id._format_document_number(rec.l10n_latam_document_number)
            current_pos = int(number.split("-")[0])
            if current_pos != rec.journal_id.l10n_ar_afip_pos_number:
                invoices = self.search([('journal_id', '=', rec.journal_id.id), ('posted_before', '=', True)], limit=1)
                # If there is no posted before invoices the user can change the POS number (x.l10n_latam_document_number)
                if (not invoices):
                    rec.journal_id.l10n_ar_afip_pos_number = current_pos
                    rec.journal_id._onchange_set_short_name()
                # If not, avoid that the user change the POS number
                else:
                    raise UserError(_('The document number can not be changed for this journal, you can only modify'
                                      ' the POS number if there is not posted (or posted before) invoices'))

    def _get_formatted_sequence(self, number=0):
        return "%s %05d-%08d" % (self.l10n_latam_document_type_id.doc_code_prefix,
                                 self.journal_id.l10n_ar_afip_pos_number, number)

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number """
        if self.journal_id.l10n_latam_use_documents and self.company_id.account_fiscal_country_id.code == "AR":
            if self.l10n_latam_document_type_id:
                return self._get_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.account_fiscal_country_id.code == "AR" and self.l10n_latam_use_documents:
            where_string += " AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s"
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
        return where_string, param

    def _l10n_ar_get_amounts(self, company_currency=False):
        """ Method used to prepare data to present amounts and taxes related amounts when creating an
        electronic invoice for argentinean and the txt files for digital VAT books. Only take into account the argentinean taxes """
        self.ensure_one()
        amount_field = company_currency and 'balance' or 'amount_currency'
        # if we use balance we need to correct sign (on price_subtotal is positive for refunds and invoices)
        sign = -1 if self.is_inbound() else 1

        # if we are on a document that works invoice and refund and it's a refund, we need to export it as negative
        sign = -sign if self.move_type in ('out_refund', 'in_refund') and\
            self.l10n_latam_document_type_id.code in self._get_l10n_ar_codes_used_for_inv_and_ref() else sign

        tax_lines = self.line_ids.filtered('tax_line_id')
        vat_taxes = tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id.l10n_ar_vat_afip_code)

        vat_taxable = self.env['account.move.line']
        for line in self.invoice_line_ids:
            if any(tax.tax_group_id.l10n_ar_vat_afip_code and tax.tax_group_id.l10n_ar_vat_afip_code not in ['0', '1', '2'] for tax in line.tax_ids):
                vat_taxable |= line

        profits_tax_group = self.env['account.chart.template'].with_company(self.company_id).ref(
            'tax_group_percepcion_ganancias',
            raise_if_not_found=False,
        )
        if not profits_tax_group:
            raise RedirectWarning(
                message=_(
                    "A required tax group could not be found (XML ID: %s).\n"
                    "Please reload your chart template in order to reinstall the required tax group.\n\n"
                    "Note: You might have to relink your existing taxes to this new tax group.",
                    'tax_group_percepcion_ganancias',
                ),
                action=self.env.ref('account.action_account_config').id,
                button_text=_("Accounting Settings"),
            )

        return {'vat_amount': sign * sum(vat_taxes.mapped(amount_field)),
                # For invoices of letter C should not pass VAT
                'vat_taxable_amount': sign * sum(vat_taxable.mapped(amount_field)) if self.l10n_latam_document_type_id.l10n_ar_letter != 'C' else self.amount_untaxed,
                'vat_exempt_base_amount': sign * sum(self.invoice_line_ids.filtered(lambda x: x.tax_ids.filtered(lambda y: y.tax_group_id.l10n_ar_vat_afip_code == '2')).mapped(amount_field)),
                'vat_untaxed_base_amount': sign * sum(self.invoice_line_ids.filtered(lambda x: x.tax_ids.filtered(lambda y: y.tax_group_id.l10n_ar_vat_afip_code == '1')).mapped(amount_field)),
                # used on FE
                'not_vat_taxes_amount': sign * sum((tax_lines - vat_taxes).mapped(amount_field)),
                # used on BFE + TXT
                'iibb_perc_amount': sign * sum(tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code == '07').mapped(amount_field)),
                'mun_perc_amount': sign * sum(tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code == '08').mapped(amount_field)),
                'intern_tax_amount': sign * sum(tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code == '04').mapped(amount_field)),
                'other_taxes_amount': sign * sum(tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code == '99').mapped(amount_field)),
                'profits_perc_amount': sign * sum(tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id == profits_tax_group).mapped(amount_field)),
                'vat_perc_amount': sign * sum(tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code == '06').mapped(amount_field)),
                'other_perc_amount': sign * sum(tax_lines.filtered(lambda r: r.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code == '09' and r.tax_line_id.tax_group_id != profits_tax_group).mapped(amount_field)),
                }

    def _get_vat(self):
        """ Applies on wsfe web service and in the VAT digital books """
        # if we are on a document that works invoice and refund and it's a refund, we need to export it as negative
        sign = -1 if self.move_type in ('out_refund', 'in_refund') and\
            self.l10n_latam_document_type_id.code in self._get_l10n_ar_codes_used_for_inv_and_ref() else 1

        res = []
        vat_taxable = self.env['account.move.line']
        # get all invoice lines that are vat taxable
        for line in self.line_ids:
            if any(tax.tax_group_id.l10n_ar_vat_afip_code and tax.tax_group_id.l10n_ar_vat_afip_code not in ['0', '1', '2'] for tax in line.tax_line_id) and line['amount_currency']:
                vat_taxable |= line
        for tax_group in vat_taxable.mapped('tax_group_id'):
            base_imp = sum(self.invoice_line_ids.filtered(lambda x: x.tax_ids.filtered(lambda y: y.tax_group_id.l10n_ar_vat_afip_code == tax_group.l10n_ar_vat_afip_code)).mapped('price_subtotal'))
            imp = abs(sum(vat_taxable.filtered(lambda x: x.tax_group_id.l10n_ar_vat_afip_code == tax_group.l10n_ar_vat_afip_code).mapped('amount_currency')))
            res += [{'Id': tax_group.l10n_ar_vat_afip_code,
                     'BaseImp': sign * base_imp,
                     'Importe': sign * imp}]

        # Report vat 0%
        vat_base_0 = sum(self.invoice_line_ids.filtered(lambda x: x.tax_ids.filtered(lambda y: y.tax_group_id.l10n_ar_vat_afip_code == '3')).mapped('price_subtotal'))
        if vat_base_0:
            res += [{'Id': '3', 'BaseImp': sign * vat_base_0, 'Importe': 0.0}]

        return res if res else []

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.company_id.account_fiscal_country_id.code == 'AR':
            return 'l10n_ar.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_ar_get_invoice_totals_for_report(self):
        """If the invoice document type indicates that vat should not be detailed in the printed report (result of _l10n_ar_include_vat()) then we overwrite tax_totals field so that includes taxes in the total amount, otherwise it would be showing amount_untaxed in the amount_total"""
        self.ensure_one()
        tax_totals = self.tax_totals
        include_vat = self._l10n_ar_include_vat()
        if not include_vat:
            return tax_totals

        tax_group_ids = {
            tax_group['id']
            for subtotal in tax_totals['subtotals']
            for tax_group in subtotal['tax_groups']
        }
        tax_group_ids_to_exclude = self.env['account.tax.group']\
            .browse(tax_group_ids)\
            .filtered(lambda tax_group: (
                self._l10n_ar_is_tax_group_other_national_ind_tax(tax_group)
                or self._l10n_ar_is_tax_group_vat(tax_group)
            )).ids
        if tax_group_ids_to_exclude:
            tax_totals = self.env['account.tax']._exclude_tax_groups_from_tax_totals_summary(tax_totals, tax_group_ids_to_exclude)
        return tax_totals

    def _l10n_ar_get_invoice_custom_tax_summary_for_report(self):
        """ Get a new tax details for RG 5614/2024 to show ARCA VAT and Other National Internal Taxes. """
        if self.l10n_latam_document_type_id.code not in ('6', '7', '8'):
            return []

        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            tax_group = tax_data['tax'].tax_group_id
            skip = False
            name = None
            if self._l10n_ar_is_tax_group_other_national_ind_tax(tax_group):
                name = _("Other National Ind. Taxes %s", base_line['currency_id'].symbol)
            elif self._l10n_ar_is_tax_group_vat(tax_group):
                name = _("VAT Content %s", base_line['currency_id'].symbol)
            else:
                skip = True
            return {
                'name': name,
                'skip': skip,
            }

        AccountTax = self.env['account.tax']
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        results = []
        for grouping_key, values in values_per_grouping_key.items():
            if (
                grouping_key
                and not grouping_key['skip']
                and not self.currency_id.is_zero(values['tax_amount_currency'])
            ):
                results.append({
                    'name': grouping_key['name'],
                    'tax_amount_currency': values['tax_amount_currency'],
                    'formatted_tax_amount_currency': formatLang(self.env, values['tax_amount_currency']),
                })
        return results

    def _l10n_ar_include_vat(self):
        self.ensure_one()
        return self.l10n_latam_document_type_id.l10n_ar_letter in ['B', 'C', 'X', 'R']

    @api.model
    def _l10n_ar_is_tax_group_other_national_ind_tax(self, tax_group):
        return tax_group.l10n_ar_tribute_afip_code in ('01', '04')

    @api.model
    def _l10n_ar_is_tax_group_vat(self, tax_group):
        return bool(tax_group.l10n_ar_vat_afip_code)
