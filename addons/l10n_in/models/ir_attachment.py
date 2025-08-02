from odoo import models, api
import json


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create_json_attachment(self, name, data, model, record_id, company_id=None):
        """
        Creates a JSON attachment linked to a record.

        :param name: Base name of the file (e.g., invoice number)
        :param data: Python dictionary to be dumped into JSON
        :param model: Model name as a string (e.g., 'account.move')
        :param record_id: ID of the record to link the attachment to
        :param company_id: Optional company ID; defaults to current user's company
        """
        json_name = f"{name.replace('/', '_')}.json"
        return self.create({
            'name': json_name,
            'raw': json.dumps(data).encode(),
            'res_model': model,
            'res_id': record_id,
            'mimetype': 'application/json',
            'company_id': company_id or self.env.company.id,
        })
