# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.report import render_report
from odoo import api, fields, models
from odoo.addons.decimal_precision import decimal_precision as dp


class MarketingCampaignActivity(models.Model):
    _name = "marketing.campaign.activity"
    _description = "Campaign Activity"
    _order = "name"


    name = fields.Char(required=True)
    campaign_id = fields.Many2one(
        'marketing.campaign', string='Campaign', required=True, ondelete='cascade', index=True)
    object_id = fields.Many2one(
        related='campaign_id.object_id', string='Object', readonly=True)
    start = fields.Boolean(
        help="This activity is launched when the campaign starts.", index=True)
    condition = fields.Text(required=True, default='True',
                        help="Python expression to decide whether the activity can be executed, otherwise it will be deleted or cancelled."
                        "The expression may use the following [browsable] variables:\n"
                        "   - activity: the campaign activity\n"
                        "   - workitem: the campaign workitem\n"
                        "   - resource: the resource object this campaign item represents\n"
                        "   - transitions: list of campaign transitions outgoing from this activity\n"
                        "...- re: Python regular expression module")
    type = fields.Selection(selection="_get_action_types", required=True, default='email',
                        help="""The type of action to execute when an item enters this activity, such as:
- Email: send an email using a predefined email template
- Report: print an existing Report defined on the resource item and save it into a specific directory
- Custom Action: execute a predefined action, e.g. to modify the fields of the resource record
""")
    email_template_id = fields.Many2one('mail.template', string='Email Template',
                                        help='The email to send when this activity is activated')
    report_id = fields.Many2one('ir.actions.report.xml', string='Report',
                                help='The report to generate when this activity is activated', )

    server_action_id = fields.Many2one('ir.actions.server', string='Action',
                                       help="The action to perform when this activity is activated")
    to_ids = fields.One2many('marketing.campaign.transition',
                             inverse_name='activity_from_id',
                             string='Next Activities')
    from_ids = fields.One2many('marketing.campaign.transition',
                               inverse_name='activity_to_id',
                               string='Previous Activities')
    variable_cost = fields.Float(help="Set a variable cost if you consider that every campaign item that has reached this point has entailed a certain cost. You can get cost statistics in the Reporting section",
                                 digits=dp.get_precision('Product Price'))
    revenue = fields.Float(help="Set an expected revenue if you consider that every campaign item that has reached this point has generated a certain revenue. You can get revenue statistics in the Reporting section",
                           digits=dp.get_precision('Account'))
    signal = fields.Char(
        help='An activity with a signal can be called programmatically. Be careful, the workitem is always created when a signal is sent')
    keep_if_condition_not_met = fields.Boolean(string="Don't Delete Workitems",
                                               help="By activating this option, workitems that aren't executed because the condition is not met are marked as cancelled instead of being deleted.")

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        segment_id = self.env.context.get('segment_id')
        if segment_id:
            segment = self.env['marketing.campaign.segment'].browse(segment_id)
            return segment.campaign_id.activity_ids
        return super(MarketingCampaignActivity, self).search(args, offset=offset, limit=limit, order=order, count=count)

    def _get_action_types(self):
        return [
            ('email', 'Email'),
            ('report', 'Report'),
            ('action', 'Custom Action'),
            # TODO implement the subcampaigns.
            # TODO implement the subcampaign out. disallow out transitions from
            # subcampaign activities ?
            #('subcampaign', 'Sub-Campaign'),
        ]

    def _process_wi_report(self, activity, workitem):
        report_data, format = render_report(self.env.cr, self.env.uid, [], activity.report_id.report_name, {}, context=self.env.context)
        attach_vals = {
            'name': '%s_%s_%s' % (activity.report_id.report_name, activity.name, workitem.partner_id.name),
            'datas_fname': '%s.%s' % (activity.report_id.report_name, activity.report_id.report_type),
            'datas': base64.encodestring(report_data),
        }
        self.env['ir.attachment'].create(attach_vals)

    def _process_wi_action(self, activity, workitem):
        server_obj = self.env['ir.actions.server']
        action_context = dict(self.env.context,
                              active_id=workitem.res_id,
                              active_ids=[workitem.res_id],
                              active_model=workitem.object_id.model,
                              workitem=workitem)
        server_obj.run.with_context([activity.server_action_id.id], context=action_context)

    def _process_wi_email(self, activity, workitem):
        return activity.email_template_id.send_mail(workitem.res_id)

    @api.multi
    def process(self, workitem):
        self.ensure_one()
        method = '_process_wi_%s' % (self.type,)
        action = getattr(self, method, None)
        if not action:
            raise NotImplementedError('Method %r is not implemented on %r object.' % (method, self))
        return action(self, workitem)
