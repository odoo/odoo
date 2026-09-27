from odoo import api, fields, models
from odoo.tools.translate import html_translate


class TestTranslationRelated_Translation_1(models.Model):
    _name = 'test_translation.related_translation_1'
    _description = 'A model to test translation for related fields'

    name = fields.Char('Name', translate=True)
    html = fields.Html('HTML', translate=html_translate)


class TestTranslationRelated_Translation_2(models.Model):
    _name = 'test_translation.related_translation_2'
    _description = 'A model to test translation for related fields'

    related_id = fields.Many2one('test_translation.related_translation_1', string='Parent Model')
    name = fields.Char('Name Related', related='related_id.name', readonly=False)
    html = fields.Html('HTML Related', related='related_id.html', readonly=False)
    computed_name = fields.Char('Name Computed', compute='_compute_name')
    name_en = fields.Char('Name EN', compute='_compute_name_en')
    computed_html = fields.Char('HTML Computed', compute='_compute_html')

    @api.depends_context('lang')
    @api.depends('related_id.name')
    def _compute_name(self):
        for record in self:
            record.computed_name = record.related_id.name

    @api.depends('name')
    def _compute_name_en(self):
        for record in self.with_context(lang='en_US'):
            record.name_en = record.name

    @api.depends_context('lang')
    @api.depends('related_id.html')
    def _compute_html(self):
        for record in self:
            record.computed_html = record.related_id.html


class TestTranslationRelated_Translation_3(models.Model):
    _name = 'test_translation.related_translation_3'
    _description = 'A model to test translation for related fields'

    related_id = fields.Many2one('test_translation.related_translation_2', string='Parent Model')
    name = fields.Char('Name Related', related='related_id.name', readonly=False)
    html = fields.Html('HTML Related', related='related_id.html', readonly=False)


class TestTranslationRelated_Translation_4(models.Model):
    _name = 'test_translation.related_translation_4'
    _description = 'A model to test translation for inherited translated fields'
    _inherits = {
        'test_translation.related_translation_1': 'related_id',
    }

    related_id = fields.Many2one('test_translation.related_translation_1', string='Parent Model', required=True, ondelete='cascade')
