from odoo import fields, models


class TestWebPartner(models.Model):
    _name = 'test_web.partner'
    _description = 'Test Web Partner'

    def _default_category(self):
        return self.env['test_web.partner.category'].browse(self.env.context.get('category_id'))

    name = fields.Char()
    type = fields.Selection([
        ('contact', 'Contact'),
        ('invoice', 'Invoice'),
        ('delivery', 'Delivery'),
        ('other', 'Other'),
    ], default='contact')
    category_id = fields.Many2many('test_web.partner.category', column1='partner_id', column2='category_id', string='Tags', default=_default_category)


class TestWebPartnerCategory(models.Model):
    _name = 'test_web.partner.category'
    _description = 'Test Web Partner Category'

    name = fields.Char()
    partner_ids = fields.Many2many('test_web.partner', column1='category_id', column2='partner_id')


class TestWebCountry(models.Model):
    _name = 'test_web.country'
    _description = 'Test Web Country'

    name = fields.Char()
