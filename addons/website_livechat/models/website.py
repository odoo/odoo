# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.mail.tools.discuss import add_guest_to_context


class Website(models.Model):
    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel')

    @add_guest_to_context
    def _get_livechat_channel_info(self):
        """ Get the livechat info dict (button text, channel name, ...) for the livechat channel of
            the current website.
        """
        self.ensure_one()
        if self.channel_id:
            # sudo - im_livechat.channel: getting bsaic info related to live chat channel is allowed.
            return self.channel_id.sudo().get_livechat_info()
        return {}

    @api.model
    def search_url_dependencies(self, res_model, res_ids):
        dependencies = super().search_url_dependencies(res_model, res_ids)
        if not issubclass(self.env.registry[res_model], self.env.registry['website.searchable.mixin']):
            return dependencies
        records = self.env[res_model].browse([int(res_id) for res_id in res_ids])
        answers_sudo = records._get_chatbot_redirect_answers()
        if not answers_sudo:
            return dependencies
        model_display_name = self.env['ir.model']._display_name_for(['chatbot.script.answer'])[0]['display_name']
        field_string = answers_sudo.fields_get(['redirect_record_ref'])['redirect_record_ref']['string']
        dependencies.setdefault(model_display_name, [])
        dependencies[model_display_name] += [{
            'field_name': field_string,
            'record_name': f"{answer.chatbot_script_id.title}: {answer.display_name}",
            'link': f'/odoo/chatbot.script/{answer.chatbot_script_id.id}',
            'model_name': model_display_name,
            'url': answer.redirect_record_ref.website_url,
        } for answer in answers_sudo]
        return dependencies

    @api.model
    def _get_settings_to_copy_onto_new_default_website(self):
        """ Provides a list of settings that should always be set on the default
        website. When the default website changes, a check is performed. If some
        of these settings are not already set on the new default website, they
        are copied from the previous default website."""
        return super()._get_settings_to_copy_onto_new_default_website() + ['channel_id']
