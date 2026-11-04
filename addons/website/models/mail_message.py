from odoo import api, models

from odoo.addons.website.tools import add_seo_rels_to_links


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self._should_add_seo_rels(vals):
                vals["body"] = add_seo_rels_to_links(
                    vals["body"],
                    self._get_seo_rels_base_url(vals),
                )
        return super().create(vals_list)

    def write(self, vals):
        if self._should_add_seo_rels(vals):
            vals["body"] = add_seo_rels_to_links(
                vals["body"],
                self._get_seo_rels_base_url(vals),
            )
        return super().write(vals)

    def _should_add_seo_rels(self, vals):
        """
        Return whether links in the comments should be marked as user-generated content.
        To mark a model's comments as user-generated content, add an attribute `_add_seo_rels = True`
        """
        if not vals.get("body"):
            return False
        model_name = vals.get("model") or self.model
        model = self.env.registry.get(model_name)
        return model and getattr(model, '_add_seo_rels', False)

    def _get_seo_rels_base_url(self, vals):
        """
        Return the base url of the website of the document the message is
        posted on, so that links to this website are not marked as
        user-generated.
        """
        if vals.get("model"):
            return self.env[vals["model"]].browse(vals.get("res_id")).get_base_url()
        return self.env[self.model].browse(self.res_id).get_base_url()
