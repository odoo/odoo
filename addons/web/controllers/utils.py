# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
import hashlib
import io
import logging
import re
from collections import OrderedDict, defaultdict

import babel.messages.pofile
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from lxml import etree
from werkzeug.urls import iri_to_uri

from odoo.tools import apply_inheritance_specs
from odoo.tools.translate import _
from odoo.tools.misc import file_open
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


def clean_action(action, env):
    action_type = action.setdefault('type', 'ir.actions.act_window_close')
    if action_type == 'ir.actions.act_window':
        action = fix_view_modes(action)

    # When returning an action, keep only relevant fields/properties
    readable_fields = env[action['type']]._get_readable_fields()
    action_type_fields = env[action['type']]._fields.keys()

    cleaned_action = {
        field: value
        for field, value in action.items()
        # keep allowed fields and custom properties fields
        if field in readable_fields or field not in action_type_fields
    }

    # Warn about custom properties fields, because use is discouraged
    action_name = action.get('name') or action
    custom_properties = action.keys() - readable_fields - action_type_fields
    if custom_properties:
        _logger.warning("Action %r contains custom properties %s. Passing them "
            "via the `params` or `context` properties is recommended instead",
            action_name, ', '.join(map(repr, custom_properties)))

    return cleaned_action


def ensure_db(redirect='/web/database/selector'):
    # This helper should be used in web client auth="none" routes
    # if those routes needs a db to work with.
    # If the heuristics does not find any database, then the users will be
    # redirected to db selector or any url specified by `redirect` argument.
    # If the db is taken out of a query parameter, it will be checked against
    # `http.db_filter()` in order to ensure it's legit and thus avoid db
    # forgering that could lead to xss attacks.
    db = request.params.get('db') and request.params.get('db').strip()

    # Ensure db is legit
    if db and db not in http.db_filter([db]):
        db = None

    if db and not request.session.db:
        # User asked a specific database on a new session.
        # That mean the nodb router has been used to find the route
        # Depending on installed module in the database, the rendering of the page
        # may depend on data injected by the database route dispatcher.
        # Thus, we redirect the user to the same page but with the session cookie set.
        # This will force using the database route dispatcher...
        r = request.httprequest
        url_redirect = werkzeug.urls.url_parse(r.base_url)
        if r.query_string:
            # in P3, request.query_string is bytes, the rest is text, can't mix them
            query_string = iri_to_uri(r.query_string)
            url_redirect = url_redirect.replace(query=query_string)
        request.session.db = db
        werkzeug.exceptions.abort(request.redirect(url_redirect.to_url(), 302))

    # if db not provided, use the session one
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db

    # if no database provided and no database in session, use monodb
    if not db:
        all_dbs = http.db_list(force=True)
        if len(all_dbs) == 1:
            db = all_dbs[0]

    # if no db can be found til here, send to the database selector
    # the database selector will redirect to database manager if needed
    if not db:
        werkzeug.exceptions.abort(request.redirect(redirect, 303))

    # always switch the session to the computed db
    if db != request.session.db:
        request.session = http.root.session_store.new()
        request.session.update(http.get_default_session(), db=db)
        request.session.context['lang'] = request.default_lang()
        werkzeug.exceptions.abort(request.redirect(request.httprequest.url, 302))


def fix_view_modes(action):
    """ For historical reasons, Odoo has weird dealings in relation to
    view_mode and the view_type attribute (on window actions):

    * one of the view modes is ``tree``, which stands for both list views
      and tree views
    * the choice is made by checking ``view_type``, which is either
      ``form`` for a list view or ``tree`` for an actual tree view

    This methods simply folds the view_type into view_mode by adding a
    new view mode ``list`` which is the result of the ``tree`` view_mode
    in conjunction with the ``form`` view_type.

    TODO: this should go into the doc, some kind of "peculiarities" section

    :param dict action: an action descriptor
    :returns: nothing, the action is modified in place
    """
    if not action.get('views'):
        generate_views(action)

    if action.pop('view_type', 'form') != 'form':
        return action

    if 'view_mode' in action:
        action['view_mode'] = ','.join(
            mode if mode != 'tree' else 'list'
            for mode in action['view_mode'].split(','))
    action['views'] = [
        [id, mode if mode != 'tree' else 'list']
        for id, mode in action['views']
    ]

    return action


