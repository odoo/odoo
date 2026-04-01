# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import pathlib
import os
import re
import shutil

import odoo.modules
from odoo import api
from .config import config

VERSION = 1
DEFAULT_EXCLUDE = [
    "__manifest__.py",
    "__openerp__.py",
    "tests/**/*",
    "static/lib/**/*",
    "static/tests/**/*",
    "migrations/**/*",
    "upgrades/**/*",
]

STANDARD_MODULES = ['web', 'web_enterprise', 'theme_common', 'base']
MAX_FILE_SIZE = 25 * 2**20 # 25 MB
MAX_LINE_SIZE = 100000
VALID_EXTENSION = ['.py', '.js', '.xml', '.css', '.scss']

class Cloc(object):
    def __init__(self):
        self.modules = {}
        self.code = {}
        self.total = {}
        self.errors = {}
        self.excluded = {}
        self.max_width = 70

    #------------------------------------------------------
    # Parse
    #------------------------------------------------------
    def parse_xml(self, s):
        s = s.strip() + "\n"
        # Unbalanced xml comments inside a CDATA are not supported, and xml
        # comments inside a CDATA will (wrongly) be considered as comment
        total = s.count("\n")
        s = re.sub("(<!--.*?-->)", "", s, flags=re.DOTALL)
        s = re.sub(r"\s*\n\s*", r"\n", s).lstrip()
        return s.count("\n"), total

    def parse_py(self, s):
        try:
            s = s.strip() + "\n"
            total = s.count("\n")
            lines = set()
            for i in ast.walk(ast.parse(s)):
                # we only count 1 for a long string or a docstring
                if hasattr(i, 'lineno'):
                    lines.add(i.lineno)
            return len(lines), total
        except Exception:
            return (-1, "Syntax Error")

    def parse_c_like(self, s, regex):
        # Based on https://stackoverflow.com/questions/241327
        s = s.strip() + "\n"
        total = s.count("\n")
        # To avoid to use too much memory we don't try to count file
        # with very large line, usually minified file
        if max(len(l) for l in s.split('\n')) > MAX_LINE_SIZE:
            return -1, "Max line size exceeded"

        def replacer(match):
            s = match.group(0)
            return " " if s.startswith('/') else s

        comments_re = re.compile(regex, re.DOTALL | re.MULTILINE)
        s = re.sub(comments_re, replacer, s)
        s = re.sub(r"\s*\n\s*", r"\n", s).lstrip()
        return s.count("\n"), total

    def parse_js(self, s):
        return self.parse_c_like(s, r'//.*?$|(?<!\\)/\*.*?\*/|\'(\\.|[^\\\'])*\'|"(\\.|[^\\"])*"')

    def parse_scss(self, s):
        return self.parse_c_like(s, r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"')

    def parse_css(self, s):
        return self.parse_c_like(s, r'/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"')

    def parse(self, s, ext):
        if ext == '.py':
            return self.parse_py(s)
        elif ext == '.js':
            return self.parse_js(s)
        elif ext == '.xml':
            return self.parse_xml(s)
        elif ext == '.css':
            return self.parse_css(s)
        elif ext == '.scss':
            return self.parse_scss(s)

    #------------------------------------------------------
    # Enumeration
    #------------------------------------------------------
    def book(self, module, item='', count=(0, 0), exclude=False):
        if count[0] == -1:
            self.errors.setdefault(module, {})
            self.errors[module][item] = count[1]
        elif exclude and item:
            self.excluded.setdefault(module, {})
            self.excluded[module][item] = count
        else:
            self.modules.setdefault(module, {})
            if item:
                self.modules[module][item] = count
            self.code[module] = self.code.get(module, 0) + count[0]
            self.total[module] = self.total.get(module, 0) + count[1]
            self.max_width = max(self.max_width, len(module), len(item) + 4)

    def count_path(self, path, exclude=None):
        path = path.rstrip('/')
        exclude_list = []
        for i in odoo.modules.module.MANIFEST_NAMES:
            manifest_path = os.path.join(path, i)
            try:
                with open(manifest_path, 'rb') as manifest:
                    exclude_list.extend(DEFAULT_EXCLUDE)
                    d = ast.literal_eval(manifest.read().decode('latin1'))
                    for j in ['cloc_exclude', 'demo', 'demo_xml']:
                        exclude_list.extend(d.get(j, []))
                    break
            except Exception:
                pass
        if not exclude:
            exclude = set()
        for i in filter(None, exclude_list):
            exclude.update(str(p) for p in pathlib.Path(path).glob(i))

        module_name = os.path.basename(path)
        self.book(module_name)
        for root, _dirs, files in os.walk(path):
            for file_name in files:
                file_path = os.path.join(root, file_name)

                if file_path in exclude:
                    continue

                ext = os.path.splitext(file_path)[1].lower()
                if ext not in VALID_EXTENSION:
                    continue

                if os.path.getsize(file_path) > MAX_FILE_SIZE:
                    self.book(module_name, file_path, (-1, "Max file size exceeded"))
                    continue

                with open(file_path, 'rb') as f:
                    # Decode using latin1 to avoid error that may raise by decoding with utf8
                    # The chars not correctly decoded in latin1 have no impact on how many lines will be counted
                    content = f.read().decode('latin1')
                self.book(module_name, file_path, self.parse(content, ext))

    def count_modules(self, env):
        # Exclude standard addons paths
        exclude_path = {
            m.addons_path for name in STANDARD_MODULES
            if (m := odoo.modules.Manifest.for_addon(name, display_warning=False))
        }

        domain = [('state', '=', 'installed')]
        # if base_import_module is present
        if env['ir.module.module']._fields.get('imported'):
            domain.append(('imported', '=', False))
        module_list = env['ir.module.module'].search(domain).mapped('name')

        for module_name in module_list:
            manifest = odoo.modules.Manifest.for_addon(module_name)
            if manifest and manifest.addons_path not in exclude_path:
                self.count_path(manifest.path)

    def count_customization(self, env):
        imported_module_sa = ""
        if env['ir.module.module']._fields.get('imported'):
            imported_module_sa = "OR (m.imported = TRUE AND m.state = 'installed')"
        query = """
                SELECT s.id, min(m.name), array_agg(d.module)
                  FROM ir_act_server AS s
             LEFT JOIN ir_model_data AS d
                    ON (d.res_id = s.id AND d.model = 'ir.actions.server')
             LEFT JOIN ir_module_module AS m
                    ON m.name = d.module
                 WHERE s.state = 'code' AND (m.name IS null {})
              GROUP BY s.id
        """.format(imported_module_sa)
        env.cr.execute(query)
        data = {r[0]: (r[1], r[2]) for r in env.cr.fetchall()}
        for a in env['ir.actions.server'].browse(data.keys()):
            self.book(
                data[a.id][0] or "odoo/studio",
                "ir.actions.server/%s: %s" % (a.id, a.name),
                self.parse_py(a.code),
                '__cloc_exclude__' in data[a.id][1]
            )

        imported_module_field = ("'odoo/studio'", "")
        if env['ir.module.module']._fields.get('imported'):
            imported_module_field = ("min(m.name)", "AND m.imported = TRUE AND m.state = 'installed'")
        # We always want to count manual compute field unless they are generated by studio
        # the module should be odoo/studio unless it comes from an imported module install
        # because manual field get an external id from the original module of the model
        query = r"""
                SELECT f.id, f.name, {}, array_agg(d.module)
                  FROM ir_model_fields AS f
             LEFT JOIN ir_model_data AS d ON (d.res_id = f.id AND d.model = 'ir.model.fields')
             LEFT JOIN ir_module_module AS m ON m.name = d.module {}
                 WHERE f.compute IS NOT null AND f.state = 'manual'
              GROUP BY f.id, f.name
        """.format(*imported_module_field)
        env.cr.execute(query)
        # Do not count field generated by studio
        all_data = env.cr.fetchall()
        data = {r[0]: (r[2], r[3]) for r in all_data if not ("studio_customization" in r[3] and not r[1].startswith('x_studio'))}
        for f in env['ir.model.fields'].browse(data.keys()):
            self.book(
                data[f.id][0] or "odoo/studio",
                "ir.model.fields/%s: %s" % (f.id, f.name),
                self.parse_py(f.compute),
                '__cloc_exclude__' in data[f.id][1]
            )

        if not env['ir.module.module']._fields.get('imported'):
            return

        # Count qweb view only from imported module and not studio
        query = """
            SELECT view.id, min(mod.name), array_agg(data.module)
              FROM ir_ui_view view
        INNER JOIN ir_model_data data ON view.id = data.res_id AND data.model = 'ir.ui.view'
         LEFT JOIN ir_module_module mod ON mod.name = data.module AND mod.imported = True
             WHERE view.type = 'qweb' AND data.module != 'studio_customization'
          GROUP BY view.id
            HAVING count(mod.name) > 0
        """
        env.cr.execute(query)
        custom_views = {r[0]: (r[1], r[2]) for r in env.cr.fetchall()}
        for view in env['ir.ui.view'].browse(custom_views.keys()):
            module_name = custom_views[view.id][0]
            self.book(
                module_name,
                "/%s/views/%s.xml" % (module_name, view.name),
                self.parse_xml(view.arch_base),
                '__cloc_exclude__' in custom_views[view.id][1]
            )

        # Count js, xml, css/scss file from imported module
        query = r"""
            SELECT attach.id, min(mod.name), array_agg(data.module)
              FROM ir_attachment attach
        INNER JOIN ir_model_data data ON attach.id = data.res_id AND data.model = 'ir.attachment'
         LEFT JOIN ir_module_module mod ON mod.name = data.module AND mod.imported = True
             WHERE attach.name ~ '.*\.(js|xml|css|scss)$'
          GROUP BY attach.id
            HAVING count(mod.name) > 0
        """
        env.cr.execute(query)
        uploaded_file = {r[0]: (r[1], r[2]) for r in env.cr.fetchall()}
        for attach in env['ir.attachment'].browse(uploaded_file.keys()):
            module_name = uploaded_file[attach.id][0]
            ext = os.path.splitext(attach.url)[1].lower()
            if ext not in VALID_EXTENSION:
                continue

            if len(attach.datas) > MAX_FILE_SIZE:
                self.book(module_name, attach.url, (-1, "Max file size exceeded"))
                continue

            # Decode using latin1 to avoid error that may raise by decoding with utf8
            # The chars not correctly decoded in latin1 have no impact on how many lines will be counted
            content = attach.raw.decode('latin1')
            self.book(
                module_name,
                attach.url,
                self.parse(content, ext),
                '__cloc_exclude__' in uploaded_file[attach.id][1],
            )

    def count_env(self, env):
        self.count_modules(env)
        self.count_customization(env)

    def count_database(self, database):
        registry = odoo.modules.registry.Registry(database)
        with registry.cursor() as cr:
            uid = api.SUPERUSER_ID
            env = api.Environment(cr, uid, {})
            self.count_env(env)

    #------------------------------------------------------
    # Report
    #------------------------------------------------------
    # pylint: disable=W0141
    def report(self, verbose=False, width=None):
        # Prepare format
        if not width:
            width = min(self.max_width, shutil.get_terminal_size()[0] - 24)
        hr = "-" * (width + 24) + "\n"
        fmt = '{k:%d}{lines:>8}{other:>8}{code:>8}\n' % (width,)

        # Render
        s = fmt.format(k="Odoo cloc", lines="Line", other="Other", code="Code")
        s += hr
        for m in sorted(self.modules):
            s += fmt.format(k=m, lines=self.total[m], other=self.total[m]-self.code[m], code=self.code[m])
            if verbose:
                for i in sorted(self.modules[m], key=lambda i: self.modules[m][i][0], reverse=True):
                    code, total = self.modules[m][i]
                    s += fmt.format(k='    ' + i, lines=total, other=total - code, code=code)
        s += hr
        total = sum(self.total.values())
        code = sum(self.code.values())
        s += fmt.format(k='', lines=total, other=total - code, code=code)
        print(s)

        if self.excluded and verbose:
            ex = fmt.format(k="Excluded", lines="Line", other="Other", code="Code")
            ex += hr
            for m in sorted(self.excluded):
                for i in sorted(self.excluded[m], key=lambda i: self.excluded[m][i][0], reverse=True):
                    code, total = self.excluded[m][i]
                    ex += fmt.format(k='    ' + i, lines=total, other=total - code, code=code)
            ex += hr
            print(ex)

        if self.errors:
            e = "\nErrors\n\n"
            for m in sorted(self.errors):
                e += "{}\n".format(m)
                for i in sorted(self.errors[m]):
                    e += fmt.format(k='    ' + i, lines=self.errors[m][i], other='', code='')
            print(e)
