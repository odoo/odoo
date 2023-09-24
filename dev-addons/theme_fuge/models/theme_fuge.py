# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import models


class FugeTheme(models.AbstractModel):
    _inherit = 'theme.utils'

    def _fuge_theme_post_copy(self, mod):
        self.enable_view('website_blog.opt_blog_sidebar_show')
        self.enable_view('website_blog.opt_blog_list_view')
        self.disable_view('website_blog.opt_posts_loop_show_author')
        self.disable_view('website_sale.add_grid_or_list_option')
        self.disable_view('website_sale.products_list_view')
