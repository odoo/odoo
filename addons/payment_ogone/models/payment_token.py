# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    def write(self, values):
        """Override to prevent archiving of tokens during Ogone to Worldline migration.

        :param dict values: The values to write on the record.
        :return: None if the write is skipped, otherwise the result of the parent write.
        :rtype: bool or None
        """
        if self.env.context.get('skip_token_archival') and 'active' in values:
            values.pop('active')
        return super().write(values)
