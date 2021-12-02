# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
import time
import logging

from odoo.tests import common, Form

_logger = logging.getLogger(__name__)


class TestMrpSerialMassProducePerformance(common.TransactionCase):

    @unittest.skip
    def test_smp_performance(self):

        total_quantity = 1000
        quantity = 1

        raw_materials_count = 10
        trackings = [
            'none',
            # 'lot',
            # 'serial'
        ]

        _logger.info('setting up environment')

        raw_materials = []
        for i in range(raw_materials_count):
            raw_materials.append(self.env['product.product'].create({
                'name': '@raw_material#' + str(i + 1),
                'type': 'product',
                'tracking': trackings[i % len(trackings)]
            }))
        finished = self.env['product.product'].create({
            'name': '@finished',
            'type': 'product',
            'tracking': 'serial',
        })
        bom = self.env['mrp.bom'].create({
            'product_id': finished.id,
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_uom_id': finished.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption': 'flexible',
            'bom_line_ids': [(0, 0, {'product_id': p[0]['id'], 'product_qty': 1}) for p in raw_materials]
        })

        form = Form(self.env['mrp.production'])
        form.product_id = finished
        form.bom_id = bom
        form.product_qty = total_quantity

        mo = form.save()

        mo.action_confirm()

        for i in range(raw_materials_count):
            if raw_materials[i].tracking == 'none':
                self.env['stock.quant'].with_context(inventory_mode=True).create({
                    'product_id': raw_materials[i].id,
                    'inventory_quantity': total_quantity,
                    'location_id': mo.location_src_id.id,
                })._apply_inventory()
            elif raw_materials[i].tracking == 'lot':
                qty = total_quantity
                while qty > 0:
                    lot = self.env['stock.lot'].create({
                        'product_id': raw_materials[i].id,
                        'company_id': self.env.company.id,
                    })
                    self.env['stock.quant'].with_context(inventory_mode=True).create({
                        'product_id': raw_materials[i].id,
                        'inventory_quantity': 10,
                        'location_id': mo.location_src_id.id,
                        'lot_id': lot.id,
                    })._apply_inventory()
                    qty -= 10
            else:
                for _ in range(total_quantity):
                    lot = self.env['stock.lot'].create({
                        'product_id': raw_materials[i].id,
                        'company_id': self.env.company.id,
                    })
                    self.env['stock.quant'].with_context(inventory_mode=True).create({
                        'product_id': raw_materials[i].id,
                        'inventory_quantity': 1,
                        'location_id': mo.location_src_id.id,
                        'lot_id': lot.id,
                    })._apply_inventory()

        mo.action_assign()

        action = mo.action_serial_mass_produce_wizard()
        wizard = Form(self.env['stock.assign.serial'].with_context(**action['context']))
        wizard.next_serial_number = "sn#1"
        wizard.next_serial_count = quantity
        action = wizard.save().generate_serial_numbers_production()
        wizard = Form(self.env['stock.assign.serial'].browse(action['res_id']))
        wizard = wizard.save()

        _logger.info('generating serial numbers')
        start = time.perf_counter()
        if quantity == total_quantity:
            wizard.apply()
        else:
            wizard.create_backorder()
        end = time.perf_counter()
        _logger.info('time to produce %s/%s: %s', quantity, total_quantity, end - start)
