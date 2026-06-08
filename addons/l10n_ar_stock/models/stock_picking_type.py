import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    l10n_ar_document_type_id = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string="Document Type",
        domain=lambda self: [('id', 'in', self._get_allowed_document_type_ids())],
        help="Argentina: Select the document type to be assigned on the Remito"
    )
    l10n_ar_cai_authorization_code = fields.Char(
        string="CAI",
        copy=False,
        help="Argentina: Add the CAI number for Remitos given by ARCA",
    )
    l10n_ar_cai_expiration_date = fields.Date(
        string="CAI Expiration Date",
        copy=False,
        help="Argentina: Add the CAI expiration date given by ARCA for the sequence configured here",
    )
    l10n_ar_sequence_number_start = fields.Char(
        string="Sequence From",
        copy=False,
        help="Argentina: Add the first sequence number given by ARCA for this CAI",
    )
    l10n_ar_sequence_number_end = fields.Char(
        string="Sequence To",
        copy=False,
        help="Argentina: Add the last sequence number given by ARCA for this CAI",
    )
    l10n_ar_delivery_sequence_prefix = fields.Char(
        string="Delivery Guide Prefix",
        default='00001',
        compute='_compute_l10n_ar_stock_sequence_fields',
        inverse='_set_l10n_ar_stock_delivery_sequence_prefix',
        help="Argentina: Prefix for the delivery guide sequence number. It is used to generate the delivery guide number.",
    )
    l10n_ar_next_delivery_number = fields.Integer(
        string="Next Delivery Guide Number",
        compute='_compute_l10n_ar_stock_sequence_fields',
        inverse='_set_l10n_ar_stock_next_delivery_number',
        help="Argentina: Hold the next sequence to use as delivery guide number.",
    )
    l10n_ar_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        copy=False,
        string="Delivery Guide Number Sequence",
        help="Argentina: Hold the sequence to generate a delivery guide number.",
    )

    # === BUSINESS METHODS === #

    def _get_allowed_document_type_ids(self):
        """Limit document types to only those used for Remitos in Argentina"""
        return [
            self.env.ref('l10n_ar.dc_r_r').id,
            self.env.ref('l10n_ar.dc_remito_x').id
        ]

    # === CONSTRAINT METHODS === #

    @api.constrains('l10n_ar_sequence_number_start', 'l10n_ar_sequence_number_end')
    def _constrains_l10n_ar_sequence_number(self):
        regex = re.compile(r"[0-9]{8}")
        for picking_type in self:
            for number in (picking_type.l10n_ar_sequence_number_start, picking_type.l10n_ar_sequence_number_end):
                if number and not regex.fullmatch(number):
                    raise ValidationError(_("%(sequence_number)s is not a valid sequence number. Sequence numbers should contain exactly 8 digits (e.g. 00012345).", sequence_number=number))

    # === COMPUTE METHODS === #

    @api.depends('l10n_ar_sequence_id')
    def _compute_l10n_ar_stock_sequence_fields(self):
        for picking_type in self:
            if sequence := picking_type.l10n_ar_sequence_id:
                picking_type.l10n_ar_delivery_sequence_prefix = (sequence.prefix or '').rstrip('-')
                picking_type.l10n_ar_next_delivery_number = sequence.number_next
            else:
                picking_type.l10n_ar_delivery_sequence_prefix = False
                picking_type.l10n_ar_next_delivery_number = False

    # === INVERSE METHODS === #

    def _ensure_l10n_ar_stock_sequence(self):
        for picking_type in self:
            if not picking_type.l10n_ar_sequence_id:

                picking_type.l10n_ar_sequence_id = self.env['ir.sequence'].sudo().create({
                    'name': _('%(company)s Sequence %(name)s', company=picking_type.company_id.name, name=picking_type.display_name),
                    'company_id': picking_type.company_id.id,
                    'padding': 8,
                    'implementation': 'no_gap',
                })

    def _set_l10n_ar_stock_delivery_sequence_prefix(self):
        for picking_type in self:
            if prefix := picking_type.l10n_ar_delivery_sequence_prefix:
                picking_type._ensure_l10n_ar_stock_sequence()
                picking_type.l10n_ar_sequence_id.prefix = f'{prefix}-'

    def _set_l10n_ar_stock_next_delivery_number(self):
        for picking_type in self:
            if number := picking_type.l10n_ar_next_delivery_number:
                picking_type._ensure_l10n_ar_stock_sequence()
                picking_type.l10n_ar_sequence_id.number_next = number
