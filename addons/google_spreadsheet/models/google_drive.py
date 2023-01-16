# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

import requests
from lxml import etree
import re
import werkzeug.urls

from odoo import api, models
from odoo.tools import misc
from odoo.addons.google_account import TIMEOUT

_logger = logging.getLogger(__name__)


class GoogleDrive(models.Model):
    _inherit = 'google.drive.config'

    def get_google_scope(self):
        scope = super(GoogleDrive, self).get_google_scope()
        return '%s https://www.googleapis.com/auth/spreadsheets' % scope

    @api.model
    def write_config_formula(self, attachment_id, spreadsheet_key, model, domain, groupbys, view_id):
        access_token = self.get_access_token(scope='https://www.googleapis.com/auth/spreadsheets')

        formula = self._get_data_formula(model, domain, groupbys, view_id)

        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        dbname = self._cr.dbname
        user = self.env['res.users'].browse(self.env.user.id).read(['login', 'password'])[0]
        username = user['login']
        password = user['password']
        if not password:
            config_formula = '=oe_settings("%s";"%s")' % (url, dbname)
        else:
            config_formula = '=oe_settings("%s";"%s";"%s";"%s")' % (url, dbname, username, password)
        request = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": "A1", "values": [[formula]]},
                {"range": "O60", "values": [[config_formula]]},
            ]
        }
        try:
            req = requests.post(
                'https://sheets.googleapis.com/v4/spreadsheets/%s/values:batchUpdate?%s' % (spreadsheet_key, werkzeug.urls.url_encode({'access_token': access_token})),
                data=json.dumps(request),
                headers={'content-type': 'application/json', 'If-Match': '*'},
                timeout=TIMEOUT,
            )
        except IOError:
            _logger.warning("An error occured while writing the formula on the Google Spreadsheet.")

        description = '''
        formula: %s
        ''' % formula
        if attachment_id:
            self.env['ir.attachment'].browse(attachment_id).write({'description': description})
        return True

    def _get_data_formula(self, model, domain, groupbys, view_id):
        fields = self.env[model].fields_view_get(view_id=view_id, view_type='tree')
        doc = etree.XML(fields.get('arch'))
        display_fields = []
        for node in doc.xpath("//field"):
            if node.get('modifiers'):
                modifiers = json.loads(node.get('modifiers'))
                if not modifiers.get('invisible') and not modifiers.get('column_invisible'):
                    display_fields.append(node.get('name'))
        fields = " ".join(display_fields)
        domain = domain.replace("'", r"\'").replace('"', "'").replace('True', 'true').replace('False', 'false')
        if groupbys:
            fields = "%s %s" % (groupbys, fields)
            formula = '=oe_read_group("%s";"%s";"%s";"%s")' % (model, fields, groupbys, domain)
        else:
            formula = '=oe_browse("%s";"%s";"%s")' % (model, fields, domain)
        return formula

    @api.model
    def set_spreadsheet(self, model, domain, groupbys, view_id):
        config = self.env.ref('google_spreadsheet.google_spreadsheet_template')

        if self._module_deprecated():
            return {
                'url': config.google_drive_template_url,
                'deprecated': True,
                'formula': self._get_data_formula(model, domain, groupbys, view_id),
            }

        title = 'Spreadsheet %s' % model
        res = self.copy_doc(False, config.google_drive_resource_id, title, model)

        mo = re.search("(key=|/d/)([A-Za-z0-9-_]+)", res['url'])
        if mo:
            key = mo.group(2)

        self.write_config_formula(res.get('id'), key, model, domain, groupbys, view_id)
        return res
