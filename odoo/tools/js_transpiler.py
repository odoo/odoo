"""
This code is what let us use ES6-style modules in odoo.
Classic Odoo modules are composed of a top-level :samp:`odoo.define({name},{dependencies},{body_function})` call.
This processor will take files starting with an `@odoo-module` annotation (in a comment) and convert them to classic modules.
If any file has the ``/** odoo-module */`` on top of it, it will get processed by this class.
It performs several operations to get from ES6 syntax to the usual odoo one with minimal changes.
This is done on the fly, this not a pre-processing tool.

Caveat: This is done without a full parser, only using regex. One can only expect to cover as much edge cases
as possible with reasonable limitations. Also, this only changes imports and exports, so all JS features used in
the original source need to be supported by the browsers.
"""

import re
import logging
from functools import partial

from odoo.tools.misc import OrderedSet

_logger = logging.getLogger(__name__)

def transpile_javascript(url, content):
    """
    Transpile the code from native JS modules to custom odoo modules.

    :param content: The original source code
    :param url: The url of the file in the project
    :return: The transpiled source code
    """
    module_path = url_to_module_path(url)
    legacy_odoo_define = get_aliased_odoo_define_content(module_path, content)
    dependencies = OrderedSet()
    # The order of the operations does sometimes matter.
    steps = [
        convert_legacy_default_import,
        convert_basic_import,
        convert_default_and_named_import,
        convert_default_and_star_import,
        convert_default_import,
        convert_star_import,
        convert_unnamed_relative_import,
        convert_from_export,
        convert_star_from_export,
        remove_index,
        partial(convert_relative_require, url, dependencies),
        convert_export_function,
        convert_export_class,
        convert_variable_export,
        convert_object_export,
        convert_default_export,
        partial(wrap_with_qunit_module, url),
        partial(wrap_with_odoo_define, module_path, dependencies),
    ]
    for s in steps:
        content = s(content)
    if legacy_odoo_define:
        content += legacy_odoo_define
    return content


URL_RE = re.compile(r"""
    /?(?P<module>\S+)    # /module name
    /([\S/]*/)?static/   # ... /static/
    (?P<type>src|tests|lib)  # src, test, or lib file
    (?P<url>/[\S/]*)     # URL (/...)
    """, re.VERBOSE)


def url_to_module_path(url):
    """
    Odoo modules each have a name. (odoo.define("<the name>", [<dependencies>], function (require) {...});
    It is used in to be required later. (const { something } = require("<the name>").
    The transpiler transforms the url of the file in the project to this name.
    It takes the module name and add a @ on the start of it, and map it to be the source of the static/src (or
    static/tests, or static/lib) folder in that module.

    in: web/static/src/one/two/three.js
    out: @web/one/two/three.js
    The module would therefore be defined and required by this path.

    :param url: an url in the project
    :return: a special path starting with @<module-name>.
    """
    match = URL_RE.match(url)
    if match:
        url = match["url"]
        if url.endswith(('/index.js', '/index')):
            url, _ = url.rsplit('/', 1)
        if url.endswith('.js'):
            url = url[:-3]
        if match["type"] == "src":
            return "@%s%s" % (match['module'], url)
        elif match["type"] == "lib":
            return "@%s/../lib%s" % (match['module'], url)
        else:
            return "@%s/../tests%s" % (match['module'], url)
    else:
        raise ValueError("The js file %r must be in the folder '/static/src' or '/static/lib' or '/static/test'" % url)

def wrap_with_qunit_module(url, content):
    """
    Wraps the test file content (source code) with the QUnit.module('module_name', function() {...}).
    """
    if "tests" in url and re.search(r'QUnit\.(test|debug|only)\(', content):
        match = URL_RE.match(url)
        return f"""QUnit.module("{match["module"]}", function() {{{content}}});"""
    else:
        return content

def wrap_with_odoo_define(module_path, dependencies, content):
    """
    Wraps the current content (source code) with the odoo.define call.
    It adds as a second argument the list of dependencies.
    Should logically be called once all other operations have been performed.
    """
    return f"""odoo.define({module_path!r}, {list(dependencies)}, function (require) {{
'use strict';
let __exports = {{}};
{content}
return __exports;
}});
"""


