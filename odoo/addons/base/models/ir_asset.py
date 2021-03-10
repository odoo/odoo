# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os

from glob import glob
from logging import getLogger

from odoo.tools import config
from odoo.tools.func import lazy
from odoo.addons import __path__ as ADDONS_PATH
from odoo import api, fields, http, models
from odoo.modules.module import read_manifest


_logger = getLogger(__name__)

SCRIPT_EXTENSIONS = ['js']
STYLE_EXTENSIONS = ['css', 'scss', 'sass', 'less']
TEMPLATE_EXTENSIONS = ['xml']
DEFAULT_SEQUENCE = 16

# Default directive:  `file_path` or `('append', 'file_path')`
APPEND_DIRECTIVE = 'append'
# `('include', 'bundle')`
INCLUDE_DIRECTIVE = 'include'
# `('prepend', 'file_path')`
PREPEND_DIRECTIVE = 'prepend'
# `('remove', 'file_path')`
REMOVE_DIRECTIVE = 'remove'

# `('after', 'target_path', 'file_path')`
AFTER_DIRECTIVE = 'after'
# `('before', 'target_path', 'file_path')`
BEFORE_DIRECTIVE = 'before'
# `('replace', 'target_path', 'file_path')`
REPLACE_DIRECTIVE = 'replace'

DIRECTIVES_WITH_TARGET = [AFTER_DIRECTIVE, BEFORE_DIRECTIVE, REPLACE_DIRECTIVE]


def fs2web(path):
    """Converts a file system path to a web path"""
    return '/'.join(os.path.split(path))

def get_paths(path_def, extensions=None, manifest_cache=None):
    """
    Returns a list of file paths matching a given glob (path_def) as well as
    the addon targetted by the path definition. If no file matches that glob,
    the path definition is returned as is. This is either because the glob is
    not correctly written or because it points to an URL.

    :param path_def: the definition (glob) of file paths to match
    :param extensions: a list of extensions that found files must match
    :returns: a tuple: the addon targetted by the path definition [0] and the
        list of glob files matching the definition [1] (or the glob itself if
        none). Note that these paths are filtered on the given `extensions`.
    """
    if manifest_cache is None:
        manifest_cache = http.addons_manifest

    paths = []
    path_url = fs2web(path_def)
    path_parts = [part for part in path_url.split('/') if part]
    addon = path_parts[0]
    addon_manifest = manifest_cache.get(addon)

    if addon_manifest:
        addons_path = os.path.join(addon_manifest['addons_path'], '')[:-1]
        full_path = os.path.normpath(os.path.join(addons_path, *path_parts))
        # When fetching template file paths, we need the full paths since xml
        # files are read from the file system. But web assets (scripts and
        # stylesheets) must be loaded using relative paths, hence the trimming
        # for non-xml file paths.
        paths = [
            path
                if path.split('.')[-1] in TEMPLATE_EXTENSIONS
                else path[len(addons_path):]
            for path in sorted(glob(full_path, recursive=True))
        ]
    else:
        addon = None

    if not len(paths):
        # No file matching the path; the path_def is considered as a URL (or a
        # miswritten glob, resulting in a console error).
        paths = [path_url if not addon or path_url.startswith('/') else '/' + path_url]

    # Paths are filtered on the extensions (if any).
    return addon, [path
        for path in paths
        if not extensions or path.split('.')[-1] in extensions
    ]


if config['test_enable']:
    def get_all_manifests_cache():
        manifest_cache = {}
        for addons_path in ADDONS_PATH:
            for module in sorted(os.listdir(str(addons_path))):
                if module not in manifest_cache:
                    manifest = read_manifest(addons_path, module)
                    if not manifest or not manifest.get('installable', True):
                        continue
                    manifest['addons_path'] = addons_path
                    manifest_cache[module] = manifest
        return manifest_cache

    http.addons_manifest = lazy(get_all_manifests_cache)


