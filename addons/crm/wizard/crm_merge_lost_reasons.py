from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MergeLostReasons(models.TransientModel):
    _name = 'crm.merge.lost.reasons'
    _description = 'Merge Lost Reasons'

    @api.model
    def default_get(self, fields):
        res = super(MergeLostReasons, self).default_get(fields)
        lost_reason_ids = self._context.get('active_ids')
        res['lost_reason_id'] = lost_reason_ids[0]
        res['lost_reasons_ids'] = lost_reason_ids

        return res

    lost_reason_id = fields.Many2one("crm.lost.reason", context={'append_id_to_name': True})
    lost_reasons_ids = fields.Many2many("crm.lost.reason")

    def action_merge_lost_reason(self):
        lost_reason_ids = self.env['crm.lost.reason'].browse(
            self._context.get('active_ids'))
        if len(lost_reason_ids) <= 1:
            raise UserError(
                _('Please select more than one Lost Reason from the list.'))
        if not all(ids.active for ids in lost_reason_ids):
            raise UserError(_('Only active lost reasons can be merged'))
        crm_lead_ids = self.env['crm.lead'].search(
            [('active', '=', False), ('lost_reason.id', 'in', lost_reason_ids.ids)])
        for lost_record_id in crm_lead_ids:
            lost_record_id.write({'lost_reason': self.lost_reason_id})
        for ids in lost_reason_ids:
            if self.lost_reason_id != ids:
                ids.write({'active': False})
