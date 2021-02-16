# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

import logging
import os
import requests
import shutil
import tarfile
import sys

from odoo import api, fields, models, modules

logger = logging.getLogger(__name__)

STATE_AVAILABLE = 'available'
STATE_INSTALLED = 'installed'

STATES = [(STATE_AVAILABLE, "Available"), (STATE_INSTALLED, "Installed")]


class VersionGitHubTag(models.Model):
    _name = 'formio.version.github.tag'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Formio Version GitHub Tag'
    #_order = 'create_date desc, id asc'

    # IMPORTANT NOTES
    # ===============
    # Formio published release ain't available with the GitHub releases API
    # https://developer.github.com/v3/repos/releases/#list-releases
    #
    # GitHub tags API
    # https://developer.github.com/v3/repos/#list-repository-tags

    name = fields.Char(required=True)
    version_name = fields.Char('_compute_fields')
    formio_version_id = fields.Many2one('formio.version')
    archive_url = fields.Char(compute='_compute_fields', string="Archive URL")
    changelog_url = fields.Char(compute='_compute_fields', string="Changelog URL")
    state = fields.Selection(
        selection=STATES, string="State",
        default=STATE_AVAILABLE, required=True, tracking=True,
        help="""\
        - Available: Not downloaded and installed yet.
        - Installed: Downloaded and installed.""")
    install_date = fields.Datetime(string='Installed on', compute='_compute_install_date', store=True)

    @api.depends('name')
    def _compute_fields(self):
        for r in self:
            if r.name:
                r.archive_url = 'https://github.com/formio/formio.js/archive/%s.tar.gz' % r.name
                r.changelog_url = 'https://github.com/formio/formio.js/blob/%s/Changelog.md' % r.name
                r.version_name = r.name[1:]
            else:
                r.archive_url = False
                r.changelog_url = False
                r.version_name = False

    @api.depends('state')
    def _compute_install_date(self):
        for r in self:
            if r.state == STATE_INSTALLED:
                r.install_date = fields.Datetime.now()
            else:
                r.install_date = False
        
    @api.model
    def check_and_register_available_versions(self):
        vals_list = self.env['formio.version.github.checker.wizard'].check_new_versions()
        if vals_list:
            self.create(vals_list)

    def action_download_install(self):
        if self.formio_version_id:
            return

        response = requests.get(self.archive_url, stream=True)
        logger.info('download => %s' % self.archive_url)
        tar_path = '/tmp/%s.tar.gz' % self.version_name
        static_path = modules.get_module_resource('formio', 'static/installed')
        if sys.platform == 'win32':
            tar_path = '%s\\%s.tar.gz' % (static_path, self.version_name)
        if response.status_code == 200:
            with open(tar_path, 'wb') as f:
                f.write(response.raw.read())
                tar = tarfile.open(tar_path)
                if sys.platform == 'win32':
                    tar.extractall('%s' % static_path, members=self._tar_extract_members(tar))
                else:
                    tar.extractall('/tmp', members=self._tar_extract_members(tar))
                tar.close()

            extract_path = '/tmp/formio.js-%s/dist' % self.version_name
            if sys.platform == 'win32':
                extract_path = '%s\\formio.js-%s\\dist' % (static_path, self.version_name)

            # static_path = modules.get_module_resource('formio', 'static/installed')
            static_version_dir = '%s/%s' % (static_path, self.version_name)
            os.makedirs(static_version_dir, exist_ok=True)

            version_model = self.env['formio.version']
            asset_model = self.env['formio.version.asset']
            attachment_model = self.env['ir.attachment']

            # First delete if any already. If repeating download/install.
            domain = [('name', '=', self.version_name)]
            version_model.search(domain).unlink()

            vals = {
                'name': self.version_name,
            }
            version = version_model.create(vals)

            # Add assets
            assets_vals_list = []
            default_assets_css = self.env['formio.default.asset.css'].search([])
            for das in default_assets_css:
                default_asset_vals = {
                    'version_id': version.id,
                    'attachment_id': das.attachment_id.id,
                    'type': 'css'
                }
                assets_vals_list.append(default_asset_vals)

            for root, dirs, files in os.walk(extract_path):
                for dname in dirs:
                    original_dir = '%s/%s' % (root, dname)
                    target_dir = '%s/%s' % (static_version_dir, dname)
                    # first delete target_dir (if exist it won't clash)
                    shutil.rmtree(target_dir, ignore_errors=True)
                    shutil.move(original_dir, target_dir)
                
                for fname in files:
                    original_file = '%s/%s' % (root, fname)
                    target_file = '%s/%s' % (static_version_dir, fname)
                    shutil.move(original_file, target_file)

                    # attachment
                    url = '/formio/static/installed/%s/%s' % (self.version_name, fname)
                    attachment_vals = {
                        'name': url,
                        'type': 'url',
                        'public': True,
                        'url': url
                    }
                    attachment = attachment_model.create(attachment_vals)

                    # assets
                    asset_vals = {
                        'version_id': version.id,
                        'attachment_id': attachment.id
                    }
                    ext = os.path.splitext(fname)[1]

                    if ext == '.css':
                        asset_vals['type'] = 'css'
                    elif ext == '.js':
                        asset_vals['type'] = 'js'
                    assets_vals_list.append(asset_vals)

            if assets_vals_list:
                res = asset_model.create(assets_vals_list)

            # cleanup and update
            os.remove(tar_path)
            tmp_path = '/tmp/formio.js-%s' % self.version_name
            if sys.platform == 'win32':
                tmp_path = '%s\\formio.js-%s' % (static_path, self.version_name)
            shutil.rmtree(tmp_path)
            self.write({'state': STATE_INSTALLED, 'formio_version_id': version.id})

    def action_reset_installed(self):
        if self.formio_version_id:
            vals = {'formio_version_id': False, 'state': STATE_AVAILABLE}
            self.write(vals)
            self.action_download_install()

    def _tar_extract_members(self, members):
        full_todo = ['formio.full.min.js', 'formio.full.min.css']
        full_done = []
        src = {'formio.full.min.js': 'formio.js', 'formio.full.min.css': 'formio.full.css'}
        src_todo = []
        fonts_done = False

        for tarinfo in members:
            basename = os.path.basename(tarinfo.name)
            dirname = os.path.dirname(tarinfo.name)
            
            dir_1 = os.path.basename(dirname)
            dir_2 = os.path.basename(os.path.dirname(dirname))

            if basename in full_todo:
                logger.info('tar extract member => %s' % basename)
                full_done.append(basename)
                yield tarinfo
            elif dir_1 == 'fonts' and dir_2 == 'dist':
                logger.info('tar extract => dist/fonts')
                yield tarinfo

        # In case minimized files not found
        src_todo = [src[todo] for todo in full_todo if todo not in full_done]
        for tarinfo in members:
            filename = os.path.basename(tarinfo.name)
            if filename in src_todo:
                logger.info('tar extract member => %s' % filename)
                yield tarinfo
