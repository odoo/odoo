import os
import re
import logging
from lxml import html
from subprocess import Popen, PIPE

import openerp
from openerp.osv import orm
from openerp.tools import which
from openerp.addons.base.ir.ir_qweb import AssetError, JavascriptAsset, QWebException

_logger = logging.getLogger(__name__)


class QWeb_less(orm.AbstractModel):
    _name = "website.qweb"
    _inherit = "website.qweb"

    def render_tag_call_assets(self, element, template_attributes, generated_attributes, qwebcontext):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(element):
            # An asset bundle is rendered in two differents contexts (when genereting html and
            # when generating the bundle itself) so they must be qwebcontext free
            # even '0' variable is forbidden
            template = qwebcontext.get('__template__')
            raise QWebException("t-call-assets cannot contain children nodes", template=template)
        xmlid = template_attributes['call-assets']
        cr, uid, context = [getattr(qwebcontext, attr) for attr in ('cr', 'uid', 'context')]
        bundle = AssetsBundle(xmlid, cr=cr, uid=uid, context=context, registry=self.pool)
        css = self.get_attr_bool(template_attributes.get('css'), default=True)
        js = self.get_attr_bool(template_attributes.get('js'), default=True)
        return bundle.to_html(css=css, js=js, debug=bool(qwebcontext.get('debug')))

    def render_tag_snippet(self, element, template_attributes, generated_attributes, qwebcontext):
        d = qwebcontext.copy()
        d[0] = self.render_element(element, template_attributes, generated_attributes, d)
        cr = d.get('request') and d['request'].cr or None
        uid = d.get('request') and d['request'].uid or None

        template = self.eval_format(template_attributes["snippet"], d)
        elements = html.fragments_fromstring(self.render(cr, uid, template, d))

        id = elements[0].get('data-oe-id', None)
        if id:
            elements[0].set('data-oe-name', self.pool['ir.ui.view'].browse(cr, uid, int(id), context=qwebcontext.context).name)
            elements[0].set('data-oe-type', "snippet")

        elements[0].set('data-oe-thumbnail', template_attributes.get('thumbnail', 'oe-thumbnail'))

        return "".join(map(html.tostring, elements))


class AssetsBundle(openerp.addons.base.ir.ir_qweb.AssetsBundle):
    rx_preprocess_imports = re.compile("""(@import\s?['"]([^'"]+)['"](;?))""")

    def parse(self):
        fragments = html.fragments_fromstring(self.html)
        for el in fragments:
            if isinstance(el, basestring):
                self.remains.append(el)
            elif isinstance(el, html.HtmlElement):
                src = el.get('src', '')
                href = el.get('href', '')
                atype = el.get('type')
                media = el.get('media')
                if el.tag == 'style':
                    if atype == 'text/sass' or src.endswith('.sass'):
                        self.stylesheets.append(SassAsset(self, inline=el.text, media=media))
                    elif atype == 'text/less' or src.endswith('.less'):
                        self.stylesheets.append(LessStylesheetAsset(self, inline=el.text, media=media))
                    else:
                        self.stylesheets.append(StylesheetAsset(self, inline=el.text, media=media))
                elif el.tag == 'link' and el.get('rel') == 'stylesheet' and self.can_aggregate(href):
                    if href.endswith('.sass') or atype == 'text/sass':
                        self.stylesheets.append(SassAsset(self, url=href, media=media))
                    elif href.endswith('.less') or atype == 'text/less':
                        self.stylesheets.append(LessStylesheetAsset(self, url=href, media=media))
                    else:
                        self.stylesheets.append(StylesheetAsset(self, url=href, media=media))
                elif el.tag == 'script' and not src:
                    self.javascripts.append(JavascriptAsset(self, inline=el.text))
                elif el.tag == 'script' and self.can_aggregate(src):
                    self.javascripts.append(JavascriptAsset(self, url=src))
                else:
                    self.remains.append(html.tostring(el))
            else:
                try:
                    self.remains.append(html.tostring(el))
                except Exception:
                    # notYETimplementederror
                    raise NotImplementedError

    def to_html(self, sep=None, css=True, js=True, debug=False):
        if sep is None:
            sep = '\n            '
        response = []
        if debug:
            if css and self.stylesheets:
                self.preprocess_css()
                if self.css_errors:
                    msg = '\n'.join(self.css_errors)
                    self.stylesheets.append(StylesheetAsset(self, inline=self.css_message(msg)))
                for style in self.stylesheets:
                    response.append(style.to_html())
            if js:
                for jscript in self.javascripts:
                    response.append(jscript.to_html())
        else:
            url_for = self.context.get('url_for', lambda url: url)
            if css and self.stylesheets:
                href = '/web/css/%s/%s' % (self.xmlid, self.version)
                response.append('<link href="%s" rel="stylesheet"/>' % url_for(href))
            if js:
                src = '/web/js/%s/%s' % (self.xmlid, self.version)
                response.append('<script type="text/javascript" src="%s"></script>' % url_for(src))
        response.extend(self.remains)
        return sep + sep.join(response)

    def css(self):
        content = self.get_cache('css')
        if content is None:
            content = self.preprocess_css()

            if self.css_errors:
                msg = '\n'.join(self.css_errors)
                content += self.css_message(msg)

            # move up all @import rules to the top
            matches = []

            def push(matchobj):
                matches.append(matchobj.group(0))
                return ''

            content = re.sub(self.rx_css_import, push, content)

            matches.append(content)
            content = u'\n'.join(matches)
            if self.css_errors:
                return content
            self.set_cache('css', content)

        return content

    def set_cache(self, type, content):
        ira = self.registry['ir.attachment']
        ira.invalidate_bundle(self.cr, openerp.SUPERUSER_ID, type=type, xmlid=self.xmlid)
        url = '/web/%s/%s/%s' % (type, self.xmlid, self.version)
        ira.create(self.cr, openerp.SUPERUSER_ID, dict(
                    datas=content.encode('utf8').encode('base64'),
                    type='binary',
                    name=url,
                    url=url,
                ), context=self.context)

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

    def preprocess_css(self):
        """
            Checks if the bundle contains any sass/less content, then compiles it to css.
            Returns the bundle's flat css.
        """
        for atype in (SassAsset, LessStylesheetAsset):
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

        return '\n'.join(asset.minify() for asset in self.stylesheets)

    def compile_sass(self):
        self.preprocess_css()

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
        error += "This error occured while compiling the bundle '%s' containing:" % self.xmlid
        for asset in self.stylesheets:
            if isinstance(asset, (SassAsset, LessStylesheetAsset)):
                error += '\n    - %s' % (asset.url if asset.url else '<inline sass>')
        return error


