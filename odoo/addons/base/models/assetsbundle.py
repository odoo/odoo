# -*- coding: utf-8 -*-
import base64
import os
import re
import hashlib
import itertools
import json
import textwrap
import uuid
try:
    import sass as libsass
except ImportError:
    # If the `sass` python library isn't found, we fallback on the
    # `sassc` executable in the path.
    libsass = None
from contextlib import closing
from datetime import datetime
from subprocess import Popen, PIPE
from collections import OrderedDict
from odoo import fields, tools, SUPERUSER_ID
from odoo.tools.pycompat import to_text
from odoo.tools.misc import file_open
from odoo.http import request
from odoo.modules.module import get_resource_path
from .qweb import escape
import psycopg2
from odoo.tools import func, misc

import logging
_logger = logging.getLogger(__name__)

EXTENSIONS = (".js", ".css", ".scss", ".sass", ".less")


class CompileError(RuntimeError): pass
def rjsmin(script):
    """ Minify js with a clever regex.
    Taken from http://opensource.perlig.de/rjsmin (version 1.1.0)
    Apache License, Version 2.0 """
    def subber(match):
        """ Substitution callback """
        groups = match.groups()
        return (
            groups[0] or
            groups[1] or
            (groups[3] and (groups[2] + '\n')) or
            groups[2] or
            (groups[5] and "%s%s%s" % (
                groups[4] and '\n' or '',
                groups[5],
                groups[6] and '\n' or '',
            )) or
            (groups[7] and '\n') or
            (groups[8] and ' ') or
            (groups[9] and ' ') or
            (groups[10] and ' ') or
            ''
        )

    result = re.sub(
        r'([^\047"\140/\000-\040]+)|((?:(?:\047[^\047\\\r\n]*(?:\\(?:[^'
        r'\r\n]|\r?\n|\r)[^\047\\\r\n]*)*\047)|(?:"[^"\\\r\n]*(?:\\(?:[^'
        r'\r\n]|\r?\n|\r)[^"\\\r\n]*)*")|(?:\140[^\140\\]*(?:\\(?:[^\r\n'
        r']|\r?\n|\r)[^\140\\]*)*\140))[^\047"\140/\000-\040]*)|(?<=[(,='
        r':\[!&|?{};\r\n+*-])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*'
        r'\*+(?:[^/*][^*]*\*+)*/))*(?:(?:(?://[^\r\n]*)?[\r\n])(?:[\000-'
        r'\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)*('
        r'(?:/(?![\r\n/*])[^/\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*'
        r'(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\[\r\n]*)*/))((?:[\000-\011'
        r'\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*(?:(?:('
        r'?://[^\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*'
        r']*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000-\040&)+,.:;=?\]|}-]))?|'
        r'(?<=[\000-#%-,./:-@\[-^\140{-~-]return)(?:[\000-\011\013\014\0'
        r'16-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*(?:((?:(?://[^\r'
        r'\n]*)?[\r\n]))(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?'
        r':[^/*][^*]*\*+)*/))*)*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?:(?:\\[^'
        r'\r\n]|(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\[\r'
        r'\n]*)*/))((?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/'
        r'*][^*]*\*+)*/))*(?:(?:(?://[^\r\n]*)?[\r\n])(?:[\000-\011\013'
        r'\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000'
        r'-\040&)+,.:;=?\]|}-]))?|(?<=[^\000-!#%&(*,./:-@\[\\^{|~])(?:['
        r'\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)'
        r')*(?:((?:(?://[^\r\n]*)?[\r\n]))(?:[\000-\011\013\014\016-\040'
        r']|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000-\040"#%-\047'
        r')*,./:-@\\-^\140|-~])|(?<=[^\000-#%-,./:-@\[-^\140{-~-])((?:['
        r'\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)'
        r'))+(?=[^\000-#%-,./:-@\[-^\140{-~-])|(?<=\+)((?:[\000-\011\013'
        r'\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=\+)|(?<'
        r'=-)((?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]'
        r'*\*+)*/)))+(?=-)|(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*'
        r'+(?:[^/*][^*]*\*+)*/))+|(?:(?:(?://[^\r\n]*)?[\r\n])(?:[\000-'
        r'\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+', subber, '\n%s\n' % script
    ).strip()
    return result

