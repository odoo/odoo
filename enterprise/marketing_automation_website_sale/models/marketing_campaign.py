from markupsafe import Markup

from odoo import api, models, _


class MarketingCampaign(models.Model):
    _inherit = 'marketing.campaign'

    @api.model
    def get_campaign_templates_info(self):
        campaign_templates_info = super().get_campaign_templates_info()
        campaign_templates_info.update({
            'sales': {
                'label': _("eCommerce"),
                'templates': {
                    'purchase_followup': {
                        'title': _('Purchase Follow-up'),
                        'description': _('Send an email to customers that bought a specific product after their purchase.'),
                        'icon': '/marketing_automation_website_sale/static/img/campaign_icons/cart.svg',
                        'function': '_get_marketing_template_purchase_followup',
                    },
                    'repeat_customer': {
                        'title': _('Create Repeat Customers'),
                        'description': _('Turn one-time visitors into repeat buyers.'),
                        'icon': '/marketing_automation_website_sale/static/img/campaign_icons/star.svg',
                        'function': '_get_marketing_template_repeat_customer',
                    },
                },
            }
        })
        return campaign_templates_info

    def _get_marketing_template_purchase_followup(self):
        campaign = self.env['marketing.campaign'].create({
            'name': _('Recent Purchase Follow-up'),
            'model_id': self.env['ir.model']._get_id('sale.order'),
            'domain': repr([('state', '=', 'sale'), ('team_id.website_ids', '!=', False)]),
        })
        followup_mailing_template = self.env.ref(
            'marketing_automation_website_sale.mailing_purchase_followup_arch',
            raise_if_not_found=False
        )
        # we need to pass in dynamic expressions otherwise it will try to render them at this stage...
        followup_arch = self.env['ir.ui.view']._render_template(
            followup_mailing_template.id,
            {'name_dynamic_expression': Markup('<t t-out="object.partner_id.name"></t>')}
        ) if followup_mailing_template else ''
        followup_mailing = self.env['mailing.mailing'].create({
            'subject': _('How is everything going?'),
            'body_arch': followup_arch,
            'body_html': followup_arch,
            'mailing_model_id': self.env['ir.model']._get_id('sale.order'),
            'reply_to_mode': 'update',
            'use_in_marketing_automation': True,
            'mailing_type': 'mail',
        })
        self.env['marketing.activity'].create({
            'trigger_type': 'begin',
            'activity_type': 'email',
            'interval_type': 'days',
            'mass_mailing_id': followup_mailing.id,
            'interval_number': 7,
            'name': _('How is everything going?'),
            'campaign_id': campaign.id,
        })
        return campaign

    def _get_marketing_template_repeat_customer(self):
        campaign = self.env['marketing.campaign'].create({
            'name': _('Create Repeat Customers'),
            'model_id': self.env['ir.model']._get_id('sale.order'),
            'domain': repr([
                ('state', '=', 'sale'),
                ('team_id.website_ids', '!=', False),
                ('amount_untaxed', '>=', 100),
            ])
        })
        purchase_mailing_template = self.env.ref(
            'marketing_automation_website_sale.mailing_repeat_customer_new_purchase_arch',
            raise_if_not_found=False
        )
        arrivals_mailing_template = self.env.ref(
            'marketing_automation_website_sale.mailing_repeat_customer_new_arrivals_arch',
            raise_if_not_found=False
        )
        purchase_arch = self.env['ir.ui.view']._render_template(purchase_mailing_template.id) if purchase_mailing_template else ''
        arrivals_arch = self.env['ir.ui.view']._render_template(arrivals_mailing_template.id) if arrivals_mailing_template else ''
        purchase_mailing = self.env['mailing.mailing'].create({
            'subject': _('Thank you for your purchase'),
            'body_arch': purchase_arch,
            'body_html': purchase_arch,
            'mailing_model_id': self.env['ir.model']._get_id('sale.order'),
            'reply_to_mode': 'update',
            'use_in_marketing_automation': True,
            'mailing_type': 'mail',
        })
        arrivals_mailing = self.env['mailing.mailing'].create({
            'subject': _('Check out these new arrivals!'),
            'body_arch': arrivals_arch,
            'body_html': arrivals_arch,
            'mailing_model_id': self.env['ir.model']._get_id('sale.order'),
            'reply_to_mode': 'update',
            'use_in_marketing_automation': True,
            'mailing_type': 'mail',
        })
        self.env['marketing.activity'].create({
            'trigger_type': 'begin',
            'activity_type': 'email',
            'interval_type': 'days',
            'mass_mailing_id': purchase_mailing.id,
            'interval_number': 0,
            'name': _('Purchase Thanks'),
            'campaign_id': campaign.id,
            'child_ids': [
                (0, 0, {
                    'trigger_type': 'mail_open',
                    'activity_type': 'email',
                    'interval_type': 'weeks',
                    'mass_mailing_id': arrivals_mailing.id,
                    'interval_number': 1,
                    'name': _('New Arrivals'),
                    'campaign_id': campaign.id,
                }),
            ]
        })
        return campaign
