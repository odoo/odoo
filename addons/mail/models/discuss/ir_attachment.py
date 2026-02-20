# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo import models, fields
from odoo.tools import OrderedSet
from odoo.addons.mail.tools.discuss import Store


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    voice_ids = fields.One2many("discuss.voice.metadata", "attachment_id")

    def _check_access(self, operation):
        """Check access for attachments in Discuss channels.

        An attachment can be deleted by:
        - the author of the message related to the attachment.
        - admins/owners of the channel.
        - system admins.

        This method acts as a strict filter on `super()`, only removing access.
        """
        res = super()._check_access(operation)

        if operation not in ("write", "unlink"):
            return res
        if self.env.is_system():
            return res

        remaining = self
        error_func = None
        forbidden_ids = OrderedSet()
        if res:
            forbidden, error_func = res
            remaining -= forbidden
            forbidden_ids.update(forbidden._ids)

        channel_attachments_sudo = remaining.sudo().filtered(lambda a: a.res_model == "discuss.channel")
        if not channel_attachments_sudo:
            return res

        channels = self.env["discuss.channel"].browse(channel_attachments_sudo.mapped("res_id"))
        channel_by_id = {c.id: c for c in channels}
        for attachment in channel_attachments_sudo:
            if any(message.author_id == self.env.user.partner_id for message in attachment.message_ids):
                continue
            if channel_by_id[attachment.res_id].self_member_id.sudo().channel_role in ("admin", "owner"):
                continue
            forbidden_ids.add(attachment.id)

        if forbidden_ids:
            forbidden = self.browse(forbidden_ids)
            if error_func is None:
                error_func = partial(forbidden._make_access_error, operation)
            return forbidden, error_func

        return res

    def _bus_channel(self):
        self.ensure_one()
        if self.res_model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_channel()

    def _store_attachment_fields(self, res: Store.FieldList):
        super()._store_attachment_fields(res)
        # sudo: discuss.voice.metadata - checking the existence of voice metadata for accessible
        # attachments is fine
        res.many("voice_ids", [], sudo=True)

    def _store_permissions_fields(self, res: Store.FieldList):
        if self.env.user._is_internal():
            res.many("message_ids", ["author_id"])
        else:
            res.attr(
                "ownership_token",
                lambda a: a._get_ownership_token(),
                predicate=lambda a: any(m.is_current_user_or_guest_author for m in a.message_ids)
            )

    def _post_add_create(self, **kwargs):
        super()._post_add_create(**kwargs)
        if kwargs.get('voice'):
            self._set_voice_metadata()

    def _set_voice_metadata(self):
        self.env["discuss.voice.metadata"].create([{"attachment_id": att.id} for att in self])
