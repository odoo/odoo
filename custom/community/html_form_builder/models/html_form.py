# -*- coding: utf-8 -*-

import logging
import cgi

from openerp.http import request
from openerp import api, fields, models

_logger = logging.getLogger(__name__)

class HtmlForm(models.Model):

    _name = "html.form"
    _description = "HTML Form"

    def _default_return_url(self):
        proto_ind_url = request.httprequest.host_url.replace("http:","")
        return proto_ind_url + "form/thankyou"

    def _default_submit_url(self):
        proto_ind_url = request.httprequest.host_url.replace("http:","")
        return proto_ind_url + "form/sinsert"

    name = fields.Char(string="Form Name", required=True, translate=True)
    model_id = fields.Many2one('ir.model', string="Model", required=True)
    fields_ids = fields.One2many('html.form.field', 'html_id', string="HTML Fields")
    output_html = fields.Text(string='Embed Code', readonly=True)
    required_fields = fields.Text(readonly=True, string="Required Fields")
    defaults_values = fields.One2many('html.form.defaults', 'html_id', string="Default Values", help="Sets the value of an field before it gets inserted into the database")
    return_url = fields.Char(string="Return URL", default=_default_return_url, help="The URL that the user will be redirected to after submitting the form", required=True)
    submit_url = fields.Char(string="Submit URL", default=_default_submit_url)
    submit_action = fields.One2many('html.form.action', 'hf_id', string="Submit Actions")
    captcha = fields.Many2one('html.form.captcha', string="Captcha")
    captcha_client_key = fields.Char(string="Captcha Client Key")
    captcha_secret_key = fields.Char(string="Captcha Secret Key")

    @api.onchange('model_id')
    def _onchange_model_id(self):
        #delete all existing fields
        for field_entry in self.fields_ids:
            field_entry.unlink()

        required_string = ""
        for model_field in self.env['ir.model.fields'].search([('model_id', '=', self.model_id.id), ('required', '=', True)]):
            required_string += model_field.field_description + " (" + model_field.name + ")\n"

        self.required_fields = required_string

    @api.one
    def generate_form(self):
        html_output = ""
        html_output += "<form method=\"POST\" action=\"" + request.httprequest.host_url + "form/insert\" enctype=\"multipart/form-data\">\n"
        html_output += "  <input style=\"display:none;\" name=\"my_pie\" value=\"3.14\"/>\n"

        html_output += "  <h1>" + self.name + "</h1>\n"

        for fe in self.fields_ids:

            #each field type has it's own function that way we can make plugin modules with new field types
            method = '_generate_html_%s' % (fe.field_type.html_type,)
            action = getattr(self, method, None)

            if not action:
                raise NotImplementedError('Method %r is not implemented on %r object.' % (method, self))

            html_output += action(fe)

        html_output += "  <input type=\"hidden\" name=\"form_id\" value=\"" + str(self.id) + "\"/>\n"
        html_output += "  <input type=\"submit\" value=\"Send\"/>\n"
        html_output += "</form>\n"
        self.output_html = html_output

    def _generate_html_checkbox_group(self, fe):
        html_output = ""
        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label>\n"

        for my_record in request.env[fe.field_id.relation].search([('name', '!=', '')]):
            html_output += "  <label><input type=\"checkbox\" value=\"" + str(my_record.id) + "\" name=\"" + fe.html_name + "\"/>" + my_record.name + "</label>\n"

        return html_output

    def _generate_html_file_select(self, fe):
        html_output = ""
        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label>\n"
        html_output += "  <input type=\"file\" id=\"" + fe.html_name + "\" name=\"" + fe.html_name + "\""

        if fe.field_id.required is True:
            html_output += " required=\"required\""

        html_output += "/><br/>\n"

        return html_output

    def _generate_html_date_picker(self, fe):
        html_output = ""

        html_output += "  <script>\n"
        html_output += "  $( function() {\n"
        html_output += "    $( \"#" + fe.html_name + "\" ).datepicker({ dateFormat: 'yy-mm-dd' });\n"
        html_output += "  } );\n"
        html_output += "  </script>\n"
        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label>\n"
        html_output += "  <input type=\"text\" id=\"" + fe.html_name + "\" name=\"" + fe.html_name + "\""

        if fe.field_id.required is True:
            html_output += " required=\"required\""

        html_output += "/><br/>\n"

        return html_output

    def _generate_html_textbox(self, fe):
        html_output = ""

        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label>\n"
        html_output += "  <input type=\"text\" id=\"" + fe.html_name + "\" name=\"" + fe.html_name + "\""

        if fe.field_id.required is True:
            html_output += " required=\"required\""

        html_output += "/><br/>\n"

        return html_output

    def _generate_html_checkbox_boolean(self, fe):
        html_output = ""

        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label>\n"
        html_output += "  <input type=\"checkbox\" id=\"" + fe.html_name + "\" name=\"" + fe.html_name + "\""

        if fe.field_id.required is True:
            html_output += " required=\"required\""

        html_output += "/><br/>\n"

        return html_output

    def _generate_html_radio_group_selection(self, fe):
        html_output = ""

        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label><br/>\n"

        selection_list = dict(self.env[fe.field_id.model_id.model]._fields[fe.field_id.name].selection)

        for selection_value, selection_label in selection_list.items():
            html_output += "  <input type=\"radio\" name=\"" + selection_value + "\""

            html_output += "/> " + selection_label + "<br/>\n"

        return html_output

    def _generate_html_dropbox(self, fe):
        html_output = ""

        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label>\n"

        html_output += "  <select id=\"" + fe.html_name + "\" name=\"" + fe.html_name + "\""

        if fe.field_id.required == True:
            html_output += " required=\"required\""

        html_output += ">\n"

        if fe.field_id.ttype == "selection":

            selection_list = dict(self.env[fe.field_id.model_id.model]._fields[fe.field_id.name].selection)

            for selection_value, selection_label in selection_list.items():
                html_output += "    <option value=\"" + selection_value + "\">" + selection_label + "</option>\n"

        elif fe.field_id.ttype == "many2one":

            selection_list = request.env[fe.field_id.relation].search([])

            for row in selection_list:
                html_output += "    <option value=\"" + str(row.id) + "\">" + cgi.escape(row.name) + "</option>\n"

        html_output += "  </select><br/>\n"
        
        return html_output

    def _generate_html_textarea(self, fe):
        html_output = ""
        html_output += "  <label for='" + fe.html_name + "'>" + fe.field_label + "</label>"

        html_output += "  <textarea id=\"" + fe.html_name + "\" name=\"" + fe.html_name + "\""

        if fe.field_id.required is True:
            html_output += " required=\"required\""

        html_output += "/><br/>\n"

        return html_output

