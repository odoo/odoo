from odoo import api, models, fields
from odoo.exceptions import AccessError
from odoo.osv import expression


class TranslationWizard(models.TransientModel):
    _name = 'translation.field.wizard'
    _description = "Translation Field Wizard"

    translation_lines = fields.One2many('translation.lines', 'translation_wizard_id', string="Translations")

    @api.model
    def default_get(self, fields_list):
        res = super(TranslationWizard, self).default_get(fields_list)
        IrTranslation = self.env['ir.translation']

        domain = self._prepare_domain_to_get_records()
        translations = IrTranslation.search(domain)
        res['translation_lines'] = [(0, False, {
            'value': line.value or line.source,
            'lang': line.lang,
            'ir_translation_id': line.id,
        }) for line in translations]
        return res

    def _prepare_domain_to_get_records(self):
        """ Prepares domain to find records from ir.translation for given field in context
        """
        model = self.env.context['default_model']
        recordID = self.env.context['default_id']
        field = self.env.context['field']
        record = self.env[model].with_context(lang='en_US').browse(recordID)

        domain = ['&', ('res_id', '=', recordID), ('name', '=like', model + ',%'),]

        def make_domain(fld, rec):
            name = "%s,%s" % (fld.model_name, fld.name)
            return ['&', ('res_id', '=', rec.id), ('name', '=', name)]

        # extend domain for related fields
        for name, fld in record._fields.items():
            if not fld.translate:
                continue

            rec = record
            if fld.related:
                try:
                    # traverse related fields up to their data source
                    while fld.related:
                        rec, fld = fld.traverse_related(rec)
                    if rec:
                        domain = ['|'] + domain + make_domain(fld, rec)
                except AccessError:
                    continue

        if field:
            fld = record._fields[field]
            if not fld.related:
                domain += expression.OR([[('name', '=',  "%s,%s" % (fld.model_name, fld.name))], [('name', 'ilike', "%s,%s," % (fld.model_name, fld.name))]])
            else:
                rec = record
                try:
                    while fld.related:
                        rec, fld = fld.traverse_related(rec)
                    if rec:
                        domain += expression.OR([[('name', '=',  "%s,%s" % (fld.model_name, fld.name))], [('name', 'ilike', "%s,%s," % (fld.model_name, fld.name))]])
                except AccessError:
                    pass
        return domain

    @api.multi
    def button_dummy(self):
        return True


class TranslationLines(models.TransientModel):
    _name = 'translation.lines'
    _description = "Translation Lines"

    translation_wizard_id = fields.Many2one('translation.field.wizard')
    ir_translation_id = fields.Many2one('ir.translation', 'Translation ref')
    value = fields.Text(related="ir_translation_id.value", string='Translation', store=True, readonly=False)
    lang = fields.Selection(selection='_get_languages', string='Language', validate=False)

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].search([('translatable', '=', True)])
        return [(lang.code, lang.name) for lang in langs]
