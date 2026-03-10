# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class IrAttachment(models.Model):
    """This class inherits from 'ir.attachment' and introduces two many-to-many
     relationships: 'doc_attach_rel' for associating HR employee documents and
    'attach_rel' for attaching general HR documents to a record."""
    _inherit = 'ir.attachment'

    doc_attach_rel = fields.Many2many('hr.employee.document',
                                      'doc_attachment_ids',
                                      'attach_id3', 'doc_id',
                                      string="Attachment", invisible=1,
                                      help='This field allows you to associate'
                                           'HR employee documents with the '
                                           'record.')
    attach_rel = fields.Many2many('hr.document',
                                  'attach_ids', 'attachment_id3',
                                  'document_id',
                                  string="Attachment", invisible=1,
                                  help='This field allows you to attach HR '
                                       'documents to the record.')
