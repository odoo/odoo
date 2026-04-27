from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_get_suggested_recipients(self):
        """ This Studio override adds the field 'x_studio_partner_id' in the auto-suggested list."""
        result = super()._message_get_suggested_recipients()
        # TODO: also support x_studio_user_id?
        field = self._fields.get('x_studio_partner_id')
        if field and field.type == 'many2one' and field.comodel_name == 'res.partner':
            if self.x_studio_partner_id:
                self._message_add_suggested_recipient(result, partner=self.x_studio_partner_id, reason=self._fields['x_studio_partner_id'].string)
        return result

    def _mail_get_partner_fields(self, introspect_fields=False):
        """Include partner field set automatically by studio as an SMS recipient."""
        fields = super()._mail_get_partner_fields(introspect_fields=introspect_fields)
        field = self._fields.get('x_studio_partner_id')
        if field and field.type == 'many2one' and field.comodel_name == 'res.partner':
            fields.append('x_studio_partner_id')
        return fields
