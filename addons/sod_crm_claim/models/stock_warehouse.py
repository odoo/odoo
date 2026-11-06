# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)


from odoo import _, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    rma_loc_id = fields.Many2one('stock.location', 'RMA Location', check_company=True)
    rma_type_id = fields.Many2one("stock.picking.type", "RMA Type")

    def _get_locations_values(self, vals, code=False):
        sub_locations = super()._get_locations_values(vals, code=code)
        def_values = self.default_get(['company_id'])
        code = vals.get('code') or code or ''
        code = code.replace(' ', '').upper()
        company_id = vals.get('company_id', def_values['company_id'])
        sub_locations.update({
            'rma_loc_id': {
                'name': 'RMA',
                'active': True,
                'usage': 'internal',
                'return_location': True,
                'barcode': self._valid_barcode(code + '-RMA', company_id)
            },
        })
        return sub_locations

    def _get_sequence_values(self, name=False, code=False):
        res = super()._get_sequence_values(name=name, code=code)
        res.update(
            {
                "rma_type_id": {
                    "name": self.name + " " + _("Sequence RMAR"),
                    "prefix": self.code + '/RMAR/',
                    "padding": 5,
                    "company_id": self.company_id.id,
                },
            }
        )
        return res

    def _get_picking_type_update_values(self):
        res = super()._get_picking_type_update_values()
        customer_loc, _supplier_loc = self._get_partner_locations()
        res["rma_type_id"] = {
            "default_location_src_id": customer_loc.id,
            "default_location_dest_id": self.rma_loc_id.id,
        }
        return res

    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super()._get_picking_type_create_values(max_sequence)
        customer_loc, _supplier_loc = self._get_partner_locations()
        data.update(
            {
                "rma_type_id": {
                    "name": _("Return to RMA"),
                    "code": "incoming",
                    "use_create_lots": True,
                    "use_existing_lots": True,
                    "default_location_src_id": customer_loc.id,
                    "default_location_dest_id": self.rma_loc_id.id,
                    "sequence": next_sequence + 1,
                    "sequence_code": "RMA",
                    "company_id": self.company_id.id,
                },
            }
        )
        return data, max_sequence + 4
