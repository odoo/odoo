from odoo import api, fields, models


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    failure_type = fields.Selection(
        selection_add=[
            ('twilio_authentication', 'Authentication Error"'),
            ('twilio_callback', 'Incorrect callback URL'),
            ('twilio_from_missing', 'Missing From Number'),
            ('twilio_from_to', 'From / To identic'),
        ],
    )

    # CRUD
    # ------------------------------------------------------------

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # As we are adding keys in stable, better be sure no-one is getting crashes
        # due to missing translations
        # TODO: remove in master
        res = super().fields_get(allfields=allfields, attributes=attributes)

        existing_selection = res.get('failure_type', {}).get('selection')
        if existing_selection is None:
            return res

        updated_stable = {
            'twilio_authentication', 'twilio_callback',
            'twilio_from_missing', 'twilio_from_to',
        }
        need_update = updated_stable - set(dict(self._fields['failure_type'].selection))
        if need_update:
            self.env['ir.model.fields'].invalidate_model(['selection_ids'])
            self.env['ir.model.fields.selection']._update_selection(
                self._name,
                'failure_type',
                self._fields['failure_type'].selection,
            )
            self.env.registry.clear_cache()
            return super().fields_get(allfields=allfields, attributes=attributes)

        return res
