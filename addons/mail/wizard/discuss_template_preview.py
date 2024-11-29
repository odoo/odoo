# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class DiscussTemplatePreview(models.TransientModel):
    _name = 'discuss.template.preview'
    _description = 'Discuss Message Template Preview'

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    @api.model
    def _selection_languages(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        template_id = self.env.context.get('default_template_id')
        if not template_id or 'resource_ref' not in fields:
            return result
        discuss_template = self.env['discuss.template'].browse(template_id)
        res = self.env[discuss_template.model_id.model].search([], limit=1)
        if res:
            result['resource_ref'] = '%s,%s' % (discuss_template.model_id.model, res.id)
        return result

    template_id = fields.Many2one('discuss.template', string='Related Discuss Template', required=True)
    model_id = fields.Many2one('ir.model', string='Targeted model', related="template_id.model_id")
    lang = fields.Selection(_selection_languages, string='Template Preview Language')
    resource_ref = fields.Reference(
        string='Record',
        compute='_compute_resource_ref',
        compute_sudo=False, readonly=False,
        selection='_selection_target_model',
        store=True
    )
    no_record = fields.Boolean('No Record', compute='_compute_no_record')
    # Fields same than the discuss.template model, computed with resource_ref and lang
    subject = fields.Char('Subject', compute='_compute_discuss_template_fields')
    body = fields.Html('Body', compute='_compute_discuss_template_fields', sanitize=False)

    @api.depends('model_id')
    def _compute_no_record(self):
        for preview, preview_sudo in zip(self, self.sudo()):
            model_id = preview_sudo.model_id
            preview.no_record = not model_id or not self.env[model_id.model].search_count([])

    @api.depends('lang', 'no_record', 'resource_ref', 'template_id')
    def _compute_discuss_template_fields(self):
        to_update = self.filtered("template_id")
        to_reset = self - to_update
        to_reset.subject = False
        to_reset.body = False
        for preview in to_update:
            if preview.no_record or not preview.resource_ref:
                preview.subject = preview.template_id.subject
                preview.body = preview.template_id.body
            else:
                preview.subject = preview.template_id._render_field('subject', [preview.resource_ref.id], set_lang=preview.lang)[
                    preview.resource_ref.id
                ]
                preview.body = preview.template_id._render_field('body', [preview.resource_ref.id], set_lang=preview.lang)[
                    preview.resource_ref.id
                ]

    @api.depends('template_id')
    def _compute_resource_ref(self):
        to_update = self.filtered("template_id")
        to_reset = self - to_update
        to_reset.resource_ref = False
        for preview in to_update:
            template = preview.template_id.sudo()
            model = template.model
            res = self.env[model].search([], limit=1)
            preview.resource_ref = f'{model},{res.id}' if res else False
