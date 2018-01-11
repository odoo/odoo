# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models


class IntrastatReportWizard(models.TransientModel):
    _inherit = 'account.intrastat.wizard'

    @api.model
    def _check_missing_values(self, vals, cache):
        # Override
        super(IntrastatReportWizard, self)._check_missing_values(vals, cache)
        cache_key = 'warehouse_region_%s' % str(vals['invoice_id'])
        if cache_key not in cache:
            dropship_pick_type = self.env.ref('stock_dropshipping.picking_type_dropship', raise_if_not_found=False)
            if not dropship_pick_type:
                cache[cache_key] = False
                return

            invoice = self.env['account.invoice'].browse(vals['invoice_id'])
            stock_moves = invoice._get_last_step_stock_moves()
            stock_moves = stock_moves.filtered(lambda m: m.picking_type_id == dropship_pick_type)

            if not stock_moves:
                cache[cache_key] = False
            else:
                stock_move = stock_moves[0]
                company_country_code = vals['comp_country_code']
                vendor_country_code = stock_move.partner_id.country_id.code
                partner_country_code = stock_move.picking_partner_id.country_id.code

                # Check if we are in a triangular commerce situation.
                # Such situation happens when A = B = C or A != B != C.
                #
                # see https://www.nbb.be/doc/dq/f_pdf_ex/intra2017fr.pdf (§ 4.x)
                #
                #                   Company (B)
                #                      /\
                #                     /  \
                #                    /    \
                #                   /      \
                #         Vendor (A)--------Partner (C)

                is_triangular_commerce = (company_country_code == vendor_country_code == partner_country_code)\
                                         or (company_country_code != vendor_country_code != partner_country_code)

                # In triangular commerce, let the company region code.
                if is_triangular_commerce:
                    cache[cache_key] = False
                    return

                stock_location = stock_move.location_dest_id
                stock_locations = self.env['stock.location'].search([
                    ('parent_left', '<=', stock_location.parent_left),
                    ('parent_right', '>=', stock_location.parent_right)
                ])
                stock_warehouse = self.env['stock.warehouse'].search([
                    ('lot_stock_id', 'in', stock_locations.ids),
                    ('region_id', '!=', False)
                ], limit=1)

                # Cache the computed value to avoid performance loss.
                cache[cache_key] = stock_warehouse.region_id.code

        # Erase the company region code by the warehouse region code.
        if cache[cache_key]:
            vals['region_code'] = cache[cache_key]