class StylesheetAsset(openerp.addons.base.ir.ir_qweb.StylesheetAsset):

    @property
    def content(self):
        if self._content is None:
            self._content = self.inline or self._fetch_content()
        return self._content

    def _fetch_content(self):
        try:
            content = openerp.addons.base.ir.ir_qweb.WebAsset._fetch_content(self)
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


class SassAsset(StylesheetAsset, openerp.addons.base.ir.ir_qweb.SassAsset):

    def to_html(self):
        if self.url:
            ira = self.registry['ir.attachment']
            url = self.html_url % self.url
            domain = [('type', '=', 'binary'), ('url', '=', url)]
            ira_id = ira.search(self.cr, openerp.SUPERUSER_ID, domain, context=self.context)
            datas = self.content.encode('utf8').encode('base64')
            if ira_id:
                # TODO: update only if needed
                ira.write(self.cr, openerp.SUPERUSER_ID, ira_id, {'datas': datas}, context=self.context)
            else:
                ira.create(self.cr, openerp.SUPERUSER_ID, dict(
                    datas=datas,
                    mimetype='text/css',
                    type='binary',
                    name=url,
                    url=url,
                ), context=self.context)
        return super(SassAsset, self).to_html()

    def get_command(self):
        defpath = os.environ.get('PATH', os.defpath).split(os.pathsep)
        sass = which('sass', path=os.pathsep.join(defpath))
        return [sass, '--stdin', '-t', 'compressed', '--unix-newlines', '--compass',
                '-r', 'bootstrap-sass']


class LessStylesheetAsset(StylesheetAsset):
    html_url = '%s.css'
    rx_import = None

    def minify(self):
        return self.with_header()

    def to_html(self):
        if self.url:
            ira = self.registry['ir.attachment']
            url = self.html_url % self.url
            domain = [('type', '=', 'binary'), ('url', '=', url)]
            ira_id = ira.search(self.cr, openerp.SUPERUSER_ID, domain, context=self.context)
            datas = self.content.encode('utf8').encode('base64')
            if ira_id:
                # TODO: update only if needed
                ira.write(self.cr, openerp.SUPERUSER_ID, ira_id, {'datas': datas}, context=self.context)
            else:
                ira.create(self.cr, openerp.SUPERUSER_ID, dict(
                    datas=datas,
                    mimetype='text/css',
                    type='binary',
                    name=url,
                    url=url,
                ), context=self.context)
        return super(LessStylesheetAsset, self).to_html()

    def get_source(self):
        content = self.inline or self._fetch_content()
        return "/*! %s */\n%s" % (self.id, content)

    def get_command(self):
        defpath = os.environ.get('PATH', os.defpath).split(os.pathsep)
        if os.name == 'nt':
            lessc = which('lessc.cmd', path=os.pathsep.join(defpath))
        else:
            lessc = which('lessc', path=os.pathsep.join(defpath))
        webpath = openerp.http.addons_manifest['web']['addons_path']
        lesspath = os.path.join(webpath, 'web', 'static', 'lib', 'bootstrap', 'less')
        return [lessc, '-', '--clean-css', '--no-js', '--no-color', '--include-path=%s' % lesspath]
