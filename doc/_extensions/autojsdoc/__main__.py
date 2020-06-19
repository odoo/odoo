# -*- coding: utf-8 -*-
from __future__ import print_function
import cgitb
import fnmatch
import io
import logging

import click

import pyjsparser
import sys

from .parser.parser import ModuleMatcher
from .parser.visitor import Visitor, SKIP
from .parser import jsdoc

class Printer(Visitor):
    def __init__(self, level=0):
        super(Printer, self).__init__()
        self.level = level

    def _print(self, text):
        print('    ' * self.level, text)

    def enter_generic(self, node):
        self._print(node['type'])
        self.level += 1

    def exit_generic(self, node):
        self.level -= 1

    def enter_Identifier(self, node):
        self._print(node['name'])
        return SKIP

    def enter_Literal(self, node):
        self._print(node['value'])
        return SKIP

    def enter_BinaryExpression(self, node):
        self._print(node['operator'])
        self.level += 1

def visit_files(files, visitor, ctx):
    for name in files:
        with io.open(name) as f:
            ctx.logger.info("%s", name)
            try:
                yield visitor().visit(pyjsparser.parse(f.read()))
            except Exception as e:
                if ctx.logger.isEnabledFor(logging.DEBUG):
                    ctx.logger.exception("while visiting %s", name)
                else:
                    ctx.logger.error("%s while visiting %s", e, name)

# bunch of modules various bits depend on which are not statically defined
# (or are outside the scope of the system)
ABSTRACT_MODULES = [
    jsdoc.ModuleDoc({
        'module': 'web.web_client',
        'dependency': {'web.AbstractWebClient'},
        'exports': jsdoc.NSDoc({
            'name': 'web_client',
            'doc': 'instance of AbstractWebClient',
        }),
    }),
    jsdoc.ModuleDoc({
        'module': 'web.Tour',
        'dependency': {'web_tour.TourManager'},
        'exports': jsdoc.NSDoc({
            'name': 'Tour',
            'doc': 'maybe tourmanager instance?',
        }),
    }),
    # OH FOR FUCK'S SAKE
    jsdoc.ModuleDoc({
        'module': 'summernote/summernote',
        'exports': jsdoc.NSDoc({'doc': "totally real summernote"}),
    })
]

@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-v', '--verbose', count=True)
@click.option('-q', '--quiet', count=True)
@click.pass_context
def autojsdoc(ctx, verbose, quiet):
    logging.basicConfig(
        level=logging.INFO + (quiet - verbose) * 10,
        format="[%(levelname)s %(created)f] %(message)s",
    )
    ctx.logger = logging.getLogger('autojsdoc')
    ctx.visitor = None
    ctx.files = []
    ctx.kw = {}

@autojsdoc.command()
@click.argument('files', type=click.Path(exists=True), nargs=-1)
@click.pass_context
def ast(ctx, files):
    """ Prints a structure tree of the provided files
    """
    if not files:
        print(ctx.get_help())
    visit_files(files, lambda: Printer(level=1), ctx.parent)

@autojsdoc.command()
@click.option('-m', '--module', multiple=True, help="Only shows dependencies matching any of the patterns")
@click.argument('files', type=click.Path(exists=True), nargs=-1)
@click.pass_context
def dependencies(ctx, module, files):
    """ Prints a dot file of all modules to stdout
    """
    if not files:
        print(ctx.get_help())
    byname = {
        mod.name: mod.dependencies
        for mod in ABSTRACT_MODULES
    }
    for modules in visit_files(files, ModuleMatcher, ctx.parent):
        for mod in modules:
            byname[mod.name] = mod.dependencies

    print('digraph dependencies {')

    todo = set()
    # if module filters, roots are only matching modules
    if module:
        for f in module:
            todo.update(fnmatch.filter(byname.keys(), f))

        for m in todo:
            # set a different box for selected roots
            print('    "%s" [color=orangered]' % m)
    else:
        # otherwise check all modules
        todo.update(byname)

    done = set()
    while todo:
        node = todo.pop()
        if node in done:
            continue

        done.add(node)
        deps = byname[node]
        todo.update(deps - done)
        for dep in deps:
            print('    "%s" -> "%s";' % (node, dep))
    print('}')

try:
    autojsdoc.main(prog_name='autojsdoc')
except Exception:
    print(cgitb.text(sys.exc_info()))
