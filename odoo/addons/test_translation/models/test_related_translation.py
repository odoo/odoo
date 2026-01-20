from odoo import api, fields, models
from odoo.tools.translate import html_translate


class TestOrmRelated_Translation_1(models.Model):
    _name = 'test_orm.related_translation_1'
    _description = 'A model to test translation for related fields'

    name = fields.Char('Name', translate=True)
    html = fields.Html('HTML', translate=html_translate)


class TestOrmRelated_Translation_2(models.Model):
    _name = 'test_orm.related_translation_2'
    _description = 'A model to test translation for related fields'

    related_id = fields.Many2one('test_orm.related_translation_1', string='Parent Model')
    name = fields.Char('Name Related', related='related_id.name', readonly=False)
    html = fields.Html('HTML Related', related='related_id.html', readonly=False)
    computed_name = fields.Char('Name Computed', compute='_compute_name')
    computed_html = fields.Char('HTML Computed', compute='_compute_html')

    @api.depends_context('lang')
    @api.depends('related_id.name')
    def _compute_name(self):
        for record in self:
            record.computed_name = record.related_id.name

    @api.depends_context('lang')
    @api.depends('related_id.html')
    def _compute_html(self):
        for record in self:
            record.computed_html = record.related_id.html


class TestOrmRelated_Translation_3(models.Model):
    _name = 'test_orm.related_translation_3'
    _description = 'A model to test translation for related fields'

    related_id = fields.Many2one('test_orm.related_translation_2', string='Parent Model')
    name = fields.Char('Name Related', related='related_id.name', readonly=False)
    html = fields.Html('HTML Related', related='related_id.html', readonly=False)
