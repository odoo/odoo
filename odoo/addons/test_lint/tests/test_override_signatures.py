import collections
import inspect
import itertools

import odoo
from odoo.modules.registry import Registry
from odoo.tests.common import get_db_name, tagged
from .lint_case import LintCase


POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD
EMPTY = inspect.Parameter.empty


failure_message = """\
Invalid override of {model}.{method} in {child_module}, {message}.

Original definition in {parent_module}:
    def {method}{original_signature}

Incompatible definition in {child_module}:
    def {method}{override_signature}"""


methods_to_sanitize = {
    method_name
    for method_name in dir(odoo.models.BaseModel)
    if not method_name.startswith('_')
} - {
    # Not yet sanitized...
    'write', 'create', 'default_get', 'init'
}


class HitMiss:
    def __init__(self):
        self.hit = 0
        self.miss = 0
    @property
    def ratio(self):
        return self.hit / (self.hit + self.miss)
counter = collections.defaultdict(HitMiss)


def get_odoo_module_name(python_module_name):
    if python_module_name.startswith('odoo.addons.'):
        return python_module_name.split('.')[2]
    if python_module_name == 'odoo.models':
        return 'odoo'

    return python_module_name


def assert_valid_override(parent_signature, child_signature):
    pparams = parent_signature.parameters
    cparams = child_signature.parameters

    # parent and child have exact same signature
    if pparams == cparams:
        return

    parent_is_annotated = any(p.annotation is not inspect._empty for p in pparams.values())
    child_is_annotated = any(p.annotation is not inspect._empty for p in cparams.values())

    # don't check annotations when one of the two methods is not annotated
    if parent_is_annotated != child_is_annotated:
        pparams = {name: param.replace(annotation=EMPTY) for name, param in pparams.items()}
        cparams = {name: param.replace(annotation=EMPTY) for name, param in cparams.items()}
        parent_is_annotated = child_is_annotated = False

        # parent and child have exact same signature, modulo annotations
        if pparams == cparams:
            return

    # parent has *args/**kwargs: child can define new custom args/kwargs
    parent_has_varargs = any(pp.kind == VAR_POSITIONAL for pp in pparams.values())
    parent_has_varkwargs = any(pp.kind == VAR_KEYWORD for pp in pparams.values())

    # child has *args/**kwargs: all unknown args/kargs are delegated
    child_has_varargs = any(cp.kind == VAR_POSITIONAL for cp in cparams.values())
    child_has_varkwargs = any(cp.kind == VAR_KEYWORD for cp in cparams.values())

    # check positionals
    pposparams = [(pp_name, pp) for pp_name, pp in pparams.items()
                  if pp.kind in (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD)]
    cposparams = [(cp_name, cp) for cp_name, cp in cparams.items()
                  if cp.kind in (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD)]
    if len(cposparams) < len(pposparams):
        assert child_has_varargs, "missing positional parameters"
        assert cposparams == pposparams[:len(cposparams)], "wrong positional parameters"
    elif len(cposparams) > len(pposparams):
        assert parent_has_varargs, "too many positional parameters"
        assert cposparams[:len(pposparams)] == pposparams, "wrong positional parameters"
    else:
        assert cposparams == pposparams, "wrong positional parameters"

    # check keywords
    pkwparams = {(pp_name, pp) for pp_name, pp in pparams.items()
                 if pp.kind in (POSITIONAL_OR_KEYWORD, KEYWORD_ONLY)}
    ckwparams = {(cp_name, cp) for cp_name, cp in cparams.items()
                 if cp.kind in (POSITIONAL_OR_KEYWORD, KEYWORD_ONLY)}
    if ckwparams < pkwparams:
        assert child_has_varkwargs, "missing keyword parameters"
    elif ckwparams > pkwparams:
        assert parent_has_varkwargs, "too many keyword parameters"
    elif ckwparams != pkwparams:
        assert child_has_varkwargs and parent_has_varkwargs, "wrong keyword parameters"


@tagged('-at_install', 'post_install')
class TestLintOverrideSignatures(LintCase):
    def test_lint_override_signature(self):
        self.failureException = TypeError
        registry = Registry(get_db_name())
        for model_name, model_cls in registry.items():
            for method_name, _ in inspect.getmembers(model_cls, inspect.isroutine):
                if method_name not in methods_to_sanitize:
                    continue

                # Find the original function definition
                reverse_mro = reversed(model_cls.mro()[1:-1])
                for parent_class in reverse_mro:
                    method = getattr(parent_class, method_name, None)
                    if callable(method):
                        break

                parent_module = get_odoo_module_name(parent_class.__module__)
                original_signature = inspect.signature(method)

                # Assert that all child classes correctly override the method
                for child_class in reverse_mro:
                    if method_name not in child_class.__dict__:
                        continue
                    override = getattr(child_class, method_name)

                    child_module = get_odoo_module_name(child_class.__module__)
                    override_signature = inspect.signature(override)

                    with self.subTest(module=child_module, model=model_name, method=method_name):
                        try:
                            assert_valid_override(original_signature, override_signature)
                            counter[method_name].hit += 1
                        except AssertionError as exc:
                            counter[method_name].miss += 1
                            msg = failure_message.format(
                                message=exc.args[0],
                                model=model_name,
                                method=method_name,
                                child_module=child_module,
                                parent_module=parent_module,
                                original_signature=original_signature,
                                override_signature=override_signature,
                            )
                            raise TypeError(msg) from None

        #with open('/tmp/odoo-override-signatures.md', 'w') as f:
        #    f.write('method|hit|miss|ratio\n')
        #    f.write('------|---|----|-----\n')
        #    for method_name, hm in sorted(counter.items(), key=lambda x: x[1].miss):
        #        f.write(f'{method_name}|{hm.hit}|{hm.miss}|{hm.ratio:.3f}\n')
