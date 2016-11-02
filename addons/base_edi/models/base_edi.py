# -*- coding: utf-8 -*-

import jinja2
from StringIO import StringIO
from lxml import etree
from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError

class BaseJinja(models.Model):
    _name = 'base.jinja'

    def _load_template(self, template_xml, template_values):
        template = jinja2.Template(template_xml, trim_blocks=True, lstrip_blocks=True)
        filled_template = template.render(template_values)
        return filled_template

class BaseEdi(models.Model):
    _name = 'base.edi'
    _inherit = 'base.jinja'

    def _check_business_doc_validity(self, business_document, template_xsd_path):
        xml_schema_doc = etree.parse(tools.file_open(template_xsd_path))
        xml_schema = etree.XMLSchema(xml_schema_doc)
        xml_doc_str = business_document.encode('utf-8')
        xml_doc = etree.fromstring(xml_doc_str)
        if not xml_schema.validate(xml_doc):
            raise ValidationError('The generate file is unvalid')

    def _create_template_values(self):
        return {
            'item': self,
            'tools': tools,
        }

    def create_business_document(self, template):
        if not template:
            return None
        template_xml = tools.file_open(template.xml_path).read()
        template_values = self._create_template_values()
        business_document = self._load_template(template_xml, template_values)
        if template.xsd_path:
            self._check_business_doc_validity(business_document, template.xsd_path)
        return business_document

    def _create_pdf_attachment(self, filename, pdf_content):
        attach = self.env['ir.attachment'].create({
            'name': filename,
            'res_id': self.id,
            'res_model': unicode(self._name),
            'datas': pdf_content.encode('base64'),
            'datas_fname': filename,
            'type': 'binary',
            })
        action = self.env['ir.actions.act_window'].for_xml_id(
            'base', 'action_attachment')
        action.update({
            'res_id': attach.id,
            'views': False,
            'view_mode': 'form,tree'
            })
        return action