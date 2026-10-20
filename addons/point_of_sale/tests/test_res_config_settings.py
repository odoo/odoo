# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import Command
from odoo.tests import Form
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestConfigureShops(TestPoSCommon):
    """ Shops are now configured from the general settings.
        This test suite ensures that changes made in the general settings
        should reflect to the pos.config record pointed by the
        pos_config_id field.
    """
    _test_user_groups = None  # FIXME list needed groups

    def _remove_on_payment_taxes(self):
        """ Call this when testing the res.config.settings with Form.
            The `on_payment` taxes need to be removed, otherwise, a warning will show in the log.
        """
        self.env['account.tax'].search([
            ('company_id', '=', self.env.company.id), ('tax_exigibility', '=', 'on_payment')
        ]).unlink()

    def test_properly_set_pos_config_x2many_fields(self):
        """Simulate what is done from the res.config.settings view when editing x2 many fields."""

        self._remove_on_payment_taxes()
        pos_config = self.env['pos.config'].create({
            'name': 'Shop 1',
            'module_pos_restaurant': False,
            'payment_method_ids': [
                Command.create({
                    'name': 'Bank 1',
                    'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
                    'type': 'bank',
                    'company_id': self.env.company.id,
                }),
                Command.create({
                    'name': 'Bank 2',
                    'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
                    'type': 'bank',
                    'company_id': self.env.company.id,
                }),
                Command.create({
                    'name': 'Cash',
                    'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
                    'type': 'cash',
                    'company_id': self.env.company.id,
                })
            ]
        })

        # Manually simulate the unlinking of the second record and then save the settings.
        # It will be a set of link commands except the one we want to delete.
        linked_ids = pos_config.payment_method_ids.ids
        second_id = linked_ids[1]
        commands = [Command.link(_id) for _id in linked_ids if _id != second_id]

        pos_config.with_context(from_settings_view=True).write({
            'payment_method_ids': commands
        })

        self.assertTrue(second_id not in pos_config.payment_method_ids.ids)
        self.assertTrue(len(pos_config.payment_method_ids) == 2)

    def test_write_default_and_available_presets_on_multiple_pos_configs(self):
        preset = self.env['pos.preset'].create({'name': 'Preset 1'})

        pos_config1 = self.env['pos.config'].create({'name': 'Shop 1', 'module_pos_restaurant': False})
        pos_config2 = self.env['pos.config'].create({'name': 'Shop 2', 'module_pos_restaurant': False})
        pos_config3 = self.env['pos.config'].create({'name': 'Shop 3', 'module_pos_restaurant': False})

        pos_configs = pos_config1 | pos_config2 | pos_config3

        pos_configs.write({
            'use_presets': True,
            'available_preset_ids': [(6, 0, [preset.id])],
            'default_preset_id': preset.id,
        })

    def test_fallback_nomenclature_swapped_when_company_nomenclature_changes(self):
        default_nomenclature = self.env.ref('barcodes.default_barcode_nomenclature')
        gs1_nomenclature = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.env.company.nomenclature_id = default_nomenclature
        pos_config = self.env['pos.config'].create({
            'name': 'Shop 1',
            'module_pos_restaurant': False,
            'fallback_nomenclature_id': gs1_nomenclature.id,
        })

        # e.g. from the Inventory settings
        self.env.company.nomenclature_id = gs1_nomenclature
        self.assertEqual(pos_config.fallback_nomenclature_id, default_nomenclature)

        self.env.company.nomenclature_id = default_nomenclature
        self.assertEqual(pos_config.fallback_nomenclature_id, gs1_nomenclature)

    def test_fallback_nomenclature_swapped_from_pos_settings(self):
        self._remove_on_payment_taxes()
        default_nomenclature = self.env.ref('barcodes.default_barcode_nomenclature')
        gs1_nomenclature = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.env.company.nomenclature_id = default_nomenclature
        pos_config = self.env['pos.config'].create({
            'name': 'Shop 1',
            'module_pos_restaurant': False,
            'fallback_nomenclature_id': gs1_nomenclature.id,
        })

        with Form(self.env['res.config.settings']) as form:
            form.pos_config_id = pos_config
            form.barcode_nomenclature_id = gs1_nomenclature
            self.assertEqual(form.pos_fallback_nomenclature_id, default_nomenclature)

        self.assertEqual(self.env.company.nomenclature_id, gs1_nomenclature)
        self.assertEqual(pos_config.fallback_nomenclature_id, default_nomenclature)

    def test_fallback_nomenclature_kept_empty_when_company_nomenclature_cleared(self):
        default_nomenclature = self.env.ref('barcodes.default_barcode_nomenclature')
        self.env.company.nomenclature_id = default_nomenclature
        pos_config = self.env['pos.config'].create({
            'name': 'Shop 1',
            'module_pos_restaurant': False,
        })

        self.env.company.nomenclature_id = False
        self.assertFalse(pos_config.fallback_nomenclature_id)

    def test_fallback_nomenclature_kept_empty_when_nomenclature_cleared_from_pos_settings(self):
        self._remove_on_payment_taxes()
        self.env.company.nomenclature_id = self.env.ref('barcodes.default_barcode_nomenclature')
        pos_config = self.env['pos.config'].create({
            'name': 'Shop 1',
            'module_pos_restaurant': False,
        })

        with Form(self.env['res.config.settings']) as form:
            form.pos_config_id = pos_config
            form.barcode_nomenclature_id = self.env['barcode.nomenclature']
            self.assertFalse(form.pos_fallback_nomenclature_id)

        self.assertFalse(pos_config.fallback_nomenclature_id)