class AssetError(Exception):
    pass


class AssetNotFound(AssetError):
    pass


class AssetsBundle(object):
    rx_css_import = re.compile("(@import[^;{]+;?)", re.M)
    rx_preprocess_imports = re.compile("""(@import\s?['"]([^'"]+)['"](;?))""")
    rx_css_split = re.compile("\/\*\! ([a-f0-9-]+) \*\/")

    TRACKED_BUNDLES = ['web.assets_common', 'web.assets_backend']

    def __init__(self, name, files, env=None):
        self.name = name
        self.env = request.env if env is None else env
        self.javascripts = []
        self.stylesheets = []
        self.css_errors = []
        self._checksum = None
        self.files = files
        self.user_direction = self.env['res.lang']._lang_get(
            self.env.context.get('lang') or self.env.user.lang
        ).direction
        for f in files:
            if f['atype'] == 'text/sass':
                self.stylesheets.append(SassStylesheetAsset(self, url=f['url'], filename=f['filename'], inline=f['content'], media=f['media'], direction=self.user_direction))
            elif f['atype'] == 'text/scss':
                self.stylesheets.append(ScssStylesheetAsset(self, url=f['url'], filename=f['filename'], inline=f['content'], media=f['media'], direction=self.user_direction))
            elif f['atype'] == 'text/less':
                self.stylesheets.append(LessStylesheetAsset(self, url=f['url'], filename=f['filename'], inline=f['content'], media=f['media'], direction=self.user_direction))
            elif f['atype'] == 'text/css':
                self.stylesheets.append(StylesheetAsset(self, url=f['url'], filename=f['filename'], inline=f['content'], media=f['media'], direction=self.user_direction))
            elif f['atype'] == 'text/javascript':
                self.javascripts.append(JavascriptAsset(self, url=f['url'], filename=f['filename'], inline=f['content']))

    def to_node(self, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False):
        """
        :returns [(tagName, attributes, content)] if the tag is auto close
        """
        response = []
        if debug and 'assets' in debug:
            if css and self.stylesheets:
                is_css_preprocessed, old_attachments = self.is_css_preprocessed()
                if not is_css_preprocessed:
                    self.preprocess_css(debug=debug, old_attachments=old_attachments)
                    if self.css_errors:
                        msg = '\n'.join(self.css_errors)
                        response.append(JavascriptAsset(self, inline=self.dialog_message(msg)).to_node())
                        response.append(StylesheetAsset(self, url="/web/static/lib/bootstrap/css/bootstrap.css").to_node())
                if not self.css_errors:
                    for style in self.stylesheets:
                        response.append(style.to_node())

            if js:
                for jscript in self.javascripts:
                    response.append(jscript.to_node())
        else:
            if css and self.stylesheets:
                css_attachments = self.css() or []
                for attachment in css_attachments:
                    attr = OrderedDict([
                        ["type", "text/css"],
                        ["rel", "stylesheet"],
                        ["href", attachment.url],
                        ['data-asset-xmlid', self.name],
                        ['data-asset-version', self.version],
                    ])
                    response.append(("link", attr, None))
                if self.css_errors:
                    msg = '\n'.join(self.css_errors)
                    response.append(JavascriptAsset(self, inline=self.dialog_message(msg)).to_node())
            if js and self.javascripts:
                attr = OrderedDict([
                    ["async", "async" if async_load else None],
                    ["defer", "defer" if defer_load or lazy_load else None],
                    ["type", "text/javascript"],
                    ["data-src" if lazy_load else "src", self.js().url],
                    ['data-asset-xmlid', self.name],
                    ['data-asset-version', self.version],
                ])
                response.append(("script", attr, None))

        return response

    @func.lazy_property
    def last_modified(self):
        """Returns last modified date of linked files"""
        return max(itertools.chain(
            (asset.last_modified for asset in self.javascripts),
            (asset.last_modified for asset in self.stylesheets),
        ))

    @func.lazy_property
    def version(self):
        return self.checksum[0:7]

    @func.lazy_property
    def checksum(self):
        """
        Not really a full checksum.
        We compute a SHA512/256 on the rendered bundle + max linked files last_modified date
        """
        check = u"%s%s" % (json.dumps(self.files, sort_keys=True), self.last_modified)
        return hashlib.sha512(check.encode('utf-8')).hexdigest()[:64]

    def _get_asset_template_url(self):
        return "/web/content/{id}-{unique}/{extra}{name}{sep}{type}"

    def _get_asset_url_values(self, id, unique, extra, name, sep, type):  # extra can contain direction or/and website
        return {
            'id': id,
            'unique': unique,
            'extra': extra,
            'name': name,
            'sep': sep,
            'type': type,
        }

    def get_asset_url(self, id='%', unique='%', extra='', name='%', sep="%", type='%'):
        return self._get_asset_template_url().format(
            **self._get_asset_url_values(id=id, unique=unique, extra=extra, name=name, sep=sep, type=type)
        )

    def _unlink_attachments(self, attachments):
        """ Unlinks attachments without actually calling unlink, so that the ORM cache is not cleared.

        Specifically, if an attachment is generated while a view is rendered, clearing the ORM cache
        could unload fields loaded with a sudo(), and expected to be readable by the view.
        Such a view would be website.layout when main_object is an ir.ui.view.
        """
        to_delete = set(attach.store_fname for attach in attachments if attach.store_fname)
        self.env.cr.execute(f"DELETE FROM {attachments._table} WHERE id IN %s", [tuple(attachments.ids)])
        for file_path in to_delete:
            attachments._file_delete(file_path)

    def clean_attachments(self, type):
        """ Takes care of deleting any outdated ir.attachment records associated to a bundle before
        saving a fresh one.

        When `type` is js we need to check that we are deleting a different version (and not *any*
        version) because, as one of the creates in `save_attachment` can trigger a rollback, the
        call to `clean_attachments ` is made at the end of the method in order to avoid the rollback
        of an ir.attachment unlink (because we cannot rollback a removal on the filestore), thus we
        must exclude the current bundle.
        """
        ira = self.env['ir.attachment']
        url = self.get_asset_url(
            extra='%s' % ('rtl/' if type == 'css' and self.user_direction == 'rtl' else ''),
            name=self.name,
            sep='',
            type='.%s' % type
        )
        domain = [
            ('url', '=like', url),
            '!', ('url', '=like', self.get_asset_url(unique=self.version))
        ]
        attachments = ira.sudo().search(domain)
        # avoid to invalidate cache if it's already empty (mainly useful for test)

        if attachments:
            self._unlink_attachments(attachments)
            # force bundle invalidation on other workers
            self.env['ir.qweb'].clear_caches()

        return True

    def get_attachments(self, type, ignore_version=False):
        """ Return the ir.attachment records for a given bundle. This method takes care of mitigating
        an issue happening when parallel transactions generate the same bundle: while the file is not
        duplicated on the filestore (as it is stored according to its hash), there are multiple
        ir.attachment records referencing the same version of a bundle. As we don't want to source
        multiple time the same bundle in our `to_html` function, we group our ir.attachment records
        by file name and only return the one with the max id for each group.
        """
        unique = "%" if ignore_version else self.version
        url_pattern = self.get_asset_url(
            unique=unique,
            extra='%s' % ('rtl/' if type == 'css' and self.user_direction == 'rtl' else ''),
            name=self.name,
            sep='',
            type='.%s' % type
        )
        self.env.cr.execute("""
             SELECT max(id)
               FROM ir_attachment
              WHERE create_uid = %s
                AND url like %s
           GROUP BY name
           ORDER BY name
         """, [SUPERUSER_ID, url_pattern])
        attachment_ids = [r[0] for r in self.env.cr.fetchall()]
        return self.env['ir.attachment'].sudo().browse(attachment_ids)

    def save_attachment(self, type, content):
        assert type in ('js', 'css')
        ira = self.env['ir.attachment']

        # Set user direction in name to store two bundles
        # 1 for ltr and 1 for rtl, this will help during cleaning of assets bundle
        # and allow to only clear the current direction bundle
        # (this applies to css bundles only)
        fname = '%s.%s' % (self.name, type)
        mimetype = 'application/javascript' if type == 'js' else 'text/css'
        values = {
            'name': fname,
            'mimetype': mimetype,
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'raw': content.encode('utf8'),
        }
        attachment = ira.with_user(SUPERUSER_ID).create(values)

        url = self.get_asset_url(
            id=attachment.id,
            unique=self.version,
            extra='%s' % ('rtl/' if type == 'css' and self.user_direction == 'rtl' else ''),
            name=fname,
            sep='',  # included in fname
            type=''
        )
        values = {
            'url': url,
        }
        attachment.write(values)

        if self.env.context.get('commit_assetsbundle') is True:
            self.env.cr.commit()

        self.clean_attachments(type)

        # For end-user assets (common and backend), send a message on the bus
        # to invite the user to refresh their browser
        if self.env and 'bus.bus' in self.env and self.name in self.TRACKED_BUNDLES:
            channel = (self.env.registry.db_name, 'bundle_changed')
            message = (self.name, self.version)
            self.env['bus.bus'].sendone(channel, message)
            _logger.debug('Asset Changed:  xml_id: %s -- version: %s' % message)

        return attachment

    def js(self):
        attachments = self.get_attachments('js')
        if not attachments:
            content = ';\n'.join(asset.minify() for asset in self.javascripts)
            return self.save_attachment('js', content)
        return attachments[0]

    def css(self):
        attachments = self.get_attachments('css')
        if not attachments:
            # get css content
            css = self.preprocess_css()
            if self.css_errors:
                return self.get_attachments('css', ignore_version=True)

            # move up all @import rules to the top
            matches = []
            css = re.sub(self.rx_css_import, lambda matchobj: matches.append(matchobj.group(0)) and '', css)
            matches.append(css)
            css = u'\n'.join(matches)

            self.save_attachment("css", css)
            attachments = self.get_attachments('css')
        return attachments

    def dialog_message(self, message):
        """
        Returns a JS script which shows a warning to the user on page load.
        TODO: should be refactored to be a base js file whose code is extended
              by related apps (web/website).
        """
        return """
            (function (message) {
                'use strict';

                if (window.__assetsBundleErrorSeen) {
                    return;
                }
                window.__assetsBundleErrorSeen = true;

                if (document.readyState !== 'loading') {
                    onDOMContentLoaded();
                } else {
                    window.addEventListener('DOMContentLoaded', () => onDOMContentLoaded());
                }

                async function onDOMContentLoaded() {
                    var odoo = window.top.odoo;
                    if (!odoo || !odoo.define) {
                        useAlert();
                        return;
                    }

                    // Wait for potential JS loading
                    await new Promise(resolve => {
                        const noLazyTimeout = setTimeout(() => resolve(), 10); // 10 since need to wait for promise resolutions of odoo.define
                        odoo.define('AssetsBundle.PotentialLazyLoading', function (require) {
                            'use strict';

                            const lazyloader = require('web.public.lazyloader');

                            clearTimeout(noLazyTimeout);
                            lazyloader.allScriptsLoaded.then(() => resolve());
                        });
                    });

                    var alertTimeout = setTimeout(useAlert, 10); // 10 since need to wait for promise resolutions of odoo.define
                    odoo.define('AssetsBundle.ErrorMessage', function (require) {
                        'use strict';

                        require('web.dom_ready');
                        var core = require('web.core');
                        var Dialog = require('web.Dialog');

                        var _t = core._t;

                        clearTimeout(alertTimeout);
                        new Dialog(null, {
                            title: _t("Style error"),
                            $content: $('<div/>')
                                .append($('<p/>', {text: _t("The style compilation failed, see the error below. Your recent actions may be the cause, please try reverting the changes you made.")}))
                                .append($('<pre/>', {html: message})),
                        }).open();
                    });
                }

                function useAlert() {
                    window.alert(message);
                }
            })("%s");
        """ % message.replace('"', '\\"').replace('\n', '&NewLine;')

    def _get_assets_domain_for_already_processed_css(self, assets):
        """ Method to compute the attachments' domain to search the already process assets (css).
        This method was created to be overridden.
        """
        return [('url', 'in', list(assets.keys()))]

    def is_css_preprocessed(self):
        preprocessed = True
        old_attachments = self.env['ir.attachment'].sudo()
        asset_types = [SassStylesheetAsset, ScssStylesheetAsset, LessStylesheetAsset]
        if self.user_direction == 'rtl':
            asset_types.append(StylesheetAsset)

        for atype in asset_types:
            outdated = False
            assets = dict((asset.html_url, asset) for asset in self.stylesheets if isinstance(asset, atype))
            if assets:
                assets_domain = self._get_assets_domain_for_already_processed_css(assets)
                attachments = self.env['ir.attachment'].sudo().search(assets_domain)
                old_attachments += attachments
                for attachment in attachments:
                    asset = assets[attachment.url]
                    if asset.last_modified > attachment['__last_update']:
                        outdated = True
                        break
                    if asset._content is None:
                        asset._content = (attachment.raw or b'').decode('utf8')
                        if not asset._content and attachment.file_size > 0:
                            asset._content = None # file missing, force recompile

                if any(asset._content is None for asset in assets.values()):
                    outdated = True

                if outdated:
                    preprocessed = False

        return preprocessed, old_attachments

    def preprocess_css(self, debug=False, old_attachments=None):
        """
            Checks if the bundle contains any sass/less content, then compiles it to css.
            If user language direction is Right to Left then consider css files to call run_rtlcss,
            css files are also stored in ir.attachment after processing done by rtlcss.
            Returns the bundle's flat css.
        """
        if self.stylesheets:
            compiled = ""
            for atype in (SassStylesheetAsset, ScssStylesheetAsset, LessStylesheetAsset):
                assets = [asset for asset in self.stylesheets if isinstance(asset, atype)]
                if assets:
                    source = '\n'.join([asset.get_source() for asset in assets])
                    compiled += self.compile_css(assets[0].compile, source)

            # We want to run rtlcss on normal css, so merge it in compiled
            if self.user_direction == 'rtl':
                stylesheet_assets = [asset for asset in self.stylesheets if not isinstance(asset, (SassStylesheetAsset, ScssStylesheetAsset, LessStylesheetAsset))]
                compiled += '\n'.join([asset.get_source() for asset in stylesheet_assets])
                compiled = self.run_rtlcss(compiled)

            if not self.css_errors and old_attachments:
                self._unlink_attachments(old_attachments)
                old_attachments = None

            fragments = self.rx_css_split.split(compiled)
            at_rules = fragments.pop(0)
            if at_rules:
                # Sass and less moves @at-rules to the top in order to stay css 2.1 compatible
                self.stylesheets.insert(0, StylesheetAsset(self, inline=at_rules))
            while fragments:
                asset_id = fragments.pop(0)
                asset = next(asset for asset in self.stylesheets if asset.id == asset_id)
                asset._content = fragments.pop(0)

                if debug:
                    try:
                        fname = os.path.basename(asset.url)
                        url = asset.html_url
                        with self.env.cr.savepoint():
                            self.env['ir.attachment'].sudo().create(dict(
                                raw=asset.content.encode('utf8'),
                                mimetype='text/css',
                                type='binary',
                                name=fname,
                                url=url,
                                res_model=False,
                                res_id=False,
                            ))

                        if self.env.context.get('commit_assetsbundle') is True:
                            self.env.cr.commit()
                    except psycopg2.Error:
                        pass

        return '\n'.join(asset.minify() for asset in self.stylesheets)

    def compile_css(self, compiler, source):
        """Sanitizes @import rules, remove duplicates @import rules, then compile"""
        imports = []
        def handle_compile_error(e, source):
            error = self.get_preprocessor_error(e, source=source)
            _logger.warning(error)
            self.css_errors.append(error)
            return ''
        def sanitize(matchobj):
            ref = matchobj.group(2)
            line = '@import "%s"%s' % (ref, matchobj.group(3))
            if '.' not in ref and line not in imports and not ref.startswith(('.', '/', '~')):
                imports.append(line)
                return line
            msg = "Local import '%s' is forbidden for security reasons. Please remove all @import {your_file} imports in your custom files. In Odoo you have to import all files in the assets, and not through the @import statement." % ref
            _logger.warning(msg)
            self.css_errors.append(msg)
            return ''
        source = re.sub(self.rx_preprocess_imports, sanitize, source)

        compiled = ''
        try:
            compiled = compiler(source)
        except CompileError as e:
            return handle_compile_error(e, source=source)

        compiled = compiled.strip()

        # Post process the produced css to add required vendor prefixes here
        compiled = re.sub(r'(appearance: (\w+);)', r'-webkit-appearance: \2; -moz-appearance: \2; \1', compiled)

        # Most of those are only useful for wkhtmltopdf (some for old PhantomJS)
        compiled = re.sub(r'(display: ((?:inline-)?)flex((?: ?!important)?);)', r'display: -webkit-\2box\3; display: -webkit-\2flex\3; \1', compiled)
        compiled = re.sub(r'(justify-content: flex-(\w+)((?: ?!important)?);)', r'-webkit-box-pack: \2\3; \1', compiled)
        compiled = re.sub(r'(flex-flow: (\w+ \w+);)', r'-webkit-flex-flow: \2; \1', compiled)
        compiled = re.sub(r'(flex-direction: (column);)', r'-webkit-box-orient: vertical; -webkit-box-direction: normal; -webkit-flex-direction: \2; \1', compiled)
        compiled = re.sub(r'(flex-wrap: (\w+);)', r'-webkit-flex-wrap: \2; \1', compiled)
        compiled = re.sub(r'(flex: ((\d)+ \d+ (?:\d+|auto));)', r'-webkit-box-flex: \3; -webkit-flex: \2; \1', compiled)

        return compiled

    def run_rtlcss(self, source):
        rtlcss = 'rtlcss'
        if os.name == 'nt':
            try:
                rtlcss = misc.find_in_path('rtlcss.cmd')
            except IOError:
                rtlcss = 'rtlcss'
        cmd = [rtlcss, '-']


        try:
            rtlcss = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except Exception:

            # Check the presence of rtlcss, if rtlcss not available then we should return normal less file
            try:
                process = Popen(
                    ['rtlcss', '--version'], stdout=PIPE, stderr=PIPE
                )
            except (OSError, IOError):
                _logger.warning('You need https://rtlcss.com/ to convert css file to right to left compatiblity. Use: npm install -g rtlcss')
                return source

            msg = "Could not execute command %r" % cmd[0]
            _logger.error(msg)
            self.css_errors.append(msg)
            return ''

        result = rtlcss.communicate(input=source.encode('utf-8'))
        if rtlcss.returncode:
            cmd_output = ''.join(misc.ustr(result))
            if not cmd_output:
                cmd_output = "Process exited with return code %d\n" % rtlcss.returncode
            error = self.get_rtlcss_error(cmd_output, source=source)
            _logger.warning(error)
            self.css_errors.append(error)
            return ''
        rtlcss_result = result[0].strip().decode('utf8')
        return rtlcss_result

    def get_preprocessor_error(self, stderr, source=None):
        """Improve and remove sensitive information from sass/less compilator error messages"""
        error = misc.ustr(stderr).split('Load paths')[0].replace('  Use --trace for backtrace.', '')
        if 'Cannot load compass' in error:
            error += "Maybe you should install the compass gem using this extra argument:\n\n" \
                     "    $ sudo gem install compass --pre\n"
        error += "This error occured while compiling the bundle '%s' containing:" % self.name
        for asset in self.stylesheets:
            if isinstance(asset, PreprocessedCSS):
                error += '\n    - %s' % (asset.url if asset.url else '<inline sass>')
        return error

    def get_rtlcss_error(self, stderr, source=None):
        """Improve and remove sensitive information from sass/less compilator error messages"""
        error = misc.ustr(stderr).split('Load paths')[0].replace('  Use --trace for backtrace.', '')
        error += "This error occured while compiling the bundle '%s' containing:" % self.name
        return error

