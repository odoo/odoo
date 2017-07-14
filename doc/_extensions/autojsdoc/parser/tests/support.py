# -*- coding: utf-8 -*-
import operator

import pyjsparser

from autojsdoc import jsdoc
from autojsdoc.parser.parser import ModuleMatcher

params = operator.attrgetter('name', 'type', 'doc')


def parse(s):
    tree = pyjsparser.parse(s)
    mods = ModuleMatcher().visit(tree)
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
        'exports': jsdoc.LiteralDoc({'value': "ok"}),
    }),
    'dep2': jsdoc.ModuleDoc({
        'module': 'dep2',
        'exports': jsdoc.LiteralDoc({'value': 42.}),
    }),
    'dep3': jsdoc.ModuleDoc({
        'module': 'dep3',
        'exports': jsdoc.LiteralDoc({'value': 56.}),
    }),
    'Class': jsdoc.ModuleDoc({
        'module': 'Class',
        'exports': jsdoc.ClassDoc({
            'class': 'Class'
        }),
    }),
    'mixins': jsdoc.ModuleDoc({
        'module': 'mixins',
        'exports': jsdoc.NSDoc({
            'name': 'mixins',
            '_members': jsdoc.ClassDoc({
                'class': "Bob",
            })
        })
    }),
    'Mixin': jsdoc.ModuleDoc({
        'module': 'Mixin',
        'exports': jsdoc.MixinDoc({
            '_members': [
                jsdoc.FunctionDoc({
                    'function': 'a',
                })
            ]
        })
    })
}
