import odoo.tests
@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestWebsiteCrm(odoo.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('website_crm_tour', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.website_crm_tour")

        # need environment using the test cursor as it's not committed
        record = self.env(cr=self.registry.test_cr)['crm.lead'].search([('description', '=', '### TOUR DATA ###')])
        assert record.env.cr is self.registry.test_cr
        assert len(record) == 1
        assert record.contact_name == 'John Smith'
        assert record.email_from == 'john@smith.com'
        assert record.partner_name == 'Odoo S.A.'