class IrAsset(models.Model):
    """This model contributes to two things:

        1. It exposes a public function returning a list of all file paths
        declared in a given list of addons;

        2. It allows to create 'ir.asset' records to add additional directives
        to certain bundles.
    """

    _name = 'ir.asset'
    _description = 'Asset'

    @api.model_create_multi
    def create(self, vals_list):
        self.clear_caches()
        return super().create(vals_list)

    def write(self, values):
        self.clear_caches()
        return super().write(values)

    def unlink(self):
        self.clear_caches()
        return super().unlink()

    name = fields.Char(string='Name', required=True)
    bundle = fields.Char(string='Bundle name', required=True)
    directive = fields.Selection(string='Directive', selection=[
        (APPEND_DIRECTIVE, 'Append'),
        (PREPEND_DIRECTIVE, 'Prepend'),
        (AFTER_DIRECTIVE, 'After'),
        (BEFORE_DIRECTIVE, 'Before'),
        (REMOVE_DIRECTIVE, 'Remove'),
        (REPLACE_DIRECTIVE, 'Replace'),
        (INCLUDE_DIRECTIVE, 'Include')], default=APPEND_DIRECTIVE)
    glob = fields.Char(string='Path', required=True)
    target = fields.Char(string='Target')
    active = fields.Boolean(string='active', default=True)
    sequence = fields.Integer(string="Sequence", default=DEFAULT_SEQUENCE, required=True)

    def get_asset_paths(self, bundle, addons=None, css=False, js=False, xml=False, asset_paths=None, circular_path=None):
        """
        Fetches all asset file paths from a given list of addons matching a
        certain bundle. The returned list is composed of tuples containing the
        file path [1] and the first addon calling it [0]. Asset loading is
        performed as following:

        1. At each initial call (i.e. not a recursive call), a new list of
        assets is generated.

        2. All 'ir.asset' records matching the given bundle and with a sequence
        number inferior to 16 are applied.

        3. The manifests of all given addons are checked for assets declaration
        for the given bundle. If any, they are read sequentially and their
        operations are applied to the current list.

        4. After all manifests have been parsed, the remaining 'ir.asset'
        records matching the bundle are also applied to the current list.

        :param addons: list of addon names as strings. The files returned will
            only be contained in the given addons.
        :param bundle: name of the bundle from which to fetch the file paths
        :param css: boolean: whether or not to include style files
        :param js: boolean: whether or not to include script files
        :param xml: boolean: whether or not to include template files
        :param asset_paths: (addon, path)[]: the current list of loaded assets.
            It starts blank (initial) and is given to each subsequent call.
        :returns: the list of tuples (path, addon, bundle)
        """
        exts = []
        manifest_cache = self._get_manifest_cache()
        if js:
            exts += SCRIPT_EXTENSIONS
        if css:
            exts += STYLE_EXTENSIONS
        if xml:
            exts += TEMPLATE_EXTENSIONS

        if addons is None:
            addons = self._get_addons_list()

        # 1. Creates an empty assets list (if initial call).
        if asset_paths is None:
            asset_paths = []
        # This index will be used when prepending: files will be prepend at the
        # start of the CURRENT bundle.
        bundle_start_index = len(asset_paths)

        def get_path_index(path, raise_if_none=True):
            """Returns the index of the given path in the current assets list."""
            for i in range(len(asset_paths)):
                if asset_paths[i][0] == path:
                    return i
            if raise_if_none:
                raise Exception("File %s not found in bundle %s" % (path, bundle))

        def add_paths(addon, paths, target_index=None):
            """Adds the given paths to the current list. An index can be specified."""
            target_index = len(asset_paths) if target_index is None else target_index
            for path in paths:
                if get_path_index(path, False) is not None:
                    # the path is already present in the asset list: don't duplicate it
                    continue
                asset_paths.insert(target_index, (path, addon, bundle))
                target_index += 1

        def remove_paths(targets):
            """Removes the given paths from the current assets list.
            Returns the index of the first target"""
            for target in targets:
                target_index = get_path_index(target)
                del asset_paths[target_index]

        def process_path(directive, target, path_def):
            """
            This sub function is meant to take a directive and a set of
            arguments and apply them to the current asset_paths list
            accordingly.

            It is nested inside `get_asset_paths` since we need the current
            list of addons, extensions, asset_paths and manifest_cache.

            :param directive: string
            :param path_def: string
            """
            if not path_def:
                # 2 arguments given: no target
                path_def = target
                target = None

            if directive == INCLUDE_DIRECTIVE:
                c_path = list(circular_path) if circular_path else []
                if bundle in c_path:
                    c_path.append(bundle)  # to have a full circle in the exception
                    raise Exception('Circular assets bundle declaration: %s' % ' > '.join(c_path))
                c_path.append(bundle)
                # Recursively calls this function for each 'include' directive.
                return self.get_asset_paths(path_def, addons, css, js, xml, asset_paths, c_path)

            addon, paths = get_paths(path_def, exts, manifest_cache)

            if directive in DIRECTIVES_WITH_TARGET:
                _, target_paths = get_paths(target, exts, manifest_cache)
                if not len(target_paths):
                    # The list is empty when the target path has the wrong extension.
                    # -> nothing to replace
                    return
                target_index = get_path_index(target_paths[0])

            if directive == REPLACE_DIRECTIVE:
                # Remove all target paths and add all paths found
                add_paths(addon, paths, target_index)
                remove_paths(target_paths)
            elif directive == REMOVE_DIRECTIVE:
                # Remove all paths found
                remove_paths(paths)
            else:
                # Add all paths found...
                insert_index = None
                if directive == BEFORE_DIRECTIVE:
                    insert_index = target_index
                elif directive == AFTER_DIRECTIVE:
                    insert_index = target_index + 1
                elif directive == PREPEND_DIRECTIVE:
                    insert_index = bundle_start_index
                add_paths(addon, paths, insert_index)

        # 2. Goes through the first sequence of 'ir.asset' records
        assets = self.sudo().search(self._get_asset_domain(bundle)).sorted(key='sequence')
        for asset in assets.filtered(lambda a: a.sequence < DEFAULT_SEQUENCE):
            process_path(asset.directive, asset.target, asset.glob)

        # 3. Goes through all addons' manifests.
        for addon in addons:
            manifest = manifest_cache.get(addon)
            if not manifest:
                continue
            manifest_assets = manifest.get('assets', {})
            for path_def in manifest_assets.get(bundle, []):
                # Default directive: append
                directive = APPEND_DIRECTIVE
                target = None
                if type(path_def) == tuple:
                    # Additional directive given
                    if path_def[0] in DIRECTIVES_WITH_TARGET:
                        directive, target, path_def = path_def
                    else:
                        directive, path_def = path_def
                process_path(directive, target, path_def)

        # 4. Goes through the rest of 'ir.asset' records
        for asset in assets.filtered(lambda a: a.sequence >= DEFAULT_SEQUENCE):
            process_path(asset.directive, asset.target, asset.glob)

        return asset_paths

    def get_related_bundle(self, target_path_def, root_bundle):
        """
        Returns the first bundle directly defining a glob matching the target
        path. This is useful when generating an 'ir.asset' record to override
        a specific asset and target the right bundle, i.e. the first one
        defining the target path.

        :param target_path_def: string: path to match.
        :root_bundle: string: bundle from which to initiate the search.
        :returns: the first matching bundle or None
        """
        ext = target_path_def.split('.')[-1]
        target_path = get_paths(target_path_def)[1][0]

        js = False
        css = False
        xml = False

        if ext in SCRIPT_EXTENSIONS:
            js = True
        elif ext in STYLE_EXTENSIONS:
            css = True
        elif ext in TEMPLATE_EXTENSIONS:
            xml = True

        asset_paths = self.get_asset_paths(bundle=root_bundle, css=css, js=js, xml=xml)

        for path, _, bundle in asset_paths:
            if path == target_path:
                return bundle

        return root_bundle

    def _get_asset_domain(self, bundle):
        """Meant to be overridden to add additional parts to the search domain"""
        return [('bundle', '=', bundle), ('active', '=', True)]

    def _get_addons_list(self):
        """
        Returns the list of addons to take into account when loading assets.
        Can be overridden to filter the returned list of modules.
        :returns: string[]: list of module names
        """
        if not http.request:
            return self.env['ir.module.module'].sudo()._installed_sorted()
        else:
            return http.module_boot()

    @staticmethod
    def _get_manifest_cache():
        return http.addons_manifest
