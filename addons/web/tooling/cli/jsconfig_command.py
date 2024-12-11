import os
import ast
import json
from collections import defaultdict

from . import get_absolute_path, defineCommand, get_tooling, CONFIG, ODOO_PATH

from logging import getLogger
logger = getLogger(__name__)


def get_manifest(path):
    m_path = path.joinpath("__manifest__.py")
    if m_path.is_file():
        with open(m_path, encoding="utf-8") as f:
            return ast.literal_eval(f.read())
    return {}


def process_modules_dependencies(modules):
    module_depends = {}
    repo_depends = defaultdict(set)

    def get_full_depends(module_name):
        if module_name in module_depends:
            return module_depends[module_name]
        depends = set()
        module = modules[module_name]
        for dep in module["depends"]:
            if dep not in modules:
                continue
            repo_depends[module["repo"]].add(modules[dep]["repo"])
            depends.add(dep)
            depends.update(get_full_depends(dep))
        module_depends[module_name] = depends
        return depends

    for name in modules:
        get_full_depends(name)

    return repo_depends, module_depends


def _default_module_filter(path):
    return not path.name.startswith("l10n_") and not path.name.startswith("test_")


def get_odoo_modules(path, filter=_default_module_filter):
    for addon in path.iterdir():
        if not addon.is_dir():
            continue
        if not filter(addon):
            continue
        if not addon.joinpath("__manifest__.py").is_file():
            continue
        yield addon


def get_module_paths_aliases(path, module):
    path = str(path)
    path = path + "/" if path else ""
    if module.joinpath("static/src").is_dir():
        key_src = f"@{module.name}/*"
        src = f"{path}{module.name}/static/src/*"
        yield key_src, [src]
    if module.joinpath("static/tests").is_dir():
        key_test = f"@{module.name}/../tests/*"
        test = f"{path}{module.name}/static/tests/*"
        yield key_test, [test]


def get_repositories(addons_path):
    for path, infos in addons_path.items():
        absolute_path = get_absolute_path(path).resolve()
        yield absolute_path, {"modules": {}}


def get_modules_in_repository(repo_path):
    for module in sorted(get_odoo_modules(repo_path)):
        yield {
            "name": module.name,
            "path": module,
            "repo": repo_path,
            "depends": get_manifest(module).get("depends", [])
        }


def make_js_configs(addons_path):
    odoo_addons = CONFIG["odoo"].joinpath("addons")
    repos = dict()
    all_modules = dict()
    for repo_path, repo_obj in get_repositories(addons_path):
        repos[repo_path] = repo_obj
        for module in get_modules_in_repository(repo_path):
            repo_obj["modules"][module["name"]] = module
            all_modules[module["name"]] = module

    repo_depends, module_depends = process_modules_dependencies(all_modules)
    module_depends = {m: list(k) for m, k in module_depends.items()}

    jsconfig_file = None
    base_jsconfig = get_tooling(ODOO_PATH).joinpath("_jsconfig.json")
    if base_jsconfig.exists():
        with open(base_jsconfig, encoding="utf-8") as f:
            jsconfig_file = f.read()
    if not jsconfig_file:
        jsconfig_json = {
            "compilerOptions": {
                "typeRoots": [],
            },
            "include": [],
            "exclude": [],
        }
        jsconfig_file = json.dumps(jsconfig_json)
    for abs_path, repo in repos.items():
        jsconfig_origin = json.loads(jsconfig_file)
        include = []
        exclude = []
        typeRoots = []

        if abs_path != odoo_addons:
            to_odoo = os.path.relpath(odoo_addons, start=abs_path)
            for p in jsconfig_origin["include"]:
                include.append(to_odoo + "/" + p)
            for p in jsconfig_origin["exclude"]:
                exclude.append(to_odoo + "/" + p)
            for p in jsconfig_origin["compilerOptions"]["typeRoots"]:
                typeRoots.append(to_odoo + "/" + p)
        else:
            include = jsconfig_origin.get("include", [])
            exclude = jsconfig_origin.get("exclude", [])
            typeRoots = jsconfig_origin["compilerOptions"].get("typeRoots", [])

        paths = {}
        for dep_repo_path in (repo_depends[abs_path] or {odoo_addons, abs_path}):
            repo = repos[dep_repo_path]
            if dep_repo_path == abs_path:
                path_prefix = "."
            else:
                path_prefix = os.path.relpath(dep_repo_path, start=abs_path)
            for mname, module in repo["modules"].items():
                paths.update(get_module_paths_aliases(path_prefix, module["path"]))
            if dep_repo_path != odoo_addons:
                include.extend([path_prefix + "/**/*.js", path_prefix + "/**/*.ts"])
                exclude.append(path_prefix + "/**/node_modules")

        jsconfig = {
            "extends": str(get_tooling(ODOO_PATH).joinpath("_jsconfig.json")),
            "compilerOptions": {
                "plugins": [
                    {"name": "odoo-tsserver-dependencies-completion", "depsMap": module_depends}
                ],
                "typeRoots": typeRoots,
                "paths": paths,
            },
            "include": include,
            "exclude": exclude,
        }
        yield abs_path.joinpath("jsconfig.json"), jsconfig


def create_js_configs(addons_path):
    for path, jsconfig in make_js_configs(addons_path):
        with open(path, "w+", encoding="utf-8") as f:
            f.write(json.dumps(jsconfig, indent=2))
        logger.info("Created jsconfig at %s", path)


def remove_js_configs(addons_path):
    for repo_path, repo_obj in get_repositories(addons_path):
        jsconf_file = repo_path.joinpath("jsconfig.json")
        if jsconf_file.exists():
            jsconf_file.unlink()
            logger.info("Removed %s", jsconf_file)
        else:
            logger.info("File %s doesn't exist.", jsconf_file)


@defineCommand
class jsconfig:
    def execute(self, addons_path, operation, args):
        if operation == "install":
            return create_js_configs(addons_path)
        else:
            return remove_js_configs(addons_path)
