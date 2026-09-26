# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from ast import literal_eval

from odoo.tests import common, new_test_user


class TestFleetManagerDomain(common.TransactionCase):

    def test_manager_candidates_are_fleet_users_of_the_vehicle_company(self):
        company_a, company_b = self.env['res.company'].create([
            {'name': 'Fleet Company A'},
            {'name': 'Fleet Company B'},
        ])
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Audi'})
        model = self.env['fleet.vehicle.model'].create({'brand_id': brand.id, 'name': 'A3'})
        vehicle = self.env['fleet.vehicle'].create({
            'model_id': model.id,
            'company_id': company_a.id,
        })
        normal_user_ab = new_test_user(
            self.env, 'normal_user_ab',
            company_id=company_a.id, company_ids=[(6, 0, (company_a + company_b).ids)])
        admin_ab = new_test_user(
            self.env, 'fleet_admin_ab', groups='fleet.fleet_group_manager',
            company_id=company_b.id, company_ids=[(6, 0, (company_a + company_b).ids)])
        admin_b = new_test_user(
            self.env, 'fleet_admin_b', groups='fleet.fleet_group_manager',
            company_id=company_b.id, company_ids=[(6, 0, company_b.ids)])
        officer_ab = new_test_user(
            self.env, 'fleet_officer_ab', groups='fleet.fleet_group_user',
            company_id=company_b.id, company_ids=[(6, 0, (company_a + company_b).ids)])
        officer_b = new_test_user(
            self.env, 'fleet_officer_b', groups='fleet.fleet_group_user',
            company_id=company_b.id, company_ids=[(6, 0, company_b.ids)])

        domain = self.env['fleet.vehicle'].fields_get(['manager_id'])['manager_id']['domain']
        domain = re.sub(r'\bcompany_id\b', str(vehicle.company_id.id), domain)
        candidates = self.env['res.users'].search(literal_eval(domain))

        # Normal user can't be a manager
        self.assertNotIn(normal_user_ab, candidates)
        # Admin from main company B (has access to company A) → can be selectable as manager
        self.assertIn(admin_ab, candidates)
        # Officer from main company B (has access to company A) → can be selectable as manager
        self.assertIn(officer_ab, candidates)
        # Admin from main company B (hasn't access to company A) → can't be selectable as manager
        self.assertNotIn(admin_b, candidates)
        # Officer from main company B (hasn't access to company A) → can't be selectable as manager
        self.assertNotIn(officer_b, candidates)
