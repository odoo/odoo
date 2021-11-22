# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LotLabelLayout(models.TransientModel):
    _name = 'lot.label.layout'
    _description = 'Choose the sheet layout to print the labels'

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7', '2 x 7'),
        ('4x7', '4 x 7'),
        ('4x12', '4 x 12'),
        ('zpl', 'ZPL')], string="Format", default='2x7', required=True)
    custom_quantity = fields.Integer('Quantity', default=1, required=True)
    lot_ids = fields.Many2many('stock.production.lot')
    rows = fields.Integer(compute='_compute_dimensions')
    columns = fields.Integer(compute='_compute_dimensions')

    @api.depends('print_format')
    def _compute_dimensions(self):
        for wizard in self:
            if 'x' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')[:2]
                wizard.columns = int(columns)
                wizard.rows = int(rows)
            else:
                wizard.columns, wizard.rows = 1, 1

    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))

        if self.print_format == 'dymo':
            xml_id = 'stock.report_lot_label_dymo'
        elif 'x' in self.print_format:
            xml_id = 'stock.report_lot_label1'
        elif self.print_format == 'zpl':
            xml_id = 'stock.report_lot_label_zpl'
        else:
            xml_id = ''

        data = {
            'active_model': 'stock.production.lot',
            'quantity_by_lot': {l: self.custom_quantity for l in self.lot_ids.ids},
            'layout_wizard': self.id,
        }
        return xml_id, data

    def process(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        if not xml_id:
            raise UserError(_('Unable to find report template for %s format', self.print_format))
        return self.env.ref(xml_id).report_action(None, data=data)
