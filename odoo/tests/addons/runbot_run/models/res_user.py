from odoo.addons.base.models.res_users import Users
from odoo.exceptions import UserError

_user_write = Users.write


forbidden_fields = ('password', 'login', 'totp_secret', 'lang')
def user_write(self, values_list):
    if self.env.registry.loaded and self.env.cr.dbname.endswith('-all'):
        for user, values in zip(self, values_list):
            if (any(field in values for field in forbidden_fields) and
                user.id in (self.env['ir.model.data']._xmlid_to_res_id('base.user_admin'),
                               self.env['ir.model.data']._xmlid_to_res_id('base.user_demo'))):

                message_suffix = "on -all database for users admin and demo. Please use another user or another database (-base, duplicated database, ...)"
                if "totp_secret" in values:
                    message = f"Runbot: Cannot enable 2fa {message_suffix}"
                elif "lang" in values:
                    message = f"Runbot: Cannot change lang {message_suffix}"
                else:
                    message = f"Runbot: Cannot change login and password {message_suffix}"
                raise UserError(message)

    _user_write(self, values_list)

Users.write = user_write
