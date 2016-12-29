# -*- coding: utf-8 -*-

import os.path
import jinja2
from odoo import models, fields, api, tools

class BaseJinja(models.Model):
    _name = 'base.jinja'

    def _create_environment(self, autoescape=True, trim_blocks=True, lstrip_blocks=True):
        # environment = jinja2.Environment(loader=None,
        #           autoescape=autoescape,
        #           trim_blocks=trim_blocks,
        #           lstrip_blocks=lstrip_blocks)
        # return environment
        return

    def _load_schema(self, schema):
        return

    def _load_template(self, template_file, schema=None):
        # environment = self._create_environment()
        template = jinja2.Template(template_file, trim_blocks=True, lstrip_blocks=True)
        return template

class BaseEdi(models.Model):
    _name = 'base.edi'
    _inherit = 'base.jinja'

    def _create_template_values(self):
        return {
            'item': self,
            'tools': tools,
        }

    def create_business_document(self, template):
        if not template:
            return None
        template_file = os.path.join(template.path, template.name + '.xml')
        template = self._load_template(tools.file_open(template_file).read())
        template_values = self._create_template_values()
        business_document = template.render(template_values)
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