from odoo.fields import Command


class WebsiteMassMailingMultiCompanyCommon:

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_marketing.write({'company_ids': [Command.link(cls.company_2.id)]})
        cls.website_a, cls.website_b = cls.env['website'].create([
            {
                'name': 'Website A',
                'company_id': cls.company_admin.id,
                'domain': 'http://website-a.test',
            },
            {
                'name': 'Website B',
                'company_id': cls.company_2.id,
                'domain': 'http://website-b.test',
            },
        ])
        cls.env['ir.config_parameter'].sudo().set_param('web.base.url', 'http://website-a.test')
