# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
import logging
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

class MenuController(http.Controller):
    """Controller for handling redirections to various pages based on menu
    clicks. This class defines several routes that redirect users to different
    pages in the website based on the menus clicked. Each method corresponds to
    a specific page in the 'theme_medicate' theme."""

    @http.route('/home', website=True, type='http', auth='public', csrf=False)
    def home_page(self):
        """Redirect to the home page."""
        return request.render('theme_medicate.home_page_load_snippet')

    @http.route('/contact-us', website=True, type='http', auth='public', csrf=False)
    def contact_us(self):
        """Redirect to the contact us page."""
        return request.render('theme_medicate.contactus_template')

    @http.route('/about', website=True, type='http', auth='public', csrf=False)
    def about_page(self):
        """Redirect to the about page."""
        return request.render('theme_medicate.load_about_us_snippet')

    @http.route('/service', website=True, type='http', auth='public', csrf=False)
    def service_page(self):
        """Redirect to the about page."""
        return request.render('theme_medicate.load_services_snippet')

    @http.route('/read_more', website=True, type='http', auth='public',
                csrf=False)
    def blog_details(self):
        """Redirect to the portfolio Another Action page."""
        return request.render('theme_medicate.blog_details_more')
