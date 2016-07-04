# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import zipfile

import openerp
from openerp import api, fields, models
from openerp.addons.web.http import request
from openerp import tools

class Forum(models.Model):
    _inherit = "forum.forum"

    #Allow chrome extension link in forum
    allow_chrome_extension = fields.Boolean("Allow Chrome Extension", help="This will show Download link for chrome plugin on this forum.")

    @api.multi
    def can_ask(self):
        user = self.env.user
        can_ask = user.karma >= self.karma_ask
        return {'can_ask': can_ask, 'allow_link': self.allow_link, 'required_karma': self.karma_ask}

    @api.onchange('allow_chrome_extension')
    def _onchange_allow_chrome(self):
        if self.allow_chrome_extension:
            self.allow_link = True

    @api.onchange('allow_link')
    def _onchange_allow_link(self):
        if not self.allow_link:
            self.allow_chrome_extension = False

    @api.multi
    def generate_extension(self):
        with openerp.tools.osutil.tempdir() as ext_dir:
            directory = os.path.dirname(os.path.dirname(__file__))
            source_path = os.path.abspath(os.path.join(directory, 'forum_link_extension'))
            ext_dir_path = os.path.join(ext_dir, 'forum_link_extension')
            shutil.copytree(source_path, ext_dir_path)
            config_file_path = os.path.abspath(os.path.join(ext_dir_path, 'static/src/js/config.js'))
            config_file = open(config_file_path, 'wb')
            config_data = """website_forum_chrome.server_parameters = {
                'host': '%s',
                'database': '%s',
                'forum_name': '%s',
                'forum_id': %s
            }
            """%(request.httprequest.host_url, request.db, self.name, self.id)
            config_file.write(tools.ustr(config_data))
            config_file.close()
            t = tempfile.TemporaryFile()
            openerp.tools.osutil.zip_dir(ext_dir, t, include_dir=False)
            t.seek(0)

            return t
