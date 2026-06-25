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
        def _get_processed_product_details(product, no_variant_att, unit, qty):
            """
            returns a tuple containing the product qty, unit, name, its never-created variant
            attribute value along with their translations if needed and the product's. The tuple
            represents a product details in a goods_row.
            """
            product_name = product.with_context(lang=primary_lang, display_default_code=False).display_name
            product_translated_name = product.with_context(lang=consignee_id.lang, display_default_code=False).display_name
            product_no_variant_att_value = no_variant_att.with_context(lang=primary_lang).name
            product_translated_no_variant_att_value = no_variant_att.with_context(lang=consignee_id.lang).name
            return (
                qty,
                unit.with_context(lang=primary_lang).name if unit else False,
                product_name + (f' ({product_no_variant_att_value})' if product_no_variant_att_value else ''),
               (product_translated_name + (f' ({product_translated_no_variant_att_value})' if product_translated_no_variant_att_value else '')) if consignee_id and primary_lang != consignee_id.lang else False,
            )

        def _get_goods_row(package=False, move=False, mls=False):
            """
            returns a goods_row which represents a row in the goods section of the cmr report.
            Each goods_row represents an outermost package, a stock move with no packages or
            stock move_lines of the same product and unit and have no packages.
            Note that mls != False when there is a package or when some move_lines on a move
            don't have a package and some do, hence it's always move != False OR mls != False

            :param package: an outermost package if a package exists.
            :param move: a stock move, always with no packages on it if such move exists.
            :param mls: stock move_lines which are either the move_lines inside a package
                (package != False) or move_lines with no package (package = False).
            :return: dict represnts a row in the goods section:
                {'package_name': name of the outermost package if exists,
                'packing_method': name of the package_type_id on the outermost package if exists,
                'products': list of products inside that goods_row,
                'hs_codes': list of hs_code of each product in the list of products,
                'weight': weight of the whole goods_row including the packages if exist on the row,
                'volume': volume of the whole goods_row including the packages if exist on the row,
                }
            """
            products, hs_codes = [], []
            weight, volume = 0, 0
            if mls:
                for (product, no_variant_att, unit), mls in mls.grouped(lambda ml: (ml.product_id, ml.move_id.never_product_template_attribute_value_ids, ml.uom_id if has_uom_id else False)).items():
                    product_processed_details = _get_processed_product_details(product, no_variant_att, unit, sum(mls.mapped('quantity')))
                    products.append(product_processed_details)
                    hs_codes.append(product.hs_code if 'hs_code' in product._fields else False)
                    weight = package.shipping_weight or packages_weight.get(package, 0) if package else (sum(mls.mapped('quantity_product_uom')) * product.weight)
                    volume = 0.0
                    if package:
                        volume = package.package_type_id.packaging_length *\
                                package.package_type_id.width *\
                                package.package_type_id.height *\
                                packages_volume_factor if package.package_type_id else 0.0
                    else:
                        volume = (sum(mls.mapped('quantity_product_uom')) * product.volume)
            else:
                product_processed_details = _get_processed_product_details(move.product_id, move.never_product_template_attribute_value_ids, move.uom_id, move.quantity)
                products = [product_processed_details]
                hs_codes = [move.product_id.hs_code if 'hs_code' in move.product_id._fields else False]
                weight = move.quantity_product_uom * move.product_id.weight
                volume = move.quantity_product_uom * move.product_id.volume

            return {
                'package_name': package.name if package else False,
                'packing_method': package.package_type_id.name if package and package.package_type_id else False,
                'products': products,
                'hs_codes': hs_codes,
                'weight': kg_uom.round(weight_uom._compute_quantity(weight, kg_uom)),
                'volume': m3_uom.round(volume * volume_factor),
            }

        # weight and volume should always be in kg and cubic meter regardless of the system unit
        weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        volume_uom = self.env['product.template']._get_volume_uom_id_from_ir_config_parameter()
        volume_factor = 1 if volume_uom == m3_uom else 0.0283168
        has_uom_id = 'uom_id' in self.env['stock.move.line']._fields

        # to convert package volume dimensions from cubic mm to cubic m
        packages_volume_factor = 1e-9 if volume_uom == m3_uom else 1

        done_pickings = pickings.filtered(lambda p: p.state == 'done')
        done_outermost_packages = done_pickings.package_history_ids.outermost_dest_id
        ongoing_outermost_packages = (pickings - done_pickings).move_line_ids.result_package_id.outermost_package_id
        packageless_moves = pickings.move_ids.filtered(lambda m: not m.package_ids)

        packages_weight = done_outermost_packages._get_weight()
        packages_weight.update(ongoing_outermost_packages._get_weight(pickings.ids))

        consignee_id = pickings[0].sale_id.partner_id if 'sale_id' in pickings[0]._fields and pickings[0].sale_id else pickings[0].partner_id
        en_lang = self.env['res.lang'].search([('code', '=like', 'en_%')], limit=1)
        primary_lang = en_lang.code if en_lang else (pickings[0].company_id.partner_id.lang or 'en_US')

        processed_mls_ids = set()
        goods_rows = []
        for package in done_outermost_packages:
            mls = done_pickings.move_line_ids.filtered(lambda ml: ml.quantity and ml.package_history_id.outermost_dest_id == package)
            goods_rows.append(_get_goods_row(package, False, mls))
            processed_mls_ids.update(mls.ids)

        for package in ongoing_outermost_packages:
            mls = package.move_line_ids.filtered(lambda ml: ml.quantity and ml.picking_id.id in pickings.ids)
            goods_rows.append(_get_goods_row(package, False, mls))
            processed_mls_ids.update(mls.ids)

        for move in packageless_moves:
            if move.quantity:
                goods_rows.append(_get_goods_row(False, move, False))
                processed_mls_ids.update(move.move_line_ids.ids)

        packageless_mls = pickings.move_line_ids - self.env['stock.move.line'].browse(processed_mls_ids)
        for (__, __, __), mls in packageless_mls.grouped(lambda ml: (ml.product_id, ml.move_id.never_product_template_attribute_value_ids, ml.uom_id if has_uom_id else False)).items():
            if any(mls.mapped('quantity')):
                goods_rows.append(_get_goods_row(False, False, mls))

        return {
            'should_compress_goods_rows': len(pickings.move_ids) > 6,
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
