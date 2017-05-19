# -*- coding: utf-8 -*-
import logging
import os
import sys
import zipfile
from os.path import join as opj

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules import load_information_from_description_file
from odoo.tools import convert_file, exception_to_unicode, pycompat
from odoo.tools.osutil import tempdir

_logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024 * 1024  # in megabytes


class IrModule(models.Model):
    _inherit = "ir.module.module"

    imported = fields.Boolean(string="Imported Module")

    @api.multi
    def import_module(self, module, path, force=False):
        known_mods = self.search([])
        known_mods_names = {m.name: m for m in known_mods}
        installed_mods = [m.name for m in known_mods if m.state == 'installed']

        terp = load_information_from_description_file(module, mod_path=path)
        values = self.get_values_from_terp(terp)

        unmet_dependencies = set(terp['depends']).difference(installed_mods)
        if unmet_dependencies:
            raise UserError(_("Unmet module dependencies: %s") % ', '.join(unmet_dependencies))

        mod = known_mods_names.get(module)
        if mod:
            mod.write(dict(state='installed', **values))
            mode = 'update' if not force else 'init'
        else:
            assert terp.get('installable', True), "Module not installable"
            self.create(dict(name=module, state='installed', imported=True, **values))
            mode = 'init'

        for kind in ['data', 'init_xml', 'update_xml']:
            for filename in terp[kind]:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ('.xml', '.csv', '.sql'):
                    _logger.info("module %s: skip unsupported file %s", module, filename)
                    continue
                _logger.info("module %s: loading %s", module, filename)
                noupdate = False
                if filename.endswith('.csv') and kind in ('init', 'init_xml'):
                    noupdate = True
                pathname = opj(path, filename)
                idref = {}
                convert_file(self.env.cr, module, filename, idref, mode=mode, noupdate=noupdate, kind=kind, pathname=pathname)

        path_static = opj(path, 'static')
        IrAttachment = self.env['ir.attachment']
        if os.path.isdir(path_static):
            for root, dirs, files in os.walk(path_static):
                for static_file in files:
                    full_path = opj(root, static_file)
                    with open(full_path, 'r') as fp:
                        data = fp.read().encode('base64')
                    url_path = '/%s%s' % (module, full_path.split(path)[1].replace(os.path.sep, '/'))
                    url_path = url_path.decode(sys.getfilesystemencoding())
                    filename = os.path.split(url_path)[1]
                    values = dict(
                        name=filename,
                        datas_fname=filename,
                        url=url_path,
                        res_model='ir.ui.view',
                        type='binary',
                        datas=data,
                    )
                    attachment = IrAttachment.search([('url', '=', url_path), ('type', '=', 'binary'), ('res_model', '=', 'ir.ui.view')])
                    if attachment:
                        attachment.write(values)
                    else:
                        IrAttachment.create(values)

        return True

    @api.model
    def import_zipfile(self, module_file, force=False):
        if not module_file:
            raise Exception(_("No file sent."))
        if not zipfile.is_zipfile(module_file):
            raise UserError(_('File is not a zip file!'))

        success = []
        errors = dict()
        module_names = []
        with zipfile.ZipFile(module_file, "r") as z:
            for zf in z.filelist:
                if zf.file_size > MAX_FILE_SIZE:
                    raise UserError(_("File '%s' exceed maximum allowed file size") % zf.filename)

            with tempdir() as module_dir:
                z.extractall(module_dir)
                dirs = [d for d in os.listdir(module_dir) if os.path.isdir(opj(module_dir, d))]
                for mod_name in dirs:
                    module_names.append(mod_name)
                    try:
                        # assert mod_name.startswith('theme_')
                        path = opj(module_dir, mod_name)
                        self.import_module(mod_name, path, force=force)
                        success.append(mod_name)
                    except Exception as e:
                        _logger.exception('Error while importing module')
                        errors[mod_name] = exception_to_unicode(e)
        r = ["Successfully imported module '%s'" % mod for mod in success]
        for mod, error in pycompat.items(errors):
            r.append("Error while importing module '%s': %r" % (mod, error))
        return '\n'.join(r), module_names
