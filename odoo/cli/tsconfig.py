import argparse
import glob
import json
import os
import re
import sys

from . import Command
from odoo.modules.module import MANIFEST_NAMES


class TSConfig(Command):
    """Generates tsconfig files for javascript code"""

    def __init__(self):
        self.command_name = "tsconfig"

    def get_module_list(self, path):
        return [
            mod.split(os.path.sep)[-2]
            for mname in MANIFEST_NAMES
            for mod in glob.glob(os.path.join(path, f'*/{mname}'))
        ]

    def clean_path(self, path):
        return re.sub(r"/{2,}", "/", path)

    def prefix_suffix_path(self, path, prefix, suffix):
        return self.clean_path(f"{prefix}/{path}/{suffix}")

    def remove_(self, modules, module):
        for name, path in modules:
            if module == name:
                modules.remove((name, path))

    def run(self, cmdargs):
        parser = argparse.ArgumentParser(
            prog="%s %s" % (sys.argv[0].split(os.path.sep)[-1], self.command_name),
            description=self.__doc__
        )
        parser.add_argument('--addons-path', type=str, nargs=1, dest="paths")
        args = parser.parse_args(args=cmdargs)

        paths = list(map(self.clean_path, args.paths[0].split(',')))
        modules = {}
        for path in paths:
            for module in self.get_module_list(path):
                modules[module] = self.prefix_suffix_path(module, path, "/static/src/*")

        content = self.generate_file_content(modules, paths)
        # pylint: disable=bad-builtin
        print(json.dumps(content, indent=2))

    def generate_imports(self, modules):
        return {
            f'@{module}/*': [path]
            for module, path in modules.items()
        }

    def generate_file_content(self, modules, paths):
        return {
            'compilerOptions': {
                "baseUrl": ".",
                "target": "es2019",
                "checkJs": True,
                "allowJs": True,
                "noEmit": True,
                "typeRoots": list(map(lambda p: p + "/web/tooling/types", paths)),
                "paths": self.generate_imports(modules)
            }, "exclude": self.generate_excludes()
        }

    def generate_excludes(self):
        return [
            "/**/*.po",
            "/**/*.py",
            "/**/*.pyc",
            "/**/*.xml",
            "/**/*.png",
            "/**/*.md",
            "/**/*.dat",
            "/**/*.scss",
            "/**/*.jpg",
            "/**/*.svg",
            "/**/*.pot",
            "/**/*.csv",
            "/**/*.mo",
            "/**/*.txt",
            "/**/*.less",
            "/**/*.bcmap",
            "/**/*.properties",
            "/**/*.html",
            "/**/*.ttf",
            "/**/*.rst",
            "/**/*.css",
            "/**/*.pack",
            "/**/*.idx",
            "/**/*.h",
            "/**/*.map",
            "/**/*.gif",
            "/**/*.sample",
            "/**/*.doctree",
            "/**/*.so",
            "/**/*.pdf",
            "/**/*.xslt",
            "/**/*.conf",
            "/**/*.woff",
            "/**/*.xsd",
            "/**/*.eot",
            "/**/*.jst",
            "/**/*.flow",
            "/**/*.sh",
            "/**/*.yml",
            "/**/*.pfb",
            "/**/*.jpeg",
            "/**/*.crt",
            "/**/*.template",
            "/**/*.pxd",
            "/**/*.dylib",
            "/**/*.pem",
            "/**/*.rng",
            "/**/*.xsl",
            "/**/*.xls",
            "/**/*.cfg",
            "/**/*.pyi",
            "/**/*.pth",
            "/**/*.markdown",
            "/**/*.key",
            "/**/*.ico",
        ]
