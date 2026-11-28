from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _index(self, bin_data, mimetype, checksum=None):
        # The KSeF batch parts are ZIP slices: nothing to index
        if self.env.context.get('skip_attachment_indexation'):
            return False
        return super()._index(bin_data, mimetype, checksum=checksum)
