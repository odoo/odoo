from odoo.exceptions import UserError
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

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
