# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from itertools import groupby

from odoo import api, fields, models, tools


class StockInventoryReport(models.Model):
    _name = 'stock.inventory.report'
    _description = 'Products (Inventory Report)'
    _auto = False

    location_id = fields.Many2one('stock.location', 'Location')
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    owner_id = fields.Many2one('res.partner', 'Owner')
    package_id = fields.Many2one('stock.quant.package', 'Package')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    company_id = fields.Many2one('res.company', 'Company')
    quantity = fields.Float('Quantity', group_operator='SUM')
    date = fields.Datetime(string='Date', group_operator='MAX')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'stock_inventory_report')
        query = """ CREATE OR REPLACE VIEW stock_inventory_report AS (
            SELECT
                row_number() OVER() AS id,
                product_id,
                lot_id,
                package_id,
                owner_id,
                date,
                quantity,
                location_id,
                company_id
            FROM
            (
                SELECT
                    product_id,
                    lot_id,
                    package_id,
                    owner_id,
                    - SUM(qty_done) AS quantity,
                    location_id,
                    date,
                    company_id
                FROM
                    stock_move_line
                WHERE
                    state = 'done'
                GROUP BY
                    product_id,
                    lot_id,
                    package_id,
                    owner_id,
                    date,
                    location_id,
                    company_id
                UNION ALL
                SELECT
                    product_id,
                    lot_id,
                    result_package_id AS package_id,
                    owner_id,
                    SUM(qty_done) AS quantity,
                    location_dest_id AS location_id,
                    date,
                    company_id
                FROM
                    stock_move_line
                WHERE
                    state = 'done'
                GROUP BY
                    product_id,
                    lot_id,
                    result_package_id,
                    owner_id,
                    date,
                    location_dest_id,
                    company_id
            )
            AS ml
        ) """
        self.env.cr.execute(query)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        records = super(StockInventoryReport, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        returned_records = []

        def _key_groupby_sorted(record):
            return [record.get('product_id') or (),
            record.get('package_id') or (), record.get('location_id') or ()]

        for f, groups in groupby(sorted(records, key=_key_groupby_sorted), key=_key_groupby_sorted):
            groups = list(groups)

            records = OrderedDict()
            for record in groups:
                lot_and_owner = (record.get('lot_id'), record.get('owner_id'))
                if lot_and_owner in records:
                    if not fields or 'quantity' in fields:
                        records[lot_and_owner]['quantity'] += record['quantity']
                    if not fields or 'date' in fields:
                        if record['date'] > records[lot_and_owner]['date']:
                            records[lot_and_owner]['date'] = record['date']
                else:
                    records[lot_and_owner] = record

            for record in records.values():
                if not fields or 'quantity' in fields:
                    if not record['quantity']:
                        continue
                returned_records.append(record)

        return returned_records

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        groups = super(StockInventoryReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        groups_filtered = []
        for group in groups:
            # It will probably destroy the performance but the sum for a group
            # could be 0 but could contains different lot or package, ...
            # the only way to know if a group is relevant or not is to check
            # with a search read if lot and owner reconcile each other.
            real_records = self.search_read(group.get('__domain', []))
            if real_records:
                # Set the real number of useful records
                group[(groupby and groupby[0] or '') + '_count'] = len(real_records)
                groups_filtered.append(group)
        return groups_filtered

    @api.model
    def search_count(self, args):
        """ return the number of reconciled records """
        return len(self.search_read(args))