EXPORT_FCT_RE = re.compile(r"""
    ^
    (?P<space>\s*)                          # space and empty line
    export\s+                               # export
    (?P<type>(async\s+)?function)\s+        # async function or function
    (?P<identifier>\w+)                     # name the function
    """, re.MULTILINE | re.VERBOSE)


def convert_export_function(content):
    """
    Transpile functions that are being exported.

    .. code-block:: javascript

        // before
        export function name
        // after
       __exports.name = name; function name

        // before
        export async function name
        // after
        __exports.name = name; async function name

    """
    repl = r"\g<space>__exports.\g<identifier> = \g<identifier>; \g<type> \g<identifier>"
    return EXPORT_FCT_RE.sub(repl, content)

EXPORT_CLASS_RE = re.compile(r"""
    ^
    (?P<space>\s*)                          # space and empty line
    export\s+                               # export
    (?P<type>class)\s+                      # class
    (?P<identifier>\w+)                     # name of the class
    """, re.MULTILINE | re.VERBOSE)


def convert_export_class(content):
    """
    Transpile classes that are being exported.

    .. code-block:: javascript

        // before
        export class name
        // after
        const name = __exports.name = class name

    """
    repl = r"\g<space>const \g<identifier> = __exports.\g<identifier> = \g<type> \g<identifier>"
    return EXPORT_CLASS_RE.sub(repl, content)


EXPORT_FCT_DEFAULT_RE = re.compile(r"""
    ^
    (?P<space>\s*)                          # space and empty line
    export\s+default\s+                     # export default
    (?P<type>(async\s+)?function)\s+        # async function or function
    (?P<identifier>\w+)                     # name of the function
    """, re.MULTILINE | re.VERBOSE)


def convert_export_function_default(content):
    """
    Transpile functions that are being exported as default value.

    .. code-block:: javascript

        // before
        export default function name
        // after
        __exports[Symbol.for("default")] = name; function name

        // before
        export default async function name
        // after
        __exports[Symbol.for("default")] = name; async function name

    """
    repl = r"""\g<space>__exports[Symbol.for("default")] = \g<identifier>; \g<type> \g<identifier>"""
    return EXPORT_FCT_DEFAULT_RE.sub(repl, content)

EXPORT_CLASS_DEFAULT_RE = re.compile(r"""
    ^
    (?P<space>\s*)                          # space and empty line
    export\s+default\s+                     # export default
    (?P<type>class)\s+                      # class
    (?P<identifier>\w+)                     # name of the class or the function
    """, re.MULTILINE | re.VERBOSE)


def convert_export_class_default(content):
    """
    Transpile classes that are being exported as default value.

    .. code-block:: javascript

        // before
        export default class name
        // after
        const name = __exports[Symbol.for("default")] = class name

    """
    repl = r"""\g<space>const \g<identifier> = __exports[Symbol.for("default")] = \g<type> \g<identifier>"""
    return EXPORT_CLASS_DEFAULT_RE.sub(repl, content)

EXPORT_VAR_RE = re.compile(r"""
    ^
    (?P<space>\s*)              # space and empty line
    export\s+                   # export
    (?P<type>let|const|var)\s+  # let or cont or var
    (?P<identifier>\w+)         # variable name
    """, re.MULTILINE | re.VERBOSE)


def convert_variable_export(content):
    """
    Transpile variables that are being exported.

    .. code-block:: javascript

        // before
        export let name
        // after
        let name = __exports.name
        // (same with var and const)

    """
    repl = r"\g<space>\g<type> \g<identifier> = __exports.\g<identifier>"
    return EXPORT_VAR_RE.sub(repl, content)


EXPORT_DEFAULT_VAR_RE = re.compile(r"""
    ^
    (?P<space>\s*)              # space and empty line
    export\s+default\s+         # export default
    (?P<type>let|const|var)\s+  # let or const or var
    (?P<identifier>\w+)\s*      # variable name
    """, re.MULTILINE | re.VERBOSE)


