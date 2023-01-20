# -*- coding: utf-8 -*-
# (C) 2021 Smile (<https://www.smile.eu>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestAudit(TransactionCase):

    def setUp(self):
        super(TestAudit, self).setUp()
        rule_vals = {
            'name': 'Audit rule on partners',
            'model_id': self.env.ref('base.model_res_partner').id,
            'log_create': True
        }
        self.env['audit.rule'].create(rule_vals)
        partner_vals = {
            'name': 'Partner',
            'is_company': False,
            'email': 'LasLabs@ExAmPlE.CoM',
        }
        self.partner = self.env['res.partner'].create(partner_vals)

    def test_log_created_on_create(self):
        """ A log should be created on creating a partner"""
        log = self.env['audit.log'].search([
            ('model_id', '=', self.env.ref('base.model_res_partner').id),
            ('method', '=', 'create'),
            ('res_id', '=', self.partner.id),
        ], limit=1)
        self.assertEqual(
            log.name, 'Partner', 'No audit log after partner creation')

    def test_log_created_on_write(self):
        """ A log should be created on updating a partner"""
        self.partner.write({'name': 'Updated Partner'})
        log = self.env['audit.log'].search([
            ('model_id', '=', self.env.ref('base.model_res_partner').id),
            ('method', '=', 'write'),
            ('res_id', '=', self.partner.id),
        ])
        self.assertEqual(
            log.res_id, self.partner.id, 'No audit log after partner updating')

    def test_log_created_on_unlink(self):
        """ A log should be created on deleting a partner"""
        self.partner.unlink()
        log = self.env['audit.log'].search([
            ('model_id', '=', self.env.ref('base.model_res_partner').id),
            ('method', '=', 'unlink'),
            ('res_id', '=', self.partner.id),
        ])
        self.assertEqual(
            log.name, 'Partner', 'No audit log after partner unlink')
