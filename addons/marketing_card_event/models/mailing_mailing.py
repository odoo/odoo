from odoo import api, fields, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    @api.depends('card_campaign_id')
    def _compute_mailing_domain(self):
        super()._compute_mailing_domain()

        # we consider if the card campaign is based on an (allowed) model, from the event module, that has an "event_id" field
        # it's always relevant to limit the domain to the related event
        for mailing in self.filtered(
            lambda m: m.card_campaign_id and m.card_campaign_id.res_model in m.card_campaign_id._get_allowed_event_model_names()
        ):
            mailing_domain = fields.Domain(mailing._parse_mailing_domain())
            TargetModel = self.env[mailing.card_campaign_id.res_model]
            if (event_record := mailing.card_campaign_id.preview_record_ref) and 'event_id' in event_record:
                if not any(condition.field_expr == 'event_id' for condition in mailing_domain.iter_conditions()):
                    final_domain = fields.Domain('event_id', '=', event_record.event_id.id) & mailing_domain
                else:
                    # only support explicit '=' or 'in', if the condition is more complex nothing happens
                    # it is assumed the user knows what they are doing
                    final_domain = mailing_domain.optimize(TargetModel).map_conditions(
                        lambda condition: (
                            fields.Domain('event_id', '=', event_record.event_id.id)
                            if condition.field_expr == 'event_id' and condition.operator == 'in'
                            else condition
                        )
                    ).optimize(TargetModel)
            mailing.mailing_domain = repr(final_domain)
