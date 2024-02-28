from odoo import fields, models, _, _ct, _lt, _lct
from odoo.tools.translate import xml_translate


class TestTranslationImportModel1(models.Model):
    _name = 'test.translation.import.model1'
    _description = 'Translation Test 1'

    name = fields.Char('Name', translate=True, help='Help, English')
    selection = fields.Selection([
        ('foo', 'Selection Foo'),
        ('bar', 'Selection Bar'),
    ], export_string_translation=False)
    xml = fields.Text('XML', translate=xml_translate)

    def get_code_translation(self):
        _('slot')  # a code translation for both python and js(static/src/xml/js_template.xml)
        return _('Code, English')

    def get_code_context_translation(self):
        return _ct('context', 'Code, English')

    def get_code_lazy_translation(self):
        return _lt('Code Lazy, English')

    def get_code_lazy_context_translation(self):
        return _lct('context', 'Code Lazy, English')

    def get_code_placeholder_translation(self, *args, **kwargs):
        return _('Code, %s, English', *args, **kwargs)

    def get_code_context_placeholder_translation(self, *args, **kwargs):
        return _ct('context', 'Code, %s, English', *args, **kwargs)

    def get_code_named_placeholder_translation(self, *args, **kwargs):
        return _('Code, %(num)s, %(symbol)s, English', *args, **kwargs)

    def get_code_context_named_placeholder_translation(self, *args, **kwargs):
        return _ct('context', 'Code, %(num)s, %(symbol)s, English', *args, **kwargs)


class TestTranslationImportModel2(models.Model):
    _inherits = {'test.translation.import.model1': 'model1_id'}
    _name = 'test.translation.import.model2'
    _description = 'Translation Test 2'

    model1_id = fields.Many2one('test.translation.import.model1', required=True, ondelete='cascade')
