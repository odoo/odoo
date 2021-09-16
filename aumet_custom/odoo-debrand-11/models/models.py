from odoo import models, fields, api, _, exceptions


class OdooDebrand(models.Model):
    _inherit = 'website'

    @api.depends('favicon')
    def get_favicon(self):
        self.favicon_url = \
            'data:image/png;base64,' + str(self.favicon.decode('UTF-8'))
        # python 3.x has sequence of bytes object,
        #  so we should decode it, else we get data starting with 'b'

    @api.depends('company_logo')
    def get_company_logo(self):
        self.company_logo_url = \
            ('data:image/png;base64,' +
             str(self.company_logo.decode('utf-8')))

    company_logo = fields.Binary("Logo", attachment=True,
                                 help="This field holds"
                                      " the image used "
                                      "for the Company Logo")
    company_name = fields.Char("Company Name", help="Branding Name")
    company_website = fields.Char("Company URL")
    favicon_url = fields.Char("Url", compute='get_favicon')
    company_logo_url = fields.Char("Url", compute='get_company_logo')


class WebsiteConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    company_logo = fields.Binary(related='website_id.company_logo',
                                 string="Company Logo",
                                 help="This field holds the image"
                                      " used for the Company Logo",
                                 readonly=False)
    company_name = fields.Char(related='website_id.company_name',
                               string="Company Name",
                               readonly=False)
    company_website = fields.Char(related='website_id.company_website',
                                  readonly=False)

    # Sample Error Dialogue
    def error(self):
        raise exceptions.ValidationError(
            "This is a test Error message. You dont need to save the config after pop wizard.")

    # Sample Warning Dialogue
    def warning(self):
        raise exceptions.UserError("This is a test Error message. You don't need to save the config after pop wizard.")


from odoo import api, models, _


class Channel(models.Model):
    _inherit = 'mail.channel'

    @api.model
    def init_odoobot(self):
        if self.env.user.odoobot_state in [False, 'not_initialized']:
            odoobot_id = self.env['ir.model.data'].xmlid_to_res_id("base.partner_root")
            channel_info = self.channel_get([odoobot_id])
            channel = self.browse(channel_info['id'])
            message = _(
                "Hello,<br/>System chat helps employees collaborate efficiently. I'm here to help you discover its features.<br/><b>Try to send me an emoji</b> <span class=\"o_odoobot_command\">:)</span>")
            channel.sudo().message_post(body=message, author_id=odoobot_id, message_type="comment",
                                        subtype_xmlid="mail.mt_comment")
            self.env.user.odoobot_state = 'onboarding_emoji'
            return channel
