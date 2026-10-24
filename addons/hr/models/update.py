from odoo import api, models, fields


class Publisher_WarrantyContract(models.AbstractModel):
    _inherit = 'publisher_warranty.contract'

    @api.model
    def _get_message(self):
        msg = super()._get_message()
        date_now = fields.Date.context_today(self)
        msg['nbr_employees_wo_user'] = self.env["hr.employee"].search_count([
            ('active', '=', True),
            ('version_ids', 'any', [
                ('contract_date_start', '!=', False), ('contract_date_start', '<=', date_now),
                '|', ('contract_date_end', '>=', date_now), ('contract_date_end', '=', False),
            ]),
            '|', ('user_id', '=', False),
                '|', ('user_id.active', '=', False),
                     ('user_id.share', '=', True),
        ])
        return msg
