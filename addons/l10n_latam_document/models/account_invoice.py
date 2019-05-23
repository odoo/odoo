# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):

    _inherit = "account.invoice"
    _order = "date_invoice desc, l10n_latam_document_number desc, number desc, id desc"

    l10n_latam_amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_l10n_latam_amount_and_taxes'
    )
    l10n_latam_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_l10n_latam_amount_and_taxes'
    )
    l10n_latam_tax_line_ids = fields.One2many(
        compute="_compute_l10n_latam_amount_and_taxes",
        comodel_name='account.invoice.tax',
        string='Taxes'
    )
    l10n_latam_available_document_type_ids = fields.Many2many(
        'l10n_latam.document.type',
        compute='_compute_l10n_latam_available_document_types',
        string='Available Document Types',
    )
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Document Type',
        copy=False,
        readonly=True,
        auto_join=True,
        index=True,
    )
    l10n_latam_sequence_id = fields.Many2one(
        'ir.sequence',
        compute='_compute_l10n_latam_sequence',
    )
    l10n_latam_document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        index=True,
    )
    l10n_latam_next_number = fields.Integer(
        compute='compute_l10n_latam_next_number',
        string='Next Number',
    )
    l10n_latam_use_documents = fields.Boolean(
        related='journal_id.l10n_latam_use_documents',
    )
    l10n_latam_country_code = fields.Char(
        related='company_id.country_id.code',
        help='Technical field used to hide/show fields regarding the '
        'localization'
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        string='Document Reference',
    )

    @api.depends('l10n_latam_document_type_id', 'journal_id')
    def _compute_l10n_latam_sequence(self):
        for rec in self:
            rec.l10n_latam_sequence_id = \
                rec.journal_id.get_document_type_sequence(rec)

    @api.depends(
        'amount_untaxed', 'amount_tax', 'tax_line_ids', 'l10n_latam_document_type_id')
    def _compute_l10n_latam_amount_and_taxes(self):
        for invoice in self:
            taxes_included = (
                invoice.l10n_latam_document_type_id and
                invoice.l10n_latam_document_type_id.get_taxes_included() or False)
            if not taxes_included:
                l10n_latam_amount_tax = invoice.amount_tax
                l10n_latam_amount_untaxed = invoice.amount_untaxed
                not_included_taxes = invoice.tax_line_ids
            else:
                included_taxes = invoice.tax_line_ids.filtered(
                    lambda x: x.tax_id in taxes_included)
                not_included_taxes = (
                    invoice.tax_line_ids - included_taxes)
                l10n_latam_amount_tax = sum(not_included_taxes.mapped('amount'))
                l10n_latam_amount_untaxed = invoice.amount_untaxed + sum(
                    included_taxes.mapped('amount'))
            invoice.l10n_latam_amount_tax = l10n_latam_amount_tax
            invoice.l10n_latam_amount_untaxed = l10n_latam_amount_untaxed
            invoice.l10n_latam_tax_line_ids = not_included_taxes

    @api.depends(
        'journal_id.sequence_id.number_next_actual',
        'l10n_latam_sequence_id.number_next_actual',
    )
    def compute_l10n_latam_next_number(self):
        """ Show next number only for invoices without number and on draft
        state """
        for invoice in self.filtered(
                lambda x: not x.display_name and x.state == 'draft'):
            if invoice.l10n_latam_use_documents:
                sequence = invoice.l10n_latam_sequence_id
            elif (
                    invoice.type in ['out_refund', 'in_refund'] and
                    invoice.journal_id.refund_sequence
            ):
                sequence = invoice.journal_id.refund_sequence_id
            else:
                sequence = invoice.journal_id.sequence_id
            # we must check if sequence use date ranges
            if not sequence.use_date_range:
                invoice.l10n_latam_next_number = sequence.number_next_actual
            else:
                dt = fields.Date.today()
                if self.env.context.get('ir_sequence_date'):
                    dt = self.env.context.get('ir_sequence_date')
                seq_date = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', sequence.id),
                    ('date_from', '<=', dt),
                    ('date_to', '>=', dt)], limit=1)
                if not seq_date:
                    seq_date = sequence._create_date_range_seq(dt)
                invoice.l10n_latam_next_number = seq_date.number_next_actual

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Refund'),
            'in_refund': _('Vendor Refund'),
        }
        result = []
        for inv in self:
            result.append((
                inv.id,
                "%s %s" % (
                    inv.display_name or TYPES[inv.type],
                    inv.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([
                '|', ('l10n_latam_document_number', '=', name),
                ('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.constrains(
        'journal_id',
        'partner_id',
        'l10n_latam_document_type_id',
    )
    def _get_document_type(self):
        """ Como los campos responsible y journal document type no los
        queremos hacer funcion porque no queremos que sus valores cambien nunca
        y como con la funcion anterior solo se almacenan solo si se crea desde
        interfaz, hacemos este hack de constraint para computarlos si no estan
        computados"""
        for rec in self.filtered(
                lambda x: not x.l10n_latam_document_type_id and
                x.l10n_latam_available_document_type_ids):
            rec.l10n_latam_document_type_id = (
                rec._get_available_document_types(
                    rec.journal_id, rec.type, rec.partner_id
                ).get('document_type'))

    @api.depends(
        'move_name',
        'l10n_latam_document_number',
        'l10n_latam_document_type_id.doc_code_prefix'
    )
    def _compute_display_name(self):
        """ If move_name then invoice has been validated, then:
        * If document number and document type, we show them
        * Else, we show move_name
        """
        # al final no vimos porque necesiamos que este el move name, es util
        # mostrar igual si existe el numero, por ejemplo si es factura de
        # proveedor
        # if self.l10n_latam_document_number and self.l10n_latam_document_type_id and self.move_name:
        for rec in self:
            if rec.l10n_latam_document_number and rec.l10n_latam_document_type_id:
                display_name = ("%s%s" % (
                    rec.l10n_latam_document_type_id.doc_code_prefix or '',
                    rec.l10n_latam_document_number))
            else:
                display_name = rec.move_name
            rec.display_name = display_name

    @api.multi
    def _check_use_documents(self):
        """
        check invoices has document class but journal require it (we check
        all invoices, not only argentinian ones)
        """
        without_doucument_class = self.filtered(
            lambda r: (
                not r.l10n_latam_document_type_id and r.journal_id.l10n_latam_use_documents))
        if without_doucument_class:
            raise UserError(_(
                'Some invoices have a journal that require a document but not '
                'document type has been selected.\n'
                'Invoices ids: %s' % without_doucument_class.ids))

    @api.multi
    def _get_localization_invoice_vals(self):
        """
        Function to be inherited by different localizations and add custom
        data to invoice on invoice validation
        """
        self.ensure_one()
        return {}

    @api.multi
    def action_move_create(self):
        """
        We add currency rate on move creation so it can be used by electronic
        invoice later on action_number
        """
        self._check_use_documents()
        res = super(AccountInvoice, self).action_move_create()
        self._set_document_data()
        return res

    @api.multi
    def _set_document_data(self):
        """
        If journal document dont have any sequence, then document number
        must be set on the account.invoice and we use thisone
        A partir de este metodo no debería haber errores porque el modulo de
        factura electronica ya habria pedido el cae. Lo ideal sería hacer todo
        esto antes que se pida el cae pero tampoco se pueden volver a atras los
        conusmos de secuencias. TODO mejorar esa parte
        """
        # We write document_number field with next invoice number by
        # document type
        for invoice in self:
            _logger.info(
                'Setting document data on account.invoice and account.move')
            document_type = invoice.l10n_latam_document_type_id
            inv_vals = self._get_localization_invoice_vals()
            if invoice.l10n_latam_use_documents:
                if not invoice.l10n_latam_document_number:
                    # TODO: crear la sequencia si no existe, usar la que existe
                    if not invoice.l10n_latam_sequence_id:
                        raise UserError(_(
                            'Error!. Please define sequence on the journal '
                            'related documents to this invoice or set the '
                            'document number.'))
                    document_number = \
                        invoice.l10n_latam_sequence_id.next_by_id()
                    inv_vals['l10n_latam_document_number'] = document_number
                # for canelled invoice number that still has a document_number
                # if validated again we use old document_number
                # also use this for supplier invoices
                else:
                    document_number = invoice.l10n_latam_document_number
                invoice.move_id.write({
                    'l10n_latam_document_type_id': document_type.id,
                    'l10n_latam_document_number': document_number,
                })
            invoice.write(inv_vals)
        return True

    @api.onchange('journal_id', 'partner_id', 'company_id')
    def onchange_journal_partner_company(self):
        res = self._get_available_document_types(
            self.journal_id, self.type, self.partner_id)
        self.l10n_latam_document_type_id = res['document_type']

    @api.depends('journal_id', 'partner_id', 'company_id')
    def _compute_l10n_latam_available_document_types(self):
        """
        This function should only be inherited if you need to add another
        "depends", for eg, if you need to add a depend on "new_field" you
        should add:

        @api.depends('new_field')
        def _get_available_document_types(
                self, journal, invoice_type, partner):
            return super(
                AccountInvoice, self)._get_available_document_types(
                    journal, invoice_type, partner)
        """
        for invoice in self:
            res = invoice._get_available_document_types(
                invoice.journal_id, invoice.type, invoice.partner_id)
            invoice.l10n_latam_available_document_type_ids = res[
                'available_document_types']

    @api.multi
    def write(self, vals):
        """
        If someone change the type (for eg from sale order), we update
        de document type
        """
        inv_type = vals.get('type')
        # if len(vals) == 1 and vals.get('type'):
        # podrian pasarse otras cosas ademas del type
        if inv_type:
            for rec in self:
                res = rec._get_available_document_types(
                    rec.journal_id, inv_type, rec.partner_id)
                vals['l10n_latam_document_type_id'] = res[
                    'document_type'].id
                # call write for each inoice
                super(AccountInvoice, rec).write(vals)
                return True
        return super(AccountInvoice, self).write(vals)

    @api.model
    def _get_available_document_types(
            self, journal, invoice_type, partner):
        """ This function is to be inherited by different localizations and
        MUST return a dictionary with two keys:
        * 'available_document_types': available document types on
        this invoice
        * 'document_type': suggested document type on this invoice
        """
        if not journal.l10n_latam_use_documents:
            return {
                'available_document_types':
                    self.env['l10n_latam.document.type'],
                'document_type':
                    self.env['l10n_latam.document.type'],
            }
        raise UserError(_(
            'Method not implemented by localization of %s') % (
                journal.company_id.country_id.name))

    @api.constrains('l10n_latam_document_type_id', 'l10n_latam_document_number')
    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def validate_document_number(self):
        # if we have a sequence, number is set by sequence and we dont
        # check this
        for rec in self.filtered(
                lambda x: not x.l10n_latam_sequence_id and x.l10n_latam_document_type_id):
            l10n_latam_document_number = \
                rec.l10n_latam_document_type_id._format_document_number(
                    rec.l10n_latam_document_number)
            if l10n_latam_document_number != rec.l10n_latam_document_number:
                rec.l10n_latam_document_number = l10n_latam_document_number

    @api.constrains('type', 'l10n_latam_document_type_id')
    def check_invoice_type_document_type(self):
        for rec in self:
            internal_type = rec.l10n_latam_document_type_id.internal_type
            invoice_type = rec.type
            if not internal_type:
                continue
            elif internal_type in [
                    'debit_note', 'invoice'] and invoice_type in [
                    'out_refund', 'in_refund']:
                raise Warning(_(
                    'You can not use a %s document type with a refund '
                    'invoice') % internal_type)
            elif internal_type == 'credit_note' and invoice_type in [
                    'out_invoice', 'in_invoice']:
                raise Warning(_(
                    'You can not use a %s document type with a invoice') % (
                    internal_type))

    @api.model
    def _prepare_refund(
            self, invoice, date_invoice=None,
            date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice=date_invoice,
            date=date, description=description, journal_id=journal_id)
        refund_document_type_id = self._context.get(
            'refund_document_type_id', False)
        refund_document_number = self._context.get(
            'refund_document_number', False)
        if refund_document_type_id:
            values['l10n_latam_document_type_id'] = \
                refund_document_type_id
        if refund_document_number:
            values['l10n_latam_document_number'] = refund_document_number
        return values

    @api.multi
    def _check_duplicate_supplier_reference(self):
        """We make reference only unique if you are not using documents.
        Documents already guarantee to not encode twice same vendor bill.
        """
        return super(
            AccountInvoice, self.filtered(lambda x: not x.l10n_latam_use_documents))

    @api.constrains('l10n_latam_document_number', 'partner_id', 'company_id')
    def _check_document_number_unique(self):
        """ We dont implement this on _check_duplicate_supplier_reference
        because we want to check it on data entry and also because we validate
        customer invoices (not only supplier ones)
        """
        for rec in self.filtered(
                lambda x: x.l10n_latam_use_documents and x.l10n_latam_document_number):
            domain = [
                ('type', '=', rec.type),
                ('l10n_latam_document_number', '=', rec.l10n_latam_document_number),
                ('l10n_latam_document_type_id', '=', rec.l10n_latam_document_type_id.id),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id)
            ]
            msg = (
                'Error en factura con id %s: El numero de comprobante (%s)'
                ' debe ser unico por tipo de documento')
            if rec.type in ['out_invoice', 'out_refund']:
                # si es factura de cliente entonces tiene que ser numero
                # unico por compania y tipo de documento
                rec.search(domain)
            else:
                # si es factura de proveedor debe ser unica por proveedor
                domain += [
                    ('partner_id.commercial_partner_id', '=',
                        rec.commercial_partner_id.id)]
                msg += ' y proveedor'
            if rec.search(domain):
                raise UserError(msg % (rec.id, rec.l10n_latam_document_number))
