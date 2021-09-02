# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Onestein - Andrea Stirpe
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailMail(models.AbstractModel):
    _inherit = "mail.mail"

    def _send_prepare_body(self):
        body = super()._send_prepare_body()
        return self.env["mail.render.mixin"].remove_href_odoo(
            body or "", remove_parent=0, remove_before=1
        )
