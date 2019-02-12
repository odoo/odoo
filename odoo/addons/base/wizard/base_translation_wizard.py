from odoo import api, models, fields


class TranslationWizard(models.TransientModel):
    _name = 'translation.field.wizard'
    _description = "Translation Field Wizard"

    translation_ids = fields.One2many('translation.wizard.sub', 'translation_wizard_id', string="Translations")

    @api.model
    def default_get(self, fields_list):
        res = super(TranslationWizard, self).default_get(fields_list)
        IrTranslation = self.env['ir.translation']
        domain = self.env.context.get('translation_domain') or []
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