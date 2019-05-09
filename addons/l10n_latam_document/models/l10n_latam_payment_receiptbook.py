# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class L10nLatamAccountPaymentReceiptbook(models.Model):

    _name = 'l10n_latam.payment.receiptbook'
    _description = 'Latam Payment Receiptbook'
    _order = 'sequence asc'

    sequence = fields.Integer(
        help="Used to order the receiptbooks",
        default=10,
    )
    name = fields.Char(
        size=64,
        required=True,
        index=True,
    )
    partner_type = fields.Selection(
        [('customer', 'Customer'), ('supplier', 'Vendor')],
        required=True,
        index=True,
    )
    next_number = fields.Integer(
        related='sequence_id.number_next_actual'
    )
    sequence_type = fields.Selection(
        [('automatic', 'Automatic'), ('manual', 'Manual')],
        readonly=False,
        default='automatic',
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Document Sequence',
        help="This field contains the information related to the numbering "
        "of the receipt entries of this receiptbook.",
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env[
            'res.company']._company_default_get('l10n_latam.payment.receiptbook')
    )
    prefix = fields.Char(
    )
    padding = fields.Integer(
        'Number Padding',
        default=8,
        help="automatically adds some '0' on the left of the 'Number' to get "
        "the required padding size."
    )
    active = fields.Boolean(
        default=True,
    )
    document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        required=True,
    )

    @api.multi
    def write(self, vals):
        """ If user change prefix/padding we change prefix of sequence.
        """
        prefix = vals.get('prefix')
        padding = vals.get('padding')
        for rec in self:
            if prefix and rec.sequence_id:
                rec.sequence_id.prefix = prefix
            if padding and rec.sequence_id:
                rec.sequence_id.padding = padding
        return super(L10nLatamAccountPaymentReceiptbook, self).write(vals)

    @api.model
    def create(self, vals):
        sequence_type = vals.get(
            'sequence_type', self._context.get('default_sequence_type'))
        prefix = vals.get(
            'prefix', self._context.get('default_prefix'))
        padding = vals.get(
            'prefix', self._context.get('default_padding'))
        company_id = vals.get(
            'company_id', self._context.get('default_company_id'))

        if sequence_type == 'automatic' and not vals.get('sequence_id') \
           and company_id:
            seq_vals = {
                'name': vals['name'],
                'implementation': 'no_gap',
                'prefix': prefix,
                'padding': padding,
                'number_increment': 1
            }
            sequence = self.env['ir.sequence'].sudo().create(seq_vals)
            vals.update({'sequence_id': sequence.id})
        return super(L10nLatamAccountPaymentReceiptbook, self).create(vals)
