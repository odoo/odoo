from odoo import fields, models
from odoo.tools.misc import limited_field_access_token

from odoo.addons.mail.tools.discuss import Store, StoreFieldSpec


class MixinMailPresence(models.AbstractModel):
    _name = "mixin.mail.presence"
    _description = "Presence of a partner or a guest, served with an access token"

    im_status = fields.Char(
        string="IM Status",
        compute="_compute_presence",
        compute_sudo=True,
    )
    offline_since = fields.Datetime(
        string="Offline since",
        compute="_compute_presence",
        compute_sudo=True,
    )

    def _compute_presence(self) -> None:
        self.im_status = False
        self.offline_since = False

    def _get_im_status_access_token(self) -> str:
        self.check_singleton()
        return limited_field_access_token(self, "im_status", scope="mail.presence")

    def _field_store_repr(self, field_spec: StoreFieldSpec) -> list[StoreFieldSpec]:
        if field_spec == "avatar_128":
            return [
                Store.Attr(
                    "avatar_128_access_token",
                    lambda record: record._get_avatar_128_access_token(),
                ),
                "write_date",
            ]
        if field_spec == "im_status":
            return [
                "im_status",
                Store.Attr(
                    "im_status_access_token",
                    lambda record: record._get_im_status_access_token(),
                ),
            ]
        return super()._field_store_repr(field_spec)
