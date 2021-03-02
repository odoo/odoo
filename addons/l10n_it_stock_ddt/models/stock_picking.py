# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_it_transport_reason = fields.Selection([('sale', 'Sale'),
                                                 ('outsourcing', 'Outsourcing'),
                                                 ('evaluation', 'Evaluation'),
                                                 ('gift', 'Gift'),
                                                 ('transfer', 'Transfer'),
                                                 ('substitution', 'Substitution'),
                                                 ('attemped_sale', 'Attempted Sale'),
                                                 ('loaned_use', 'Loaned for Use'),
                                                 ('repair', 'Repair')], default="sale", tracking=True, string='Transport Reason')
    l10n_it_transport_method = fields.Selection([('sender', 'Sender'), ('recipient', 'Recipient'), ('courier', 'Courier service')],
                                                default="sender", string='Transport Method')
    l10n_it_transport_method_details = fields.Char('Transport Note')
    l10n_it_parcels = fields.Integer(string="Parcels", default=1)
    l10n_it_country_code = fields.Char(related="company_id.country_id.code")
    l10n_it_ddt_number = fields.Char('DDT Number', readonly=True)

    def action_done(self):
        super(StockPicking, self).action_done()
        for picking in self.filtered(lambda p: p.picking_type_id.l10n_it_ddt_sequence_id):
            picking.l10n_it_ddt_number = picking.picking_type_id.l10n_it_ddt_sequence_id.next_by_id()


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    l10n_it_ddt_sequence_id = fields.Many2one('ir.sequence')

    def _get_dtt_ir_seq_vals(self, warehouse_id, sequence_code):
        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            ir_seq_name = wh.name + ' ' + _('Sequence') + ' ' + sequence_code
            ir_seq_prefix = wh.code + '/' + sequence_code + '/DDT'
        else:
            ir_seq_name = _('Sequence') + ' ' + sequence_code
            ir_seq_prefix = sequence_code + '/DDT'
        return ir_seq_name, ir_seq_prefix

    @api.model
    def create(self, vals):
        company = self.env['res.company'].browse(vals['company_id'])
        if 'l10n_it_ddt_sequence_id' not in vals or not vals['l10n_it_ddt_sequence_id'] and vals['code'] == 'outgoing' \
                and company.country_id.code == 'IT':
            ir_seq_name, ir_seq_prefix = self._get_dtt_ir_seq_vals(vals.get('warehouse_id'), vals['sequence_code'])
            vals['l10n_it_ddt_sequence_id'] = self.env['ir.sequence'].create({
                    'name': ir_seq_name,
                    'prefix': ir_seq_prefix,
                    'padding': 5,
                    'company_id': vals['company_id'],
                    'implementation': 'no_gap',
                }).id
        return super(StockPickingType, self).create(vals)

    def write(self, vals):
        if 'sequence_code' in vals:
            for picking_type in self.filtered(lambda p: p.l10n_it_ddt_sequence_id):
                warehouse = picking_type.warehouse_id.id if 'warehouse_id' not in vals else vals['warehouse_ids']
                ir_seq_name, ir_seq_prefix = self._get_dtt_ir_seq_vals(warehouse, vals['sequence_code'])
                picking_type.l10n_it_ddt_sequence_id.write({
                        'name': ir_seq_name,
                        'prefix': ir_seq_prefix,
                    })
        return super(StockPickingType, self).write(vals)