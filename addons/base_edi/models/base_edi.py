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

    def _check_business_doc_validity(self, xml_tree, xml_schema):
        if not xml_schema.validate(xml_tree):
            raise ValidationError('The generate file is unvalid')

    def _create_str_from_tree(self, xml_tree):
        return etree.tostring(xml_tree, pretty_print=True)

    def _create_xsd_schema(self, template_xsd_path):
        if not template_xsd_path:
            return None
        xml_schema_doc = etree.parse(tools.file_open(template_xsd_path))
        xml_schema = etree.XMLSchema(xml_schema_doc)
        return xml_schema

    def _create_xml_tree(self, business_document):
        xml_parser = etree.XMLParser(remove_blank_text=True)
        xml_doc_str = business_document.encode('utf-8')
        xml_tree = etree.fromstring(xml_doc_str, parser=xml_parser)
        return xml_tree

    def _create_template_values(self):
        return {'item': self}

    def create_business_document(self, template):
        if not template:
            return None
        template_xml = tools.file_open(template.xml_path).read()
        template_values = self._create_template_values()
        business_document = self._load_template(template_xml, template_values)
        xml_schema = self._create_xsd_schema(template.xsd_path)
        xml_tree = self._create_xml_tree(business_document)
        if xml_schema:
            self._check_business_doc_validity(xml_tree, xml_schema)
        business_document_content = self._create_str_from_tree(xml_tree)
        return business_document_content

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