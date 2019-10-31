import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_admin(self):
        # Seen that:
        # - this test relies on demo data that are entirely in USD (pricelists)
        # - that main demo company is gelocated in US
        # - that this test awaits for hardcoded USDs amount
        # we have to force company currency as USDs only for this test
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.env.ref('base.USD').id, self.env.ref('base.main_company').id])
        self.start_tour("/", 'event_buy_tickets', login="admin")

    def test_demo(self):
        self.start_tour("/", 'event_buy_tickets', login="demo")

    # TO DO - add public test with new address when convert to web.tour format.
