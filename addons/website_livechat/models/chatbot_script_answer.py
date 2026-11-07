# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin


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
            and model_cls._compute_website_url is not located_mixin._compute_website_url
        ]
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([('model', 'in', model_names)])]

    @api.constrains('redirect_record_ref')
    def _check_redirect_record_ref_published(self):
        if unpublished := self.filtered(
            lambda answer: answer.redirect_record_ref
            and 'is_published' in answer.redirect_record_ref._fields
            and not answer.redirect_record_ref.is_published,
        ):
            raise ValidationError(self.env._(
                "The following pages must be published to be used as chatbot redirection:\n%(pages)s",
                pages="\n".join(f"- {answer.redirect_record_ref.display_name}" for answer in unpublished),
            ))

    def _get_redirect_link(self):
        # sudo - website.searchable.mixin: visitor can be redirected to records linked by the chatbot
        record_sudo = self.sudo().redirect_record_ref
        # The website fields disappear when the website module is uninstalled.
        if not record_sudo or 'website_url' not in record_sudo or not record_sudo.exists():
            return super()._get_redirect_link()

        # Shared records use the visitor's website; links must remain absolute
        # for livechat embedded on external sites.
        is_shared = 'website_id' not in record_sudo or not record_sudo.website_id
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        if is_shared and website:
            return urljoin(website.get_base_url(), record_sudo.website_url)
        return record_sudo.website_absolute_url
