# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Yadhukrishnan K (odoo@cybrosys.com)
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
################################################################################
from odoo import http
from odoo.http import request


class EasyLanguageSelector(http.Controller):
    """
    The EasyLanguageSelector passing minute that selected in the  login user account.

        Methods:
            get_idle_time(self):
                when the page is loaded adding total activated languages options to the selection field.
                return a list variable.
    """

    @http.route('/get_idle_time/timer', auth='public', type='json')
    def get_idle_time(self):
        """
        Summery:
            Getting value that selected from the login user account and pass it to the js function.
        return:
            type:It is a variable, that contain selected minutes.
        """
        if request.env.user.enable_idle:
            return request.env.user.idle_time
