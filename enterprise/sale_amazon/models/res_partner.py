# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    amazon_email = fields.Char(help="The encrypted email of the customer. Does not forward mails.")

    def _amazon_create_activity_set_state(self, user_id, state_code):
        """ Create an activity on the Amazon partner for the salesperson to set the state.

        :param int user_id: The salesperson of the related Amazon account.
        :param str state_code: The state code received from Amazon.
        :return: None.
        """
        activity_message = _(
            "This Amazon partner was created with an invalid state (%s); please set the correct"
            " state manually.",
            state_code,
        )
        self.activity_schedule(
            act_type_xmlid='mail.mail_activity_data_todo',
            user_id=user_id,
            note=activity_message,
        )
