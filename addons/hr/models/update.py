from odoo import api, models


class Publisher_WarrantyContract(models.AbstractModel):
    _inherit = 'publisher_warranty.contract'

    @api.model
    def _get_message(self):
        msg = super()._get_message()
        msg['nbr_employees_wo_user'] = self.env["hr.employee"].search_count([
            ('active', '=', True),
            '|', ('user_id', '=', False), ('user_id.active', '=', False),
        ])
        return msg
