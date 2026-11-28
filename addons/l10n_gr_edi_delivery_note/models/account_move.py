from odoo import api, fields, models
from odoo.addons.l10n_gr_edi.models.preferred_classification import TYPES_WITH_CORRELATE_INVOICE


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_gr_edi_correlated_picking_ids = fields.Many2many(
        comodel_name='stock.picking',
        compute='_compute_l10n_gr_edi_correlated_picking_ids',
        string="Correlated Delivery Notes",
    )

    @api.depends('move_type', 'invoice_line_ids.sale_line_ids.move_ids.picking_id.l10n_gr_edi_mark')
    def _compute_l10n_gr_edi_correlated_picking_ids(self):
        for move in self:
            if move.move_type == 'out_invoice':  # Delivery notes only relate to customer invoices
                pickings = move.invoice_line_ids.sale_line_ids.move_ids.picking_id
                move.l10n_gr_edi_correlated_picking_ids = pickings.filtered(
                    lambda picking: picking.l10n_gr_edi_mark and picking.picking_type_code == 'outgoing'
                )
            else:
                move.l10n_gr_edi_correlated_picking_ids = False

    def _l10n_gr_edi_get_invoices_xml_vals(self):
        # EXTENDS 'l10n_gr_edi'
        xml_vals = super()._l10n_gr_edi_get_invoices_xml_vals()
        for invoice_values in xml_vals['invoice_values_list']:
            # myDATA does not accept connected MARKs on these document types
            if invoice_values['header_invoice_type'] in TYPES_WITH_CORRELATE_INVOICE:
                continue
            move = invoice_values['__move__']
            invoice_values['connected_marks'] = move.l10n_gr_edi_correlated_picking_ids.mapped('l10n_gr_edi_mark')
        return xml_vals
