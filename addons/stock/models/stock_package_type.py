# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPackageType(models.Model):
    _name = 'stock.package.type'
    _description = "Stock package type"

    def _get_default_length_uom(self):
        return self.env['product.template']._get_length_uom_name_from_ir_config_parameter()

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    name = fields.Char('Package Type', required=True)
    sequence = fields.Integer('Sequence', default=1, help="The first in the sequence is the default one.")
    sequence_id = fields.Many2one('ir.sequence', 'Reference Sequence', check_company=True, copy=False)
    sequence_code = fields.Char('Sequence Prefix', copy=False)
    height = fields.Float('Height', help="Packaging Height")
    width = fields.Float('Width', help="Packaging Width")
    packaging_length = fields.Float('Length', help="Packaging Length")
    base_weight = fields.Float(string='Weight', help='Weight of the package type')
    max_weight = fields.Float('Max Weight', help='Maximum weight shippable in this packaging')
    barcode = fields.Char('Barcode', copy=False)
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', default=_get_default_weight_uom)
    length_uom_name = fields.Char(string='Length unit of measure label', compute='_compute_length_uom_name', default=_get_default_length_uom)
    company_id = fields.Many2one('res.company', 'Company', index=True)
    identification_method = fields.Selection(
        selection=[('auto', 'Sequence'), ('manual', 'Pre-printed Rolls')],
        string='Identify Package', default='auto',
        help="For Put in Pack:\n"
             " * Sequence: Package number is automatically generated using the reference sequence.\n"
             " * Pre-printed Rolls: Package number is entered by the user manually or by scanning a specific package barcode (existing or new).")
    package_use = fields.Selection([
        ('disposable', 'Disposable Box'),
        ('reusable', 'Reusable Box (totes)'),
        ], string='Package Use', default='disposable', required=True,
        help="""Reusable boxes are used for batch picking and emptied afterwards to be reused. In the barcode application, scanning a reusable box will add the products in this box.
        Disposable boxes aren't reused, when scanning a disposable box in the barcode application, the contained products are added to the transfer.""")
    has_quants = fields.Boolean('Has Contents', compute='_compute_has_quants')
    storage_category_capacity_ids = fields.One2many('stock.storage.category.capacity', 'package_type_id', 'Storage Category Capacity', copy=True)
    route_ids = fields.Many2many('stock.route', string='Routes', domain="[('package_type_selectable', '=', True)]")

    _barcode_uniq = models.Constraint(
        'unique(barcode)',
        'A barcode can only be assigned to one package type!',
    )
    _positive_height = models.Constraint(
        'CHECK(height>=0.0)',
        'Height must be positive',
    )
    _positive_width = models.Constraint(
        'CHECK(width>=0.0)',
        'Width must be positive',
    )
    _positive_length = models.Constraint(
        'CHECK(packaging_length>=0.0)',
        'Length must be positive',
    )
    _positive_max_weight = models.Constraint(
        'CHECK(max_weight>=0.0)',
        'Max Weight must be positive',
    )

    def _compute_has_quants(self):
        pack_type_quants = dict(self.env['stock.package']._read_group(
            domain=[('quant_ids', '!=', False)], groupby=['package_type_id'], aggregates=['__count']))

        for package_type in self:
            package_type.has_quants = pack_type_quants.get(package_type, 0) > 0

    def _compute_length_uom_name(self):
        for package_type in self:
            package_type.length_uom_name = self.env['product.template']._get_length_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_name(self):
        for package_type in self:
            package_type.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", package_type.name)) for package_type, vals in zip(self, vals_list)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence_id') and vals.get('sequence_code'):
                vals['sequence_id'] = self.env['ir.sequence'].sudo().create({
                    'name': self.env._('Package Type Sequence %(code)s', code=vals['sequence_code']),
                    'prefix': vals['sequence_code'] + '/',
                    'padding': 7,
                    'company_id': vals.get('company_id'),
                }).id
        return super().create(vals_list)

    def write(self, vals):
        seq_vals = {}
        if 'sequence_code' in vals:
            seq_vals['name'] = self.env._('Package Type Sequence %(code)s', code=vals['sequence_code'])
            seq_vals['prefix'] = vals['sequence_code'] + '/'
        if 'company_id' in vals:
            seq_vals['company_id'] = vals['company_id']
        if seq_vals:
            self.sequence_id.sudo().write(seq_vals)
        return super().write(vals)
