# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    _task_user_active_idx = models.Index("(user_id) WHERE res_model='project.task' AND active = TRUE")
