# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from odoo import models
from odoo.addons.web.controllers.main import CSVExport, ExcelExport


class IrAsync(models.Model):
    _inherit = "ir.async"

    def _export_csv(self, data):
        """ Export CSV to an attachment instead of a http stream """
        exporter = CSVExport()
        blob = exporter._base(data, self.env)
        att = self._exported_data_as_attachment(exporter, data, blob)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': (f"/web/content/{att.id}/{att.name}?download=1"
                    f"&access_token={att.access_token}")
        }

    def _export_xlsx(self, data):
        """ Export XLSX to an attachment instead of a http stream """
        exporter = ExcelExport()
        blob = exporter._base(data, self.env)
        att = self._exported_data_as_attachment(exporter, data, blob)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': (f"/web/content/{att.id}/{att.name}?download=1"
                    f"&access_token={att.access_token}")
        }

    def _exported_data_as_attachment(self, exporter, params, data):
        """ Save the exported data in an attachment """
        fname = exporter.filename(params["model"])
        att = self.env['ir.attachment'].sudo().create({
            'name': fname,
            'datas': base64.b64encode(data),
            'type': 'binary',
            'res_model': 'ir.async',
            'res_id': self.env.context['async_job_id']
        })
        att.generate_access_token()
        return att
