from odoo import fields, models


class JobMatchProfile(models.Model):
    _name = 'job.match.profile'
    _description = 'Job Match Profile'
    _order = 'sequence, id'

    name = fields.Char('Job Profile', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer('Color')
    image_1920 = fields.Image('Image', max_width=1920, max_height=1920)
    image_512 = fields.Image(
        'Image 512', related='image_1920', max_width=512, max_height=512, store=True)
    description = fields.Html('Description', translate=True)
    posting_url = fields.Char(
        'Job Posting URL',
        help="Link to the job or internship posting shown on the result page.")
    weight_ids = fields.One2many(
        'job.match.answer.weight', 'profile_id', string='Answer Weights')
