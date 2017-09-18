# -*- coding: utf-8 -*-
import operator

import pyjsparser

from autojsdoc.parser import jsdoc, parser

params = operator.attrgetter('name', 'type', 'doc')


def parse(s, source=None):
    tree = pyjsparser.parse(s)
    mods = parser.ModuleMatcher(source).visit(tree)
    post(mods)
    return mods

def post(mods):
    modules = dict(BASE_MODULES)
    modules.update((m.name, m) for m in mods)

    for mod in mods:
        mod.post_process(modules)

BASE_MODULES = {
    'other': jsdoc.ModuleDoc({
        'module': 'other',
        '_members': [
            ('<exports>', jsdoc.LiteralDoc({'name': 'value', 'value': "ok"})),
        ],
    }),
    'dep2': jsdoc.ModuleDoc({
        'module': 'dep2',
        '_members': [
            ('<exports>', jsdoc.LiteralDoc({'value': 42.})),
        ],
    }),
    'dep3': jsdoc.ModuleDoc({
        'module': 'dep3',
        '_members': [
            ('<exports>', jsdoc.LiteralDoc({'value': 56.})),
        ],
    }),
    'Class': jsdoc.ModuleDoc({
        'module': 'Class',
        '_members': [
            ('<exports>', jsdoc.ClassDoc({
                'name': 'Class',
                'doc': "Base Class"
            })),
        ],
    }),
    'mixins': jsdoc.ModuleDoc({
        'module': 'mixins',
        '_members': [
            ('<exports>', jsdoc.NSDoc({
                'name': 'mixins',
                '_members': [
                    ('Bob', jsdoc.ClassDoc({'class': "Bob"})),
                ]
            })),
        ],
    }),
    'Mixin': jsdoc.ModuleDoc({
        'module': 'Mixin',
        '_members': [
            ('<exports>', jsdoc.MixinDoc({
                '_members': [
                    ('a', jsdoc.FunctionDoc({'function': 'a'})),
                ]
            })),
        ],
    })
}
