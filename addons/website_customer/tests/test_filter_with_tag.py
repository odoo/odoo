from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class CustomerFilterWithTag(HttpCase):
    def test_customer_filter_with_tag(self):
        partner_AB = self.env['res.partner'].create({'name': "Partner AB"})
        tag_A = self.env['res.partner.tag'].create({'name': "Tag A"})
        tag_B = self.env['res.partner.tag'].create({'name': "Tag B"})

        self.env['res.partner'].create([{
            'name': "Company A",
            'assigned_partner_id': partner_AB.id,
            'website_published': True,
            'website_tag_ids': [tag_A.id, tag_B.id],
        }])

        self.env['res.partner'].create([{
            'name': "Company B",
            'assigned_partner_id': partner_AB.id,
            'website_published': True,
            'website_tag_ids': [tag_B.id],
        }])

        self.start_tour(
            self.env['website'].get_client_action_url("/customers"),
            'customer_filter_with_tag_tour',
            login='admin',
        )