# I think generate_views,fix_view_modes should go into js ActionManager
def generate_views(action):
    """
    While the server generates a sequence called "views" computing dependencies
    between a bunch of stuff for views coming directly from the database
    (the ``ir.actions.act_window model``), it's also possible for e.g. buttons
    to return custom view dictionaries generated on the fly.

    In that case, there is no ``views`` key available on the action.

    Since the web client relies on ``action['views']``, generate it here from
    ``view_mode`` and ``view_id``.

    Currently handles two different cases:

    * no view_id, multiple view_mode
    * single view_id, single view_mode

    :param dict action: action descriptor dictionary to generate a views key for
    """
    view_id = action.get('view_id') or False
    if isinstance(view_id, (list, tuple)):
        view_id = view_id[0]

    # providing at least one view mode is a requirement, not an option
    view_modes = action['view_mode'].split(',')

    if len(view_modes) > 1:
        if view_id:
            raise ValueError('Non-db action dictionaries should provide '
                             'either multiple view modes or a single view '
                             'mode and an optional view id.\n\n Got view '
                             'modes %r and view id %r for action %r' % (
                view_modes, view_id, action))
        action['views'] = [(False, mode) for mode in view_modes]
        return
    action['views'] = [(view_id, view_modes[0])]


def _get_login_redirect_url(uid, redirect=None):
    """ Decide if user requires a specific post-login redirect, e.g. for 2FA, or if they are
    fully logged and can proceed to the requested URL
    """
    if request.session.uid: # fully logged
        return redirect or '/web'

    # partial session (MFA)
    url = request.env(user=uid)['res.users'].browse(uid)._mfa_url()
    if not redirect:
        return url

    parsed = werkzeug.urls.url_parse(url)
    qs = parsed.decode_query()
    qs['redirect'] = redirect
    return parsed.replace(query=werkzeug.urls.url_encode(qs)).to_url()


def _local_web_translations(trans_file):
    messages = []
    try:
        with file_open(trans_file, filter_ext=('.po')) as t_file:
            po = babel.messages.pofile.read_po(t_file)
    except Exception:
        return
    for x in po:
        if x.id and x.string and "openerp-web" in x.auto_comments:
            messages.append({'id': x.id, 'string': x.string})
    return messages


class HomeStaticTemplateHelpers:
    r"""
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
        """
        :param str|list addons: plain list or comma separated list of addons
        :param str db: the current db we are working on
        :param bool checksum_only: only computes the checksum of all files for addons
        :param str debug: the debug mode of the session
        """
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
            _logger.error("Could not parse file %s: %s", file_name, e.msg)
            raise

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
                # owl chokes on comments, disable debug comments for now
                # pylint: disable=W0125
                if False: # self.debug and inherit_mode == self.EXTENSION_MODE:
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

    def _read_addon_file(self, path_or_url):
        """Read the content of a file or an ``ir.attachment`` record given by
        ``path_or_url``.

        :param str path_or_url:
        :returns: bytes
        :raises FileNotFoundError: if the path does not match a module file
            or an attachment
        """
        try:
            with file_open(path_or_url, 'rb') as fp:
                contents = fp.read()
        except FileNotFoundError as e:
            attachment = request.env['ir.attachment'].sudo().search([
                ('url', '=', path_or_url),
                ('type', '=', 'binary'),
            ], limit=1)
            if attachment:
                contents = attachment.raw
            else:
                raise e
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
                    self._compute_xml_tree(addon, fname, contents)

                    if root is None:
                        root = etree.Element('templates')

        for addon in self.template_dict.values():
            for template in addon.values():
                root.append(template)

        return etree.tostring(root, encoding='utf-8') if root is not None else b'', checksum.hexdigest()[:64]

    def _get_asset_paths(self, bundle):
        """Proxy for ir_asset._get_asset_paths
        Useful to make 'self' testable.
        """
        return request.env['ir.asset']._get_asset_paths(addons=self.addons, bundle=bundle, xml=True)

    def _get_qweb_templates(self, bundle):
        """One and only entry point that gets and evaluates static qweb templates

        :rtype: (str, str)
        """
        xml_paths = defaultdict(list)

        # group paths by module, keeping them in order
        for path, addon, _ in self._get_asset_paths(bundle):
            addon_paths = xml_paths[addon]
            if path not in addon_paths:
                addon_paths.append(path)

        content, checksum = self._concat_xml(xml_paths)
        return content, checksum

    @classmethod
    def get_qweb_templates_checksum(cls, addons=None, db=None, debug=False, bundle=None):
        return cls(addons, db, checksum_only=True, debug=debug)._get_qweb_templates(bundle)[1]

    @classmethod
    def get_qweb_templates(cls, addons=None, db=None, debug=False, bundle=None):
        return cls(addons, db, debug=debug)._get_qweb_templates(bundle)[0]
