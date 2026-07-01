# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Megha AP (odoo@cybrosys.com)
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
################################################################################
from odoo import api, fields, models


class VideoStore(models.Model):
    """In this model you can store recoded data as a record and view it
    later"""
    _name = 'video.store'
    _description = 'Screen record video storage'
    _rec_name = 'date'

    date = fields.Datetime(string='Date', default=fields.Datetime.now,
                           help="Date of screen capture")
    description = fields.Char(string='Description',
                              help='Add description for recording')
    video = fields.Char(string='Screen Record',
                        help="Recorded videos can be view here")

    @api.model
    def video_record(self, url):
        """function used to create a record when the screen record is
         stopped"""
        self.create({'description': '', 'video': url})
        return True
