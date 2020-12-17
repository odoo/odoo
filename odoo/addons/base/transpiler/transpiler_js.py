import re

class TranspilerJS:

    def __init__(self, content, url, generate = False):
        super().__init__()
        self.content = content
        self.url = url
        self.generate = generate

    def convert(self):
        new_content = self.content
        legacy_odoo_define = self.get_legacy_odoo_define(new_content, self.url)
        new_content = self.remove_comment(new_content)
        new_content = self.replace_legacy_default_import(new_content)
        new_content = self.replace_import(new_content)
        new_content = self.replace_default_import(new_content)
        new_content = self.replace_relative_imports(new_content)
        new_content = self.replace_function_and_class_export(new_content)
        new_content = self.replace_variable_export(new_content)
        new_content = self.replace_list_export(new_content)
        new_content = self.replace_default(new_content)
        new_content = self.add_odoo_def(new_content, self.url)
        if legacy_odoo_define:
            new_content += legacy_odoo_define

        if self.generate:
            with open('generated_test_transpiler_files/' + self.url.split("/")[-1], 'w') as f:
                f.write(new_content)

        return new_content

    def get_define_url(self, url):
        result = re.match(r"\/?(?P<module>\w+)\/[\w\/]*js\/(?P<url>[\w\/]*)", url)
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
        # class_or_function = re.findall(pattern, content)
        # new_content = content + "\n" + "\n".join([f"__exports.{name[1]} = {name[1]};" for name in class_or_function])

        # if default:
        #     new_content = content + "\n" + "\n".join([f"__exports.__default = {name[1]};" for name in class_or_function])
        # p = re.compile(pattern)
        # repl = r"\g<type> \g<identifier>"
        # return p.sub(repl, new_content)
        p = re.compile(pattern)
        return p.sub(repl, content)

    def replace_variable_export(self, content, default=False):
        # pattern = r"export\s+(?P<type>let|const|var)\s+(?P<identifier>\w+)\s*="
        # variables = re.findall(pattern, content)
        # new_content = content + "\n" + "\n".join([f"__exports.{name[1]} = {name[1]};" for name in variables])

        # p = re.compile(pattern)
        # repl = r"\g<type> \g<identifier> ="
        # return p.sub(repl, new_content)
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

    def remove_comment(self, content):
        # first we remove the slashes in strings
        p = re.compile(r"""([\"'`].*/.*[\"'`])""")

        def repl(matchobj):
            string = matchobj.group(0)
            return string.replace('/', "@___slash___@")

        new_content = p.sub(repl, content)

        # We remove the comments
        p = re.compile(r'(\/\*([^*]|[\r\n]|(\*+([^*\/]|[\r\n])))*\*+\/)|(\/\/(.+?)$)', flags=re.MULTILINE)
        repl = r""
        new_content = p.sub(repl, new_content)

        # We add the slashes in strings
        return new_content.replace("@___slash___@", '/')

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

    def get_legacy_odoo_define(self, content, url):
        define_url = self.get_define_url(url)
        result = re.match(r"\/\*\*\s+odoo-alias\s*(?P<default>default)?\s+(?P<alias>\S+)\s*\*\*\/", content)
        if bool(result):
            d = result.groupdict()
            alias = d['alias']
            default = ".__default" if d.get('default') else ""
            return """\nodoo.define(`%s`, function(require) {
                    console.warn("%s is deprecated. Please use %s instead");
                    return require('%s')%s;
                    });\n""" % (alias, alias,  define_url, define_url, default)
