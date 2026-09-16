# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sahla Sherin (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.addons.web_editor.tools import get_video_embed_code
from odoo.exceptions import ValidationError


class GymExercise(models.Model):
    """The model gym. exercise for defining the exercises."""
    _name = "gym.exercise"
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]
    _description = "Gym Exercises"
    _columns = {
        'image': fields.Binary("Image", help="This field holds the image"
                               )}

    name = fields.Char(string="Name", help='Define the name of exercise')
    exercise_for_ids = fields.Many2many("exercise.for",
                                        string="Exercise For",
                                        help='For which part this exercise')
    equipment_ids = fields.Many2one('product.product',
                                    string='Equipment',
                                    required=True, tracking=True,
                                    domain="[('gym_product', '!=',False)]",
                                    help='The equiments used')
    note_benefit = fields.Html(string='Note', help='Can add note here')
    note_step = fields.Html(string='Note', help='Can add note step')
    embed_code = fields.Html(compute="_compute_embed_code", sanitize=False,
                             help='The embed code')
    video_url = fields.Char(string='Video URL',
                            help='URL of a video for showcasing your product.')
    image = fields.Binary(string="Image", help="This field holds the image")
    image12 = fields.Binary(string="Image", help="This field holds the image")
    image123 = fields.Binary(string="Image", help="This field holds the image")
    image124 = fields.Binary(string="Image", help="This field holds the image")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='This field hold the company id')

    @api.constrains('video_url')
    def _check_valid_video_url(self):
        """Check url is valid or not """
        for image in self:
            if image.video_url and not image.embed_code:
                raise ValidationError(
                    _("Provided video URL for '%s' is not valid. "
                      "Please enter a valid video URL.", image.name))
    @api.depends('video_url')
    def _compute_embed_code(self):
        """To get video field """
        for image in self:
            image.embed_code = get_video_embed_code(image.video_url)