class HtmlFormCaptcha(models.Model):

    _name = "html.form.captcha"
    _description = "HTML Form Captcha"

    name = fields.Char(string="Captcha Name")
    internal_name = fields.Char(string="Internal Name")

class HtmlFormAction(models.Model):

    _name = "html.form.action"
    _description = "HTML Form Action"

    hf_id = fields.Many2one('html.form', string="HTML Form")
    action_type_id = fields.Many2one('html.form.action.type', string="Submit Action")
    setting_name = fields.Char(string="Internal Name", related="action_type_id.internal_name")
    settings_description = fields.Char(string="Settings Description")
    custom_server_action = fields.Many2one('ir.actions.server', string="Custom Server Action")

    @api.onchange('custom_server_action')
    def _onchange_custom_server_action(self):
        if self.custom_server_action:
            self.settings_description = "Server Action: " + self.custom_server_action.name

class HtmlFormActionType(models.Model):

    _name = "html.form.action.type"
    _description = "HTML Form Action Type"

    name = fields.Char(string="Name")
    internal_name = fields.Char(string="Internal Name", help="action is executed in controller '_html_action_<internal_name>'")

class HtmlFormField(models.Model):

    _name = "html.form.field"
    _description = "HTML Form Field"
    _order = "sequence asc"

    sequence = fields.Integer(string="Sequence")
    html_id = fields.Many2one('html.form', ondelete='cascade', string="HTML Form")
    model_id = fields.Many2one('ir.model', string="Model", readonly=True)
    model = fields.Char(related="model_id.model", string="Model Name", readonly=True)
    field_id = fields.Many2one('ir.model.fields', domain="[('name','!=','create_date'),('name','!=','create_uid'),('name','!=','id'),('name','!=','write_date'),('name','!=','write_uid'),('name','!=','display_name')]", string="Form Field")
    field_type = fields.Many2one('html.form.field.type', string="Field Type")
    field_label = fields.Char(string="Field Label")
    html_name = fields.Char(string="HTML Name")
    validation_format = fields.Char(string="Validation Format")
    setting_general_required = fields.Boolean(string="Required")
    setting_radio_group_layout_type = fields.Selection([('single', 'Single'), ('multi', 'Multi')], string="Layout Type")
    setting_date_format = fields.Selection([('days', 'Days'), ('months', 'Months'), ('years', 'Years')], string="Date Format")
    setting_datetime_format = fields.Selection([('days', 'Days'), ('months', 'Months'), ('years', 'Years')], string="Datetime Format")
    setting_input_group_sub_fields = fields.Many2many('ir.model.fields', string="Sub Fields")
    setting_binary_file_type_filter = fields.Selection([('image', 'Image'), ('audio', 'Audio')], string="File Type Filter")
    character_limit = fields.Integer(string="Character Limit", default="100")

    @api.model
    def create(self, values):
        sequence = self.env['ir.sequence'].next_by_code('html.form.field')
        values['sequence'] = sequence

        return super(HtmlFormField, self).create(values)

    @api.onchange('field_id')
    def _onchange_field_id(self):
        """Set the default field type, html_name and field label"""
        if self.field_id:
            self.field_type = self.env['html.form.field.type'].search([('data_type', '=', self.field_id.ttype), ('default', '=', True)])[0].id
            self.html_name = self.field_id.name
            self.field_label = self.field_id.field_description

