# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models
from odoo.tools.misc import hmac


class View(models.Model):

    _inherit = "ir.ui.view"

    def read_combined(self, fields=None):
        root = super(View, self).read_combined(fields)
        if self.type != "qweb" or '/website_form/' not in root['arch']:  #Performance related check, reduce the amount of operation for unrelated views
            return root
        root_node = etree.fromstring(root['arch'])
        nodes = root_node.xpath('.//form[contains(@action, "/website_form/")]')
        for form in nodes:
            existing_hash_node = form.find('.//input[@type="hidden"][@name="website_form_signature"]')
            if existing_hash_node is not None:
                existing_hash_node.getparent().remove(existing_hash_node)
            input_nodes = form.xpath('.//input[contains(@name, "email_")]')
            form_values = {input_node.attrib['name']: input_node for input_node in input_nodes}
            # if this form does not send an email, ignore. But at this stage,
            # the value of email_to can still be None in case of default value
            if 'email_to' not in form_values.keys():
                continue
            elif not form_values['email_to'].attrib.get('value'):
                form_values['email_to'].attrib['value'] = self.env.company.email or ''
            has_cc = {'email_cc', 'email_bcc'} & form_values.keys()
            value = form_values['email_to'].attrib['value'] + (':email_cc' if has_cc else '')
            hash_value = hmac(self.sudo().env, 'website_form_signature', value)
            hash_node = '<input type="hidden" class="form-control s_website_form_input s_website_form_custom" name="website_form_signature" value=""/>'
            if has_cc:
                hash_value += ':email_cc'
            form_values['email_to'].addnext(etree.fromstring(hash_node))
            form_values['email_to'].getnext().attrib['value'] = hash_value
        root['arch'] = etree.tostring(root_node)
        return root
