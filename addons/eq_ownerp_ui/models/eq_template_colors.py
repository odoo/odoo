# -*- coding: utf-8 -*-
# Copyright 2014-now Equitania Software GmbH - Pforzheim - Germany
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _
import re


class EqTemplateColors(models.TransientModel):
    _name = "eq.template.colors"
    _description = 'Color Picker'

    SCSS_TEMPLATE = """
        
        <data inherit_id="web.layout">
            <xpath expr="//body" position="inside">
                <style>

            body {{
                color: {eq_basic_text_color};
            }}

            body a,
            .o_form_view .o_form_uri,
            .o_form_view .oe_button_box .oe_stat_button .o_button_icon {{
                color: {eq_link_color};
            }}

            .o_list_view .text-info {{
                color: {eq_link_color} !important;
            }}

            body a:hover,
            .o_form_view .o_form_uri:hover,
            .o_form_view .oe_button_box .oe_stat_button .o_button_icon:hover {{
                color: darken({eq_link_color},20%);
            }}

            .o_main_navbar {{
                background: {eq_navi_background} !important;
                border-bottom: 1px solid {eq_navi_background} !important;
            }}

            .o_main_navbar > ul > li > a,
            .o_main_navbar > ul > li > label,
            .o_main_navbar > .o_menu_brand {{
                color: {eq_navi_fontcolor} !important;
            }}

            .o_main_navbar > ul > li > a:hover,
            .o_main_navbar > ul > li > label:hover,
            .o_main_navbar > a:hover, .o_main_navbar > a:focus,
            .o_main_navbar > button:hover, .o_main_navbar > button:focus,
            .o_main_navbar > ul > li.o_extra_menu_items.show > ul > li > a.dropdown-toggle,
            .o_main_navbar .show .dropdown-toggle,
            .navbar-default .navbar-nav > .active > a,
            .navbar-default .navbar-nav > .active > a:hover,
            .navbar-default .navbar-nav > .active > a:focus,
            .navbar-default .navbar-nav > .open > a,
            .navbar-default .navbar-nav > .open > a:hover,
            .navbar-default .navbar-nav > .open > a:focus {{
                background: {eq_navi_hover};
                color: {eq_navi_hover_fontcolor} !important;
            }}

            .o_menu_apps .dropdown-menu a.o_app i.o-app-icon,
            #sidebar .eq_new_icons i.o-app-icon {{
                color:{eq_apps_color};
            }}

            .text-muted {{
                color: {eq_basic_secondary_color} !important;
            }}

            .btn-primary {{
                color: {eq_btn_primary_fontcolor};
                background: {eq_btn_primary_background};
                border-color: {eq_btn_primary_background};
            }}

            .btn-primary:hover,
            .btn-primary:focus,
            .btn-primary.focus,
            .btn-primary:not(:disabled):not(.disabled):active,
            .btn-primary:not(:disabled):not(.disabled).active,
            .show > .btn-primary.dropdown-toggle {{
                color: {eq_btn_primary_fontcolor} !important;
                background: {eq_btn_primary_background} !important;
                filter: brightness(90%);
            }}

            .btn-secondary {{
                color: {eq_btn_secondary_fontcolor};
                background: {eq_btn_secondary_background};
            }}
            
            .btn-secondary:hover,
            .btn-secondary:focus,
            .btn-secondary.focus,
            .btn-secondary:not(:disabled):not(.disabled):active,
            .btn-secondary:not(:disabled):not(.disabled).active,
            .show > .btn-secondary.dropdown-toggle {{
                color: {eq_btn_secondary_fontcolor} !important;
                background: {eq_btn_secondary_background} !important;
                filter: brightness(90%);
            }}

            .o_field_statusbar > .o_statusbar_status > .o_arrow_button.o_arrow_button_current.disabled {{
                background-color: {eq_navi_background} !important;
            }}

            .o_field_statusbar > .o_statusbar_status > .o_arrow_button.o_arrow_button_current.disabled:after, .o_field_statusbar > .o_statusbar_status > .o_arrow_button.o_arrow_button_current.disabled:before {{
                border-left-color: {eq_navi_background} !important;
            }}

            .btn-fill-odoo, .btn-odoo {{
                color: {eq_btn_primary_fontcolor};
                background-color: {eq_btn_primary_background};
                border-color: {eq_btn_primary_background};
                box-shadow: 0;
            }}

            {eq_background_img}
            
            </style>
        </xpath>
    </data>

    """

    name = fields.Char(string="Name", default="Template Colors")
    eq_color_template_id = fields.Many2one('eq.colors', string='Color Template')
    # Basic Colors
    eq_basic_text_color = fields.Char(string="Basic Text Color")
    eq_basic_secondary_color = fields.Char(string="Basic Secondary Color")
    eq_link_color = fields.Char(string="Link Color")
    # Navigation
    eq_apps_color = fields.Char(string="App-Icon Color")
    eq_navi_background = fields.Char(string="Navigation Background")
    eq_navi_fontcolor = fields.Char(string="Navigation Fontcolor")
    eq_navi_hover = fields.Char(string="Navigation Hover Background")
    eq_navi_hover_fontcolor = fields.Char(string="Navigation Hover Font Color")
    # Buttons
    eq_btn_primary_background = fields.Char(string="Primary Button Backgroundcolor")
    eq_btn_primary_fontcolor = fields.Char(string="Primary Button Fontcolor")
    eq_btn_secondary_background = fields.Char(string="Secondary Button Backgroundcolor")
    eq_btn_secondary_fontcolor = fields.Char(string="Secondary Button Fontcolor")

    # Background Image
    eq_company_id =  fields.Many2one('res.company', string='Company')
    eq_background_image_name = fields.Char(string="Background Image Name",related='eq_company_id.eq_background_image_name',readonly=False)
    eq_background_image = fields.Binary(string="Background Image",related='eq_company_id.eq_background_image',readonly=False)

    @api.onchange('eq_color_template_id')
    def eq_set_colors(self):
        if self.eq_color_template_id:
            self.eq_navi_background = self.eq_color_template_id.eq_navi_background
            self.eq_navi_fontcolor = self.eq_color_template_id.eq_navi_fontcolor
            self.eq_navi_hover = self.eq_color_template_id.eq_navi_hover
            self.eq_navi_hover_fontcolor = self.eq_color_template_id.eq_navi_hover_fontcolor
            self.eq_apps_color = self.eq_color_template_id.eq_apps_color
            self.eq_link_color = self.eq_color_template_id.eq_link_color
            self.eq_basic_text_color = self.eq_color_template_id.eq_basic_text_color
            self.eq_basic_secondary_color = self.eq_color_template_id.eq_basic_secondary_color
            self.eq_btn_primary_background = self.eq_color_template_id.eq_btn_primary_background
            self.eq_btn_primary_fontcolor = self.eq_color_template_id.eq_btn_primary_fontcolor
            self.eq_btn_secondary_background = self.eq_color_template_id.eq_btn_secondary_background
            self.eq_btn_secondary_fontcolor = self.eq_color_template_id.eq_btn_secondary_fontcolor
    
    def execute(self):
        self.env['ir.config_parameter'].set_param("eq_navi_background", self.eq_navi_background)
        self.env['ir.config_parameter'].set_param("eq_navi_fontcolor", self.eq_navi_fontcolor)
        self.env['ir.config_parameter'].set_param("eq_navi_hover", self.eq_navi_hover)
        self.env['ir.config_parameter'].set_param("eq_navi_hover_fontcolor", self.eq_navi_hover_fontcolor)
        self.env['ir.config_parameter'].set_param("eq_apps_color", self.eq_apps_color)
        self.env['ir.config_parameter'].set_param("eq_basic_text_color", self.eq_basic_text_color)
        self.env['ir.config_parameter'].set_param("eq_basic_secondary_color", self.eq_basic_secondary_color)
        self.env['ir.config_parameter'].set_param("eq_link_color", self.eq_link_color)
        self.env['ir.config_parameter'].set_param("eq_btn_primary_background", self.eq_btn_primary_background)
        self.env['ir.config_parameter'].set_param("eq_btn_primary_fontcolor", self.eq_btn_primary_fontcolor)
        self.env['ir.config_parameter'].set_param("eq_btn_secondary_background", self.eq_btn_secondary_background)
        self.env['ir.config_parameter'].set_param("eq_btn_secondary_fontcolor", self.eq_btn_secondary_fontcolor)
        if self.eq_color_template_id:
            self.env['ir.config_parameter'].set_param("eq_color_template_id", self.eq_color_template_id.id)
        self.scss_create_or_update_attachment()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def reset_default(self):
        self.env['ir.config_parameter'].set_param("eq_navi_background", '#374D8B')
        self.eq_navi_background = '#374D8B'
        self.env['ir.config_parameter'].set_param("eq_navi_fontcolor", '#FFFFFF')
        self.eq_navi_fontcolor = '#FFFFFF'
        self.env['ir.config_parameter'].set_param("eq_navi_hover", '#FFFFFF')
        self.eq_navi_hover = '#FFFFFF'
        self.env['ir.config_parameter'].set_param("eq_navi_hover_fontcolor", '#1E2C52')
        self.eq_navi_hover_fontcolor = '#1E2C52'
        self.env['ir.config_parameter'].set_param("eq_apps_color", '#374D8B')
        self.eq_apps_color = '#374D8B'
        self.env['ir.config_parameter'].set_param("eq_basic_text_color", '#141414')
        self.eq_basic_text_color = '#141414'
        self.env['ir.config_parameter'].set_param("eq_basic_secondary_color", '#858585')
        self.eq_basic_secondary_color = '#858585'
        self.env['ir.config_parameter'].set_param("eq_link_color", '#284DA3')
        self.eq_link_color = '#284DA3'
        self.env['ir.config_parameter'].set_param("eq_btn_primary_background", '#374D8B')
        self.eq_btn_primary_background = '#374D8B'
        self.env['ir.config_parameter'].set_param("eq_btn_primary_fontcolor", '#FFFFFF')
        self.eq_btn_primary_fontcolor = '#FFFFFF'
        self.env['ir.config_parameter'].set_param("eq_btn_secondary_background", '#CFCFCF')
        self.eq_btn_secondary_background = '#CFCFCF'
        self.env['ir.config_parameter'].set_param("eq_btn_secondary_fontcolor", '#212529')
        self.eq_btn_secondary_fontcolor = '#212529'
        self.scss_create_or_update_attachment()

    @api.model
    def default_get(self, fields):
        if self.env['ir.config_parameter'].get_param("eq_navi_background"):
            eq_navi_background = self.env['ir.config_parameter'].get_param("eq_navi_background")
        else:
            eq_navi_background = '#374D8B'
        if self.env['ir.config_parameter'].get_param("eq_navi_fontcolor"):
            eq_navi_fontcolor = self.env['ir.config_parameter'].get_param("eq_navi_fontcolor")
        else:
            eq_navi_fontcolor = '#FFFFFF'
        if self.env['ir.config_parameter'].get_param("eq_navi_hover"):
            eq_navi_hover = self.env['ir.config_parameter'].get_param("eq_navi_hover")
        else:
            eq_navi_hover = '#FFFFFF'
        if self.env['ir.config_parameter'].get_param("eq_navi_hover_fontcolor"):
            eq_navi_hover_fontcolor = self.env['ir.config_parameter'].get_param("eq_navi_hover_fontcolor")
        else:
            eq_navi_hover_fontcolor = '#1E2C52'
        if self.env['ir.config_parameter'].get_param("eq_apps_color"):
            eq_apps_color = self.env['ir.config_parameter'].get_param("eq_apps_color")
        else:
            eq_apps_color = '#374D8B'
        if self.env['ir.config_parameter'].get_param("eq_basic_text_color"):
            eq_basic_text_color = self.env['ir.config_parameter'].get_param("eq_basic_text_color")
        else:
            eq_basic_text_color = '#141414'
        if self.env['ir.config_parameter'].get_param("eq_basic_secondary_color"):
            eq_basic_secondary_color = self.env['ir.config_parameter'].get_param("eq_basic_secondary_color")
        else:
            eq_basic_secondary_color = '#858585'
        if self.env['ir.config_parameter'].get_param("eq_link_color"):
            eq_link_color = self.env['ir.config_parameter'].get_param("eq_link_color")
        else:
            eq_link_color = '#284DA3'
        if self.env['ir.config_parameter'].get_param("eq_btn_primary_background"):
            eq_btn_primary_background = self.env['ir.config_parameter'].get_param("eq_btn_primary_background")
        else:
            eq_btn_primary_background = '#374D8B'
        if self.env['ir.config_parameter'].get_param("eq_btn_primary_fontcolor"):
            eq_btn_primary_fontcolor = self.env['ir.config_parameter'].get_param("eq_btn_primary_fontcolor")
        else:
            eq_btn_primary_fontcolor = '#FFFFFF'
        if self.env['ir.config_parameter'].get_param("eq_btn_secondary_background"):
            eq_btn_secondary_background = self.env['ir.config_parameter'].get_param("eq_btn_secondary_background")
        else:
            eq_btn_secondary_background = '#CFCFCF'
        if self.env['ir.config_parameter'].get_param("eq_btn_secondary_fontcolor"):
            eq_btn_secondary_fontcolor = self.env['ir.config_parameter'].get_param("eq_btn_secondary_fontcolor")
        else:
            eq_btn_secondary_fontcolor = '#212529'
        res = {
            "eq_navi_background": eq_navi_background,
            "eq_navi_fontcolor": eq_navi_fontcolor,
            "eq_navi_hover": eq_navi_hover,
            "eq_navi_hover_fontcolor": eq_navi_hover_fontcolor,
            "eq_apps_color": eq_apps_color,
            "eq_basic_text_color": eq_basic_text_color,
            "eq_basic_secondary_color": eq_basic_secondary_color,
            "eq_link_color": eq_link_color,
            "eq_btn_primary_background": eq_btn_primary_background,
            "eq_btn_primary_fontcolor": eq_btn_primary_fontcolor,
            "eq_btn_secondary_background": eq_btn_secondary_background,
            "eq_btn_secondary_fontcolor": eq_btn_secondary_fontcolor,
            "eq_company_id": self.env.company.id,
        }
        if self.env['ir.config_parameter'].get_param("eq_color_template_id"):
            res['eq_color_template_id'] = int(self.env['ir.config_parameter'].get_param("eq_color_template_id"))
        return res

    def scss_create_or_update_attachment(self):
        IrAttachmentObj = self.env['ir.attachment']
        parameters = self.sudo().default_get([])
        web_responsive = self.env["ir.module.module"].search([("name","=","web_responsive"),("state","=","installed")])
        web_enterprise = self.env["ir.module.module"].search([("name","=","web_enterprise"),("state","=","installed")])
        
        if web_responsive:
            if self.env.company.eq_background_image:
                eq_image_url = 'url(/web/image/res.company/%s/eq_background_image)'%str(self.env.company.id)
                parameters['eq_background_img'] = """
                .dropdown-menu-custom {
                    background:%s !important;
                    background-size: cover !important;
                    }"""%eq_image_url
            else:
                eq_image_url = "url(/web_responsive/static/src/components/apps_menu/../../img/home-menu-bg-overlay.svg), linear-gradient(to bottom,%s,%s)"%(parameters["eq_navi_background"],parameters["eq_navi_hover"])
                parameters['eq_background_img'] = """
                .dropdown-menu-custom {
                    background:%s !important;
                    background-size: cover !important;
                    }"""%eq_image_url
        elif web_enterprise:
            if self.env.company.eq_background_image:
                eq_image_url = 'url(/web/image/res.company/%s/eq_background_image)'%str(self.env.company.id)
                parameters['eq_background_img'] = """
                .o_web_client.o_home_menu_background {
                    background:%s !important;
                    }"""%eq_image_url
            else:
                parameters['eq_background_img'] = """
                .o_web_client.o_home_menu_background {
                    background-color: %s !important;
                    }"""%parameters["eq_navi_background"]
        else:
            parameters['eq_background_img'] = ''
        eq_css_data = self.SCSS_TEMPLATE.format(**parameters)
        eq_colors = self.env.ref('eq_ownerp_ui.eq_colors')
        eq_colors.write({"arch":eq_css_data})
