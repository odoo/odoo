# -*- coding: utf-8 -*-

import cgi
import logging
import re
import simplejson
import urllib2
import werkzeug
from lxml import etree

from openerp.addons.google_account import TIMEOUT
from openerp import api, models

_logger = logging.getLogger(__name__)


class Config(models.Model):
    _inherit = 'google.drive.config'

    def get_google_scope(self):
        scope = super(Config, self).get_google_scope()
        return '%s https://spreadsheets.google.com/feeds' % scope

    def write_config_formula(self, attachment_id, spreadsheet_key, model, domain, groupbys, view_id):
        access_token = self.get_access_token(scope='https://spreadsheets.google.com/feeds')

        fields = self.env[model].fields_view_get(view_id=view_id, view_type='tree')
        doc = etree.XML(fields.get('arch'))
        display_fields = []
        for node in doc.xpath("//field"):
            if node.get('modifiers'):
                modifiers = simplejson.loads(node.get('modifiers'))
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
        dbname = self.env.cr.dbname
        username = self.env.user.login
        password = self.env.user.password
        if not password:
            config_formula = '=oe_settings("%s";"%s")' % (url, dbname)
        else:
            config_formula = '=oe_settings("%s";"%s";"%s";"%s")' % (url, dbname, username, password)
        request = '''<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:batch="http://schemas.google.com/gdata/batch"
      xmlns:gs="http://schemas.google.com/spreadsheets/2006">
  <id>https://spreadsheets.google.com/feeds/cells/{key}/od6/private/full</id>
  <entry>
    <batch:id>A1</batch:id>
    <batch:operation type="update"/>
    <id>https://spreadsheets.google.com/feeds/cells/{key}/od6/private/full/R1C1</id>
    <link rel="edit" type="application/atom+xml"
      href="https://spreadsheets.google.com/feeds/cells/{key}/od6/private/full/R1C1"/>
    <gs:cell row="1" col="1" inputValue="{formula}"/>
  </entry>
  <entry>
    <batch:id>A2</batch:id>
    <batch:operation type="update"/>
    <id>https://spreadsheets.google.com/feeds/cells/{key}/od6/private/full/R60C15</id>
    <link rel="edit" type="application/atom+xml"
      href="https://spreadsheets.google.com/feeds/cells/{key}/od6/private/full/R60C15"/>
    <gs:cell row="60" col="15" inputValue="{config}"/>
  </entry>
</feed>''' .format(key=spreadsheet_key, formula=cgi.escape(formula, quote=True), config=cgi.escape(config_formula, quote=True))

        try:
            req = urllib2.Request(
                'https://spreadsheets.google.com/feeds/cells/%s/od6/private/full/batch?%s' % (spreadsheet_key, werkzeug.url_encode({'v': 3, 'access_token': access_token})),
                data=request,
                headers={'content-type': 'application/atom+xml', 'If-Match': '*'})
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
        try:
            config = self.env.ref('google_spreadsheet.google_spreadsheet_template')
        except ValueError:
            raise
        title = 'Spreadsheet %s' % model
        res = self._model.copy_doc(self._cr, self._uid, False, config.google_drive_resource_id, title, model, context=self._context)

        mo = re.search("(key=|/d/)([A-Za-z0-9-_]+)", res['url'])
        if mo:
            key = mo.group(2)

        self.write_config_formula(res.get('id'), key, model, domain, groupbys, view_id)
        return res
