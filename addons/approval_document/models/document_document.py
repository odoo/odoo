from odoo import fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

DOCUMENT_ACCESS_ROLES = ("view", "edit")

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _name = "document.document"
    _inherit = ["document.document", "mixin.approval.access"]
    _access_approval_category = "approval_document.approval_category_document_access"

    def _get_partner_permission(self, partner) -> str:
        self.check_singleton()
        now = fields.Datetime.now()
        roles = {
            access.role
            for access in self.sudo().access_ids
            if access.partner_id == partner
            and access.role
            and (not access.expiration_date or access.expiration_date > now)
        }
        roles |= {self.with_user(user).user_permission for user in partner.user_ids}
        if _debug.logic.enabled:
            _debug.logic(
                "partner_permission",
                document=self,
                partner=partner,
                roles=sorted(r or "" for r in roles),
            )
        if "edit" in roles:
            return "edit"
        return "view" if "view" in roles else "none"

    def _has_access(self, partner, role=False):
        permission = self._get_partner_permission(partner)
        return permission == "edit" or (permission == "view" and role != "edit")

    def _request_access(self, partner, role=False):
        if role not in DOCUMENT_ACCESS_ROLES:
            _debug.logic("access_request_refused", reason="bad_role", role=role)
            raise UserError(self.env._("Ask to view or to edit a document."))
        if self.shortcut_document_id:
            _debug.logic("access_request_refused", reason="shortcut", document=self)
            raise UserError(
                self.env._("Ask for access to the document a shortcut points to.")
            )
        _debug.lifecycle("access_requested", document=self, partner=partner, role=role)
        return super()._request_access(partner, role)

    def _get_access_request_name(self, partner, role):
        if role == "edit":
            return self.env._(
                "Edit access to %(document)s for %(partner)s",
                document=self.name,
                partner=partner.name,
            )
        return self.env._(
            "View access to %(document)s for %(partner)s",
            document=self.name,
            partner=partner.name,
        )

    def _grant_access(self, partner, role=False):
        _debug.lifecycle("access_granted", document=self, partner=partner, role=role)
        self.sudo().action_update_access_rights(partners={partner: (role, None)})
