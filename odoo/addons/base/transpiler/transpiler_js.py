import re

class TranspilerJS:

    def __init__(self, content, url, generate = False):
        super().__init__()
        self.content = content
        self.url = url
        self.generate = generate
        self.comments_mapping = {}
        self.comment_id = 0
        self.strings_mapping = {}
        self.string_id = 0

    def convert(self):
        new_content = self.content
        new_content, legacy_odoo_define = self.get_legacy_odoo_define(new_content, self.url)
        new_content = self.alias_strings(new_content)
        new_content = self.alias_comments(new_content)
        new_content = self.replace_legacy_default_import(new_content)
        new_content = self.replace_import(new_content)
        new_content = self.replace_default_import(new_content)
        new_content = self.replace_relative_imports(new_content)
        new_content = self.replace_function_and_class_export(new_content)
        new_content = self.replace_variable_export(new_content)
        new_content = self.replace_list_export(new_content)
        new_content = self.replace_default(new_content)
        new_content = self.unalias_comments(new_content)
        new_content = self.unalias_strings(new_content)
        new_content = self.add_odoo_def(new_content, self.url)
        if legacy_odoo_define:
            new_content += legacy_odoo_define

        if self.generate:
            with open('generated_test_transpiler_files/' + self.url.split("/")[-1], 'w') as f:
                f.write(new_content)

        return new_content

    def get_define_url(self, url):
        result = re.match(r"\/?(?P<module>\w+)\/[\w\/]*static\/src\/(?P<url>[\w\/]*)", url)
        d = result.groupdict()
        return "@%s/%s" % (d.get('module'), d.get('url'))

    def add_odoo_def(self, content, url):
        return f"odoo.define('{self.get_define_url(url)}', function (require) {{\
                \n'use strict';\
                \nlet __exports = {{}};\
                \n{content}\
                \nreturn __exports;\
                \n}});\n"

    def replace_function_and_class_export(self, content, default=False):
        pattern = r"export\s+(?P<type>function|class)\s+(?P<identifier>\w+)"
        repl = r"const \g<identifier> = __exports.\g<identifier> = \g<type> \g<identifier>"
        if default:
            pattern = r"export\s+default\s+(?P<type>function|class)\s+(?P<identifier>\w+)"
            repl = r"const \g<identifier> = __exports.__default = \g<type> \g<identifier>"
        p = re.compile(pattern)
        return p.sub(repl, content)

    def replace_variable_export(self, content, default=False):
        p = re.compile(r"export\s+(?P<type>let|const|var)\s+(?P<identifier>\w+)\s*=")
        repl = r"\g<type> \g<identifier> = __exports.\g<identifier> ="
        if default:
            p = re.compile(r"export\s+default\s+(?P<type>let|const|var)\s+(?P<identifier>\w+)\s*=")
            repl = r"\g<type> \g<identifier> = __exports.__default ="
        return p.sub(repl, content)

    def replace_list_export(self, content):
        p = re.compile(r"export\s*(?P<list>{(\s*\w+\s*,?\s*)+}\s*);")
        repl = r"__exports = Object.assign(__exports, \g<list>);"
        return p.sub(repl, content)

    def replace_import(self, content):

        def repl(matchobj):
            d = matchobj.groupdict()
            new_list = d["list"].replace(" as ", ": ")
            path = d["path"]
            return f"const {new_list} = require({path})"

        p = re.compile(r"import\s+(?P<list>{(\s*\w+\s*,?\s*)+})\s*from\s*(?P<path>[^;\n]+)")
        return p.sub(repl, content)

    def replace_legacy_default_import(self, content):
        p = re.compile(r"import\s+(?P<identifier>\w+)\s*from\s*[\"\'](?P<path>\w+\.\w+)[\"\']")
        repl = r"""const \g<identifier> = require("\g<path>")"""
        return p.sub(repl, content)

    def replace_default_import(self, content):
        p = re.compile(r"import\s+(?P<identifier>\w+)\s*from\s*(?P<path>[^;\n]+)")
        repl = r"const \g<identifier> = require(\g<path>).__default"
        return p.sub(repl, content)

    def replace_relative_imports(self, content):
        p = re.findall(r"""require\((["'])([^@\"\']+)(["'])\)""", content)
        for open, path, close in p:
            if not bool(re.match(r"\w+\.\w+", path)):
                content = re.sub(rf"require\({str(open)}{path}{str(close)}\)", f'require("{self.get_full_import_path(path)}")', content)
        return content

    def alias_comments(self, content):
        p = re.compile(r"""(?P<comment>(\/\*([^*]|[\r\n]|(\*+([^*\/]|[\r\n])))*\*+\/)|(\/\/(.+?)$))""", flags=re.MULTILINE)

        def repl(matchobj):
            self.comment_id += 1
            string = matchobj.groupdict().get('comment')
            self.comments_mapping[self.comment_id] = string
            return f"@___comment{{{self.comment_id}}}___@"

        result = p.sub(repl, content)
        return result


    def unalias_comments(self, content):
        p = re.compile(r"""@___comment\{(?P<id>[0-9]+)\}___@""")

        def repl(matchobj):
            id = int(matchobj.groupdict().get("id"))
            return self.comments_mapping[id]

        result = p.sub(repl, content)
        return result

    def alias_strings(self, content):
        p = re.compile(r"""(?P<all>(?P<from>from\s+)?(`.*?`|\".*?\"|'.*?'))""", flags=re.DOTALL)

        def repl(matchobj):
            has_from = matchobj.groupdict().get('from')
            if has_from:
                return matchobj.groupdict().get('all')
            self.string_id += 1
            string = matchobj.groupdict().get('all')
            self.strings_mapping[self.string_id] = string
            return f"@___string{{{self.string_id}}}___@"

        return p.sub(repl, content)

    def unalias_strings(self, content):
        p = re.compile(r"""@___string\{(?P<id>[0-9]+)\}___@""")

        def repl(matchobj):
            id = int(matchobj.groupdict()["id"])
            return self.strings_mapping[id]

        return p.sub(repl, content)

    def replace_default(self, content):
        new_content = self.replace_function_and_class_export(content, True)
        new_content = self.replace_variable_export(new_content, True)
        p = re.compile(r'export\s+default(\s+\w+\s*=)?')
        repl = r"__exports.__default ="
        return p.sub(repl, new_content)

    def get_full_import_path(self, path_rel):
        url_split = self.url.split("/")
        path_rel_split = path_rel.split("/")
        nb_back = len([v for v in path_rel_split if v == ".."]) + 1
        result = "/".join(url_split[:-nb_back] + [v for v in path_rel_split if not v in ["..", "."]])
        return self.get_define_url(result)

    @staticmethod
    def is_odoo_module(content):
        result = re.match(r"\/\*\*\s+@odoo-module\s+(alias=(?P<alias>\S+))?\s*\*\*\/", content)
        return bool(result)

    def get_legacy_odoo_define(self, content, url):
        define_url = self.get_define_url(url)
        pattern = r"\/\*\*\s+@odoo-module\s+(alias=(?P<alias>\S+))?\s*\*\*\/"
        result = re.match(pattern, content)
        if bool(result):
            p = re.compile(pattern)
            d = result.groupdict()
            alias = d.get('alias')
            if alias:
                return p.sub("", content), """\nodoo.define(`%s`, function(require) {
                        console.warn("%s is deprecated. Please use %s instead");
                        return require('%s').__default;
                        });\n""" % (alias, alias,  define_url, define_url)

        return content, False
