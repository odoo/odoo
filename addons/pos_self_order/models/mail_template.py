from odoo import _, api, models

class MailTemplate(models.Model):
    _name = 'mail.template'
    _inherit = ['mail.template', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['pos.preset'].mail_template_id.ids)]

    def _load_pos_data_dependencies(self):
        return ['pos.preset']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id']

    def _render_lang(self, res_ids, engine='inline_template'):
        langs = super()._render_lang(res_ids, engine=engine)
        if self.render_model != 'pos.order':
            return langs
        for order in self.env['pos.order'].browse(filter(None, res_ids)):
            if lang := order.self_ordering_lang_id.filtered('active').code:
                langs[order.id] = lang
        return langs
