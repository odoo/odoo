from odoo import models, fields, api, _


class L10nGtEdiPhrase(models.Model):
    _name = "l10n_gt_edi.phrase"
    _description = "Guatemalan Phrases Object"
    _rec_names_search = ["phrase_type", 'scenario_code', "scenario_description"]

    phrase_type = fields.Integer(required=True)
    phrase_description = fields.Char(required=True)
    scenario_code = fields.Integer(required=True)
    scenario_description = fields.Char(required=True)
    pdf_message = fields.Char(required=True)

    @api.depends("phrase_type", "scenario_code")
    def _compute_display_name(self):
        """
        Render the display name in the format of "Type <type> Code <code>"
        """
        for item in self:
            item.display_name = _("Type %(type)s Code %(code)s", type=item.phrase_type, code=item.scenario_code)