class HtmlFormDefaults(models.Model):

    _name = "html.form.defaults"
    _description = "HTML Form Defaults"

    html_id = fields.Many2one('html.form', ondelete='cascade', string="HTML Form")
    model_id = fields.Many2one('ir.model', string="Model", readonly=True)
    model = fields.Char(related="model_id.model", string="Model Name", readonly=True)
    field_id = fields.Many2one('ir.model.fields', string="Form Fields")
    default_value = fields.Char(string="Default Value", help="use 'user_id' to get the current website user, 'partner_id' for the user partner record")

class HtmlFormFieldType(models.Model):

    _name = "html.form.field.type"
    _description = "HTML Form Field Type"

    name = fields.Char(string="Name")
    html_type = fields.Char(string="HTML Type", help="Internal Reference to this HTML type")
    data_type = fields.Char(string="Data Type", help="The Odoo data type(ttype)")
    default = fields.Boolean(string="Default", help="Is this the default HTML type for this datatype?")

class HtmlFormHistory(models.Model):

    _name = "html.form.history"
    _description = "HTML Form History"

    html_id = fields.Many2one('html.form', ondelete='cascade', string="HTML Form", readonly=True)
    form_name = fields.Char(related="html_id.name", string="Form Name")
    ref_url = fields.Char(string="Reference URL", readonly=True)
    record_id = fields.Integer(string="Record ID", readonly=True)
    insert_data = fields.One2many('html.form.history.field', 'html_id', string="HTML Fields", readonly=True)

class HtmlFormHistoryField(models.Model):

    _name = "html.form.history.field"
    _description = "HTML Form History Field"

    html_id = fields.Many2one('html.form.history', ondelete='cascade', string="HTML History Form")
    field_id = fields.Many2one('ir.model.fields', string="Field")
    insert_value = fields.Char(string="Insert Value")
