# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    _date_res_id_id_for_burndown_chart = models.Index("(date, res_id, id) WHERE model = 'project.task' AND message_type = 'notification'")
