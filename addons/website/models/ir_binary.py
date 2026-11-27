from odoo import models
from odoo.fields import Domain


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record(
            self, xmlid=None, res_model='ir.attachment', res_id=None,
            access_token=None, field=None
    ):
        record = None
        if xmlid:
            website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
            if website.theme_id:
                # The website's own image first, then its theme's, then the generic one
                domain = Domain('key', '=', xmlid) & website.website_domain() & website._theme_domain()
                Attachment = self.env['ir.attachment']
                if self.env.user.share:
                    domain &= Domain('public', '=', True)
                    Attachment = Attachment.sudo()
                record = Attachment.search(domain, order='website_id, theme_id', limit=1)

        if not record:
            record = super()._find_record(xmlid, res_model, res_id, access_token, field=field)

        return record
