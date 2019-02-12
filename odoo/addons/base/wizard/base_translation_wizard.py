from odoo import api, models, fields
from odoo.exceptions import AccessError
from odoo.osv import expression


class TranslationWizard(models.TransientModel):
    _name = 'translation.field.wizard'
    _description = "Translation Field Wizard"

    show_src = fields.Boolean(default=False)
    translation_lines = fields.Many2many(comodel_name='ir.translation', string="Translations")

    @api.onchange('show_src')
    def _onchange_show_src(self):
        model = self.env.context['translated_model']
        res_id = self.env.context['translated_res_id']
        field = self.env.context['translated_field']
        record = self.env[model].browse(res_id)

        fld = record._fields[field]
        if fld.related:
            # traverse related field to construct domain on another model
            try:
                while fld.related:
                    record, fld = fld.traverse_related(record)
                res_id = record.id
            except AccessError:
                pass

        translation_name = "%s,%s" % (fld.model_name, fld.name)
        domain = [
            ('lang', '!=', self.env.context['lang']),
            ('res_id', '=', res_id),
            ('name', '=', translation_name),
        ]

        translations = self.env['ir.translation'].search(domain, order='lang, src')
        self.translation_lines = [(6, False, translations.ids)] + [(1, t.id, {
            # newly generated translations have no value, prefill with source
            'value': t.source,
        }) for t in translations if not t.value]

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        model_name = self.env.context['translated_model']
        field_name = self.env.context['translated_field']

        # for better UX, will show the source too for complexe translations
        field = self.env[model_name]._fields[field_name]
        if callable(field.translate):
            res['show_src'] = True

        return res
