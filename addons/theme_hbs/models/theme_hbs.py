from odoo import models

class ThemeHBS(models.AbstractModel):

    _inherit = 'theme.utils'

    def _theme_hbs_post_copy(self, mod):
    #     # these are available views for headers and footer:
    #     ##
    #     # Other examples::
    #     # website.template_header_default
    #     # website.template_header_default_align_right
    #     # website.template_header_hamburger_align_right
        # website.template_header_sales_one
    #     # website.template_header_sales_three
    #     # website.template_header_search
    #     ##
        self.enable_view('website.template_header_sales_three')

    #     ##
    #     # website.template_footer_headline
    #     # website.template_footer_contact
    #     # website.template_footer_descriptive
            # website.template_footer_links
    #     # website.template_footer_minimalist
    #     #website.template_footer_slideout
    #     # #

        self.enable_view('website.template_footer_links')






    # example of how to override the header and footer templates to add custom ones

    # @property
    # def _header_template(self):
    #     return ['theme_hbs.custom_header'] + super()._header_template

    # @property
    # def _footer_template(self):
    #     return ['theme_hbs.custom_footer'] + super()._footer_template

    # def _theme_hbs_post_copy(self, mod):
    #     self.enable_view('theme_hbs.custom_header')
    #     self.enable_view('theme_hbs.custom_footer')
