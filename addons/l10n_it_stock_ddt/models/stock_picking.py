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
    l10n_it_ddt_number = fields.Char('DDT Number', readonly=True)
    l10n_it_show_print_ddt_button = fields.Boolean(compute="_compute_l10n_it_show_print_ddt_button")

    @api.depends('country_code',
                 'picking_type_code',
                 'state',
                 'is_locked',
                 'move_ids',
                 'location_id',
                 'location_dest_id')
    def _compute_l10n_it_show_print_ddt_button(self):
        # Enable printing the DDT for done outgoing shipments
        # or dropshipping (picking going from supplier to customer)
        for picking in self:
            picking.l10n_it_show_print_ddt_button = (
                picking.country_code == 'IT'
                and picking.state == 'done'
                and picking.is_locked
                and (picking.picking_type_code == 'outgoing'
                     or (
                         picking.move_ids_without_package
                         and picking.move_ids_without_package[0].partner_id
                         and picking.location_id.usage == 'supplier'
                         and picking.location_dest_id.usage == 'customer'
                         )
                     )
                )

    def _action_done(self):
        super(StockPicking, self)._action_done()
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company = self.env['res.company'].browse(vals.get('company_id', False)) or self.env.company
            if company.country_id.code == 'IT' and vals['code'] == 'outgoing' and ('l10n_it_ddt_sequence_id' not in vals or not vals['l10n_it_ddt_sequence_id']):
                ir_seq_name, ir_seq_prefix = self._get_dtt_ir_seq_vals(vals.get('warehouse_id'), vals['sequence_code'])
                vals['l10n_it_ddt_sequence_id'] = self.env['ir.sequence'].create({
                        'name': ir_seq_name,
                        'prefix': ir_seq_prefix,
                        'padding': 5,
                        'company_id': company.id,
                        'implementation': 'no_gap',
                    }).id
        return super().create(vals_list)

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
