# -*- coding: utf-8 -*-
import os
import re
import hashlib
import itertools
import json
import textwrap
import operator
import uuid
from datetime import datetime
from subprocess import Popen, PIPE
from odoo import fields, tools
from odoo.http import request
from openerp.tools.translate import xml_translate, _
from odoo.modules.module import get_resource_path
import psycopg2
import werkzeug
from odoo.tools import func, misc

import logging
_logger = logging.getLogger(__name__)

MAX_CSS_RULES = 4095


def rjsmin(script):
    """ Minify js with a clever regex.
    Taken from http://opensource.perlig.de/rjsmin
    Apache License, Version 2.0 """
    def subber(match):
        """ Substitution callback """
        groups = match.groups()
        return (
            groups[0] or
            groups[1] or
            groups[2] or
            groups[3] or
            (groups[4] and '\n') or
            (groups[5] and ' ') or
            (groups[6] and ' ') or
            (groups[7] and ' ') or
            ''
        )

    result = re.sub(
        r'([^\047"/\000-\040]+)|((?:(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?'
        r'\n|\r)[^\047\\\r\n]*)*\047)|(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|'
        r'\r)[^"\\\r\n]*)*"))[^\047"/\000-\040]*)|(?:(?<=[(,=:\[!&|?{};\r\n]'
        r')(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
        r'))*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*'
        r'(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*'
        r'))|(?:(?<=[\000-#%-,./:-@\[-^`{-~-]return)(?:[\000-\011\013\014\01'
        r'6-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*((?:/(?![\r\n/*])[^/'
        r'\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]'
        r'*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*))|(?<=[^\000-!#%&(*,./'
        r':-@\[\\^`{|~])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/'
        r'*][^*]*\*+)*/))*(?:((?:(?://[^\r\n]*)?[\r\n]))(?:[\000-\011\013\01'
        r'4\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000-\040"#'
        r'%-\047)*,./:-@\\-^`|-~])|(?<=[^\000-#%-,./:-@\[-^`{-~-])((?:[\000-'
        r'\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=[^'
        r'\000-#%-,./:-@\[-^`{-~-])|(?<=\+)((?:[\000-\011\013\014\016-\040]|'
        r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=\+)|(?<=-)((?:[\000-\011\0'
        r'13\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=-)|(?:[\0'
        r'00-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))+|(?:'
        r'(?:(?://[^\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*'
        r']*\*+(?:[^/*][^*]*\*+)*/))*)+', subber, '\n%s\n' % script
    ).strip()
    return result


class AssetError(Exception):
    pass


class AssetNotFound(AssetError):
    pass


def utf8(val):
    if isinstance(val, str):
        return val or ''
    return val and unicode(val).encode('utf-8') or ''


class AssetsBundle(object):
    rx_css_import = re.compile("(@import[^;{]+;?)", re.M)
    rx_preprocess_imports = re.compile("""(@import\s?['"]([^'"]+)['"](;?))""")
    rx_css_split = re.compile("\/\*\! ([a-f0-9-]+) \*\/")

    def __init__(self, name, files, remains, env=None):
        self.name = name
        self.env = request.env if env is None else env
        self.max_css_rules = self.env.context.get('max_css_rules', MAX_CSS_RULES)
        self.javascripts = []
        self.stylesheets = []
        self.xmlsheets = []
        self.css_errors = []
        self.remains = []
        self._checksum = None
        self.files = files
        self.remains = remains
        for f in files:
            if f['atype'] == 'text/sass':
                self.stylesheets.append(SassStylesheetAsset(self, url=f['url'], filename=f['filename'], inline=f['content'], media=f['media']))
            elif f['atype'] == 'text/less':
                self.stylesheets.append(LessStylesheetAsset(self, url=f['url'], filename=f['filename'], inline=f['content'], media=f['media']))
            elif f['atype'] == 'text/css':
                self.stylesheets.append(StylesheetAsset(self, url=f['url'], filename=f['filename'], inline=f['content'], media=f['media']))
            elif f['atype'] == 'text/javascript':
                self.javascripts.append(JavascriptAsset(self, url=f['url'], filename=f['filename'], inline=f['content']))
            elif f['atype'] == 'application/xml':
                self.xmlsheets.append(XMLsheetAsset(self, url=f['url'], filename=f['filename']))

    def to_html(self, sep=None, css=True, js=True, xml=True, debug=False, async=False, url_for=(lambda url: url)):
        if sep is None:
            sep = '\n            '
        response = []
        if debug == 'assets':
            if css and self.stylesheets:
                if not self.is_css_preprocessed():
                    self.preprocess_css(debug=debug)
                    if self.css_errors:
                        msg = '\n'.join(self.css_errors)
                        self.stylesheets.append(StylesheetAsset(self, inline=self.css_message(msg)))
                for style in self.stylesheets:
                    response.append(style.to_html())
            if js:
                for jscript in self.javascripts:
                    response.append(jscript.to_html())
                if xml and self.xmlsheets:
                    response.append('<script %s type="text/javascript" src="%s"></script>' % (async and 'async="async"' or '', self.xml(minify=False).url))
        else:
            if css and self.stylesheets:
                css_attachments = self.css()
                if not self.css_errors:
                    for attachment in css_attachments:
                        response.append('<link href="%s" rel="stylesheet"/>' % url_for(attachment.url))
                else:
                    msg = '\n'.join(self.css_errors)
                    self.stylesheets.append(StylesheetAsset(self, inline=self.css_message(msg)))
                    for style in self.stylesheets:
                        response.append(style.to_html())
            if js and self.javascripts:
                response.append('<script %s type="text/javascript" src="%s"></script>' % (async and 'async="async"' or '', url_for(self.js().url)))
            if js and xml and self.xmlsheets:
                response.append('<script %s type="text/javascript" src="%s"></script>' % (async and 'async="async"' or '', self.xml().url))

        response.extend(self.remains)

        return sep + sep.join(response)

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
        We compute a SHA1 on the rendered bundle + max linked files last_modified date
        """
        check = json.dumps(self.files) + ",".join(self.remains) + str(self.last_modified)
        return hashlib.sha1(check).hexdigest()

    def clean_attachments(self, type):
        """ Takes care of deleting any outdated ir.attachment records associated to a bundle before
        saving a fresh one.

        When `type` is css we need to check that we are deleting a different version (and not *any*
        version) because css may be paginated and, therefore, may produce multiple attachments for
        the same bundle's version.

        When `type` is js we need to check that we are deleting a different version (and not *any*
        version) because, as one of the creates in `save_attachment` can trigger a rollback, the
        call to `clean_attachments ` is made at the end of the method in order to avoid the rollback
        of an ir.attachment unlink (because we cannot rollback a removal on the filestore), thus we
        must exclude the current bundle.
        """
        ira = self.env['ir.attachment']
        domain = [
            ('url', '=like', '/web/content/%-%/{0}{1}.{2}'.format(self.name, '%' if type == 'css' else '', type)),  # The wilcards are id, version and pagination number (if any)
            '!', ('url', '=like', '/web/content/%-{}/%'.format(self.version))
        ]
        if type == 'js':
            domain += ['!', ('url', '=like', '/web/content/%.xml.js')]

        return ira.sudo().search(domain).unlink()

    def get_attachments(self, type):
        """ Return the ir.attachment records for a given bundle. This method takes care of mitigating
        an issue happening when parallel transactions generate the same bundle: while the file is not
        duplicated on the filestore (as it is stored according to its hash), there are multiple
        ir.attachment records referencing the same version of a bundle. As we don't want to source
        multiple time the same bundle in our `to_html` function, we group our ir.attachment records
        by file name and only return the one with the max id for each group.
        """
        url_pattern = '/web/content/%-{version}/{name}{add}.{type}'.format(
            version=self.version, name=self.name, add='.%' if type == 'css' else '', type=type)
        req = """
            SELECT max(id)
                FROM ir_attachment
                WHERE url like %%s %s
            GROUP BY datas_fname
            ORDER BY datas_fname
        """ % ("and url not like '%%.xml.js'" if type == 'js' else '')
        self.env.cr.execute(req, (url_pattern,))
        attachment_ids = [r[0] for r in self.env.cr.fetchall()]
        return self.env['ir.attachment'].sudo().browse(attachment_ids)

    def save_attachment(self, type, content, inc=None):
        ira = self.env['ir.attachment']

        fname = '%s%s.%s' % (self.name, ('' if inc is None else '.%s' % inc), type)
        values = {
            'name': "/web/content/%s" % type,
            'datas_fname': fname,
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'datas': utf8(content).encode('base64'),
        }
        attachment = ira.sudo().create(values)

        url = '/web/content/%s-%s/%s' % (attachment.id, self.version, fname)
        values = {
            'name': url,
            'url': url,
        }
        attachment.write(values)

        if self.env.context.get('commit_assetsbundle') is True:
            self.env.cr.commit()

        self.clean_attachments(type)

        return attachment

    def js(self):
        attachments = self.get_attachments('js')
        if not attachments:
            content = ';\n'.join(asset.minify() for asset in self.javascripts)
            return self.save_attachment('js', content)
        return attachments[0]

    def xml_translations(self, modules=None, lang=None):
        if modules is None:
            m = self.env['ir.module.module'].sudo()
            modules = [x['name'] for x in m.search_read([('state', '=', 'installed')], ['name'])]

        res_lang = self.env['res.lang'].sudo()
        langs = res_lang.search([("code", "=", lang)])
        lang_params = None
        if langs:
            lang_params = langs.read(["name", "direction", "date_format", "time_format", "grouping", "decimal_point", "thousands_sep"])[0]

        # Regional languages (ll_CC) must inherit/override their parent lang (ll), but this is
        # done server-side when the language is loaded, so we only need to load the user's lang.
        ir_translation = self.env['ir.translation'].sudo()
        translations_per_module = {}
        domain = [('module', 'in', modules), ('lang', '=', lang), ('type', '=', 'code'),
                  ('comments', 'like', 'openerp-web'), ('name', '=like', '%.xml'), ('value', '!=', '')]
        messages = ir_translation.search_read(domain, ['module', 'src', 'value', 'lang'], order='module')

        for mod, msg_group in itertools.groupby(messages, key=operator.itemgetter('module')):
            translations_per_module.setdefault(mod, {'messages':[]})
            translations_per_module[mod]['messages'].extend({'id': m['src'], 'string': m['value']} for m in msg_group)
        return {
            'lang_parameters': lang_params,
            'modules': translations_per_module,
            'multi_lang': len(res_lang.get_installed()) > 1,
        }

    def xml(self, minify=True):
        lang = self.env.context.get('lang', 'en_US')
        type = '%s.xml.js' % lang
        if not minify:
            type = 'debug.%s' % type

        attachments = self.get_attachments(type)
        if not attachments:
            if minify:
                content = self.xmlsheets[0].to_js(self.name, '\n\n'.join([asset.minify() for asset in self.xmlsheets]))
            else:
                content = '\n'.join(asset.to_js() for asset in self.xmlsheets)

            modules = list(set([asset.url.split("/" if "/static/" in asset.url else ".", 1)[0]
                        for asset in (self.xmlsheets + self.javascripts) if asset.url]))
            if modules:
                js = [
                    'odoo.define("base.ir.translation.%s", function (require) {' % self.name,
                    '"use strict"',
                    'var translation = require("web.translation");',
                    '/* lang: %s, modules: %s */' % (lang, ','.join(modules)),
                    'translation._t.database.set_bundle(%s)' % json.dumps(self.xml_translations(modules, lang)),
                    '});'
                ]
                content = '%s\n\n%s' % (utf8(content), utf8('\n'.join(js)))

            return self.save_attachment(type, content)
        return attachments[0]

    def css(self):
        attachments = self.get_attachments('css')
        if not attachments:
            # get css content
            css = self.preprocess_css()
            if self.css_errors:
                return

            # move up all @import rules to the top
            matches = []
            css = re.sub(self.rx_css_import, lambda matchobj: matches.append(matchobj.group(0)) and '', css)
            matches.append(css)
            css = '\n'.join(matches)

            # split for browser max file size and browser max expression
            re_rules = '([^{]+\{(?:[^{}]|\{[^{}]*\})*\})'
            re_selectors = '()(?:\s*@media\s*[^{]*\{)?(?:\s*(?:[^,{]*(?:,|\{(?:[^}]*\}))))'
            page = []
            pages = [page]
            page_selectors = 0
            for rule in re.findall(re_rules, css):
                selectors = len(re.findall(re_selectors, rule))
                if page_selectors + selectors <= self.max_css_rules:
                    page_selectors += selectors
                    page.append(rule)
                else:
                    pages.append([rule])
                    page = pages[-1]
                    page_selectors = selectors
            for idx, page in enumerate(pages):
                self.save_attachment("css", ' '.join(page), inc=idx)
            attachments = self.get_attachments('css')
        return attachments

    def css_message(self, message):
        # '\A' == css content carriage return
        message = message.replace('\n', '\\A ').replace('"', '\\"')
        return """
            body:before {
                background: #ffc;
                width: 100%%;
                font-size: 14px;
                font-family: monospace;
                white-space: pre;
                content: "%s";
            }
        """ % message

    def is_css_preprocessed(self):
        preprocessed = True
        for atype in (SassStylesheetAsset, LessStylesheetAsset):
            outdated = False
            assets = dict((asset.html_url, asset) for asset in self.stylesheets if isinstance(asset, atype))
            if assets:
                assets_domain = [('url', 'in', assets.keys())]
                attachments = self.env['ir.attachment'].sudo().search(assets_domain)
                for attachment in attachments:
                    asset = assets[attachment.url]
                    if asset.last_modified > fields.Datetime.from_string(attachment['__last_update']):
                        outdated = True
                        break
                    if asset._content is None:
                        asset._content = attachment.datas and attachment.datas.decode('base64').decode('utf8') or ''
                        if not asset._content and attachment.file_size > 0:
                            asset._content = None # file missing, force recompile

                if any(asset._content is None for asset in assets.itervalues()):
                    outdated = True

                if outdated:
                    if attachments:
                        attachments.unlink()
                    preprocessed = False

        return preprocessed

    def preprocess_css(self, debug=False):
        """
            Checks if the bundle contains any sass/less content, then compiles it to css.
            Returns the bundle's flat css.
        """
        for atype in (SassStylesheetAsset, LessStylesheetAsset):
            assets = [asset for asset in self.stylesheets if isinstance(asset, atype)]
            if assets:
                cmd = assets[0].get_command()
                source = '\n'.join([asset.get_source() for asset in assets])
                compiled = self.compile_css(cmd, source)

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
                                    datas=utf8(asset.content).encode('base64'),
                                    mimetype='text/css',
                                    type='binary',
                                    name=url,
                                    url=url,
                                    datas_fname=fname,
                                    res_model=False,
                                    res_id=False,
                                ))

                            if self.env.context.get('commit_assetsbundle') is True:
                                self.env.cr.commit()
                        except psycopg2.Error:
                            pass

        return '\n'.join(asset.minify() for asset in self.stylesheets)

    def compile_css(self, cmd, source):
        """Sanitizes @import rules, remove duplicates @import rules, then compile"""
        imports = []

        def sanitize(matchobj):
            ref = matchobj.group(2)
            line = '@import "%s"%s' % (ref, matchobj.group(3))
            if '.' not in ref and line not in imports and not ref.startswith(('.', '/', '~')):
                imports.append(line)
                return line
            msg = "Local import '%s' is forbidden for security reasons." % ref
            _logger.warning(msg)
            self.css_errors.append(msg)
            return ''
        source = re.sub(self.rx_preprocess_imports, sanitize, source)

        try:
            compiler = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except Exception:
            msg = "Could not execute command %r" % cmd[0]
            _logger.error(msg)
            self.css_errors.append(msg)
            return ''
        result = compiler.communicate(input=source.encode('utf-8'))
        if compiler.returncode:
            error = self.get_preprocessor_error(''.join(result), source=source)
            _logger.warning(error)
            self.css_errors.append(error)
            return ''
        compiled = result[0].strip().decode('utf8')
        return compiled

    def get_preprocessor_error(self, stderr, source=None):
        """Improve and remove sensitive information from sass/less compilator error messages"""
        error = stderr.split('Load paths')[0].replace('  Use --trace for backtrace.', '')
        if 'Cannot load compass' in error:
            error += "Maybe you should install the compass gem using this extra argument:\n\n" \
                     "    $ sudo gem install compass --pre\n"
        error += "This error occured while compiling the bundle '%s' containing:" % self.name
        for asset in self.stylesheets:
            if isinstance(asset, PreprocessedCSS):
                error += '\n    - %s' % (asset.url if asset.url else '<inline sass>')
        return error


class WebAsset(object):
    html_url_format = '%s'
    _content = None
    _filename = None
    _last_update = None
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
        if not (self.inline or self._filename or self._last_update):
            path = filter(None, self.url.split('/'))
            self._filename = get_resource_path(*path)
            if self._filename:
                return
            try:
                # Test url against ir.attachments
                fields = ['__last_update', 'datas', 'mimetype']
                domain = [('type', '=', 'binary'), ('url', '=', self.url)]
                attach = self.bundle.env['ir.attachment'].sudo().search_read(domain, fields)
                self._last_update = attach[0]['__last_update']
                self._content = attach[0]['datas'].decode('base64')
            except Exception:
                raise AssetNotFound("Could not find %s" % self.name)

    def to_html(self):
        raise NotImplementedError()

    @func.lazy_property
    def last_modified(self):
        try:
            self.stat()
            if self._filename:
                return datetime.fromtimestamp(os.path.getmtime(self._filename))
            elif self._last_update:
                server_format = tools.DEFAULT_SERVER_DATETIME_FORMAT
                try:
                    return datetime.strptime(self._last_update, server_format + '.%f')
                except ValueError:
                    return datetime.strptime(self._last_update, server_format)
        except Exception:
            pass
        return datetime(1970, 1, 1)

    @property
    def content(self):
        if self._content is None:
            self._content = self.inline or self._fetch_content()
        return utf8(self._content)

    def _fetch_content(self):
        """ Fetch content from file or database"""
        try:
            self.stat()
            if self._filename:
                with open(self._filename, 'rb') as fp:
                    return fp.read().decode('utf-8')
            else:
                return self._content
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
        except AssetError, e:
            return "console.error(%s);" % json.dumps(e.message)

    def to_html(self):
        if self.url:
            return '<script type="text/javascript" src="%s"></script>' % (self.html_url)
        else:
            return '<script type="text/javascript" charset="utf-8">%s</script>' % self.with_header()


class XMLsheetAsset(WebAsset):
    def __init__(self, *args, **kw):
        super(XMLsheetAsset, self).__init__(*args, **kw)
        if not ((self.url[0] == "/" and "/static/" in self.url) or ("/" not in self.url and "." in self.url)):
            raise AssetError('Wrong XML url "%s", please use a static file with relative path or a template xmlid' % self.url)

    def stat(self):
        if '/static/' in self.url:
            return super(XMLsheetAsset, self).stat()

        module, name = self.url.split('.', 1)
        record = self.bundle.env['ir.model.data'].sudo().get_object(module, name)
        self._last_update = getattr(record, '__last_update')
        self._content = '<t t-name="%s">%s</t>' % (self.url, record.render())

    def _fetch_content(self):
        """ Fetch content from file or database"""
        if '/static/' not in self.url:
            self.stat()
            return self._content

        try:
            datas = super(XMLsheetAsset, self)._fetch_content()
        except AssetError, e:
            return "console.error(%s);" % json.dumps(e.message)

        if not self.bundle.env.context.get('lang'):
            return datas

        trans = {t['src']: t['value'] for t in self.bundle.env['ir.translation'].sudo().search_read(
            [('comments', 'like', 'openerp-web'),
             ('type', '=', 'code'),
             ('name', 'like', self.url),
             ('lang', '=', self.bundle.env.lang)],
            ['src', 'value'], order="value ASC")}

        missing_trans = set()
        def callback(term):
            if trans.get(term):
                return trans[term]
            if term not in trans and re.search(r'\w', term):
                missing_trans.add(term)
            return term
        datas = xml_translate(callback, datas)

        if missing_trans:
            query = """ INSERT INTO ir_translation (lang, type, name, src, value, module, comments)
                        SELECT l.code, 'code', %(name)s, %(src)s, %(src)s, %(module)s, 'openerp-web'
                        FROM res_lang l
                        WHERE l.active AND NOT EXISTS (
                            SELECT 1 FROM ir_translation
                            WHERE lang=l.code AND type='code' AND name=%(name)s AND src=%(src)s AND module=%(module)s
                        );
                    """
            for src in missing_trans:
                self.bundle.env.cr.execute(query, {'name': self.url, 'src': src, 'module': self.url.split("/", 1)[0]})

        return datas

    def with_header(self, content=None):
        if content is None:
            content = self.content
        return '\n<!-- %s -->\n%s' % (self.name, content)

    def minify(self, xml_in=None, pretty=False):
        if xml_in is None:
            xml_in = self.content

        xml = re.sub(r'>', ">~::~", xml_in)
        xml = re.sub(r'<', "~::~<", xml)
        parts = xml.split('~::~')

        indent = "    "
        inComment = False
        inPre = False #pre tag or xml:space="preserve"
        deep = 0
        xml_out = ''

        def addxml(part):
            if inPre:
                return part
            else:
                return (pretty and (len(xml_out) < 2 or xml_out[-2] == ">") and ("\n" + indent * deep) or "") + re.sub(r'\s{1,}', " ", part)

        for key, part in enumerate(parts):
            # start comment or <![CDATA[...]]> or <!DOCTYPE
            if part.find('<!') > -1:
                inComment = True
            # end comment  or <![CDATA[...]]>
            if part[-3:] == '-->' or part[-2:] == ']>' or part[:9] == '<!DOCTYPE':
                inComment = False
                continue
            # remove all comments
            if inComment or not part:
                continue

            if re.search(r'^<[^>]+ t-name=', part):
                xml_out += "\n"

            if part.find('<?xml') > -1 or part.find('<template') > -1 or part.find('</template') > -1:
                continue

            if re.search(r'<pre( |>)', part) or re.search(r'^<[^/](.*[^/])?>$', part) and 'xml:space="preserve"' in part:
                inPre = deep
            if inPre is not False and inPre == deep-1 and part.find('</') > -1:
                inPre = False

            # <? xml ... ?>
            if part.find('<?') > -1:
                xml_out += addxml(part)
            # <elm></elm>
            elif key and re.search(r'^<\w', parts[key-1]) and re.search(r'^<\/\w', part) and \
                    re.search(r'^<[\w:\-\.\,]+', parts[key-1]).group(0) == re.search(r'^<\/[\w:\-\.\,]+', part).group(0).replace('/', ''):

                xml_out += part
                deep -= 1
             # <elm>
            elif re.search(r'<\w', part) and part.find('</') == -1 and part.find('/>') == -1:
                xml_out += addxml(part)
                deep += 1
             # <elm>...</elm>
            elif(re.search(r'<\w', part) and part.find('</') > -1):
                xml_out += addxml(part)
            # </elm>
            elif part.find('</') > -1:
                deep -= 1
                xml_out += addxml(part)
            # <elm/>
            elif part.find('/>') > -1:
                xml_out += addxml(part)
            # space and content in pre
            elif inPre:
                xml_out += part
            # space and content but does not add space if there were none in the template
            else:
                last_is_space = not len(xml_out) or re.search(r'\s', xml_out[-1])
                part = re.sub(r'\s+', " ", part)
                if last_is_space:
                    part = re.sub(r'^\s+', "", part)
                xml_out += part

        return self.with_header(utf8(xml_out))

    def to_js(self, name=None, content=None, with_header=True):
        if name is None:
            name = "%s[%s]" % (self.bundle.name, self.url)
        if content is None:
            content = self.minify(pretty=True)
        js = [
            'odoo.define("base.ir.qweb.%s", function (require) {' % name,
            '"use strict"',
            'var core = require("web.core");',
            'var _t = core._t;',
            'var template = \'<t t-name="%s">\'+' % name,
        ]
        for line in content.split('\n'):
            if not line:
                js.append("")
            elif line[0:4] == "<!--":
                js.append("/*" + line + "*/")
            else:
                js.append("'" + line.replace("\\", "\\\\").replace("'", "\\'") + "\\n'+")
        js += [
            '\'</t>\';',
            'core.qweb.add_template(template);',
            '});'
        ]
        return '\n'.join(js)


class StylesheetAsset(WebAsset):
    rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.U)
    rx_url = re.compile(r"""url\s*\(\s*('|"|)(?!'|"|/|https?://|data:)""", re.U)
    rx_sourceMap = re.compile(r'(/\*# sourceMappingURL=.*)', re.U)
    rx_charset = re.compile(r'(@charset "[^"]+";)', re.U)

    def __init__(self, *args, **kw):
        self.media = kw.pop('media', None)
        super(StylesheetAsset, self).__init__(*args, **kw)

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
        except AssetError, e:
            self.bundle.css_errors.append(e.message)
            return ''

    def minify(self):
        # remove existing sourcemaps, make no sense after re-mini
        content = self.rx_sourceMap.sub('', self.content)
        # comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.S)
        # space
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r' *([{}]) *', r'\1', content)
        return self.with_header(content)

    def to_html(self):
        media = (' media="%s"' % werkzeug.utils.escape(self.media)) if self.media else ''
        if self.url:
            href = self.html_url
            return '<link rel="stylesheet" href="%s" type="text/css"%s/>' % (href, media)
        else:
            return '<style type="text/css"%s>%s</style>' % (media, self.with_header())


class PreprocessedCSS(StylesheetAsset):
    rx_import = None

    def __init__(self, *args, **kw):
        super(PreprocessedCSS, self).__init__(*args, **kw)
        self.html_url_format = '%%s/%s/%%s.css' % self.bundle.name
        self.html_url_args = tuple(self.url.rsplit('/', 1))

    def get_source(self):
        content = self.inline or self._fetch_content()
        return "/*! %s */\n%s" % (self.id, content)

    def get_command(self):
        raise NotImplementedError


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
