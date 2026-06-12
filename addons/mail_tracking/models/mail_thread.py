import logging

from odoo.exceptions import UserError
from odoo import api, models, _

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post(self, *, message_type='notification', **kwargs):
        if self and self._is_model_mailing_customers() and (
            message_type == 'notification' and (
                not kwargs.get('source_template_id') or not kwargs.get('source_view_id')
            )
        ):
            _logger.warning(
                _("Calling 'message_post' without view nor template")
            )
        return super().message_post(message_type=message_type, **kwargs)

    def message_notify(self, **kwargs):
        if self and self._is_model_mailing_customers() and (
            not kwargs.get('source_template_id') or not kwargs.get('source_view_id')
        ):
            _logger.warning(
                _("Calling 'message_notify' without view nor template")
            )
        return super().message_notify(**kwargs)

    @api.model
    def _is_model_mailing_customers(self):
        """Knows whether current model may contact external customers, which
        should enable outgoing message capabilities and restrictions. By
        default based on '_mailing_enabled' (i.e. being a model open for
        mass mailing means contacting external people) + potential custom
        list."""
        return getattr(self, '_mailing_enabled', False) or self._name in {
            'calendar.event',
            'forum.forum', 'forum.post',
            'slide.channel', 'slide.slide',
        }

    def _get_message_create_valid_field_names(self):
        return super()._get_message_create_valid_field_names() | {
            'source_template_id',
            'source_view_id',
            'tracking_value_ids',
        }

    def _get_log_valid_parameters(self):
        return super()._get_log_valid_parameters() | {
            'source_view_id',
            'tracking_value_ids',
        }

    def _get_message_parameters_updated_for_rendering(
        self, source_ref, source_template=False, source_view=False,
        render_values=None, **kwargs,
    ):
        render_values, kwargs = super()._get_message_parameters_updated_for_rendering(
            source_ref, source_template=source_template, source_view=source_view,
            render_values=render_values, **kwargs,
        )
        if source_template:
            # currently if template, code goes through composer -> use composer
            # field name and not 'source_template_id' message field name
            kwargs['template_id'] = source_template.id
        if source_view:
            kwargs['source_view_id'] = source_view.id
            if source_view.technical_usage != 'mail_post_source':
                _logger.warning(
                    _("Using an untagged view %(source_ref)s for rendering", source_ref=source_ref)
                )
        return render_values, kwargs

    def _check_can_update_message_content(self, messages):
        """" Checks that the current user can update the content of the message.
          * if no tracking;
        """
        super()._check_can_update_message_content(messages)
        if messages.tracking_value_ids:
            raise UserError(self.env._("Messages with tracking values cannot be modified"))

    def _message_create(self, values_list):
        for values in values_list:
            values['tracking_value_ids'] = [
                (0, 0, tracking_values)
                for tracking_values in values.get('tracking_values') or []
            ]
        return super()._message_create(values_list)
