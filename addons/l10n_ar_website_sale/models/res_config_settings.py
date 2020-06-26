# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # group_show_line_subtotals_tax_excluded = fields.Boolean(group='base.group_portal,base.group_public')
    group_show_line_subtotals_tax_included = fields.Boolean(group='base.group_portal,base.group_public')

    def set_values(self):
        """ Every time the show_line_subtotals_tax_selection change to tax_included now internal users are leaved without
        tax group. This change let to ste Tax excluded B2B for all the internal users """
        super().set_values()
        if self.show_line_subtotals_tax_selection == 'tax_included':
            self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('account.group_show_line_subtotals_tax_excluded').id)]})
