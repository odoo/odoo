import re
import logging

from odoo.tools.misc import OrderedSet

_logger = logging.getLogger(__name__)


class TagsSelector(object):
    """ Test selector based on tags. """
    filter_spec_re = re.compile(r'''
                                ^
                                ([+-]?)                     # operator_re
                                (\*|\w*)                    # tag_re
                                (?:\/([\w\/]*(?:.py)?))?    # module_re
                                (?::(\w*))?                 # test_class_re
                                (?:\.(\w*))?                # test_method_re
                                (?:\[(.*)\])?               # parameters
                                $''', re.VERBOSE)  # [-][tag][/module][:class][.method][[params]]

    def __init__(self, spec):
        """ Parse the spec to determine tags to include and exclude. """
        parts = re.split(r',(?![^\[]*\])', spec)  # split on all comma not inside [] (not followed by ])
        filter_specs = [t.strip() for t in parts if t.strip()]
        self.exclude = set()
        self.include = set()
        self.parameters = OrderedSet()

        for filter_spec in filter_specs:
            match = self.filter_spec_re.match(filter_spec)
            if not match:
                _logger.error('Invalid tag %s', filter_spec)
                continue

            sign, tag, module, klass, method, parameters = match.groups()
            is_include = sign != '-'
            is_exclude = not is_include

            if not tag and is_include:
                # including /module:class.method implicitly requires 'standard'
                tag = 'standard'
            elif not tag or tag == '*':
                # '*' indicates all tests (instead of 'standard' tests only)
                tag = None
            module_path = None
            if module and (module.endswith('.py')):
                module_path = module[:-3].replace('/', '.')
                module = None

            test_filter = (tag, module, klass, method, module_path)

            if parameters:
                # we could check here that test supports negated parameters
                self.parameters.add((test_filter, ('-' if is_exclude else '+', parameters)))
                is_exclude = False

            if is_include:
                self.include.add(test_filter)
            if is_exclude:
                self.exclude.add(test_filter)

        if (self.exclude or self.parameters) and not self.include:
            self.include.add(('standard', None, None, None, None))

    def check(self, test):
        """ Return whether ``arg`` matches the specification: it must have at
            least one tag in ``self.include`` and none in ``self.exclude`` for each tag category.
        """
        if not hasattr(test, 'test_tags'): # handle the case where the Test does not inherit from BaseCase and has no test_tags
            _logger.debug("Skipping test '%s' because no test_tag found.", test)
            return False

        test_module = test.test_module
        test_class = test.test_class
        test_tags = test.test_tags | {test_module}  # module as test_tags deprecated, keep for retrocompatibility,
        test_method = test._testMethodName

        test._test_params = []

        def _is_matching(test_filter):
            (tag, module, klass, method, module_path) = test_filter
            if tag and tag not in test_tags:
                return False
            elif module_path and not test.__module__.endswith(module_path):
                return False
            elif not module_path and module and module != test_module:
                return False
            elif klass and klass != test_class:
                return False
            elif method and test_method and method != test_method:
                return False
            return True

        if any(_is_matching(test_filter) for test_filter in self.exclude):
            return False

        if not any(_is_matching(test_filter) for test_filter in self.include):
            return False
        
        for test_filter, parameter in self.parameters:
            if _is_matching(test_filter):
                test._test_params.append(parameter)

        return True
