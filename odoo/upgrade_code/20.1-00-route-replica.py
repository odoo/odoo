"""
```diff
-@http.route(..., readonly=...)
+@http.route(..., replica=...)
```
"""

import itertools
import re


def upgrade(file_manager):
    files = [
        f for f in file_manager
        if ('controllers' in f.path.parts or f.path.stem == 'controllers')
        if f.path.suffix == '.py'
    ]

    # First pass, use the fast regexp to rewrite most files.
    files_to_check = []
    re_wz_converter = re.compile(r'<(?:model|models|string|path|any|int|float|uuid)\(')
    re_route_readonly = re.compile(
        r'@((?:(?:(?:odoo\.)?http\.)?route|mail_route)\((?:[^)]*?|.*?))\breadonly(\s*)=')
    #       support multi-line but not werkzeug converters ^^^^^^
    #              support werkzeug converters but not multi-line ^^^ [2]

    for fileno, file in enumerate(files):
        file.content = re_route_readonly.sub(r'@\1replica\2=', file.content)
        if 'readonly' in file.content and re_wz_converter.search(file.content):
            files_to_check.append(file)
        file_manager.print_progress(fileno, len(files))

    # Second pass, for the files that have all 3: (1) multiline @route,
    # (2) readonly routes, (3) werkzeug converters (e.g. <models(...)>),
    # that the above fast regexp above can't detect. The search/replace
    # is more bug-prone, but running it on the remaining files (8 in
    # community) proved effective. In all cases we list those faulty
    # files, so in case of an error, a human can easily fix them.
    if files_to_check:
        file_manager.add_to_summary(f"""\
{__name__}, @route(readonly=...) -> @route(replica=...), files to manually check:
 {"\n ".join([str(file.path) for file in files_to_check])}
""")

    route_args = ('type=', 'auth=', 'methods=', 'website=', 'sitemap=')
    for fileno, file in enumerate(files_to_check):
        lines = file.content.split('\n')
        if len(lines) < 4:
            continue

        # itertools.pairwise, but with 4 items
        it1, it2, it3, it4 = itertools.tee(iter([line.strip() for line in lines]), 4)
        next(it2)
        next(it3)
        next(it3)
        next(it4)
        next(it4)
        next(it4)

        for lineno, (line1, line2, line3, line4) in enumerate(zip(it1, it2, it3, it4)):
            if (
                # @route(['/foo/1/<int(foo)>', '/foo/2/<int(foo)>'],
                #        type="http", auth="user", readonly=True, website=True)
                'readonly=' in line3
                and sum(1 for arg in route_args if arg in line3) >= 2
            ) or (
                # @route(
                #   ['/foo/1/<int(foo)>', '/foo/2/<int(foo)>'],
                #   type="http",
                #   auth="user",
                #   readonly=True,
                #   website=True)
                line3.startswith('readonly=')
                and sum(1 for line in (line1, line2, line4) if line.startswith(route_args)) >= 2
            ):
                lines[lineno + 2] = lines[lineno + 2].replace('readonly=', 'replica=')

        file.content = '\n'.join(lines)
        file_manager.print_progress(fileno, len(files_to_check))
