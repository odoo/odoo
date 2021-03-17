# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models, api, SUPERUSER_ID


class UtmStage(models.Model):

    """Stage for utm campaigns. """
    _name = 'utm.stage'
    _description = 'Campaign Stage'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer()


class UtmMedium(models.Model):
    # OLD crm.case.channel
    _name = 'utm.medium'
    _description = 'UTM Medium'
    _order = 'name'

    name = fields.Char(string='Medium Name', required=True)
    active = fields.Boolean(default=True)


class UtmCampaign(models.Model):
    # OLD crm.case.resource.type
    _name = 'utm.campaign'
    _description = 'UTM Campaign'

    name = fields.Char(string='Campaign Name', required=True, translate=True)

    user_id = fields.Many2one(
        'res.users', string='Responsible',
        required=True, default=lambda self: self.env.uid)
    stage_id = fields.Many2one('utm.stage', string='Stage', ondelete='restrict', required=True,
        default=lambda self: self.env['utm.stage'].search([], limit=1),
        group_expand='_group_expand_stage_ids')
    tag_ids = fields.Many2many(
        'utm.tag', 'utm_tag_rel',
        'tag_id', 'campaign_id', string='Tags')

    is_auto_campaign = fields.Boolean(default=False, string="Automatically Generated Campaign", help="Allows us to filter relevant Campaigns")
    color = fields.Integer(string='Color Index')

    @api.model
    def _group_expand_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

class UtmSource(models.Model):
    _name = 'utm.source'
    _description = 'UTM Source'

    name = fields.Char(string='Source Name', required=True, translate=True)

class UtmTag(models.Model):
    """Model of categories of utm campaigns, i.e. marketing, newsletter, ... """
    _name = 'utm.tag'
    _description = 'UTM Tag'
    _order = 'name'

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(
        string='Color Index', default=lambda self: self._default_color(),
        help='Tag color. No color means no display in kanban to distinguish internal tags from public categorization tags.')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
