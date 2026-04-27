# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime

class SignRequestItem(models.Model):
    _inherit = "sign.request.item"

    itsme_validation_hash = fields.Char('itsme® Validation Token', readonly=True, copy=False)
    itsme_signer_name = fields.Char("itsme® Signer's Name", readonly=True, copy=False)
    itsme_signer_birthdate = fields.Date("itsme® Signer's Birthdate", readonly=True, copy=False)

    def write_itsme_data(self, itsme_hash, name, birthdate=None):
        self.ensure_one()
        if self.itsme_validation_hash or self.itsme_signer_name or self.itsme_signer_birthdate:
            return
        self.itsme_validation_hash = itsme_hash
        self.itsme_signer_name = name
        self.itsme_signer_birthdate = datetime.fromisoformat(birthdate)

    def _post_fill_request_item(self):
        for sri in self:
            if sri.role_id.auth_method == 'itsme' and not sri.itsme_validation_hash and not self.signed_without_extra_auth:
                raise ValidationError(_("Sign request item is not validated yet."))
        return super()._post_fill_request_item()

    def _edit_and_sign(self, signature, **kwargs):
        if self.role_id.auth_method == 'itsme':
            return self._sign(signature, validation_required=not self.signed_without_extra_auth, **kwargs)
        return super()._edit_and_sign(signature, **kwargs)
