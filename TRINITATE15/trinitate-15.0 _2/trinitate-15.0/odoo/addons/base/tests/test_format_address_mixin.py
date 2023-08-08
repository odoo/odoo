from odoo.addons.base.tests.test_views import ViewCase


class FormatAddressCase(ViewCase):
    def assertAddressView(self, model):
        # pe_partner_address_form
        address_arch = """<form><div class="o_address_format"><field name="city"/></div></form>"""
        address_view = self.View.create({
            'name': 'view',
            'model': model,
            'arch': address_arch,
            'priority': 900,
        })

        # view can be created without address_view
        form_arch = """<form><field name="id"/><div class="o_address_format"><field name="street"/></div></form>"""
        view = self.View.create({
            'name': 'view',
            'model': model,
            'arch': form_arch,
        })

        # default view, no address_view defined
        arch = self.env[model].get_view(view.id)['arch']
        self.assertIn('"street"', arch)
        self.assertNotIn('"city"', arch)

        # custom view, address_view defined
        self.env.company.country_id.address_view_id = address_view
        arch = self.env[model].get_view(view.id)['arch']
        self.assertNotIn('"street"', arch)
        self.assertIn('"city"', arch)
        # weird result: <form> inside a <form>
        self.assertRegex(arch, r"<form>.*<form>.*</form>.*</form>")
        # no_address_format context
        arch = self.env[model].with_context(no_address_format=True).get_view(view.id)['arch']
        self.assertIn('"street"', arch)
        self.assertNotIn('"city"', arch)

        belgium = self.env.ref('base.be')
        france = self.env.ref('base.fr')

        belgium.address_view_id = None
        france.address_view_id = address_view

        company_a, company_b = self.env['res.company'].create([
            {'name': 'foo', 'country_id': belgium.id},
            {'name': 'bar', 'country_id': france.id},
        ])

        arch = self.env[model].with_company(company_a).get_view(view.id)['arch']
        self.assertIn('"street"', arch)
        self.assertNotIn('"city"', arch)

        arch = self.env[model].with_company(company_b).get_view(view.id)['arch']
        self.assertNotIn('"street"', arch)
        self.assertIn('"city"', arch)


class TestPartnerFormatAddress(FormatAddressCase):
    def test_address_view(self):
        self.assertAddressView('res.partner')
