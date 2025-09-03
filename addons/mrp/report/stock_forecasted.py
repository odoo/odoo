from odoo import models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        line = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read)

        if not move_out or not move_out.raw_material_production_id or not read:
            return line

        line['move_out']['raw_material_production_id'] = move_out.raw_material_production_id.read(fields=['id', 'unreserve_visible', 'reserve_visible', 'priority'])[0]
        return line

    def _move_draft_domain(self, product_template_ids, product_ids, wh_location_ids):
        in_domain, out_domain = super()._move_draft_domain(product_template_ids, product_ids, wh_location_ids)
        in_domain += [('production_id', '=', False)]
        out_domain += [('raw_material_production_id', '=', False)]
        return in_domain, out_domain

    def _get_report_data(self, product_template_ids=False, product_ids=False):
        res = super()._get_report_data(product_template_ids, product_ids)
        mo_warehouse_data = self._get_draft_production_data(product_template_ids, product_ids, res['warehouse_view_locations'])
        if res['multiple_warehouses']:
            for warehouse in res['warehouses']:
                warehouse['draft_production_qty'] = {
                    'in': 0.0,
                    'out': 0.0
                }
                warehouse_data = mo_warehouse_data.get(warehouse['id'])
                if warehouse_data:
                    warehouse['draft_production_qty'].update({
                        'in': warehouse_data['production_qty_in'],
                        'out': warehouse_data['production_qty_out']
                    })

                    # update total quantities
                    warehouse['qty']['in'] += warehouse['draft_production_qty']['in']
                    warehouse['qty']['out'] += warehouse['draft_production_qty']['out']
        else:
            warehouse_id = res['warehouses'][0]['id']
            warehouse_data = mo_warehouse_data.get(warehouse_id, {})
            res['draft_production_qty'] = {
                'in': warehouse_data.get('production_qty_in', 0.0),
                'out': warehouse_data.get('production_qty_out', 0.0)
            }
            res['qty']['in'] += res['draft_production_qty']['in']
            res['qty']['out'] += res['draft_production_qty']['out']
        return res

    def _get_draft_production_data(self, product_template_ids=False, product_ids=False, wh_locations=False):
        """
        Draft production data grouped by warehouse
        :return: Dictionary mapping warehouse_id to draft production data
        :rtype: dict[int, dict[float]]
        """
        domain = self._product_domain(product_template_ids, product_ids)
        domain += [('state', '=', 'draft')]

        # Pending incoming quantity.
        mo_domain = domain + [('location_dest_id', 'in', wh_locations)]
        grouped_in_data = dict(
            self.env['mrp.production']._read_group(mo_domain, ['warehouse_id'], aggregates=['product_qty:sum'])
        )

        # Pending outgoing quantity.
        move_domain = domain + [
            ('raw_material_production_id', '!=', False),
            ('location_id', 'in', wh_locations),
        ]
        grouped_out_data = dict(
            self.env['stock.move']._read_group(move_domain, ['warehouse_id'], aggregates=['product_qty:sum'])
        )
        all_warehouse_ids = set(grouped_in_data.keys()) | set(grouped_out_data.keys())

        production_data_by_warehouse = {}
        for warehouse in all_warehouse_ids:
            production_data_by_warehouse[warehouse.id] = {
                'production_qty_in': grouped_in_data.get(warehouse, 0.0),
                'production_qty_out': grouped_out_data.get(warehouse, 0.0),
            }
        return production_data_by_warehouse

    def _get_reservation_data(self, move):
        if move.production_id:
            m2o = 'production_id'
        elif move.raw_material_production_id:
            m2o = 'raw_material_production_id'
        else:
            return super()._get_reservation_data(move)
        return {
            '_name': move[m2o]._name,
            'name': move[m2o].name,
            'id': move[m2o].id
        }