def convert_variable_export_default(content):
    """
    Transpile the variables that are exported as default values.

    .. code-block:: javascript

        // before
        export default let name
        // after
        let name = __exports[Symbol.for("default")]

    """
    repl = r"""\g<space>\g<type> \g<identifier> = __exports[Symbol.for("default")]"""
    return EXPORT_DEFAULT_VAR_RE.sub(repl, content)


EXPORT_OBJECT_RE = re.compile(r"""
    ^
    (?P<space>\s*)                      # space and empty line
    export\s*                           # export
    (?P<object>{[\w\s,]+})              # { a, b, c as x, ... }
    """, re.MULTILINE | re.VERBOSE)


def convert_object_export(content):
    """
    Transpile exports of multiple elements

    .. code-block:: javascript

        // before
        export { a, b, c as x }
        // after
        Object.assign(__exports, { a, b, x: c })
    """
    def repl(matchobj):
        object_process = "{" + ", ".join([convert_as(val) for val in matchobj["object"][1:-1].split(",")]) + "}"
        space = matchobj["space"]
        return f"{space}Object.assign(__exports, {object_process})"
    return EXPORT_OBJECT_RE.sub(repl, content)


EXPORT_FROM_RE = re.compile(r"""
    ^
    (?P<space>\s*)                      # space and empty line
    export\s*                           # export
    (?P<object>{[\w\s,]+})\s*           # { a, b, c as x, ... }
    from\s*                             # from
    (?P<path>(?P<quote>["'`])([^"'`]+)(?P=quote))   # "file path" ("some/path.js")
    """, re.MULTILINE | re.VERBOSE)


def convert_from_export(content):
    """
    Transpile exports coming from another source

    .. code-block:: javascript

        // before
        export { a, b, c as x } from "some/path.js"
        // after
        { a, b, c } = {require("some/path.js"); Object.assign(__exports, { a, b, x: c });}
    """
    def repl(matchobj):
        object_clean = "{" + ",".join([remove_as(val) for val in matchobj["object"][1:-1].split(",")]) + "}"
        object_process = "{" + ", ".join([convert_as(val) for val in matchobj["object"][1:-1].split(",")]) + "}"
        return "%(space)s{const %(object_clean)s = require(%(path)s);Object.assign(__exports, %(object_process)s)}" % {
            'object_clean': object_clean,
            'object_process': object_process,
            'space': matchobj['space'],
            'path': matchobj['path'],
        }
    return EXPORT_FROM_RE.sub(repl, content)


EXPORT_STAR_FROM_RE = re.compile(r"""
    ^
    (?P<space>\s*)                      # space and empty line
    export\s*\*\s*from\s*               # export * from
    (?P<path>(?P<quote>["'`])([^"'`]+)(?P=quote))   # "file path" ("some/path.js")
    """, re.MULTILINE | re.VERBOSE)


def convert_star_from_export(content):
    """
    Transpile exports star coming from another source

    .. code-block:: javascript

        // before
        export * from "some/path.js"
        // after
        Object.assign(__exports, require("some/path.js"))
    """
    repl = r"\g<space>Object.assign(__exports, require(\g<path>))"
    return EXPORT_STAR_FROM_RE.sub(repl, content)


EXPORT_DEFAULT_RE = re.compile(r"""
    ^
    (?P<space>\s*)      # space and empty line
    export\s+default    # export default
    (\s+\w+\s*=)?       # something (optional)
    """, re.MULTILINE | re.VERBOSE)


def convert_default_export(content):
    """
    This function handles the default exports.
    Either by calling another operation with a TRUE flag, and if any default is left, doing a simple replacement.

    (see convert_export_function_or_class_default and convert_variable_export_default).
    +
    .. code-block:: javascript

        // before
        export default
        // after
        __exports[Symbol.for("default")] =

    .. code-block:: javascript

        // before
        export default something =
        // after
        __exports[Symbol.for("default")] =
    """
    new_content = convert_export_function_default(content)
    new_content = convert_export_class_default(new_content)
    new_content = convert_variable_export_default(new_content)
    repl = r"""\g<space>__exports[Symbol.for("default")] ="""
    return EXPORT_DEFAULT_RE.sub(repl, new_content)


