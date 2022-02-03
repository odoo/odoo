# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import HttpCase


@odoo.tests.tagged('-at_install', 'post_install')
class TestGetModelDefinitions(HttpCase):
    def test_access_cr(self):
        """ Checks that get_model_definitions does not return anything else than models """
        with self.assertRaises(KeyError):
            self.env['ir.model']._get_model_definitions({
                'res.users': [],
                'cr': [],
            })

    def test_access_all_model_fields(self):
        """
            Check that get_model_definitions return all the required_models
            and their fields even if no field name to retrieve was specified
        """
        model_definitions = self.env['ir.model']._get_model_definitions({
            'res.users': [],
            'res.partner': [],
        })
        # models are retrieved
        self.assertIn('res.users', model_definitions)
        self.assertIn('res.partner', model_definitions)
        # check that model fields are retrieved even without passing
        # their name explicitly
        self.assertTrue(
            all(field in model_definitions['res.users']
                for field in ['partner_id', 'name', 'email']))
        self.assertTrue(
            all(field in model_definitions['res.partner']
                for field in ['title', 'parent_id', 'company_id']))

    def test_access_specific_model_fields(self):
        """
            Check that get_model_definitions only returns fields that were
            specified
        """
        model_definitions = self.env['ir.model']._get_model_definitions({
            'res.users': ['name'],
            'res.partner': ['title'],
        })
        # res.users fields should be name, id, display_name . Indeed, id and display_name are
        # retrieved anyway because they are present on all models
        self.assertEqual(
            ['display_name', 'id', 'name'],
            sorted(model_definitions['res.users'].keys())
        )
        # res.partner fields should be name, id, title
        self.assertEqual(
            ['display_name', 'id', 'title'],
            sorted(model_definitions['res.partner'].keys())
        )
