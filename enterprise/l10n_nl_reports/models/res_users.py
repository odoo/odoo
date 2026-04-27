from odoo import api, models, fields


class Users(models.Model):
    _inherit = 'res.users'

    l10n_nl_report_xaf_userid = fields.Char(compute='_get_l10n_nl_report_xaf_userid', store=False, compute_sudo=True)

    @api.depends('login', 'display_name')
    def _get_l10n_nl_report_xaf_userid(self):
        """Returns login or display name or truncated name with id"""
        for user in self:
            user.l10n_nl_report_xaf_userid = user.login
            if len(user.login) <= 35:
                user.l10n_nl_report_xaf_userid = user.login
            elif len(user.display_name) <= 35:
                user.l10n_nl_report_xaf_userid = user.display_name
            else:
                # Truncate the name on the last space/dash before the
                # 31th character (35 - len(" id:")) so the name is
                # nicely splited between two words
                truncated_name = user.display_name[:31 - len(str(user.id))]
                space_lidx = truncated_name.rfind(" ")  # not found => -1
                dash_lidx = truncated_name.rfind("-")  # not found => -1
                user.l10n_nl_report_xaf_userid = "{} id:{}".format(
                    truncated_name[:max(space_lidx, dash_lidx)], user.id)