IMPORT_BASIC_RE = re.compile(r"""
    ^
    (?P<space>\s*)                      # space and empty line
    import\s+                           # import
    (?P<object>{[\s\w,]+})\s*           # { a, b, c as x, ... }
    from\s*                             # from
    (?P<path>(?P<quote>["'`])([^"'`]+)(?P=quote))   # "file path" ("some/path")
    """, re.MULTILINE | re.VERBOSE)


def convert_basic_import(content):
    """
    Transpile the simpler import call.

    .. code-block:: javascript

        // before
        import { a, b, c as x } from "some/path"
        // after
        const {a, b, c: x} = require("some/path")
    """
    def repl(matchobj):
        new_object = matchobj["object"].replace(" as ", ": ")
        return f"{matchobj['space']}const {new_object} = require({matchobj['path']})"
    return IMPORT_BASIC_RE.sub(repl, content)


IMPORT_LEGACY_DEFAULT_RE = re.compile(r"""
    ^
    (?P<space>\s*)                                      # space and empty line
    import\s+                                           # import
    (?P<identifier>\w+)\s*                              # default variable name
    from\s*                                             # from
    (?P<path>(?P<quote>["'`])([^@\."'`][^"'`]*)(?P=quote))  # legacy alias file ("addon_name.module_name" or "some/path")
    """, re.MULTILINE | re.VERBOSE)


def convert_legacy_default_import(content):
    """
    Transpile legacy imports (that were used as they were default import).
    Legacy imports means that their name is not a path but a <addon_name>.<module_name>.
    It requires slightly different processing.

    .. code-block:: javascript

        // before
        import module_name from "addon.module_name"
        // after
        const module_name = require("addon.module_name")
    """
    repl = r"""\g<space>const \g<identifier> = require(\g<path>)"""
    return IMPORT_LEGACY_DEFAULT_RE.sub(repl, content)


IMPORT_DEFAULT = re.compile(r"""
    ^
    (?P<space>\s*)                      # space and empty line
    import\s+                           # import
    (?P<identifier>\w+)\s*              # default variable name
    from\s*                             # from
    (?P<path>(?P<quote>["'`])([^"'`]+)(?P=quote))   # "file path" ("some/path")
    """, re.MULTILINE | re.VERBOSE)


def convert_default_import(content):
    """
    Transpile the default import call.

    .. code-block:: javascript

        // before
        import something from "some/path"
        // after
        const something = require("some/path")[Symbol.for("default")]
    """
    repl = r"""\g<space>const \g<identifier> = require(\g<path>)[Symbol.for("default")]"""
    return IMPORT_DEFAULT.sub(repl, content)


IS_PATH_LEGACY_RE = re.compile(r"""(?P<quote>["'`])([^@\."'`][^"'`]*)(?P=quote)""")

IMPORT_DEFAULT_AND_NAMED_RE = re.compile(r"""
    ^
    (?P<space>\s*)                                  # space and empty line
    import\s+                                       # import
    (?P<default_export>\w+)\s*,\s*                  # default variable name,
    (?P<named_exports>{[\s\w,]+})\s*                # { a, b, c as x, ... }
    from\s*                                         # from
    (?P<path>(?P<quote>["'`])([^"'`]+)(?P=quote))   # "file path" ("some/path")
    """, re.MULTILINE | re.VERBOSE)


