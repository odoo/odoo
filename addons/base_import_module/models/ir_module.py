# -*- coding: utf-8 -*-
import ast
import base64
import logging
import lxml
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

    @api.depends('name')
    def _get_latest_version(self):
        imported_modules = self.filtered(lambda m: m.imported and m.latest_version)
        for module in imported_modules:
            module.installed_version = module.latest_version
        super(IrModule, self - imported_modules)._get_latest_version()

    @api.multi
    def _import_module(self, module, path, force=False):
        known_mods = self.search([])
        known_mods_names = {m.name: m for m in known_mods}
        installed_mods = [m.name for m in known_mods if m.state == 'installed']

        terp = load_information_from_description_file(module, mod_path=path)
        values = self.get_values_from_terp(terp)
        if 'version' in terp:
            values['latest_version'] = terp['version']

        unmet_dependencies = set(terp['depends']).difference(installed_mods)

        if unmet_dependencies:
            if (unmet_dependencies == set(['web_studio']) and
                    _is_studio_custom(path)):
                err = _("Studio customizations require Studio")
            else:
                err = _("Unmet module dependencies: %s") % ', '.join(
                    unmet_dependencies,
                )
            raise UserError(err)
        elif 'web_studio' not in installed_mods and _is_studio_custom(path):
            raise UserError(_("Studio customizations require the Odoo Studio app."))

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
                if ext == '.csv' and kind in ('init', 'init_xml'):
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
                    with open(full_path, 'rb') as fp:
                        data = base64.b64encode(fp.read())
                    url_path = '/{}{}'.format(module, full_path.split(path)[1].replace(os.path.sep, '/'))
                    if not isinstance(url_path, pycompat.text_type):
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
            raise UserError(_('Only zip files are supported.'))

        success = []
        errors = dict()
        module_names = []
        with zipfile.ZipFile(module_file, "r") as z:
            for zf in z.filelist:
                if zf.file_size > MAX_FILE_SIZE:
                    raise UserError(_("File '%s' exceed maximum allowed file size") % zf.filename)

            with tempdir() as module_dir:
                import odoo.modules.module as module
                try:
                    module.ad_paths.append(module_dir)
                    z.extractall(module_dir)
                    dirs = [d for d in os.listdir(module_dir) if os.path.isdir(opj(module_dir, d))]
                    for mod_name in dirs:
                        module_names.append(mod_name)
                        try:
                            # assert mod_name.startswith('theme_')
                            path = opj(module_dir, mod_name)
                            self._import_module(mod_name, path, force=force)
                            success.append(mod_name)
                        except Exception as e:
                            _logger.exception('Error while importing module')
                            errors[mod_name] = exception_to_unicode(e)
                finally:
                    module.ad_paths.remove(module_dir)
        r = ["Successfully imported module '%s'" % mod for mod in success]
        for mod, error in errors.items():
            r.append("Error while importing module '%s': %r" % (mod, error))
        return '\n'.join(r), module_names


def _is_studio_custom(path):
    """
    Checks the to-be-imported records to see if there are any references to
    studio, which would mean that the module was created using studio

    Returns True if any of the records contains a context with the key
    studio in it, False if none of the records do
    """
    filepaths = []
    for level in os.walk(path):
        filepaths += [os.path.join(level[0], fn) for fn in level[2]]
    filepaths = [fp for fp in filepaths if fp.lower().endswith('.xml')]

    for fp in filepaths:
        root = lxml.etree.parse(fp).getroot()

        for record in root:
            # there might not be a context if it's a non-studio module
            try:
                # ast.literal_eval is like eval(), but safer
                # context is a string representing a python dict
                ctx = ast.literal_eval(record.get('context'))
                # there are no cases in which studio is false
                # so just checking for its existence is enough
                if ctx and ctx.get('studio'):
                    return True
            except Exception:
                continue
    return False
