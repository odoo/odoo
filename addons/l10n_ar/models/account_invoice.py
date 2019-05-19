# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import re
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    afip_invoice_concepts = [
        ('1', 'Producto / Exportación definitiva de bienes'),
        ('2', 'Servicios'),
        ('3', 'Productos y Servicios'),
        ('4', '4-Otros (exportación)'),
    ]

    l10n_ar_currency_rate = fields.Float(
        copy=False,
        digits=(16, 4),
        # TODO make it editable, we have to change move creation method
        readonly=True,
        string="Currency Rate",
    )
    # Mostly used on reports
    l10n_ar_letter = fields.Selection(
        related='l10n_latam_document_type_id.l10n_ar_letter',
    )
    l10n_ar_afip_responsability_type = fields.Selection(
        related='move_id.l10n_ar_afip_responsability_type',
    )
    l10n_ar_invoice_number = fields.Integer(
        compute='_compute_l10n_ar_invoice_number',
        string='AFIP Invoice Number',
    )
    l10n_ar_afip_pos_number = fields.Integer(
        compute='_compute_l10n_ar_invoice_number',
        string="AFIP Point Of Sale",
    )
    l10n_ar_vat_tax_ids = fields.One2many(
        compute="_compute_argentina_amounts",
        comodel_name='account.invoice.tax',
        help='Vat Taxes and vat tax amounts. Is an ADHOC internal concept',
    )
    l10n_ar_vat_taxable_ids = fields.One2many(
        compute="_compute_argentina_amounts",
        comodel_name='account.invoice.tax',
        help="Does not include afip_code [0, 1, 2] because their are"
        " not taxes themselves: VAT Exempt, VAT Untaxed and VAT Not applicable"
    )
    l10n_ar_not_vat_tax_ids = fields.One2many(
        compute="_compute_argentina_amounts",
        comodel_name='account.invoice.tax',
    )
    l10n_ar_vat_base_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
    )
    l10n_ar_vat_taxable_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
    )
    l10n_ar_vat_exempt_base_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
    )
    l10n_ar_vat_untaxed_base_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
    )
    l10n_ar_vat_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
    )
    l10n_ar_other_taxes_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
    )
    l10n_ar_afip_concept = fields.Selection(
        compute='_compute_l10n_ar_afip_concept',
        inverse='_inverse_l10n_ar_afip_concept',
        selection=afip_invoice_concepts,
        string="AFIP Concept",
        help="A concept is suggested regarding the type of the products on the"
        " invoice but it is allowed to force a different type if required.",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    l10n_ar_force_afip_concept = fields.Selection(
        selection=afip_invoice_concepts,
        string="AFIP Concept",
        readonly=True,
        help='AFIP requires to report the kind of products related to the'
        ' invoices. The possible AFIP concepts are:\n'
        ' * 1 - Producto / Exportación definitiva de bienes\n'
        ' * 2 - Servicios\n'
        ' * 3 - Productos y Servicios\n'
        ' * 4 - Otros (exportación)\n',
    )
    l10n_ar_afip_service_start = fields.Date(
        string='AFIP Service Start Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    l10n_ar_afip_service_end = fields.Date(
        string='AFIP Service End Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    @api.multi
    @api.depends(
        'invoice_line_ids',
        'invoice_line_ids.product_id',
        'invoice_line_ids.product_id.type',
        'l10n_ar_force_afip_concept',
    )
    def _compute_l10n_ar_afip_concept(self):
        for rec in self.filtered(
                lambda x: x.company_id.country_id.code == 'AR' and
                x.l10n_latam_use_documents):
            afip_concept = False
            if rec.l10n_ar_force_afip_concept:
                afip_concept = rec.l10n_ar_force_afip_concept
            else:
                afip_concept = rec._get_concept()
            rec.l10n_ar_afip_concept = afip_concept

    @api.multi
    def _inverse_l10n_ar_afip_concept(self):
        for rec in self:
            if rec._get_concept() == rec.l10n_ar_afip_concept:
                rec.l10n_ar_force_afip_concept = False
            else:
                rec.l10n_ar_force_afip_concept = rec.l10n_ar_afip_concept

    @api.multi
    def _get_concept(self):
        """ Method to get the concept of the invoice considering the type of
        the products on the invoice
        """
        self.ensure_one()
        invoice_lines = self.invoice_line_ids
        product_types = set([
            x.product_id.type for x in invoice_lines
            if x.product_id])
        consumible = set(['consu', 'product'])
        service = set(['service'])
        mixed = set(['consu', 'service', 'product'])
        # default value "product"
        afip_concept = '1'
        if product_types.issubset(mixed):
            afip_concept = '3'
        if product_types.issubset(service):
            afip_concept = '2'
        if product_types.issubset(consumible):
            afip_concept = '1'
        # on expo invoice you can mix services and products
        if self.l10n_latam_document_type_id.code in ['19', '20', '21']:
            if afip_concept == '3':
                afip_concept = '1'
        return afip_concept

    @api.multi
    def _compute_argentina_amounts(self):
        for rec in self:
            vat_taxes = rec.tax_line_ids.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.l10n_ar_type == 'tax' and
                    r.tax_id.tax_group_id.l10n_ar_tax == 'vat'))
            # we add and "r.base" because only if a there is a base amount it
            # is considered taxable, this is used for eg to validate invoices
            # on afip
            vat_taxables = vat_taxes.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.l10n_ar_afip_code not in
                    [0, 1, 2]) and r.base)

            l10n_ar_vat_amount = sum(vat_taxes.mapped('amount'))
            rec.l10n_ar_vat_tax_ids = vat_taxes
            rec.l10n_ar_vat_taxable_ids = vat_taxables
            rec.l10n_ar_vat_amount = l10n_ar_vat_amount
            rec.l10n_ar_vat_taxable_amount = sum(vat_taxables.mapped('base'))
            rec.l10n_ar_vat_base_amount = sum(vat_taxes.mapped('base'))

            # vat exempt values (are the ones with code 2)
            vat_exempt_taxes = rec.tax_line_ids.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.l10n_ar_type == 'tax' and
                    r.tax_id.tax_group_id.l10n_ar_tax == 'vat' and
                    r.tax_id.tax_group_id.l10n_ar_afip_code == 2))
            rec.l10n_ar_vat_exempt_base_amount = sum(
                vat_exempt_taxes.mapped('base'))

            # vat untaxed values / no gravado (are the ones with code 1)
            vat_untaxed_taxes = rec.tax_line_ids.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.l10n_ar_type == 'tax' and
                    r.tax_id.tax_group_id.l10n_ar_tax == 'vat' and
                    r.tax_id.tax_group_id.l10n_ar_afip_code == 1))
            rec.l10n_ar_vat_untaxed_base_amount = sum(
                vat_untaxed_taxes.mapped('base'))

            # other taxes values
            not_vat_taxes = rec.tax_line_ids - vat_taxes
            l10n_ar_other_taxes_amount = sum(not_vat_taxes.mapped('amount'))
            rec.l10n_ar_not_vat_tax_ids = not_vat_taxes
            rec.l10n_ar_other_taxes_amount = l10n_ar_other_taxes_amount

    @api.multi
    @api.depends('l10n_latam_document_number', 'number')
    def _compute_l10n_ar_invoice_number(self):
        for rec in self.filtered('l10n_latam_document_number'):
            str_number = rec.l10n_latam_document_number
            if rec.l10n_latam_document_type_id.code in ['33', '99', '331', '332']:
                point_of_sale = '0'
                # leave only numbers and convert to integer
                # otherwise use date as a number
                if re.search(r'\d', str_number):
                    invoice_number = str_number
                else:
                    invoice_number = rec.date_invoice
            # despachos de importacion
            elif rec.l10n_latam_document_type_id.code == '66':
                point_of_sale = '0'
                invoice_number = '0'
            elif "-" in str_number:
                splited_number = str_number.split('-')
                invoice_number = splited_number.pop()
                point_of_sale = splited_number.pop()
            elif "-" not in str_number and len(str_number) == 12:
                point_of_sale = str_number[:4]
                invoice_number = str_number[-8:]
            else:
                raise ValidationError(_(
                    'Could not get invoice number and point of sale for '
                    'Invoice [%i] %s') % (rec.id, rec.display_name))
            rec.l10n_ar_invoice_number = int(
                re.sub("[^0-9]", "", invoice_number))
            rec.l10n_ar_afip_pos_number = int(
                re.sub("[^0-9]", "", point_of_sale))

    @api.multi
    def get_localization_invoice_vals(self):
        self.ensure_one()
        if self.company_id.country_id.code == 'AR':
            if self.company_id.currency_id == self.currency_id:
                l10n_ar_currency_rate = 1.0
            else:
                currency = self.currency_id.with_context(
                    date=self.date_invoice or fields.Date.context_today(self))
                l10n_ar_currency_rate = currency.compute(
                    1., self.company_id.currency_id, round=False)
            return {
                'l10n_ar_currency_rate': l10n_ar_currency_rate,
            }
        else:
            return super(
                AccountInvoice, self).get_localization_invoice_vals()

    @api.model
    def _get_available_document_types(
            self, journal, invoice_type, partner):
        if journal.company_id.country_id.code != 'AR':
            return super(
                AccountInvoice, self)._get_available_document_types(
                    journal, invoice_type, partner)

        document_types = document_type = self.env[
            'l10n_latam.document.type']

        commercial_partner = partner.commercial_partner_id

        if journal.l10n_latam_use_documents and commercial_partner:

            letters = journal.get_journal_letter(
                counterpart_partner=commercial_partner)

            if invoice_type in ['out_refund', 'in_refund']:
                internal_types = ['credit_note']
            else:
                internal_types = ['invoice', 'debit_note', 'receipt']

            domain = [
                ('internal_type', 'in', internal_types),
                '|', ('l10n_ar_letter', '=', False),
                ('l10n_ar_letter', 'in', letters),
            ]

            codes = journal.get_journal_codes()
            if codes:
                domain.append(('code', 'in', codes))

            document_types = document_types.search(domain)

            # If internal_type is in context we try to search for an
            # specific document. for eg used on debit notes
            internal_type = self._context.get('internal_type', False)
            if internal_type:
                document_type = document_type.search(
                    [('internal_type', '=', internal_type)] + domain, limit=1)

            # If not specific document type found, we choose another one
            if not document_type and document_types:
                document_type = document_types[0]

        return {
            'available_document_types': document_types,
            'document_type': document_type,
        }

    @api.multi
    def action_move_create(self):
        """
        We add currency rate on move creation so it can be used by electronic
        invoice later on action_number
        """
        self.check_argentinian_invoice_taxes()
        return super(AccountInvoice, self).action_move_create()

    @api.multi
    def check_argentinian_invoice_taxes(self):
        _logger.info('Running checks related to argentinian documents')

        # we consider argentinian invoices the ones from companies with
        # localization localization and that belongs to a journal with
        # use_documents
        argentinian_invoices = self.filtered(
            lambda r: (
                r.company_id.country_id.code != 'AR' and r.l10n_latam_use_documents))
        if not argentinian_invoices:
            return True

        # we check that there is one and only one vat tax. We check upon
        # validation to avoid errors on invoice creations from other menus
        # and for performance
        for inv_line in argentinian_invoices.filtered(
                lambda x: x.company_id.l10n_ar_company_requires_vat).mapped(
                    'invoice_line_ids'):
            vat_taxes = inv_line.invoice_line_tax_ids.filtered(
                lambda x:
                x.tax_group_id.l10n_ar_tax == 'vat' and x.tax_group_id.l10n_ar_type == 'tax')
            if len(vat_taxes) != 1:
                raise ValidationError(_(
                    'Debe haber un y solo un impuesto de IVA por línea. '
                    'Verificar líneas con producto "%s"' % (
                        inv_line.product_id.name)))

        # check partner has responsability so it will be assigned on invoice
        # validate
        without_responsability = argentinian_invoices.filtered(
            lambda x:
                not x.commercial_partner_id.l10n_ar_afip_responsability_type)
        if without_responsability:
            raise ValidationError(_(
                'The following invoices has a partner without AFIP '
                'responsability:\n\n'
                '%s') % ('\n'.join(
                    ['[%i] %s' % (i.id, i.display_name)
                        for i in without_responsability])))

        # we check all invoice tax lines has tax_id related
        # we exclude exempt vats and untaxed (no gravados)
        wihtout_tax_id = argentinian_invoices.mapped('tax_line_ids').filtered(
            lambda r: not r.tax_id)
        if wihtout_tax_id:
            raise ValidationError(_(
                "Some Invoice Tax Lines don't have a tax_id asociated, please "
                "correct them or try to refresh invoice. Tax lines: %s") % (
                ', '.join(wihtout_tax_id.mapped('name'))))

        # check codes has argentinian tax attributes configured
        tax_groups = argentinian_invoices.mapped(
            'tax_line_ids.tax_id.tax_group_id')
        unconfigured_tax_groups = tax_groups.filtered(
            lambda r: not r.l10n_ar_type or
            not r.l10n_ar_tax or not r.l10n_ar_application)
        if unconfigured_tax_groups:
            raise ValidationError(_(
                "You are using argentinian localization and there are some tax"
                " groups that are not configured. Tax Groups (id): %s" % (
                    ', '.join(unconfigured_tax_groups.mapped(
                        lambda x: '%s (%s)' % (x.name, x.id))))))

        # verificamos facturas de compra que deben reportar cuit y no lo tienen
        # configurado
        without_cuit = argentinian_invoices.filtered(
            lambda x: x.type in ['in_invoice', 'in_refund'] and
            x.l10n_latam_document_type_id.purchase_cuit_required and
            not x.commercial_partner_id.cuit)
        if without_cuit:
            raise ValidationError(_(
                'Las siguientes partners no tienen configurado CUIT: %s') % (
                    ', '.join(
                        without_cuit.mapped('commercial_partner_id.name'))
            ))

        # facturas que no debería tener ningún iva y tienen
        not_zero_alicuot = argentinian_invoices.filtered(
            lambda x: x.type in ['in_invoice', 'in_refund'] and
            x.l10n_latam_document_type_id.purchase_alicuots == 'zero' and
            any([t.tax_id.tax_group_id.l10n_ar_afip_code != 0 for t in x.l10n_ar_vat_tax_ids]))
        if not_zero_alicuot:
            raise ValidationError(_(
                'Las siguientes facturas tienen configurados IVA incorrecto. '
                'Debe utilizar IVA no corresponde.\n*Facturas: %s') % (
                    ', '.join(not_zero_alicuot.mapped('display_name'))
            ))

        # facturas que debería tener iva y tienen no corresponde
        zero_alicuot = argentinian_invoices.filtered(
            lambda x: x.type in ['in_invoice', 'in_refund'] and
            x.l10n_latam_document_type_id.purchase_alicuots == 'not_zero' and
            any([t.tax_id.tax_group_id.l10n_ar_afip_code == 0 for t in x.l10n_ar_vat_tax_ids]))
        if zero_alicuot:
            raise ValidationError(_(
                'Las siguientes facturas tienen IVA no corresponde pero debe '
                'seleccionar una alícuota correcta (No gravado, Exento, Cero, '
                '10,5, etc).\n*Facturas: %s') % (
                    ', '.join(zero_alicuot.mapped('display_name'))
            ))

        # Check except vat invoice
        afip_exempt_codes = ['Z', 'X', 'E', 'N', 'C']
        for invoice in argentinian_invoices:
            special_vat_taxes = invoice.tax_line_ids.filtered(
                lambda r: r.tax_id.tax_group_id.l10n_ar_afip_code in [1, 2, 3])
            if (
                    special_vat_taxes and
                    invoice.fiscal_position_id.l10n_ar_afip_code
                    not in afip_exempt_codes):
                raise ValidationError(_(
                    "If you have choose a 0, exempt or untaxed 'tax', or "
                    "you must choose a fiscal position with afip code in %s.\n"
                    "* Invoice [%i] %s") % (
                        afip_exempt_codes,
                        invoice.id,
                        invoice.display_name))

            # esto es, por eje, si hay un producto con 100% de descuento para
            # única alicuota, entonces el impuesto liquidado da cero y se
            # obliga reportar con alicuota 0, entonces se exige tmb cod de op.
            # esta restriccion no es de FE si no de aplicativo citi
            zero_vat_lines = invoice.tax_line_ids.filtered(
                lambda r: ((
                    r.tax_id.tax_group_id.l10n_ar_afip_code in [4, 5, 6, 8, 9] and
                    r.currency_id.is_zero(r.amount))))
            if (
                    zero_vat_lines and
                    invoice.fiscal_position_id.l10n_ar_afip_code
                    not in afip_exempt_codes):
                raise ValidationError(_(
                    "Si hay líneas con IVA declarado 0, entonces debe elegir "
                    "una posición fiscal con código de afip '%s'.\n"
                    "* Invoice [%i] %s") % (
                        afip_exempt_codes,
                        invoice.id,
                        invoice.display_name))

    @api.constrains('date_invoice')
    def set_date_afip(self):
        for rec in self.filtered('date_invoice'):
            date_invoice = fields.Datetime.from_string(rec.date_invoice)
            vals = {}
            if not rec.l10n_ar_afip_service_start:
                vals['l10n_ar_afip_service_start'] = (
                    date_invoice + relativedelta(day=1))
            if not rec.l10n_ar_afip_service_end:
                vals['l10n_ar_afip_service_end'] = date_invoice + \
                    relativedelta(day=1, days=-1, months=+1)
            if vals:
                rec.write(vals)