def convert_default_and_named_import(content):
    """
    Transpile default and named import on one line.

    .. code-block:: javascript

        // before
        import something, { a } from "some/path";
        import somethingElse, { b } from "legacy.module";
        // after
        const { [Symbol.for("default")]: something, a } = require("some/path");
        const somethingElse = require("legacy.module");
        const { b } = somethingElse;
    """
    def repl(matchobj):
        is_legacy = IS_PATH_LEGACY_RE.match(matchobj['path'])
        new_object = matchobj["named_exports"].replace(" as ", ": ")
        if is_legacy:
            return f"""{matchobj['space']}const {matchobj['default_export']} = require({matchobj['path']});
{matchobj['space']}const {new_object} = {matchobj['default_export']}"""
        new_object = f"""{{ [Symbol.for("default")]: {matchobj['default_export']},{new_object[1:]}"""
        return f"{matchobj['space']}const {new_object} = require({matchobj['path']})"
    return IMPORT_DEFAULT_AND_NAMED_RE.sub(repl, content)


RELATIVE_REQUIRE_RE = re.compile(r"""
    ^[^/*\n]*require\((?P<quote>[\"'`])([^\"'`]+)(?P=quote)\) # require("some/path")
    """, re.MULTILINE | re.VERBOSE)


def convert_relative_require(url, dependencies, content):
    """
    Convert the relative path contained in a 'require()'
    to the new path system (@module/path).
    Adds all modules path to dependencies.
    .. code-block:: javascript

        // Relative path:
        // before
        require("./path")
        // after
        require("@module/path")

        // Not a relative path:
        // before
        require("other_alias")
        // after
        require("other_alias")
    """
    new_content = content
    for quote, path in RELATIVE_REQUIRE_RE.findall(new_content):
        module_path = path
        if path.startswith(".") and "/" in path:
            pattern = rf"require\({quote}{path}{quote}\)"
            module_path = relative_path_to_module_path(url, path)
            repl = f'require("{module_path}")'
            new_content = re.sub(pattern, repl, new_content)
        dependencies.add(module_path)
    return new_content


IMPORT_STAR = re.compile(r"""
    ^(?P<space>\s*)       # indentation
    import\s+\*\s+as\s+   # import * as
    (?P<identifier>\w+)   # alias
    \s*from\s*            # from
    (?P<path>[^;\n]+)     # path
""", re.MULTILINE | re.VERBOSE)


def convert_star_import(content):
    """
    Transpile import star.

    .. code-block:: javascript

        // before
        import * as name from "some/path"
        // after
        const name = require("some/path")
    """
    repl = r"\g<space>const \g<identifier> = require(\g<path>)"
    return IMPORT_STAR.sub(repl, content)


IMPORT_DEFAULT_AND_STAR = re.compile(r"""
    ^(?P<space>\s*)                 # indentation
    import\s+                       # import
    (?P<default_export>\w+)\s*,\s*  # default export name,
    \*\s+as\s+                      # * as
    (?P<named_exports_alias>\w+)    # alias
    \s*from\s*                      # from
    (?P<path>[^;\n]+)               # path
""", re.MULTILINE | re.VERBOSE)


def convert_default_and_star_import(content):
    """
    Transpile import star.

    .. code-block:: javascript

        // before
        import something, * as name from "some/path";
        // after
        const name = require("some/path");
        const something = name[Symbol.for("default")];
    """
    repl = r"""\g<space>const \g<named_exports_alias> = require(\g<path>);
\g<space>const \g<default_export> = \g<named_exports_alias>[Symbol.for("default")]"""
    return IMPORT_DEFAULT_AND_STAR.sub(repl, content)


IMPORT_UNNAMED_RELATIVE_RE = re.compile(r"""
    ^(?P<space>\s*)     # indentation
    import\s+           # import
    (?P<path>[^;\n]+)   # relative path
""", re.MULTILINE | re.VERBOSE)


def convert_unnamed_relative_import(content):
    """
    Transpile relative "direct" imports. Direct meaning they are not store in a variable.

    .. code-block:: javascript

        // before
        import "some/path"
        // after
        require("some/path")
    """
    repl = r"require(\g<path>)"
    return IMPORT_UNNAMED_RELATIVE_RE.sub(repl, content)


URL_INDEX_RE = re.compile(r"""
    require\s*                 # require
    \(\s*                      # (
    (?P<path>(?P<quote>["'`])([^"'`]*/index/?)(?P=quote))  # path ended by /index or /index/
    \s*\)                      # )
""", re.MULTILINE | re.VERBOSE)


