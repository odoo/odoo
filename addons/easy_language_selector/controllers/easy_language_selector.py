# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Yadhu krishnan K (odoo@cybrosys.com)
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
    The EasyLanguageSelector class appending the activated languages in the
    systray language selection field.
        Methods:
            get_activated_languages(self):
                when the page is loaded adding total activated languages options
                 to the selection field.
                return a list variable.
            activated_languages(self, **kw):
                getting value of the selected language and change the language
                in the backend.
    """
    @http.route('/easy_language_selector/options', auth='public', type='json')
    def get_activated_languages(self):
        """
        Summary:
            transferring data to the selection field that works as a language
            selector.
        Returns:
            type:list of lists , it contains the data for the language selector.
        """
        return [{'name': res_lang_id.name,
                 'code': res_lang_id.code}
                for res_lang_id in request.env['res.lang'].search([])]

    @http.route('/easy_language_selector/change', auth='public', type='json')
    def change_active_languages(self, **kw):
        """
        Summary:
            getting value of the selected language and change the language in
            the backend.
        Args:
            kw(dict):it consists of the code of the selected language.
        """
        request.env.user.sudo().update({
            'lang': kw['data']
        })
        return True
