from odoo import api, fields, models


class LinkToRecordWizard(models.TransientModel):
    _name = "documents.link_to_record_wizard"
    _description = "Documents Link to Record"

    def _get_model_domain(self):
        models = self.env['ir.model.access']._get_allowed_models() - {'documents.document'}
        return [('model', 'in', list(models)), ('is_mail_thread', '=', 'True')]

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name)
                for model in self.env['ir.model'].sudo().search([('model', '!=', 'documents.document'), ('is_mail_thread', '=', 'True')])]

    document_ids = fields.Many2many('documents.document', string='Documents', readonly=True)
    model_id = fields.Many2one('ir.model', string='Model', domain=_get_model_domain)
    is_readonly_model = fields.Boolean('is_readonly_model', default=True)
    resource_ref = fields.Reference(string='Record', selection='_selection_target_model')
    accessible_model_ids = fields.Many2many('ir.model', string='Models', compute='_compute_accessible_model_ids')

    @api.depends_context('uid')
    def _compute_accessible_model_ids(self):
        model_ids = self.env['ir.model'].sudo().search([('model', '!=', 'documents.document'), ('is_mail_thread', '=', 'True')])
        model_ids = model_ids.filtered(lambda m: self.env[m.model].has_access('write'))
        for link_to in self:
            link_to.accessible_model_ids = model_ids.ids

    def link_to(self):
        self.ensure_one()
        self.document_ids.with_company(self.env.company).write({
            'res_model': self.resource_ref._name,
            'res_id': self.resource_ref.id,
            'is_editable_attachment': True,
        })