class WebAsset(object):
    html_url_format = '%s'
    _content = None
    _filename = None
    _ir_attach = None
    _id = None

    def __init__(self, bundle, inline=None, url=None, filename=None):
        self.bundle = bundle
        self.inline = inline
        self._filename = filename
        self.url = url
        self.html_url_args = url
        if not inline and not url:
            raise Exception("An asset should either be inlined or url linked, defined in bundle '%s'" % bundle.name)

    @func.lazy_property
    def id(self):
        if self._id is None: self._id = str(uuid.uuid4())
        return self._id

    @func.lazy_property
    def name(self):
        name = '<inline asset>' if self.inline else self.url
        return "%s defined in bundle '%s'" % (name, self.bundle.name)

    @property
    def html_url(self):
        return self.html_url_format % self.html_url_args

    def stat(self):
        if not (self.inline or self._filename or self._ir_attach):
            path = (segment for segment in self.url.split('/') if segment)
            self._filename = get_resource_path(*path)
            if self._filename:
                return
            try:
                # Test url against ir.attachments
                attach = self.bundle.env['ir.attachment'].sudo().get_serve_attachment(self.url)
                self._ir_attach = attach[0]
            except Exception:
                raise AssetNotFound("Could not find %s" % self.name)

    def to_node(self):
        raise NotImplementedError()

    @func.lazy_property
    def last_modified(self):
        try:
            self.stat()
            if self._filename:
                return datetime.fromtimestamp(os.path.getmtime(self._filename))
            elif self._ir_attach:
                return self._ir_attach['__last_update']
        except Exception:
            pass
        return datetime(1970, 1, 1)

    @property
    def content(self):
        if self._content is None:
            self._content = self.inline or self._fetch_content()
        return self._content

    def _fetch_content(self):
        """ Fetch content from file or database"""
        try:
            self.stat()
            if self._filename:
                with closing(file_open(self._filename, 'rb', filter_ext=EXTENSIONS)) as fp:
                    return fp.read().decode('utf-8')
            else:
                return base64.b64decode(self._ir_attach['datas']).decode('utf-8')
        except UnicodeDecodeError:
            raise AssetError('%s is not utf-8 encoded.' % self.name)
        except IOError:
            raise AssetNotFound('File %s does not exist.' % self.name)
        except:
            raise AssetError('Could not get content for %s.' % self.name)

    def minify(self):
        return self.content

    def with_header(self, content=None):
        if content is None:
            content = self.content
        return '\n/* %s */\n%s' % (self.name, content)


