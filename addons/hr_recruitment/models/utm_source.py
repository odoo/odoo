from odoo import _, api, models
from odoo.exceptions import UserError


class UtmSource(models.Model):
    _inherit = "utm.source"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_recruitment_sources(self):
        linked_recruitment_sources = (
            self.env["hr.recruitment.source"]
            .sudo()
            .search([("source_id", "in", self.ids)])
        )

        if linked_recruitment_sources:
            raise UserError(
                _(
                    "You cannot delete these UTM Sources as they are linked to the following recruitment sources in "
                    "Recruitment:\n%(recruitment_sources)s",
                    recruitment_sources=", ".join(
                        sorted(
                            f'"{source.display_name}"'
                            for source in linked_recruitment_sources
                        )
                    ),
                )
            )
