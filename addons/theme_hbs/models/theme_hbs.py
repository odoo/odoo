# from odoo import models

# class ThemeHBS(models.AbstractModel):

#     _inherit = 'theme.utils'

#     def _theme_purple_post_copy(self, mod):
#         # To remove when custom header-footer is read 
#         self.enable_view('website.template_header_sales_three')

#         self.enable_view('website.template_footer_links')
#         self.enable_view('theme_hbs.custom_header')

#     @property
#     def _header_template(self):
#         return ['theme_hbs.custom_header'] + super()._header_template

    # @property
    # def _footer_template(self):
    #     return ['theme_hbs.custom_footer'] + super()._footer_template

    # def _theme_purple_post_copy(self, mod):
    #     self.enable_view('theme_hbs.custom_header')
    #     self.enable_view('theme_hbs.custom_footer')
