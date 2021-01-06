import re

class TranspilerJS:

    def __init__(self, content, url, generate=False):
        super().__init__()
        self.content = content
        self.url = url
        self.define_url = self.get_define_url(url)
        self.generate = generate  # To Remove
        self.comments_mapping = {}
        self.comment_id = 0
        self.strings_mapping = {}
        self.string_id = 0

    def convert(self):
        legacy_odoo_define = self.get_legacy_odoo_define()
        #self.alias_comments()
        #self.alias_strings()
        self.replace_legacy_default_import()
        self.replace_import()
        self.replace_default_import()
        self.replace_relative_imports()
        self.replace_function_and_class_export()
        self.replace_variable_export()
        self.replace_list_export()
        self.replace_default()
        #self.unalias_strings()
        #self.unalias_comments()
        self.add_odoo_def()
        if legacy_odoo_define:
            self.content += legacy_odoo_define

        if self.generate: #To Remove
            with open('generated_test_transpiler_files/' + self.url.split("/")[-1], 'w') as f:
                f.write(self.content)

        return self.content

    def get_define_url(self, url):
        result = re.match(r"\/?(?P<module>\w+)\/[\w\/]*static\/src\/(?P<url>[\w\/]*)", url)
        d = result.groupdict()
        return "@%s/%s" % (d.get('module'), d.get('url'))

    def add_odoo_def(self):
        self.content = f"odoo.define('{self.define_url}', function (require) {{\
                \n'use strict';\
                \nlet __exports = {{}};\
                \n{self.content}\
                \nreturn __exports;\
                \n}});\n"

    # Replace EXPORT
    def replace_function_and_class_export(self, default=False):
        pattern = r"^(?P<space>\s*)export\s+(?P<type>function|class)\s+(?P<identifier>\w+)"
        repl = r"\g<space>const \g<identifier> = __exports.\g<identifier> = \g<type> \g<identifier>"
        if default:
            pattern = r"^(?P<space>\s*)export\s+default\s+(?P<type>function|class)\s+(?P<identifier>\w+)"
            repl = r"\g<space>const \g<identifier> = __exports.__default = \g<type> \g<identifier>"
        p = re.compile(pattern, re.MULTILINE)
        self.content = p.sub(repl, self.content)

    def replace_variable_export(self, default=False):
        pattern = r"^(?P<space>\s*)export\s+(?P<type>let|const|var)\s+(?P<identifier>\w+)\s*="
        repl = r"\g<space>\g<type> \g<identifier> = __exports.\g<identifier> ="
        if default:
            pattern = r"^(?P<space>\s*)export\s+default\s+(?P<type>let|const|var)\s+(?P<identifier>\w+)\s*="
            repl = r"\g<space>\g<type> \g<identifier> = __exports.__default ="
        p = re.compile(pattern, re.MULTILINE)
        self.content = p.sub(repl, self.content)

    def replace_list_export(self):
        p = re.compile(r"^(?P<space>\s*)export\s*(?P<list>{(\s*\w+\s*,?\s*)+}\s*);", re.MULTILINE)
        repl = r"\g<space>__exports = Object.assign(__exports, \g<list>);"
        self.content = p.sub(repl, self.content)

    def replace_default(self):
        self.replace_function_and_class_export(True)
        self.replace_variable_export(True)
        p = re.compile(r'^(?P<space>\s*)export\s+default(\s+\w+\s*=)?', re.MULTILINE)
        repl = r"\g<space>__exports.__default ="
        self.content = p.sub(repl, self.content)

    # Replace IMPORT
    def replace_import(self):
        def repl(matchobj):
            d = matchobj.groupdict()
            new_list = d["list"].replace(" as ", ": ")
            path = d["path"]
            space = d["space"]
            return f"{space}const {new_list} = require({path})"

        p = re.compile(r"^(?P<space>\s*)import\s+(?P<list>{(\s*\w+\s*,?\s*)+})\s*from\s*(?P<path>[^;\n]+)", re.MULTILINE)
        self.content = p.sub(repl, self.content)

    def replace_legacy_default_import(self):
        p = re.compile(r"^(?P<space>\s*)import\s+(?P<identifier>\w+)\s*from\s*[\"\'](?P<path>\w+\.\w+)[\"\']", re.MULTILINE)
        repl = r"""\g<space>const \g<identifier> = require("\g<path>")"""
        self.content = p.sub(repl, self.content)

    def replace_default_import(self):
        p = re.compile(r"^(?P<space>\s*)import\s+(?P<identifier>\w+)\s*from\s*(?P<path>[^;\n]+)", re.MULTILINE)
        repl = r"\g<space>const \g<identifier> = require(\g<path>).__default"
        self.content = p.sub(repl, self.content)

    def replace_relative_imports(self):
        p = re.findall(r"""require\((["'])([^@\"\']+)(["'])\)""", self.content)
        for open, path, close in p:
            if not bool(re.match(r"\w+\.\w+", path)):
                self.content = re.sub(rf"require\({str(open)}{path}{str(close)}\)", f'require("{self.get_full_import_path(path)}")', self.content)

    # def alias_comments(self):
    #     p = re.compile(r"""(?P<comment>(\/\*([^*]|[\r\n]|(\*+([^*\/]|[\r\n])))*\*+\/)|(\/\/(.+?)$))""", flags=re.MULTILINE)

    #     def repl(matchobj):
    #         self.comment_id += 1
    #         string = matchobj.groupdict().get('comment')
    #         self.comments_mapping[self.comment_id] = string
    #         return f"@___comment{{{self.comment_id}}}___@"

    #     self.content = p.sub(repl, self.content)

    # def unalias_comments(self):
    #     p = re.compile(r"""@___comment\{(?P<id>[0-9]+)\}___@""")

    #     def repl(matchobj):
    #         id = int(matchobj.groupdict().get("id"))
    #         return self.comments_mapping[id]

    #     self.content = p.sub(repl, self.content)

    # def alias_strings(self):
    #     p = re.compile(r"""(?P<all>(?P<from>from\s+)?(`.*?`|\".*?\"|'.*?'))""", flags=re.DOTALL)

    #     def repl(matchobj):
    #         has_from = matchobj.groupdict().get('from')
    #         if has_from:
    #             return matchobj.groupdict().get('all')
    #         self.string_id += 1
    #         string = matchobj.groupdict().get('all')
    #         self.strings_mapping[self.string_id] = string
    #         return f"@___string{{{self.string_id}}}___@"

    #     self.content = p.sub(repl, self.content)

    # def unalias_strings(self):
    #     p = re.compile(r"""@___string\{(?P<id>[0-9]+)\}___@""")

    #     def repl(matchobj):
    #         id = int(matchobj.groupdict()["id"])
    #         return self.strings_mapping[id]

    #     self.content = p.sub(repl, self.content)

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

    def get_legacy_odoo_define(self):
        pattern = r"\/\*\*\s+@odoo-module\s+(alias=(?P<alias>\S+))?\s*\*\*\/"
        result = re.match(pattern, self.content)
        if result:
            p = re.compile(pattern)
            d = result.groupdict()
            alias = d.get('alias')
            if alias:
                self.content = p.sub("", self.content)
                return """\nodoo.define(`%s`, function(require) {
                        console.warn("%s is deprecated. Please use %s instead");
                        return require('%s').__default;
                        });\n""" % (alias, alias, self.define_url, self.define_url)