class JavascriptAsset(WebAsset):
    def minify(self):
        return self.with_header(rjsmin(self.content))

    def _fetch_content(self):
        try:
            return super(JavascriptAsset, self)._fetch_content()
        except AssetError as e:
            return u"console.error(%s);" % json.dumps(to_text(e))

    def to_node(self):
        if self.url:
            return ("script", OrderedDict([
                ["type", "text/javascript"],
                ["src", self.html_url],
                ['data-asset-xmlid', self.bundle.name],
                ['data-asset-version', self.bundle.version],
            ]), None)
        else:
            return ("script", OrderedDict([
                ["type", "text/javascript"],
                ["charset", "utf-8"],
                ['data-asset-xmlid', self.bundle.name],
                ['data-asset-version', self.bundle.version],
            ]), self.with_header())


class StylesheetAsset(WebAsset):
    rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.U)
    rx_url = re.compile(r"""url\s*\(\s*('|"|)(?!'|"|/|https?://|data:)""", re.U)
    rx_sourceMap = re.compile(r'(/\*# sourceMappingURL=.*)', re.U)
    rx_charset = re.compile(r'(@charset "[^"]+";)', re.U)

    def __init__(self, *args, **kw):
        self.media = kw.pop('media', None)
        self.direction = kw.pop('direction', None)
        super(StylesheetAsset, self).__init__(*args, **kw)
        if self.direction == 'rtl' and self.url:
            self.html_url_args = self.url.rsplit('.', 1)
            self.html_url_format = '%%s/%s/%s.%%s' % ('rtl', self.bundle.name)
            self.html_url_args = tuple(self.html_url_args)

    @property
    def content(self):
        content = super(StylesheetAsset, self).content
        if self.media:
            content = '@media %s { %s }' % (self.media, content)
        return content

    def _fetch_content(self):
        try:
            content = super(StylesheetAsset, self)._fetch_content()
            web_dir = os.path.dirname(self.url)

            if self.rx_import:
                content = self.rx_import.sub(
                    r"""@import \1%s/""" % (web_dir,),
                    content,
                )

            if self.rx_url:
                content = self.rx_url.sub(
                    r"url(\1%s/" % (web_dir,),
                    content,
                )

            if self.rx_charset:
                # remove charset declarations, we only support utf-8
                content = self.rx_charset.sub('', content)

            return content
        except AssetError as e:
            self.bundle.css_errors.append(str(e))
            return ''

    def get_source(self):
        content = self.inline or self._fetch_content()
        return "/*! %s */\n%s" % (self.id, content)

    def minify(self):
        # remove existing sourcemaps, make no sense after re-mini
        content = self.rx_sourceMap.sub('', self.content)
        # comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.S)
        # space
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r' *([{}]) *', r'\1', content)
        return self.with_header(content)

    def to_node(self):
        if self.url:
            attr = OrderedDict([
                ["type", "text/css"],
                ["rel", "stylesheet"],
                ["href", self.html_url],
                ["media", escape(to_text(self.media)) if self.media else None],
                ['data-asset-xmlid', self.bundle.name],
                ['data-asset-version', self.bundle.version],
            ])
            return ("link", attr, None)
        else:
            attr = OrderedDict([
                ["type", "text/css"],
                ["media", escape(to_text(self.media)) if self.media else None],
                ['data-asset-xmlid', self.bundle.name],
                ['data-asset-version', self.bundle.version],
            ])
            return ("style", attr, self.with_header())


