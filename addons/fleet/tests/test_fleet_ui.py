# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestFleetUi(HttpCase):

    def test_allowed_fleet_managers_for_vehicle(self):
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Fleet Company B'})
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Audi'})
        model = self.env['fleet.vehicle.model'].create({'brand_id': brand.id, 'name': 'A3'})
        vehicle = self.env['fleet.vehicle'].create({
            'model_id': model.id,
            'company_id': company_a.id,
        })
        new_test_user(
            self.env, 'fleet_officer_allowed', name='Fleet Officer Allowed',
            groups='fleet.fleet_group_user',
            company_id=company_b.id, company_ids=[(6, 0, (company_a + company_b).ids)])
        new_test_user(
            self.env, 'fleet_officer_foreign', name='Fleet Officer Foreign',
            groups='fleet.fleet_group_user',
            company_id=company_b.id, company_ids=[(6, 0, company_b.ids)])

        self.start_tour(f'/odoo/fleet/{vehicle.id}', 'fleet_manager_tour', login='admin')
