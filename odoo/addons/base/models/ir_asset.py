# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from glob import glob
from logging import getLogger
from werkzeug import urls

import odoo
import odoo.modules.module  # get_manifest, don't from-import it
from odoo import api, fields, models, tools
from odoo.tools import misc

_logger = getLogger(__name__)

SCRIPT_EXTENSIONS = ('js',)
STYLE_EXTENSIONS = ('css', 'scss', 'sass', 'less')
TEMPLATE_EXTENSIONS = ('xml',)
DEFAULT_SEQUENCE = 16

# Directives are stored in variables for ease of use and syntax checks.
APPEND_DIRECTIVE = 'append'
PREPEND_DIRECTIVE = 'prepend'
AFTER_DIRECTIVE = 'after'
BEFORE_DIRECTIVE = 'before'
REMOVE_DIRECTIVE = 'remove'
REPLACE_DIRECTIVE = 'replace'
INCLUDE_DIRECTIVE = 'include'
# Those are the directives used with a 'target' argument/field.
DIRECTIVES_WITH_TARGET = [AFTER_DIRECTIVE, BEFORE_DIRECTIVE, REPLACE_DIRECTIVE]
WILDCARD_CHARACTERS = {'*', "?", "[", "]"}


def fs2web(path):
    """Converts a file system path to a web path"""
    if os.path.sep == '/':
        return path
    return '/'.join(path.split(os.path.sep))

def can_aggregate(url):
    parsed = urls.url_parse(url)
    return not parsed.scheme and not parsed.netloc and not url.startswith('/web/content')

def is_wildcard_glob(path):
    """Determine whether a path is a wildcarded glob eg: "/web/file[14].*"
    or a genuine single file path "/web/myfile.scss"""
    return not WILDCARD_CHARACTERS.isdisjoint(path)


