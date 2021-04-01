import re
from collections import OrderedDict
from lxml import etree
import hashlib
import io
import copy
from logging import getLogger
import os
from glob import glob

from odoo.tools import apply_inheritance_specs
from odoo.tools.translate import _
from odoo import http

_logger = getLogger(__name__)

SCRIPT_EXTENSIONS = ['js']

STYLE_EXTENSIONS = ['css', 'scss']

TEMPLATE_EXTENSIONS = ['xml']


def fs2web(path):
    """convert FS path into web path"""
    return '/'.join(path.split(os.path.sep))

def get_addon_files(addons=['wowl'], bundle=None, css=False, js=False, xml=False):
    """
    Helper method to get pathnames to files referenced in wowl addon's manifest file.
    :param addons: the list of addons to take into account when reading the
                   manifest bundles (default: "wowl" only)
    :param bundle: the key to read in the manifest's "assets" key (typically
                   'owl_qweb' or 'style')
    :param css: whether to take the style assets (default: False)
    :param js: whether to take the script assets (default: False)
    :param xml: whether to take the template assets (default: False)
    :return: list of tuple in the form: (addon, path name)
    """
    exts = []
    if js:
        exts += SCRIPT_EXTENSIONS
    if css:
        exts += STYLE_EXTENSIONS
    if xml:
        exts += TEMPLATE_EXTENSIONS

    manifests = http.addons_manifest
    addon_files = []
    for addon in addons:
        manifest = manifests.get(addon)

        if not manifest:
            continue

        assets = manifest.get('assets', {})

        for path_def in assets.get(bundle, []):
            path_def = os.path.join(addon, path_def)
            path_addon_manifest = manifests.get(addon)

            if not path_addon_manifest:
                continue

            addons_path = os.path.join(path_addon_manifest['addons_path'], '')[:-1]
            full_path = os.path.normpath(os.path.join(addons_path, path_def))

            glob_paths = []
            for path in glob(full_path, recursive=True):
                ext = path.split('.')[-1]
                if not exts or ext in exts:
                    glob_path = path[len(addons_path):] if ext != 'xml' else path
                    glob_paths.append(fs2web(glob_path))

            # The glob module returns an unsorted list
            glob_paths.sort()

            if len(glob_paths):
                # Files found are appended in the addon_files list if not already in it
                [addon_files.append((addon, file))
                    for file in glob_paths
                    if (addon, file) not in addon_files
                ]
            else:
                # No files matching the path definition -> interpreted as a sub-bundle
                [addon_files.append((addon, file))
                    for addon, file in get_addon_files(addons, path_def, css, js, xml)
                    if (addon, file) not in addon_files
                ]

    return addon_files


