from odoo import api, models, fields
from odoo.exceptions import AccessError


class TranslationWizard(models.TransientModel):
    _name = 'translation.field.wizard'
    _description = "Translation Field Wizard"

    translation_ids = fields.One2many('translation.wizard.sub', 'translation_wizard_id', string="Translations")

    @api.model
    def default_get(self, fields_list):
        res = super(TranslationWizard, self).default_get(fields_list)
        IrTranslation = self.env['ir.translation']

        main_lang = 'en_US'

        model = self.env.context['model']
        domain_id = self.env.context['id']
        field = self.env.context['field']
        record = self.env[model].with_context(lang=main_lang).browse(domain_id)
        domain = ['&', ('res_id', '=', domain_id), ('name', '=like', model + ',%')]

        def make_domain(fld, rec):
            name = "%s,%s" % (fld.model_name, fld.name)
            return ['&', ('res_id', '=', rec.id), ('name', '=', name)]

        # insert missing translations, and extend domain for related fields
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
            assert fld.translate and rec._name == fld.model_name
            IrTranslation.insert_missing(fld, rec)

        if field:
            fld = record._fields[field]
            if not fld.related:
                res['context'] = {
                    'search_default_name': "%s,%s" % (fld.model_name, fld.name),
                }
            else:
                rec = record
                try:
                    while fld.related:
                        rec, fld = fld.traverse_related(rec)
                    if rec:
                        rec['context'] = {'search_default_name': "%s,%s" % (fld.model_name, fld.name), }
                except AccessError:
                    pass

        domain += [('lang', '!=', self._context.get('lang')), '|', ('name', '=', "%s,%s" % (fld.model_name, fld.name)), ('name', 'ilike', "%s,%s" % (fld.model_name, fld.name))]
        irTranslations = IrTranslation.search(domain)
        res['translation_ids'] = [[0, False, {
            'source': line.source,
            'value': line.value or line.source,
            'lang': line.lang,
            'ir_translation_id': line.id,
        }] for line in irTranslations]
        return res

    @api.multi
    def translation_confirm(self):
        return True


class TranslationWizardSub(models.TransientModel):
    _name = 'translation.wizard.sub'
    _description = "Translation Sub Model"

    translation_wizard_id = fields.Many2one('translation.field.wizard')
    ir_translation_id = fields.Many2one('ir.translation', 'Translation')
    source = fields.Text(string='Source term')
    value = fields.Text(related="ir_translation_id.value", string='Translation Value', store=True, readonly=False)
    lang = fields.Selection(selection='_get_languages', string='Language', validate=False)

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].search([('translatable', '=', True)])
        return [(lang.code, lang.name) for lang in langs]