class IrAsset(models.Model):
    """This model contributes to two things:

        1. It provides a function returning a list of all file paths declared
        in a given list of addons (see _get_addon_paths);

        2. It allows to create 'ir.asset' records to add additional directives
        to certain bundles.
    """
    _name = 'ir.asset'
    _description = 'Asset'
    _order = 'sequence, id'

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
    path = fields.Char(string='Path (or glob pattern)', required=True)
    target = fields.Char(string='Target')
    active = fields.Boolean(string='active', default=True)
    sequence = fields.Integer(string="Sequence", default=DEFAULT_SEQUENCE, required=True)

    def _get_asset_paths(self, bundle, addons=None, css=False, js=False):
        """
        Fetches all asset file paths from a given list of addons matching a
        certain bundle. The returned list is composed of tuples containing the
        file path [1], the first addon calling it [0] and the bundle name.
        Asset loading is performed as follows:

        1. All 'ir.asset' records matching the given bundle and with a sequence
        strictly less than 16 are applied.

        3. The manifests of the given addons are checked for assets declaration
        for the given bundle. If any, they are read sequentially and their
        operations are applied to the current list.

        4. After all manifests have been parsed, the remaining 'ir.asset'
        records matching the bundle are also applied to the current list.

        :param bundle: name of the bundle from which to fetch the file paths
        :param addons: list of addon names as strings. The files returned will
            only be contained in the given addons.
        :param css: boolean: whether or not to include style files
        :param js: boolean: whether or not to include script files and template
            files
        :returns: the list of tuples (path, addon, bundle)
        """
        installed = self._get_installed_addons_list()
        if addons is None:
            addons = self._get_active_addons_list()

        asset_paths = AssetPaths()
        self._fill_asset_paths(bundle, addons, installed, css, js, asset_paths, [])
        return asset_paths.list

    def _fill_asset_paths(self, bundle, addons, installed, css, js, asset_paths, seen):
        """
        Fills the given AssetPaths instance by applying the operations found in
        the matching bundle of the given addons manifests.
        See `_get_asset_paths` for more information.

        :param bundle: name of the bundle from which to fetch the file paths
        :param addons: list of addon names as strings
        :param css: boolean: whether or not to include style files
        :param js: boolean: whether or not to include script files
        :param xml: boolean: whether or not to include template files
        :param asset_paths: the AssetPath object to fill
        :param seen: a list of bundles already checked to avoid circularity
        """
        if bundle in seen:
            raise Exception("Circular assets bundle declaration: %s" % " > ".join(seen + [bundle]))

        exts = []
        if js:
            exts += SCRIPT_EXTENSIONS
            exts += TEMPLATE_EXTENSIONS
        if css:
            exts += STYLE_EXTENSIONS

        # this index is used for prepending: files are inserted at the beginning
        # of the CURRENT bundle.
        bundle_start_index = len(asset_paths.list)

        def process_path(directive, target, path_def):
            """
            This sub function is meant to take a directive and a set of
            arguments and apply them to the current asset_paths list
            accordingly.

            It is nested inside `_get_asset_paths` since we need the current
            list of addons, extensions and asset_paths.

            :param directive: string
            :param target: string or None or False
            :param path_def: string
            """
            if directive == INCLUDE_DIRECTIVE:
                # recursively call this function for each INCLUDE_DIRECTIVE directive.
                self._fill_asset_paths(path_def, addons, installed, css, js, asset_paths, seen + [bundle])
                return

            addon, paths = self._get_paths(path_def, installed, exts)

            # retrieve target index when it applies
            if directive in DIRECTIVES_WITH_TARGET:
                _, target_paths = self._get_paths(target, installed, exts)
                if not target_paths and target.rpartition('.')[2] not in exts:
                    # nothing to do: the extension of the target is wrong
                    return
                target_to_index = len(target_paths) and target_paths[0] or target
                target_index = asset_paths.index(target_to_index, addon, bundle)

            if directive == APPEND_DIRECTIVE:
                asset_paths.append(paths, addon, bundle)
            elif directive == PREPEND_DIRECTIVE:
                asset_paths.insert(paths, addon, bundle, bundle_start_index)
            elif directive == AFTER_DIRECTIVE:
                asset_paths.insert(paths, addon, bundle, target_index + 1)
            elif directive == BEFORE_DIRECTIVE:
                asset_paths.insert(paths, addon, bundle, target_index)
            elif directive == REMOVE_DIRECTIVE:
                asset_paths.remove(paths, addon, bundle)
            elif directive == REPLACE_DIRECTIVE:
                asset_paths.insert(paths, addon, bundle, target_index)
                asset_paths.remove(target_paths, addon, bundle)
            else:
                # this should never happen
                raise ValueError("Unexpected directive")

        # 1. Process the first sequence of 'ir.asset' records
        assets = self._get_related_assets([('bundle', '=', bundle)]).filtered('active')
        for asset in assets.filtered(lambda a: a.sequence < DEFAULT_SEQUENCE):
            process_path(asset.directive, asset.target, asset.path)

        # 2. Process all addons' manifests.
        for addon in self._topological_sort(tuple(addons)):
            for command in odoo.modules.module.get_manifest(addon)['assets'].get(bundle, ()):
                directive, target, path_def = self._process_command(command)
                process_path(directive, target, path_def)

        # 3. Process the rest of 'ir.asset' records
        for asset in assets.filtered(lambda a: a.sequence >= DEFAULT_SEQUENCE):
            process_path(asset.directive, asset.target, asset.path)

    def _get_related_assets(self, domain):
        """
        Returns a set of assets matching the domain, regardless of their
        active state. This method can be overridden to filter the results.
        :param domain: search domain
        :returns: ir.asset recordset
        """
        return self.with_context(active_test=False).sudo().search(domain, order='sequence, id')

    def _get_related_bundle(self, target_path_def, root_bundle):
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
        installed = self._get_installed_addons_list()
        target_path = self._get_paths(target_path_def, installed)[1][0]

        css = ext in STYLE_EXTENSIONS
        js = ext in SCRIPT_EXTENSIONS or ext in TEMPLATE_EXTENSIONS

        asset_paths = self._get_asset_paths(root_bundle, css=css, js=js)

        for path, _, bundle in asset_paths:
            if path == target_path:
                return bundle

        return root_bundle

    def _get_active_addons_list(self):
        """Can be overridden to filter the returned list of active modules."""
        return self._get_installed_addons_list()

    @api.model
    @tools.ormcache('addons_tuple')
    def _topological_sort(self, addons_tuple):
        """Returns a list of sorted modules name accord to the spec in ir.module.module
        that is, application desc, sequence, name then topologically sorted"""
        IrModule = self.env['ir.module.module']

        def mapper(addon):
            manif = odoo.modules.module.get_manifest(addon)
            from_terp = IrModule.get_values_from_terp(manif)
            from_terp['name'] = addon
            from_terp['depends'] = manif.get('depends', ['base'])
            return from_terp

        manifs = map(mapper, addons_tuple)

        def sort_key(manif):
            return (not manif['application'], int(manif['sequence']), manif['name'])

        manifs = sorted(manifs, key=sort_key)

        return misc.topological_sort({manif['name']: manif['depends'] for manif in manifs})

    @api.model
    @tools.ormcache_context(keys='install_module')
    def _get_installed_addons_list(self):
        """
        Returns the list of all installed addons.
        :returns: string[]: list of module names
        """
        # Main source: the current registry list
        # Second source of modules: server wide modules
        # Third source: the currently loading module from the context (similar to ir_ui_view)
        return self.env.registry._init_modules.union(odoo.conf.server_wide_modules or []).union(self.env.context.get('install_module', []))

    def _get_paths(self, path_def, installed, extensions=None):
        """
        Returns a list of file paths matching a given glob (path_def) as well as
        the addon targeted by the path definition. If no file matches that glob,
        the path definition is returned as is. This is either because the path is
        not correctly written or because it points to a URL.

        :param path_def: the definition (glob) of file paths to match
        :param installed: the list of installed addons
        :param extensions: a list of extensions that found files must match
        :returns: a tuple: the addon targeted by the path definition [0] and the
            list of file paths matching the definition [1] (or the glob itself if
            none). Note that these paths are filtered on the given `extensions`.
        """
        paths = []
        path_url = fs2web(path_def)
        path_parts = [part for part in path_url.split('/') if part]
        addon = path_parts[0]
        addon_manifest = odoo.modules.module.get_manifest(addon)

        safe_path = True
        if addon_manifest:
            if addon not in installed:
                # Assert that the path is in the installed addons
                raise Exception("Unallowed to fetch files from addon %s" % addon)
            addons_path = os.path.join(addon_manifest['addons_path'], '')[:-1]
            full_path = os.path.normpath(os.path.join(addons_path, *path_parts))

            # first security layer: forbid escape from the current addon
            # "/mymodule/../myothermodule" is forbidden
            # the condition after the or is to further guarantee that we won't access
            # a directory that happens to be named like an addon (web....)
            if addon not in full_path or addons_path not in full_path:
                addon = None
                safe_path = False
            else:
                paths = [
                    path for path in sorted(glob(full_path, recursive=True))
                ]

            # second security layer: do we have the right to access the files
            # that are grabbed by the glob ?
            # In particular we don't want to expose data in xmls of the module
            def is_safe_path(path):
                try:
                    misc.file_path(path, SCRIPT_EXTENSIONS + STYLE_EXTENSIONS + TEMPLATE_EXTENSIONS)
                except (ValueError, FileNotFoundError):
                    return False
                if path.rpartition('.')[2] in TEMPLATE_EXTENSIONS:
                    # normpath will strip the trailing /, which is why it has to be added afterwards
                    static_path = os.path.normpath("%s/static" % addon) + os.path.sep
                    # Forbid xml to leak
                    return static_path in path
                return True

            len_paths = len(paths)
            paths = list(filter(is_safe_path, paths))
            safe_path = safe_path and len_paths == len(paths)

            # Web assets must be loaded using relative paths.
            paths = [fs2web(path[len(addons_path):]) for path in paths]
        else:
            addon = None

        if not paths and (not can_aggregate(path_url) or (safe_path and not is_wildcard_glob(path_url))):
            # No file matching the path; the path_def could be a url.
            paths = [path_url]

        if not paths:
            msg = f'IrAsset: the path "{path_def}" did not resolve to anything.'
            if not safe_path:
                msg += " It may be due to security reasons."
            _logger.warning(msg)
        # Paths are filtered on the extensions (if any).
        return addon, [
            path
            for path in paths
            if not extensions or path.split('.')[-1] in extensions
        ]

    def _process_command(self, command):
        """Parses a given command to return its directive, target and path definition."""
        if isinstance(command, str):
            # Default directive: append
            directive, target, path_def = APPEND_DIRECTIVE, None, command
        elif command[0] in DIRECTIVES_WITH_TARGET:
            directive, target, path_def = command
        else:
            directive, path_def = command
            target = None
        return directive, target, path_def