class PreprocessedCSS(StylesheetAsset):
    rx_import = None

    def __init__(self, *args, **kw):
        super(PreprocessedCSS, self).__init__(*args, **kw)
        self.html_url_args = tuple(self.url.rsplit('/', 1))
        self.html_url_format = '%%s/%s%s/%%s.css' % ('rtl/' if self.direction == 'rtl' else '', self.bundle.name)

    def get_command(self):
        raise NotImplementedError

    def compile(self, source):
        command = self.get_command()
        try:
            compiler = Popen(command, stdin=PIPE, stdout=PIPE,
                             stderr=PIPE)
        except Exception:
            raise CompileError("Could not execute command %r" % command[0])

        (out, err) = compiler.communicate(input=source.encode('utf-8'))
        if compiler.returncode:
            cmd_output = misc.ustr(out) + misc.ustr(err)
            if not cmd_output:
                cmd_output = u"Process exited with return code %d\n" % compiler.returncode
            raise CompileError(cmd_output)
        return out.decode('utf8')

class SassStylesheetAsset(PreprocessedCSS):
    rx_indent = re.compile(r'^( +|\t+)', re.M)
    indent = None
    reindent = '    '

    def minify(self):
        return self.with_header()

    def get_source(self):
        content = textwrap.dedent(self.inline or self._fetch_content())

        def fix_indent(m):
            # Indentation normalization
            ind = m.group()
            if self.indent is None:
                self.indent = ind
                if self.indent == self.reindent:
                    # Don't reindent the file if identation is the final one (reindent)
                    raise StopIteration()
            return ind.replace(self.indent, self.reindent)

        try:
            content = self.rx_indent.sub(fix_indent, content)
        except StopIteration:
            pass
        return "/*! %s */\n%s" % (self.id, content)

    def get_command(self):
        try:
            sass = misc.find_in_path('sass')
        except IOError:
            sass = 'sass'
        return [sass, '--stdin', '-t', 'compressed', '--unix-newlines', '--compass',
                '-r', 'bootstrap-sass']


