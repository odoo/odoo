from odoo.tests import HttpCase, tagged
from odoo import Command


@tagged("-at_install", "post_install")
class CustomerFilterWithTag(HttpCase):
    def test_customer_filter_with_tag(self):

        partner_AB = self.env['res.partner'].create({'name': 'Partner AB', "company_type": "company"})

        self.env["res.partner"].create([{
            "name": "Company A",
            "company_type": "company",
            "assigned_partner_id": partner_AB.id,
            "website_published": True,
            "website_tag_ids": [
                Command.create({'name': 'Tag A'}),
                Command.create({'name': 'Tag B'}),
            ],
        }])

        self.env["res.partner"].create([{
            "name": "Company B",
            "company_type": "company",
            "assigned_partner_id": partner_AB.id,
            "website_published": True,
            "website_tag_ids": [Command.create({'name': 'Tag B'})],
        }])

        self.start_tour(
            self.env["website"].get_client_action_url("/customers"),
            "customer_filter_with_tag_tour",
            login="admin",
        )
