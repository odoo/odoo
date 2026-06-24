from markupsafe import Markup

from odoo import models


class ReportCmrBatch(models.AbstractModel):
    _name = 'report.stock_fleet.report_cmr_batch'
    _description = 'CMR Batch Report'

    def _get_report_values(self, docids, data=None):
        outgoing_batches = self.env['stock.picking.batch'].browse(docids).filtered(lambda b: b.picking_type_id.code == 'outgoing')
        kg_uom = self.env.ref('uom.product_uom_kgm')
        m3_uom = self.env.ref('uom.product_uom_cubic_meter')

        pickings_data = []
        has_carrier_id = 'carrier_id' in self.env['stock.picking']._fields
        pickings_groups = outgoing_batches.picking_ids.grouped(lambda p: (p.partner_id, p.carrier_id if has_carrier_id else False))

        for pickings_group in pickings_groups.values():
            pickings_data.append(self.env['report.stock_fleet.report_cmr']._get_pickings_data(pickings_group, kg_uom, m3_uom))

        return {
            'docs': outgoing_batches,
            'pickings_data': pickings_data,
            'kg_uom_id': kg_uom,
            'm3_uom_id': m3_uom,
        }


class ReportCmr(models.AbstractModel):
    _name = 'report.stock_fleet.report_cmr'
    _description = 'CMR Report'

    def _get_report_values(self, docids, data=None):
        pickings = self.env['stock.picking'].browse(docids).filtered(lambda p: p.picking_type_id.code == 'outgoing')
        kg_uom = self.env.ref('uom.product_uom_kgm')
        m3_uom = self.env.ref('uom.product_uom_cubic_meter')

        pickings_data = [self._get_pickings_data(picking, kg_uom, m3_uom) for picking in pickings]

        return {
            'docs': pickings,
            'pickings_data': pickings_data,
            'kg_uom_id': kg_uom,
            'm3_uom_id': m3_uom,
        }

    def _get_pickings_data(self, pickings, kg_uom, m3_uom):
        done_pickings = pickings.filtered(lambda p: p.state == 'done')
        done_outermost_packages = done_pickings.package_history_ids.outermost_dest_id
        ongoing_outermost_packages = (pickings - done_pickings).move_line_ids.result_package_id.outermost_package_id

        packageless_moves = pickings.move_ids.filtered(lambda m: not m.package_ids)
        packageless_mls = pickings.move_line_ids.filtered(lambda ml: not ml.result_package_id and ml.move_id not in packageless_moves)
        has_uom_id = 'uom_id' in self.env['stock.move.line']._fields

        consignee_id = pickings[0].sale_id.partner_id if 'sale_id' in pickings[0]._fields and pickings[0].sale_id else pickings[0].partner_id
        en_lang = self.env['res.lang'].search([('code', '=like', 'en_%'), ('active', '=', True)], limit=1)
        primary_lang = en_lang.code if en_lang else (pickings[0].company_id.partner_id.lang or 'en_US')
        secondary_lang = consignee_id.lang or 'en_US'

        packages_weight = done_outermost_packages._get_weight()
        packages_weight.update(ongoing_outermost_packages._get_weight(pickings.ids))

        # weight and volume should always be in kg and cubic meter regardless of the system unit
        weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        volume_uom = self.env['product.template']._get_volume_uom_id_from_ir_config_parameter()
        volume_factor = 1 if volume_uom == m3_uom else 0.028

        # to convert package volume dimensions from cubic mm to cubic m
        packages_volume_factor = 1e-9 if volume_uom == m3_uom else 1

        goods_rows = []

        for package in (ongoing_outermost_packages | done_outermost_packages):
            if package in done_outermost_packages:
                package_mls = done_pickings.move_line_ids.filtered(lambda ml: ml.package_history_id.outermost_dest_id == package)
            else:
                package_mls = package.move_line_ids.filtered(lambda ml: ml.picking_id.id in pickings.ids)

            products = []
            hs_codes = []
            for (prod, unit), mls in package_mls.grouped(lambda ml: (ml.product_id, ml.uom_id if has_uom_id else False)).items():
                products.append(
                    sum(mls.mapped('quantity')),
                    unit.name if unit else False,
                    prod.with_context(lang=primary_lang, display_default_code=False).display_name,
                    prod.with_context(lang=secondary_lang, display_default_code=False).display_name if primary_lang != secondary_lang else False
                )
                hs_codes.append(prod.hs_code if 'hs_code' in prod._fields else False)

            package_volume = package.package_type_id.packaging_length *\
                package.package_type_id.width *\
                package.package_type_id.height if package.package_type_id else 0.0

            goods_rows.append({
                'package_name': package.name or False,
                'packing_method': package.package_type_id.name if package.package_type_id else False,
                'products': products,
                'hs_codes': hs_codes,
                'weight': kg_uom.round(weight_uom._compute_quantity(package.shipping_weight or packages_weight.get(package, 0), kg_uom)),
                'volume': m3_uom.round(package_volume * packages_volume_factor * volume_factor),
            })

        for move in packageless_moves:
            hs = move.product_id.hs_code if 'hs_code' in move.product_id._fields else False
            goods_rows.append({
                'package_name': False,
                'packing_method': False,
                'products': [(
                    move.quantity,
                    move.uom_id.name if has_uom_id and move.uom_id else False,
                    move.product_id.with_context(lang=primary_lang, display_default_code=False).display_name,
                    move.product_id.with_context(lang=secondary_lang, display_default_code=False).display_name if primary_lang != secondary_lang else False
                )],
                'hs_codes': [hs],
                'weight': kg_uom.round(weight_uom._compute_quantity(move.quantity_product_uom * move.product_id.weight, kg_uom)),
                'volume': m3_uom.round(move.quantity_product_uom * move.product_id.volume * volume_factor),
            })

        for (prod, unit), mls in packageless_mls.grouped(lambda ml: (ml.product_id, ml.uom_id if has_uom_id else False)).items():
            qty = sum(mls.mapped('quantity_product_uom'))
            hs = prod.hs_code if 'hs_code' in prod._fields else False
            goods_rows.append({
                'package_name': False,
                'packing_method': False,
                'products': [(
                    sum(mls.mapped('quantity')),
                    unit.name if unit else False,
                    prod.with_context(lang=primary_lang, display_default_code=False).display_name,
                    prod.with_context(lang=secondary_lang, display_default_code=False).display_name if primary_lang != secondary_lang else False
                )],
                'hs_codes': [hs],
                'weight': kg_uom.round(weight_uom._compute_quantity(qty * prod.weight, kg_uom)),
                'volume': m3_uom.round(qty * prod.volume * volume_factor),
            })

        return {
            'should_compress_goods_rows': len(pickings.move_ids) > 9,
            'outermost_packages_count': len(ongoing_outermost_packages | done_outermost_packages),
            'goods_rows': goods_rows,
            'sender_id': pickings[0].company_id.partner_id,
            'consignee_id': consignee_id,
            'carrier_id': pickings[0].carrier_id if 'carrier_id' in pickings[0]._fields else False,
            'delivery_address': pickings[0].partner_id,
            'warehouse_id': pickings[0].picking_type_id.warehouse_id,
            'reference': ', '.join(pickings.mapped('name')),
            'notes': Markup('<div/>').join(note for note in pickings.mapped('note') if note)
        }