class ScssStylesheetAsset(PreprocessedCSS):
    @property
    def bootstrap_path(self):
        return get_resource_path('web', 'static', 'lib', 'bootstrap', 'scss')

    precision = 8
    output_style = 'expanded'

    def compile(self, source):
        if libsass is None:
            return super(ScssStylesheetAsset, self).compile(source)

        try:
            return libsass.compile(
                string=source,
                include_paths=[
                    self.bootstrap_path,
                ],
                output_style=self.output_style,
                precision=self.precision,
            )
        except libsass.CompileError as e:
            raise CompileError(e.args[0])

    def get_command(self):
        try:
            sassc = misc.find_in_path('sassc')
        except IOError:
            sassc = 'sassc'
        return [sassc, '--stdin', '--precision', str(self.precision), '--load-path', self.bootstrap_path, '-t', self.output_style]


class LessStylesheetAsset(PreprocessedCSS):
    def get_command(self):
        try:
            if os.name == 'nt':
                lessc = misc.find_in_path('lessc.cmd')
            else:
                lessc = misc.find_in_path('lessc')
        except IOError:
            lessc = 'lessc'
        lesspath = get_resource_path('web', 'static', 'lib', 'bootstrap', 'less')
        return [lessc, '-', '--no-js', '--no-color', '--include-path=%s' % lesspath]
