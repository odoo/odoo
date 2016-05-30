# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import cgi
import json
import logging
from lxml import etree
import urllib2
import werkzeug

from odoo import api, models, _
from odoo.addons.google_account import TIMEOUT

_logger = logging.getLogger(__name__)


class Config(models.Model):
    _inherit = 'google.drive.config'

    def get_google_scope(self):
        scope = super(Config, self).get_google_scope()
        return '%s https://spreadsheets.google.com/feeds' % scope

    @api.model
    def write_config_formula(self, attachment_id, spreadsheet_key, model, domain, groupbys, view_id):
        access_token = self.get_access_token(scope='https://spreadsheets.google.com/feeds')

        fields = self.env[model].fields_view_get(view_id=view_id, view_type='tree')
        doc = etree.XML(fields.get('arch'))
        display_fields = []
        for node in doc.xpath("//field"):
            if node.get('modifiers'):
                modifiers = json.loads(node.get('modifiers'))
                if not modifiers.get('invisible') and not modifiers.get('tree_invisible'):
                    display_fields.append(node.get('name'))
        fields = " ".join(display_fields)
        domain = domain.replace("'", r"\'").replace('"', "'")
        if groupbys:
            fields = "%s %s" % (groupbys, fields)
            formula = '=oe_read_group("%s";"%s";"%s";"%s")' % (model, fields, groupbys, domain)
        else:
            formula = '=oe_browse("%s";"%s";"%s")' % (model, fields, domain)
        url = self.env['ir.config_parameter'].get_param('web.base.url')
        if not self.env.user.password:
            config_formula = '=oe_settings("%s";"%s")' % (url, self.env.cr.dbname)
        else:
            config_formula = '=oe_settings("%s";"%s";"%s";"%s")' % (url, self.env.cr.dbname, self.env.user.login, self.env.user.password)

        template = self.env.ref('google_spreadsheet.sheets_api_request_format')
        feed = etree.fromstring(template.arch_base).findall('{http://www.w3.org/2005/Atom}feed')[0]
        request = etree.tostring(feed).format(key=spreadsheet_key,
                                              formula=cgi.escape(formula, quote=True),
                                              config=cgi.escape(config_formula, quote=True))

        try:
            req = urllib2.Request('https://spreadsheets.google.com/feeds/cells/%s/od6/private/full/batch?%s' % (spreadsheet_key, werkzeug.url_encode({'v': 3, 'access_token': access_token})),
                                  data=request, headers={'content-type': 'application/atom+xml', 'If-Match': '*'})
            urllib2.urlopen(req, timeout=TIMEOUT)
        except (urllib2.HTTPError, urllib2.URLError):
            _logger.warning("An error occured while writting the formula on the Google Spreadsheet.")

        description = '''
        formula: %s
        ''' % formula
        if attachment_id:
            self.env['ir.attachment'].browse(attachment_id).write({'description': description})
        return True

    @api.model
    def set_spreadsheet(self, model, domain, groupbys, view_id):
        google_drive_config = self.env.ref('google_spreadsheet.google_spreadsheet_template')
        res = self.copy_doc(False, google_drive_config.google_drive_resource_id, _('Spreadsheet %s' % model), model)
        self.write_config_formula(res.get('id'), self._get_key_from_url(res.get('url', '')), model, domain, groupbys, view_id)
        return res
