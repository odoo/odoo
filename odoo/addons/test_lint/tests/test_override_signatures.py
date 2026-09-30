import collections
import inspect

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
Invalid override in {model} of {method}, {message}.

Original definition in {parent_module}:{original_decorators}
    def {method}{original_signature}

Incompatible override definition in {child_module}:{override_decorators}
    def {method}{override_signature}"""


MODULES_TO_IGNORE = {
    'pos_blackbox_be',  # TODO cannot update to sanitize without certification
}
METHODS_TO_IGNORE = {
    # base
    'action_timer_stop',
    '_get_eval_context',
    # mail
    '_action_done',
    '_get_html_link',
}
MODEL_METHODS_TO_IGNORE = {
    ('account.intrastat.services.be.report.handler', '_be_intrastat_get_xml_file_content'),
    ('hr.payslip', 'action_payslip_payment_report'),
    ('hr.payslip.run', 'action_payment_report'),
    ('ir.config_parameter', 'init'),
    ('mrp.production', 'action_generate_serial'),
    ('mrp.production', 'set_qty_producing'),
    ('mrp.workorder', 'button_start'),
    ('quality.check', 'add_check_in_chain'),
    ('propose.change', '_do_remove_step'),
    ('propose.change', '_do_set_picture'),
    ('propose.change', '_do_update_step'),
    ('report.pos_hr.single_employee_sales_report', '_get_domain'),
    ('report.pos_hr.single_employee_sales_report', 'get_sale_details'),
    ('sign.request', '_generate_completed_document'),
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


def check_parameter(pparam: inspect.Parameter, cparam: inspect.Parameter, is_private: bool = False) -> bool:
    # don't check annotations
    return (
        pparam.name == cparam.name
        or pparam.kind == POSITIONAL_ONLY
        or is_private  # ignore names of (positional or keyword) attributes
    ) and (
        # if parent has a default, child should have the same one
        pparam.default is EMPTY
        or pparam.default == cparam.default
    ) and (
        # if both are annotated, then they should be similar (for typing)
        (pann := pparam.annotation) is EMPTY
        or (cann := cparam.annotation) is EMPTY
        or pann == cann
        # accept annotations of different types as valid to keep logic simple
        # for example, typing can be a str or the class
        or pann.__class__ != cann.__class__
    )


def assert_valid_override(parent_signature, child_signature, is_private):
    pparams = parent_signature.parameters
    cparams = child_signature.parameters

    # parent and child have exact same signature
    if pparams == cparams:
        return

    # parent has *args/**kwargs: child can define new custom args/kwargs
    parent_has_varargs = any(pp.kind == VAR_POSITIONAL for pp in pparams.values())
    parent_has_varkwargs = any(pp.kind == VAR_KEYWORD for pp in pparams.values())

    # child has *args/**kwargs: all unknown args/kargs are delegated
    child_has_varargs = any(cp.kind == VAR_POSITIONAL for cp in cparams.values())
    child_has_varkwargs = any(cp.kind == VAR_KEYWORD for cp in cparams.values())

    # check positionals
    pos_kinds = (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD)
    pposparams = [pp for pp in pparams.values() if pp.kind in pos_kinds]
    cposparams = [cp for cp in cparams.values() if cp.kind in pos_kinds]
    if len(cposparams) < len(pposparams):
        assert child_has_varargs, "missing positional parameters"
        pposparams = pposparams[:len(cposparams)]
    elif len(cposparams) > len(pposparams):
        assert parent_has_varargs, "too many positional parameters"
        cposparams = cposparams[:len(pposparams)]
    for pparam, cparam in zip(pposparams, cposparams, strict=True):
        assert check_parameter(pparam, cparam, is_private=is_private), f"wrong positional parameter {cparam.name!r}"

    # check keywords
    kw_kinds = (KEYWORD_ONLY,) if is_private else (POSITIONAL_OR_KEYWORD, KEYWORD_ONLY)
    pkwparams = {pp_name: pp for pp_name, pp in pparams.items() if pp.kind in kw_kinds}
    ckwparams = {cp_name: cp for cp_name, cp in cparams.items() if cp.kind in kw_kinds}
    for name, pparam in pkwparams.items():
        cparam = ckwparams.get(name)
        if cparam is None:
            assert child_has_varkwargs, f"missing keyword parameter {name!r}"
        else:
            assert check_parameter(pparam, cparam, is_private=is_private), f"wrong keyword parameter {name!r}"
    if not parent_has_varkwargs:
        for name in (ckwparams.keys() - pkwparams.keys()):
            assert ckwparams[name].default is not EMPTY, "too many keyword parameters"


def assert_attribute_override(parent_method, child_method, is_private):
    if is_private:
        attributes = ('_autovacuum',)
    else:
        attributes = ('_autovacuum', '_api_model')
    for attribute in attributes:
        parent_attr = getattr(parent_method, attribute, None)
        child_attr = getattr(child_method, attribute, None)
        assert parent_attr == child_attr, f"attribute {attribute!r} does not match"
    # https://docs.python.org/3/library/typing.html#typing.final
    assert not getattr(parent_method, '__final__', False), "parent method is final"
    # https://docs.python.org/3/library/warnings.html#warnings.deprecated
    assert bool(getattr(parent_method, '__deprecated__', False)) == bool(getattr(child_method, '__deprecated__', False)), \
        "parent and child method should either both be deprecated or none of them"


def get_decorators(method):
    if not method.__name__.startswith('_') and hasattr(method, '_api_model') and method._api_model:
        return "\n    @api.model"
    return ""


@tagged('-at_install', 'post_install')
class TestLintOverrideSignatures(LintCase):
    def test_lint_override_signature(self):
        self.failureException = TypeError
        registry = Registry(get_db_name())

        for model_name, model_cls in registry.items():
            if model_cls._module in MODULES_TO_IGNORE:
                continue
            for method_name, _ in inspect.getmembers(model_cls, inspect.isroutine):
                if (
                    method_name.startswith('__')
                    or method_name in METHODS_TO_IGNORE
                    or (model_name, method_name) in MODEL_METHODS_TO_IGNORE
                ):
                    continue

                # Find the original function definition
                reverse_mro = reversed(model_cls.mro()[1:-1])
                for parent_class in reverse_mro:
                    method = getattr(parent_class, method_name, None)
                    if callable(method):
                        break

                parent_module = get_odoo_module_name(parent_class.__module__)
                original_signature = inspect.signature(method)
                original_decorators = get_decorators(method)
                is_private = method_name.startswith('_')

                # Assert that all child classes correctly override the method
                for child_class in reverse_mro:
                    if method_name not in child_class.__dict__:
                        continue
                    override = getattr(child_class, method_name)

                    child_module = get_odoo_module_name(child_class.__module__)
                    override_signature = inspect.signature(override)
                    override_decorators = get_decorators(override)

                    with self.subTest(module=child_module, model=model_name, method=method_name):
                        try:
                            assert_valid_override(original_signature, override_signature, is_private=is_private)
                            assert override_decorators == original_decorators, "decorators does not match"
                            assert_attribute_override(method, override, is_private=is_private)
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
                                original_decorators=original_decorators,
                                override_decorators=override_decorators,
                            )
                            raise TypeError(msg) from None

        #with open('/tmp/odoo-override-signatures.md', 'w') as f:
        #    f.write('method|hit|miss|ratio\n')
        #    f.write('------|---|----|-----\n')
        #    for method_name, hm in sorted(counter.items(), key=lambda x: x[1].miss):
        #        f.write(f'{method_name}|{hm.hit}|{hm.miss}|{hm.ratio:.3f}\n')
