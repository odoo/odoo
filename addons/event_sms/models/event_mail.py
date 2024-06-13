# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    @api.model
    def _selection_template_model(self):
        return super(EventTypeMail, self)._selection_template_model() + [('sms.template', 'SMS')]

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')], ondelete={'sms': 'set default'})

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        sms_model = self.env['ir.model']._get('sms.template')
        sms_mails = self.filtered(lambda mail: mail.notification_type == 'sms')
        sms_mails.template_model_id = sms_model
        super(EventTypeMail, self - sms_mails)._compute_template_model_id()


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    @api.model
    def _selection_template_model(self):
        return super(EventMailScheduler, self)._selection_template_model() + [('sms.template', 'SMS')]

    def _selection_template_model_get_mapping(self):
        return {**super(EventMailScheduler, self)._selection_template_model_get_mapping(), 'sms': 'sms.template'}

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')], ondelete={'sms': 'set default'})

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        sms_model = self.env['ir.model']._get('sms.template')
        sms_mails = self.filtered(lambda mail: mail.notification_type == 'sms')
        sms_mails.template_model_id = sms_model
        super(EventMailScheduler, self - sms_mails)._compute_template_model_id()

    def execute(self):
        oneshot_sms = self._filter_to_skip(keep_type='sms')._filter_template_ref(notification_type="sms")
        for scheduler in oneshot_sms:
            scheduler.event_id.registration_ids.filtered(
                lambda registration: registration.state != 'cancel'
            )._message_sms_schedule_mass(
                template=scheduler.template_ref,
                mass_keep_log=True
            )
            scheduler.update({
                'mail_done': True,
                'mail_count_done': len(scheduler.event_id.registration_ids.filtered(lambda r: r.state != 'cancel')),
            })

        return super(EventMailScheduler, self - oneshot_sms).execute()

    def _filter_template_ref_type_info(self, notification_type):
        if notification_type == "sms":
            return "sms.template", _("SMS template")
        return super()._filter_template_ref_type_info(notification_type)

    @api.onchange('notification_type')
    def set_template_ref_model(self):
        super().set_template_ref_model()
        mail_model = self.env['sms.template']
        if self.notification_type == 'sms':
            record = mail_model.search([('model', '=', 'event.registration')], limit=1)
            self.template_ref = "{},{}".format('sms.template', record.id) if record else False


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def execute(self):
        todo = self._filter_to_skip(keep_type='sms')

        # Exclude schedulers linked to invalid/unusable templates
        valid_schedulers = todo.scheduler_id._filter_template_ref(notification_type="sms")
        valid = todo.filtered(lambda r: r.scheduler_id in valid_schedulers)

        for scheduler, reg_mails in valid.grouped('scheduler_id').items():
            try:
                reg_mails.registration_id._message_sms_schedule_mass(
                    template=scheduler.template_ref,
                    mass_keep_log=True,
                )
            except Exception as e:  # noqa: BLE001 we should never raise and rollback here
                _logger.warning('An issue happened when sending sms template ID %s. Received error %s',
                                scheduler.template_ref.id, e)
        valid.write({'mail_sent': True})

        return super().execute()
