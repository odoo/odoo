# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Saneen K (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import api, models


class UploadMultiDocuments(models.Model):
    """
    This class handles the creation of attachments for multiple documents
    uploaded at once.

    Class: UploadMultiDocuments(models.Model)

    Attributes:
    - _name: A string representing the name of the model.

    Methods:
    - document_file_create(value, name, selected_ids, model): A method that
     creates an 'ir.attachment' record for each selected ID with the given name,
      data, res_model, and res_id attributes. The 'value' argument represents
      the uploaded file data, 'name' represents the file name, 'selected_ids'
      is a list of IDs for the records to which the attachments will be
      attached, and 'model' is the model to which the attachments will
     be attached.

    Returns: None
    """
    _name = "upload.multi.documents"
    _description = "Upload Multiple Documents"

    @api.model
    def document_file_create(self, value, name, selected_ids, model):
        """
        This method creates an 'ir.attachment' record for each selected ID with
        the given name, data, res_model, and res_id attributes.

        Method: document_file_create(value, name, selected_ids, model)

        Arguments:
        - value: A string representing the uploaded file data, encoded in
                base64 format.
        - name: A string representing the file name.
        - selected_ids: A list of integers representing the IDs for the
                        records to which the attachments will be attached.
        - model: A string representing the model to which the attachments will
                be attached.

        Returns: None
        """
        data = value.split('base64')[1] if value else False
        for rec_id in selected_ids:
            self.env['ir.attachment'].create({
                'name': name,
                'datas': data,
                'res_model': model,
                'res_id': rec_id,
            })
