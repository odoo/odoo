import uuid

from odoo import fields, models

from ..tools import debug_log as dbg


def _new_access_token():
    return str(uuid.uuid4())


class MixinPosBus(models.AbstractModel):
    _name = "mixin.pos.bus"
    _description = "Bus Mixin"

    access_token = fields.Char(
        string="Security Token",
        default=lambda self: _new_access_token(),
        copy=False,
    )

    def _get_access_token(self):
        self.check_singleton()
        if self.access_token:
            return self.access_token
        token = _new_access_token()
        dbg.lifecycle.debug("access token minted for %s", dbg.rec(self))
        self.sudo().access_token = token
        return token

    def _notify(self, *notifications, private=True) -> None:
        self.check_singleton()
        token = self._get_access_token()
        if isinstance(notifications[0], str):
            if len(notifications) != 2:
                raise ValueError(
                    "If you want to send a single notification, you must provide a name: str and a message: any"
                )
            notifications = [notifications]
        for name, message in notifications:
            dbg.pipeline.debug(
                "[bus] %s -> %s private=%s payload=%s",
                name,
                dbg.rec(self),
                private,
                dbg.lazy(
                    lambda message=message: (
                        sorted(message)
                        if isinstance(message, dict)
                        else type(message).__name__
                    )
                ),
            )
            self.env["bus.bus"]._sendone(
                token,
                f"{token}-{name}" if private else name,
                message,
            )
