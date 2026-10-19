from odoo import fields, models


class TestToolsPartner(models.Model):
    _name = 'test_tools.partner'
    _description = 'Test Tools Partner'

    name = fields.Char()


class TestToolsPartnerCategory(models.Model):
    _name = 'test_tools.partner.category'
    _description = 'Test Tools Partner Category'

    name = fields.Char(translate=True)


class TestToolsPartnerIndustry(models.Model):
    _name = 'test_tools.partner.industry'
    _description = 'Test Tools Partner Industry'

    name = fields.Char(translate=True)


class TestToolsGroups(models.Model):
    _name = 'test_tools.groups'
    _description = 'Test Tools Groups'

    name = fields.Char(translate=True)
    comment = fields.Text(translate=True)


class TestToolsCompany(models.Model):
    _name = 'test_tools.company'
    _description = 'Test Tools Company'

    name = fields.Char()
    report_footer = fields.Html(translate=True)
