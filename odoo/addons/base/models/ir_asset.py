# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os
from glob import glob
from logging import getLogger
from werkzeug import urls

import odoo
import odoo.modules.module  # get_manifest, don't from-import it
from odoo import api, fields, models, tools
from odoo.tools import misc
from odoo.tools.constants import ASSET_EXTENSIONS, EXTERNAL_ASSET

_logger = getLogger(__name__)

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
    return '*' in path or '[' in path or ']' in path or '?' in path


def _glob_static_file(pattern):
    files = glob(pattern, recursive=True)
    return sorted((file, os.path.getmtime(file)) for file in files if file.rsplit('.', 1)[-1] in ASSET_EXTENSIONS)


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
        self.env.registry.clear_cache('assets')
        return super().create(vals_list)

    def write(self, values):
        if self:
            self.env.registry.clear_cache('assets')
        return super().write(values)

    def unlink(self):
        self.env.registry.clear_cache('assets')
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

    def _get_asset_params(self):
        """
        This method can be overriden to add param _get_asset_paths call.
        Those params will be part of the orm cache key
        """
        return {}

    def _get_asset_bundle_url(self, filename, unique, assets_params, ignore_params=False):
        return f'/web/assets/{unique}/{filename}'

    def _parse_bundle_name(self, bundle_name, debug_assets):
        bundle_name, asset_type = bundle_name.rsplit('.', 1)
        rtl = False
        if not debug_assets:
            bundle_name, min_ = bundle_name.rsplit('.', 1)
            if min_ != 'min':
                raise ValueError("'min' expected in extension in non debug mode")
        if asset_type == 'css':
            if bundle_name.endswith('.rtl'):
                bundle_name = bundle_name[:-4]
                rtl = True
        elif asset_type != 'js':
            raise ValueError('Only js and css assets bundle are supported for now')
        if len(bundle_name.split('.')) != 2:
            raise ValueError(f'{bundle_name} is not a valid bundle name, should have two parts')
        return bundle_name, rtl, asset_type

    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('bundle', 'tuple(sorted(assets_params.items()))', cache='assets'),
    )
    def _get_asset_paths(self, bundle, assets_params):
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
        :param assets_params: parameters needed by overrides, mainly website_id
            see _get_asset_params
        :returns: the list of tuples (path, addon, bundle)
        """
        installed = self._get_installed_addons_list()
        addons = self._get_active_addons_list(**assets_params)

        asset_paths = AssetPaths()

        addons = self._topological_sort(tuple(addons))

        self._fill_asset_paths(bundle, asset_paths, [], addons, installed, **assets_params)
        return asset_paths.list

    def _fill_asset_paths(self, bundle, asset_paths, seen, addons, installed, **assets_params):
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

        # this index is used for prepending: files are inserted at the beginning
        # of the CURRENT bundle.
        bundle_start_index = len(asset_paths.list)

        assets = self._get_related_assets([('bundle', '=', bundle)], **assets_params).filtered('active')
        # 1. Process the first sequence of 'ir.asset' records
        for asset in assets.filtered(lambda a: a.sequence < DEFAULT_SEQUENCE):
            self._process_path(bundle, asset.directive, asset.target, asset.path, asset_paths, seen, addons, installed, bundle_start_index, **assets_params)

        # 2. Process all addons' manifests.
        for addon in addons:
            for command in odoo.modules.module._get_manifest_cached(addon)['assets'].get(bundle, ()):
                directive, target, path_def = self._process_command(command)
                self._process_path(bundle, directive, target, path_def, asset_paths, seen, addons, installed, bundle_start_index, **assets_params)

        # 3. Process the rest of 'ir.asset' records
        for asset in assets.filtered(lambda a: a.sequence >= DEFAULT_SEQUENCE):
            self._process_path(bundle, asset.directive, asset.target, asset.path, asset_paths, seen, addons, installed, bundle_start_index, **assets_params)

    def _process_path(self, bundle, directive, target, path_def, asset_paths, seen, addons, installed, bundle_start_index, **assets_params):
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
            self._fill_asset_paths(path_def, asset_paths, seen + [bundle], addons, installed, **assets_params)
            return
        if can_aggregate(path_def):
            paths = self._get_paths(path_def, installed)
        else:
            paths = [(path_def, EXTERNAL_ASSET, -1)]  # external urls

        # retrieve target index when it applies
        if directive in DIRECTIVES_WITH_TARGET:
            target_paths = self._get_paths(target, installed)
            if not target_paths and target.rpartition('.')[2] not in ASSET_EXTENSIONS:
                # nothing to do: the extension of the target is wrong
                return
            if target_paths:
                target = target_paths[0][0]
            target_index = asset_paths.index(target, bundle)

        if directive == APPEND_DIRECTIVE:
            asset_paths.append(paths, bundle)
        elif directive == PREPEND_DIRECTIVE:
            asset_paths.insert(paths, bundle, bundle_start_index)
        elif directive == AFTER_DIRECTIVE:
            asset_paths.insert(paths, bundle, target_index + 1)
        elif directive == BEFORE_DIRECTIVE:
            asset_paths.insert(paths, bundle, target_index)
        elif directive == REMOVE_DIRECTIVE:
            asset_paths.remove(paths, bundle)
        elif directive == REPLACE_DIRECTIVE:
            asset_paths.insert(paths, bundle, target_index)
            asset_paths.remove(target_paths, bundle)
        else:
            # this should never happen
            raise ValueError("Unexpected directive")

    def _get_related_assets(self, domain):
        """
        Returns a set of assets matching the domain, regardless of their
        active state. This method can be overridden to filter the results.
        :param domain: search domain
        :returns: ir.asset recordset
        """
        # active_test is needed to disable some assets through filter_duplicate for website
        # they will be filtered on active afterward
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
        installed = self._get_installed_addons_list()
        target_path, _full_path, _modified = self._get_paths(target_path_def, installed)[0]
        assets_params = self._get_asset_params()
        asset_paths = self._get_asset_paths(root_bundle, assets_params)

        for path, _full_path, bundle, _modified in asset_paths:
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
            manif = odoo.modules.module._get_manifest_cached(addon)
            from_terp = IrModule.get_values_from_terp(manif)
            from_terp['name'] = addon
            from_terp['depends'] = manif.get('depends', ['base'])
            return from_terp

        manifs = map(mapper, addons_tuple)

        def sort_key(manif):
            return (not manif['application'], int(manif['sequence']), manif['name'])

        manifs = sorted(manifs, key=sort_key)

        return misc.topological_sort({manif['name']: tuple(manif['depends']) for manif in manifs})

    @api.model
    @tools.ormcache()
    def _get_installed_addons_list(self):
        """
        Returns the list of all installed addons.
        :returns: string[]: list of module names
        """
        # Main source: the current registry list
        # Second source of modules: server wide modules
        return self.env.registry._init_modules.union(odoo.conf.server_wide_modules or [])

    def _get_paths(self, path_def, installed):
        """
        Returns a list of tuple (path, full_path, modified) matching a given glob (path_def).
        The glob can only occur in the static direcory of an installed addon.

        If the path_def matches a (list of) file, the result will contain the full_path
        and the modified time.
        Ex: ('/base/static/file.js', '/home/user/source/odoo/odoo/addons/base/static/file.js', 643636800)

        If the path_def looks like a non aggregable path (http://, /web/assets), only return the path
        Ex: ('http://example.com/lib.js', None, -1)
        The timestamp -1 is given to be thruthy while carrying no information.

        If the path_def is not a wildward, but may still be a valid addons path, return a False path
        with No timetamp
        Ex: ('/_custom/web.asset_frontend', False, None)

        :param path_def: the definition (glob) of file paths to match
        :param installed: the list of installed addons
        :param extensions: a list of extensions that found files must match
        :returns: a list of tuple: (path, full_path, modified)
        """
        paths = None
        path_def = fs2web(path_def)  # we expect to have all path definition unix style or url style, this is a safety
        path_parts = [part for part in path_def.split('/') if part]
        addon = path_parts[0]
        addon_manifest = odoo.modules.module._get_manifest_cached(addon)

        safe_path = True
        if addon_manifest:
            if addon not in installed:
                # Assert that the path is in the installed addons
                raise Exception(f"Unallowed to fetch files from addon {addon} for file {path_def}")
            addons_path = addon_manifest['addons_path']
            full_path = os.path.normpath(os.sep.join([addons_path, *path_parts]))
            # forbid escape from the current addon
            # "/mymodule/../myothermodule" is forbidden
            static_prefix = os.sep.join([addons_path, addon, 'static', ''])
            if full_path.startswith(static_prefix):
                paths_with_timestamps = _glob_static_file(full_path)
                paths = [
                    (fs2web(absolute_path[len(addons_path):]), absolute_path, timestamp)
                    for absolute_path, timestamp in paths_with_timestamps
                ]
            else:
                safe_path = False
        else:
            safe_path = False

        if not paths and not can_aggregate(path_def):  # http:// or /web/content
            paths = [(path_def, EXTERNAL_ASSET, -1)]

        if not paths and not is_wildcard_glob(path_def):  # an attachment url most likely
            paths = [(path_def, None, None)]

        if not paths:
            msg = f'IrAsset: the path "{path_def}" did not resolve to anything.'
            if not safe_path:
                msg += " It may be due to security reasons."
            _logger.warning(msg)
        # Paths are filtered on the extensions (if any).
        return paths

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

    def index(self, path, bundle):
        """Returns the index of the given path in the current assets list."""
        if path not in self.memo:
            self._raise_not_found(path, bundle)
        for index, asset in enumerate(self.list):
            if asset[0] == path:
                return index

    def append(self, paths, bundle):
        """Appends the given paths to the current list."""
        for path, full_path, last_modified in paths:
            if path not in self.memo:
                self.list.append((path, full_path, bundle, last_modified))
                self.memo.add(path)

    def insert(self, paths, bundle, index):
        """Inserts the given paths to the current list at the given position."""
        to_insert = []
        for path, full_path, last_modified in paths:
            if path not in self.memo:
                to_insert.append((path, full_path, bundle, last_modified))
                self.memo.add(path)
        self.list[index:index] = to_insert

    def remove(self, paths_to_remove, bundle):
        """Removes the given paths from the current list."""
        paths = {path for path, _full_path, _last_modified in paths_to_remove if path in self.memo}
        if paths:
            self.list[:] = [asset for asset in self.list if asset[0] not in paths]
            self.memo.difference_update(paths)
            return

        if paths_to_remove:
            self._raise_not_found([path for path, _full_path, _last_modified in paths_to_remove], bundle)

    def _raise_not_found(self, path, bundle):
        raise ValueError("File(s) %s not found in bundle %s" % (path, bundle))