class HomeStaticTemplateHelpers(object):
    """
    Helper Class that wraps the reading of static qweb templates files
    and xpath inheritance applied to those templates
    /!\ Template inheritance order is defined by ir.module.module natural order
        which is "sequence, name"
        Then a topological sort is applied, which just puts dependencies
        of a module before that module
    """
    NAME_TEMPLATE_DIRECTIVE = 't-name'
    STATIC_INHERIT_DIRECTIVE = 't-inherit'
    STATIC_INHERIT_MODE_DIRECTIVE = 't-inherit-mode'
    PRIMARY_MODE = 'primary'
    EXTENSION_MODE = 'extension'
    DEFAULT_MODE = PRIMARY_MODE

    COMMENT_PATTERN = r'Modified by [\s\w\-.]+ from [\s\w\-.]+'

    def __init__(self, addons, db, checksum_only=False, debug=False):
        '''
        :param str|list addons: plain list or comma separated list of addons
        :param str db: the current db we are working on
        :param bool checksum_only: only computes the checksum of all files for addons
        :param str debug: the debug mode of the session
        '''
        super(HomeStaticTemplateHelpers, self).__init__()
        self.addons = addons.split(',') if isinstance(addons, str) else addons
        self.db = db
        self.debug = debug
        self.checksum_only = checksum_only
        self.template_dict = OrderedDict()

    def _get_parent_template(self, addon, template):
        """Computes the real addon name and the template name
        of the parent template (the one that is inherited from)

        :param str addon: the addon the template is declared in
        :param etree template: the current template we are are handling
        :returns: (str, str)
        """
        original_template_name = template.attrib[self.STATIC_INHERIT_DIRECTIVE]
        split_name_attempt = original_template_name.split('.', 1)
        parent_addon, parent_name = tuple(split_name_attempt) if len(split_name_attempt) == 2 else (addon, original_template_name)
        if parent_addon not in self.template_dict:
            if original_template_name in self.template_dict[addon]:
                parent_addon = addon
                parent_name = original_template_name
            else:
                raise ValueError(_('Module %s not loaded or inexistent, or templates of addon being loaded (%s) are misordered') % (parent_addon, addon))

        if parent_name not in self.template_dict[parent_addon]:
            raise ValueError(_("No template found to inherit from. Module %s and template name %s") % (parent_addon, parent_name))

        return parent_addon, parent_name

    def _compute_xml_tree(self, addon, file_name, source):
        """Computes the xml tree that 'source' contains
        Applies inheritance specs in the process

        :param str addon: the current addon we are reading files for
        :param str file_name: the current name of the file we are reading
        :param str source: the content of the file
        :returns: etree
        """
        try:
            all_templates_tree = etree.parse(io.BytesIO(source), parser=etree.XMLParser(remove_comments=True)).getroot()
        except etree.ParseError as e:
            _logger.error("Could not parse file %s: %s" % (file_name, e.msg))
            raise e

        self.template_dict.setdefault(addon, OrderedDict())
        for template_tree in list(all_templates_tree):
            if self.NAME_TEMPLATE_DIRECTIVE in template_tree.attrib:
                template_name = template_tree.attrib[self.NAME_TEMPLATE_DIRECTIVE]
                dotted_names = template_name.split('.', 1)
                if len(dotted_names) > 1 and dotted_names[0] == addon:
                    template_name = dotted_names[1]
            else:
                # self.template_dict[addon] grows after processing each template
                template_name = 'anonymous_template_%s' % len(self.template_dict[addon])
            if self.STATIC_INHERIT_DIRECTIVE in template_tree.attrib:
                inherit_mode = template_tree.attrib.get(self.STATIC_INHERIT_MODE_DIRECTIVE, self.DEFAULT_MODE)
                if inherit_mode not in [self.PRIMARY_MODE, self.EXTENSION_MODE]:
                    raise ValueError(_("Invalid inherit mode. Module %s and template name %s") % (addon, template_name))

                parent_addon, parent_name = self._get_parent_template(addon, template_tree)

                # After several performance tests, we found out that deepcopy is the most efficient
                # solution in this case (compared with copy, xpath with '.' and stringifying).
                parent_tree = copy.deepcopy(self.template_dict[parent_addon][parent_name])

                xpaths = list(template_tree)
                if self.debug and inherit_mode == self.EXTENSION_MODE:
                    for xpath in xpaths:
                        xpath.insert(0, etree.Comment(" Modified by %s from %s " % (template_name, addon)))
                elif inherit_mode == self.PRIMARY_MODE:
                    parent_tree.tag = template_tree.tag
                inherited_template = apply_inheritance_specs(parent_tree, xpaths)

                if inherit_mode == self.PRIMARY_MODE:  # New template_tree: A' = B(A)
                    for attr_name, attr_val in template_tree.attrib.items():
                        if attr_name not in ('t-inherit', 't-inherit-mode'):
                            inherited_template.set(attr_name, attr_val)
                    if self.debug:
                        self._remove_inheritance_comments(inherited_template)
                    self.template_dict[addon][template_name] = inherited_template

                else:  # Modifies original: A = B(A)
                    self.template_dict[parent_addon][parent_name] = inherited_template
            else:
                if template_name in self.template_dict[addon]:
                    raise ValueError(_("Template %s already exists in module %s") % (template_name, addon))
                self.template_dict[addon][template_name] = template_tree
        return all_templates_tree

    def _remove_inheritance_comments(self, inherited_template):
        '''Remove the comments added in the template already, they come from other templates extending
        the base of this inheritance

        :param inherited_template:
        '''
        for comment in inherited_template.xpath('//comment()'):
            if re.match(self.COMMENT_PATTERN, comment.text.strip()):
                comment.getparent().remove(comment)

    def _read_addon_file(self, file_path):
        """Reads the content of a file given by file_path
        Usefull to make 'self' testable
        :param str file_path:
        :returns: str
        """
        with open(file_path, 'rb') as fp:
            contents = fp.read()
        return contents

    def _concat_xml(self, file_dict):
        """Concatenate xml files

        :param dict(list) file_dict:
            key: addon name
            value: list of files for an addon
        :returns: (concatenation_result, checksum)
        :rtype: (bytes, str)
        """
        checksum = hashlib.new('sha512')  # sha512/256
        if not file_dict:
            return b'', checksum.hexdigest()

        root = None
        for addon, fnames in file_dict.items():
            for fname in fnames:
                contents = self._read_addon_file(fname)
                checksum.update(contents)
                if not self.checksum_only:
                    xml = self._compute_xml_tree(addon, fname, contents)

                    if root is None:
                        root = etree.Element(xml.tag)

        for addon in self.template_dict.values():
            for template in addon.values():
                root.append(template)

        return etree.tostring(root, encoding='utf-8') if root is not None else b'', checksum.hexdigest()[:64]

    def _get_qweb_templates(self):
        """One and only entry point that gets and evaluates static qweb templates

        :rtype: (str, str)
        """
        files = [file for addon, file in get_addon_files(bundle='owl_qweb', xml=True)]
        content, checksum = self._concat_xml(OrderedDict([('wowl', files)]))
        return content, checksum

    @classmethod
    def get_qweb_templates_checksum(cls, addons, db=None, debug=False):
        return cls(addons, db, checksum_only=True, debug=debug)._get_qweb_templates()[1]

    @classmethod
    def get_qweb_templates(cls, addons, db=None, debug=False):
        return cls(addons, db, debug=debug)._get_qweb_templates()[0]
