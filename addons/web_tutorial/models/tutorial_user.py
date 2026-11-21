from odoo import fields, models


class TutorialUser(models.Model):
    """ The progress of a user in a tutorial, only reached with sudo """
    _name = 'web_tutorial.tutorial.user'
    _description = "Tutorial Progress"

    done = fields.Boolean(help="Whether the user finished or skipped the tutorial")
    done_step_ids = fields.Many2many("web_tutorial.step", string="Done Steps", help="The steps of the tutorial the user did")
    played_date = fields.Datetime(help="When the user last started the tutorial")
    tutorial_id = fields.Many2one("web_tutorial.tutorial", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")

    _uniq_tutorial_user = models.Constraint('unique(tutorial_id, user_id)', "A user has one progress by tutorial.")