class AssetPaths:
    """ A list of asset paths (path, addon, bundle) with efficient operations. """
    def __init__(self):
        self.list = []
        self.memo = set()

    def index(self, path, addon, bundle):
        """Returns the index of the given path in the current assets list."""
        if path not in self.memo:
            self._raise_not_found(path, bundle)
        for index, asset in enumerate(self.list):
            if asset[0] == path:
                return index

    def append(self, paths, addon, bundle):
        """Appends the given paths to the current list."""
        for path in paths:
            if path not in self.memo:
                self.list.append((path, addon, bundle))
                self.memo.add(path)

    def insert(self, paths, addon, bundle, index):
        """Inserts the given paths to the current list at the given position."""
        to_insert = []
        for path in paths:
            if path not in self.memo:
                to_insert.append((path, addon, bundle))
                self.memo.add(path)
        self.list[index:index] = to_insert

    def remove(self, paths_to_remove, addon, bundle):
        """Removes the given paths from the current list."""
        paths = {path for path in paths_to_remove if path in self.memo}
        if paths:
            self.list[:] = [asset for asset in self.list if asset[0] not in paths]
            self.memo.difference_update(paths)
            return

        if paths_to_remove:
            self._raise_not_found(paths_to_remove, bundle)

    def _raise_not_found(self, path, bundle):
        raise ValueError("File(s) %s not found in bundle %s" % (path, bundle))
