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
                )
        return super().create(vals_list)

    def write(self, vals):
        if self._should_add_seo_rels(vals):
            vals["body"] = add_seo_rels_to_links(
                vals["body"],
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
