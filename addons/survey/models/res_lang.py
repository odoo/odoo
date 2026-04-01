# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models, _
from odoo.exceptions import UserError


class ResLang(models.Model):
    _inherit = "res.lang"

    def write(self, vals):
        """ When languages are disabled, clear corresponding survey languages. """
        if 'active' in vals and not vals['active']:
            self.env['survey.user_input'].sudo().search([('lang_id', 'in', self.ids)]).lang_id = False
            surveys_sudo = self.env['survey.survey'].sudo().search([('lang_ids', 'in', self.ids)])
            if will_be_all_lang_survey_sudo := surveys_sudo.filtered(lambda survey: survey.lang_ids <= self):
                if len(self) > 1:
                    error = _("Cannot deactivate languages currently used by survey(s) only supporting those languages.")
                else:
                    error = _("Cannot deactivate a language currently used by survey(s) only supporting that language.")
                if self.env['survey.survey'].search(
                        [('id', 'in', will_be_all_lang_survey_sudo.ids)]) == will_be_all_lang_survey_sudo:
                    error += '\n'
                    error += _("Survey(s): %(surveys_list)s",
                               surveys_list=', '.join(f'"{survey.title}"' for survey in will_be_all_lang_survey_sudo))
                raise UserError(error)
            surveys_sudo.write({'lang_ids': [Command.unlink(lang.id) for lang in self]})
        return super().write(vals)
