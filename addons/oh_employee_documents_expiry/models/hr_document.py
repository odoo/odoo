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


class HrDocument(models.Model):
    """Creating hr document templates."""
    _name = 'hr.document'
    _description = 'HR Document Template '

    name = fields.Char(string='Document Name', required=True, copy=False,
                       help='You can give your Document name here.')
    note = fields.Text(string='Note', copy=False, help="Note of the document.")
    attach_ids = fields.Many2many('ir.attachment',
                                  'attach_rel', 'doc_id',
                                  'attach_id3', string="Attachment",
                                  help='You can attach the copy of your'
                                       ' document.', copy=False)
