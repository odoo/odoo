import re

from odoo import api, models


class KpiProvider(models.AbstractModel):
    _inherit = 'kpi.provider'

    @api.model
    def get_mail_activities_kpi_summary(self):
        domain = [
            '|', ('activity_type_id.kpi_provider_visibility', '=', 'all'),
                 '&', ('activity_type_id.kpi_provider_visibility', '=', 'own'),
                      ('user_id', '=', self.env.uid),
        ]
        count_by_activity_type = self.env['mail.activity'].sudo()._read_group(
            domain=domain,
            groupby=['activity_type_id'],
            aggregates=['__count'],
        )
        activity_types = self.env['mail.activity.type'].browse([pair[0].id for pair in count_by_activity_type])
        activity_types_external_ids = activity_types._get_external_ids()
        identifier_by_activity_type_id = {}
        for act_type in activity_types:
            if xmlids := activity_types_external_ids[act_type.id]:
                identifier = xmlids[0]
            else:
                identifier = act_type.name
            normalized_identifier = re.sub(r'[^a-z0-9]', '_', identifier.lower())
            identifier_by_activity_type_id[act_type.id] = 'mail_activity_type.' + normalized_identifier

        return [{
            'id': identifier_by_activity_type_id[act_type.id],
            'name': act_type.name,
            'type': 'integer',
            'value': count,
        } for act_type, count in count_by_activity_type]

    @api.model
    def get_kpi_summary(self):
        result = super().get_kpi_summary()
        result.extend(self.get_mail_activities_kpi_summary())
        return result
