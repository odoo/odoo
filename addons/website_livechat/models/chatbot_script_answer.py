# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ChatbotScriptAnswer(models.Model):
    _inherit = 'chatbot.script.answer'

    redirect_record_ref = fields.Reference(
        selection='_selection_redirect_record_ref', string="Redirect Page", index='btree_not_null',
        help="The visitor will be redirected to the website page of this record upon clicking the option. "
             "Takes precedence over the redirect link.")

    @api.model
    def _selection_redirect_record_ref(self):
        located_mixin = self.env.registry['website.located.mixin']
        searchable_mixin = self.env.registry['website.searchable.mixin']
        model_names = [
            name for name, model_cls in self.env.registry.items()
            if not model_cls._abstract and not model_cls._transient
            and issubclass(model_cls, located_mixin) and issubclass(model_cls, searchable_mixin)
            and name != 'website.controller.page'
        ]
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([('model', 'in', model_names)])]

    def _get_redirect_link(self):
        # sudo - website.searchable.mixin: visitor can be redirected to any record linked by the chatbot
        if (record_sudo := self.sudo().redirect_record_ref) and record_sudo.exists():
            return record_sudo.website_url
        return super()._get_redirect_link()