def remove_index(content):
    """
    Remove in the paths the /index.js.
    We want to be able to import a module just trough its directory name if it contains an index.js.
    So we no longer need to specify the index.js in the paths.
    """
    def repl(matchobj):
        path = matchobj["path"]
        new_path = path[: path.rfind("/index")] + path[0]
        return f"require({new_path})"
    return URL_INDEX_RE.sub(repl, content)


def relative_path_to_module_path(url, path_rel):
    """Convert the relative path into a module path, which is more generic and
    fancy.

    :param str url:
    :param path_rel: a relative path to the current url.
    :return: module path (@module/...)
    """
    url_split = url.split("/")
    path_rel_split = path_rel.split("/")
    nb_back = len([v for v in path_rel_split if v == ".."]) + 1
    result = "/".join(url_split[:-nb_back] + [v for v in path_rel_split if not v in ["..", "."]])
    return url_to_module_path(result)


ODOO_MODULE_RE = re.compile(r"""
    \s*                             # starting white space
    \/(\*|\/)                       # /* or //
    .*                              # any comment in between (optional)
    @odoo-module                    # '@odoo-module' statement
    (?P<ignore>\s+ignore)?          # module in src | tests which should not be transpiled (optional)
    (\s+alias=(?P<alias>[^\s*]+))?  # alias (e.g. alias=web.Widget, alias=@web/../tests/utils) (optional)
    (\s+default=(?P<default>\w+))?  # no implicit default export (e.g. default=false) (optional)
""", re.VERBOSE)


def is_odoo_module(url, content):
    """
    Detect if the file is a native odoo module.
    We look for a comment containing @odoo-module.

    :param url:
    :param content: source code
    :return: is this a odoo module that need transpilation ?
    """
    result = ODOO_MODULE_RE.match(content)
    if result and result['ignore']:
        return False
    addon = url.split('/')[1]
    if url.startswith(f'/{addon}/static/src') or url.startswith(f'/{addon}/static/tests'):
        return True
    return bool(result)


def get_aliased_odoo_define_content(module_path, content):
    """
    To allow smooth transition between the new system and the legacy one, we have the possibility to
    defined an alternative module name (an alias) that will act as proxy between legacy require calls and
    new modules.

    Example:
    If we have a require call somewhere in the odoo source base being:
    > vat AbstractAction require("web.AbstractAction")
    we have a problem when we will have converted to module to ES6: its new name will be more like
    "web/chrome/abstract_action". So the require would fail !
    So we add a second small modules, an alias, as such:
    > odoo.define("web/chrome/abstract_action", ['web.AbstractAction'], function (require) {
    >  return require('web.AbstractAction')[Symbol.for("default")];
    > });

    To generate this, change your comment on the top of the file.

    .. code-block:: javascript

        // before
        /** @odoo-module */
        // after
        /** @odoo-module alias=web.AbstractAction */

    Notice that often, the legacy system acted like they it did defaukt imports. That's why we have the
    "[Symbol.for("default")];" bit. If your use case does not need this default import, just do:

    .. code-block:: javascript

        // before
        /** @odoo-module */
        // after
        /** @odoo-module alias=web.AbstractAction default=false */

    :return: the alias content to append to the source code.
    """
    matchobj = ODOO_MODULE_RE.match(content)
    if matchobj:
        alias = matchobj['alias']
        if alias:
            if matchobj['default']:
                return """\nodoo.define(`%s`, ['%s'], function (require) {
                        return require('%s');
                        });\n""" % (alias, module_path, module_path)
            else:
                return """\nodoo.define(`%s`, ['%s'], function (require) {
                        return require('%s')[Symbol.for("default")];
                        });\n""" % (alias, module_path, module_path)


def convert_as(val):
    parts = val.split(" as ")
    return val if len(parts) < 2 else "%s: %s" % tuple(reversed(parts))


def remove_as(val):
    parts = val.split(" as ")
    return val if len(parts) < 2 else parts[0]
