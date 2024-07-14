# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    dummy_id = fields.Char(compute='_compute_dummy_id', inverse='_inverse_dummy_id')
    image_1920 = fields.Image(related="product_id.image_1920")
    product_reference_code = fields.Char(related="product_id.code", string="Product Reference Code")

    def _compute_dummy_id(self):
        self.dummy_id = ''

    def _inverse_dummy_id(self):
        pass

    @api.model
    def barcode_write(self, vals):
        """ Specially made to handle barcode app saving. Avoids overriding write method because pickings in barcode
        will also write to quants and handling context in this case is non-trivial. This method is expected to be
        called only when no record and vals is a list of lists of the form: [[1, quant_id, {write_values}],
        [0, 0, {write_values}], ...]} where [1, quant_id...] updates an existing quant or {[0, 0, ...]}
        when creating a new quant."""
        Quant = self.env['stock.quant'].with_context(inventory_mode=True)

        # TODO batch

        for val in vals:
            if val[0] in (0, 1) and not val[2].get('lot_id') and val[2].get('lot_name'):
                quant_db = val[0] == 1 and Quant.browse(val[1]) or False
                val[2]['lot_id'] = self.env['stock.lot'].create({
                    'name': val[2].pop('lot_name'),
                    'product_id': val[2].get('product_id', quant_db and quant_db.product_id.id or False),
                    'company_id': self.env['stock.location'].browse(val[2].get('location_id') or quant_db.location_id.id).company_id.id
                }).id

        quant_ids = []
        for val in vals:
            if val[0] == 1:
                quant_id = val[1]
                Quant.browse(quant_id).write(val[2])
                quant_ids.append(quant_id)
            elif val[0] == 0:
                quant = Quant.create(val[2])
                # in case an existing quant is written on instead (happens when scanning a product
                # with quants, but not assigned to user or doesn't have an inventory date to normally show up in view)
                if val[2].get('dummy_id'):
                    quant.write({'dummy_id': val[2].get('dummy_id')})
                quant.write({'inventory_date': val[2].get('inventory_date')})
                user_id = val[2].get('user_id')
                # assign a user if one isn't assigned to avoid line disappearing when page left and returned to
                if not quant.user_id and user_id:
                    quant.write({'user_id': user_id})
                quant_ids.append(quant.id)
        return self.browse(quant_ids)._get_stock_barcode_data()

    def action_validate(self):
        quants = self.with_context(inventory_mode=True).filtered(lambda q: q.inventory_quantity_set)
        quants._compute_inventory_diff_quantity()
        res = quants.action_apply_inventory()
        if res:
            return res
        return True

    def action_client_action(self):
        """ Open the mobile view specialized in handling barcodes on mobile devices.
        """
        action = self.env['ir.actions.actions']._for_xml_id('stock_barcode.stock_barcode_inventory_client_action')
        return dict(action, target='fullscreen')

    @api.model
    def get_existing_quant_and_related_data(self, domain):
        quants = self.search(domain)
        return quants.get_stock_barcode_data_records()

    def _get_stock_barcode_data(self):
        locations = self.env['stock.location']
        company_id = self.env.company.id
        package_types = self.env['stock.package.type']
        if not self:  # `self` is an empty recordset when we open the inventory adjustment.
            if self.env.user.has_group('stock.group_stock_multi_locations'):
                locations = self.env['stock.location'].search([('usage', 'in', ['internal', 'transit']), ('company_id', '=', company_id)], order='id')
            else:
                locations = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
            self = self.env['stock.quant'].search([('user_id', '=?', self.env.user.id), ('location_id', 'in', locations.ids), ('inventory_date', '<=', fields.Date.today())])
            if self.env.user.has_group('stock.group_tracking_lot'):
                package_types = package_types.search([])

        data = self.with_context(display_default_code=False, barcode_view=True).get_stock_barcode_data_records()
        if locations:
            data["records"]["stock.location"] = locations.read(locations._get_fields_stock_barcode(), load=False)
        if package_types:
            data["records"]["stock.package.type"] = package_types.read(package_types._get_fields_stock_barcode(), load=False)
        data['line_view_id'] = self.env.ref('stock_barcode.stock_quant_barcode').id
        return data

    def get_stock_barcode_data_records(self):
        products = self.product_id
        companies = self.company_id or self.env.company
        lots = self.lot_id
        owners = self.owner_id
        packages = self.package_id
        uoms = products.uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms = self.env['uom.uom'].search([])

        data = {
            "records": {
                "stock.quant": self.read(self._get_fields_stock_barcode(), load=False),
                "product.product": products.read(products._get_fields_stock_barcode(), load=False),
                "stock.quant.package": packages.read(packages._get_fields_stock_barcode(), load=False),
                "res.company": companies.read(['name']),
                "res.partner": owners.read(owners._get_fields_stock_barcode(), load=False),
                "stock.lot": lots.read(lots._get_fields_stock_barcode(), load=False),
                "uom.uom": uoms.read(uoms._get_fields_stock_barcode(), load=False),
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "user_id": self.env.user.id,
        }
        return data

    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'location_id',
            'inventory_date',
            'inventory_quantity',
            'inventory_quantity_set',
            'quantity',
            'product_uom_id',
            'lot_id',
            'package_id',
            'owner_id',
            'inventory_diff_quantity',
            'dummy_id',
            'user_id',
        ]

    def _get_inventory_fields_write(self):
        return ['dummy_id'] + super()._get_inventory_fields_write()
