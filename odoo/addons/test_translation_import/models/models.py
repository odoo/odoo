# -*- coding: utf-8 -*-
from odoo import fields, models, _, _lt
from odoo.tools.translate import xml_translate

class TestTranslationImportModel1(models.Model):
    _name = 'test.translation.import.model1'
    _description = 'Translation Test 1'

    name = fields.Char('Name', translate=True, help='Help, English')
    selection = fields.Selection([
        ('foo', 'Selection Foo'),
        ('bar', 'Selection Bar'),
    ])
    xml = fields.Text('XML', translate=xml_translate)

    def get_code_translation(self):
        return _('Code, English')

    def get_code_lazy_translation(self):
        return _lt('Code Lazy, English')

    def get_code_placeholder_translation(self, *args, **kwargs):
        return _('Code, %s, English', *args, **kwargs)

    def get_code_named_placeholder_translation(self, *args, **kwargs):
        return _('Code, %(num)s, %(symbol)s, English', *args, **kwargs)
