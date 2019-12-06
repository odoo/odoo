# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, SUPERUSER_ID, _
from odoo.exceptions import UserError


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

    is_website = fields.Boolean(default=False, help="Allows us to filter relevant Campaign")
    color = fields.Integer(string='Color Index')

    active = fields.Boolean(default=True)
    reference_utm_campaign_id = fields.Many2one('utm.campaign', string="Merged Into Campaign", readonly=True,
        help="If this campaign was merged into another, we keep a reference to the merged campaign to be able to \
              transfer any new statistics.")

    def name_get(self):
        if self.env.context.get('show_id', False):
            return [(utm.id, "[%s] %s" % (utm.id, utm.name)) for utm in self]
        else:
            return super(UtmCampaign, self).name_get()

    @api.model
    def _group_expand_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    def _merge_utm_campaigns(self, campaign_to_keep):
        """Merge two or more campaigns. Archive all campaigns except
        campaign_to_keep, and set a reference to campaign_to_keep for all
        archived campaigns to lead statistics to the right campaign."""
        if len(self) <= 1:
            raise UserError(_('Please select more than one campaign from the list.'))
        if not all(campaign.active for campaign in self):
            raise UserError(_('Only active campaigns can be merged.'))
        if not campaign_to_keep or campaign_to_keep not in self:
            raise UserError(_('Kept campaign should be one of the merged campaigns.'))

        merge_values = {
            'is_website': any(campaign.is_website for campaign in self),
            'tag_ids': self.mapped('tag_ids')
        }
        campaign_to_keep.update(merge_values)

        deactivated_campaigns = self - campaign_to_keep
        deactivated_campaigns.write({'active': False, 'reference_utm_campaign_id': campaign_to_keep.id})
        self.search([('reference_utm_campaign_id', 'in', deactivated_campaigns.ids)]).write({
            'reference_utm_campaign_id': campaign_to_keep.id
        })

        self._clean_merged_campaigns_references(campaign_to_keep)

    def _clean_merged_campaigns_references(self, merged_campaign):
        """After a campaign merge, other modules with m2o linked to deactivated
        campaign should be redirect to the merged one. Search all fields that is
        m2o and linked to utm.campaign and not related field. Also ignore
        fields belong to AbstractModel and models we intentionally ignored."""
        fields_to_check = self.env['ir.model.fields'].search([
            ('ttype', '=', 'many2one'),
            ('relation', '=', 'utm.campaign'),
            ('related', '=', False)])
        for field in fields_to_check:
            if not field.model_id.transient:
                model = self.env[field.model]
                if model._auto and model._name not in self._get_ignored_merge_models():
                    self._clean_merged_campaigns_reference(model._name, field.name, merged_campaign)

    def _clean_merged_campaigns_reference(self, model_name, field_name, merged_campaign):
        """Given a model_name and field_name of its m2o field link to
        utm.campaign, change all records link to archived campaigns to the one
        we keep."""
        model = self.env[model_name]
        records_to_redirect = model.sudo().search([(field_name, 'in', (self - merged_campaign).ids)])
        if records_to_redirect:
            records_to_redirect.sudo().write({field_name: merged_campaign.id})

    def _get_ignored_merge_models(self):
        """After a campaign merge, other models with m2o linked to deactivated
        campaign should be redirect to the merge one, this is done
        automatically. If manual redirection is unneeded, override the method
        and append the module name to the list."""
        return [self._name]


class UtmSource(models.Model):
    _name = 'utm.source'
    _description = 'UTM Source'

    name = fields.Char(string='Source Name', required=True, translate=True)

class UtmStage(models.Model):
    """Stage for utm campaigns. """
    _name = 'utm.stage'
    _description = 'Campaign Stage'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer()

class UtmTag(models.Model):
    """Model of categories of utm campaigns, i.e. marketing, newsletter, ... """
    _name = 'utm.tag'
    _description = 'UTM Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
