import logging
import re
from typing import Any

from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import OrderedSet

from .utils import addon_relative_path

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class TagsSelector:
    filter_spec_re = re.compile(
        r"""
                                ^
                                ([+-]?)                     # operator_re
                                (\*|\w*)                    # tag_re
                                (\/[\w\/\.-]+\.py)?         # file_re
                                (?:\/(\w+))?                # module_re
                                (?::(\w*))?                 # test_class_re
                                (?:\.(\w*))?                # test_method_re
                                (?:\[(.*)\])?               # parameters
                                $""",
        re.VERBOSE,
    )

    def __init__(self, spec: str) -> None:
        parts = re.split(r",(?![^\[]*\])", spec)
        filter_specs = [t.strip() for t in parts if t.strip()]
        self.exclude: set[tuple] = set()
        self.include: set[tuple] = set()
        self.parameters: OrderedSet = OrderedSet()

        for filter_spec in filter_specs:
            match = self.filter_spec_re.match(filter_spec)
            if not match:
                if filter_spec.endswith(".js"):
                    _debug.logic("test.tags.spec_js_ignored", spec=filter_spec)
                    _logger.debug(
                        "Ignoring JavaScript file path as test tag: %s (only .py files are supported)",
                        filter_spec,
                    )
                else:
                    _debug.logic("test.tags.spec_invalid", spec=filter_spec)
                    _logger.error("Invalid tag %s", filter_spec)
                continue

            sign, tag, file_path, module, klass, method, parameters = match.groups()
            is_include = sign != "-"
            is_exclude = not is_include

            if not tag and is_include:
                tag = "standard"
            elif not tag or tag == "*":
                tag = None
            test_filter = (tag, module, klass, method, file_path)
            _debug.logic(
                "test.tags.spec",
                spec=filter_spec,
                sign="-" if is_exclude else "+",
                tag=tag,
                file=file_path,
                module=module,
                klass=klass,
                method=method,
                params=bool(parameters),
            )

            if parameters:
                self.parameters.add(
                    (test_filter, ("-" if is_exclude else "+", parameters))
                )
                is_exclude = False

            if is_include:
                self.include.add(test_filter)
            if is_exclude:
                self.exclude.add(test_filter)

        implicit_standard = (self.exclude or self.parameters) and not self.include
        if implicit_standard:
            self.include.add(("standard", None, None, None, None))
        _debug.pipeline(
            "test.tags.parsed",
            specs=len(filter_specs),
            include=len(self.include),
            exclude=len(self.exclude),
            params=len(self.parameters),
            implicit_standard=bool(implicit_standard),
        )

    def selects(self, test: Any) -> bool:
        matches = self._matcher(test)
        selected = matches is not None and self._selects(matches)
        if _debug.logic.enabled:
            _debug.logic("test.tags.selects", test=test.id(), selected=selected)
        return selected

    def select_params(self, test: Any) -> list:
        matches = self._matcher(test)
        if matches is None or not self._selects(matches):
            test._test_params = []
        else:
            test._test_params = [
                parameter
                for test_filter, parameter in self.parameters
                if matches(test_filter)
            ]
        if _debug.logic.enabled:
            _debug.logic(
                "test.tags.select_params",
                test=test.id(),
                params=len(test._test_params),
            )
        return test._test_params

    def select_test(self, test: Any) -> bool:
        matches = self._matcher(test)
        if matches is None or not self._selects(matches):
            test._test_params = []
            if _debug.logic.enabled:
                _debug.logic("test.tags.select_test", test=test.id(), selected=False)
            return False
        test._test_params = [
            parameter
            for test_filter, parameter in self.parameters
            if matches(test_filter)
        ]
        if _debug.logic.enabled:
            _debug.logic(
                "test.tags.select_test",
                test=test.id(),
                selected=True,
                params=len(test._test_params),
            )
        return True

    def _selects(self, matches: Any) -> bool:
        if any(matches(test_filter) for test_filter in self.exclude):
            _debug.logic("test.tags.excluded")
            return False
        return any(matches(test_filter) for test_filter in self.include)

    def _matcher(self, test: Any) -> Any:
        if not getattr(test, "test_tags", None):
            if _debug.logic.enabled:
                _debug.logic("test.tags.no_tags", test=test.id())
            _logger.debug("Skipping test '%s' because no test_tag found.", test)
            return None

        test_module = test.test_module
        test_class = test.__class__.__name__
        test_tags = test.test_tags | {test_module}
        test_method = test._testMethodName
        test_module_path = addon_relative_path(test.__module__)

        def _is_matching(test_filter: tuple) -> bool:
            tag, module, klass, method, file_path = test_filter
            if tag and tag not in test_tags:
                return False
            if file_path and not file_path.endswith(test_module_path):
                return False
            if module and module != test_module:
                return False
            if klass and klass != test_class:
                return False
            if method and test_method:
                return method == test_method
            return True

        return _is_matching
