from odoo import models
from odoo.exceptions import UserError


class BaseModuleInstallRequest(models.Model):
    _name = "base.module.install.request"
    _inherit = ["base.module.install.request", "mixin.approval"]

    def _send_request(self):
        """Ask the administrators through an approval request rather than an
        e-mail each: the request is the record of who asked, who decided and
        what they said, and the engine's activities are what reach them."""
        self.action_create_approval_request()

    def action_open_install_review(self):
        """Open the dependency review that ends in the install.

        Installing is not done from the approval decision itself: it commits and
        replaces the registry, which would pull the rest of the decision out from
        under the request still being written. It stays one explicit click, as it
        was when the administrator followed the e-mail's link.
        """
        self.check_singleton()
        if self.approval_state != "approved":
            raise UserError(
                self.env._("This activation request has not been approved.")
            )
        return {
            **self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
                "base_install_request.action_base_module_install_review"
            ),
            "context": {"default_module_id": self.module_id.id},
        }

    def _get_domain_approval_category(self):
        category = self.env.ref(
            "approval_base_install_request.approval_category_module_activation",
            raise_if_not_found=False,
        )
        return [("id", "=", category.id)] if category else []

    def _get_fields_approval_protected(self):
        return ["module_id", "body_html"]

    def _get_approval_request_name(self):
        return self.env._('Activation of "%s"', self.module_id.shortdesc)

    def _get_approval_reason_html(self):
        return self.body_html or ""

    def _on_approval_approved(self):
        super()._on_approval_approved()
        for request in self:
            request.message_post(
                body=self.env._(
                    "Activation of %(module)s was approved. An administrator "
                    "installs it from this request.",
                    module=request.module_id.shortdesc,
                ),
                partner_ids=request.user_id.partner_id.ids,
                message_type="notification",
            )
