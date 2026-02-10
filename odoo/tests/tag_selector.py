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
                                (\/[\w\/\.-]+.py)?           # file_re
                                (?:\/(\w+))?                # module_re
                                (?::(\w*))?                 # test_class_re
                                (?:\.(\w*))?                # test_method_re
                                (?:\[(.*)\])?               # parameters
                                $''', re.VERBOSE)  # [-][tag][/module][:class][.method][[params]]

    def __init__(self, spec, available_modules=None):
        """ Parse the spec to determine tags to include and exclude. """
        parts = re.split(r',(?![^\[]*\])', spec)  # split on all comma not inside [] (not followed by ])
        filter_specs = [t.strip() for t in parts if t.strip()]
        self.exclude = set()
        self.include = set()
        self.parameters = OrderedSet()
        self.available_modules = available_modules and set(available_modules)
        self.has_include = False
        for filter_spec in filter_specs:
            match = self.filter_spec_re.match(filter_spec)
            if not match:
                _logger.error('Invalid tag %s', filter_spec)
                continue

            sign, tag, file_path, module, klass, method, parameters = match.groups()
            is_include = sign != '-'
            is_exclude = not is_include

            if not tag and is_include:
                # including /module:class.method implicitly requires 'standard'
                tag = 'standard'
            elif not tag or tag == '*':
                # '*' indicates all tests (instead of 'standard' tests only)
                tag = None
            test_filter = (tag, module, klass, method, file_path)

            if parameters:
                # we could check here that test supports negated parameters
                self.parameters.add((test_filter, ('-' if is_exclude else '+', parameters)))
                is_exclude = False

            if is_include:
                self.has_include = True  # this is important for tags like /nonexistingmodule,-test_x

            if is_include and module and self.available_modules and module not in self.available_modules:
                _logger.info("Module '%s' in tag selector not in the list of installed modules %s", module, available_modules)
                continue

            if is_include:
                self.include.add(test_filter)
            if is_exclude:
                self.exclude.add(test_filter)

        if (self.exclude or self.parameters) and not self.has_include:
            self.include.add(('standard', None, None, None, None))

    def check(self, test):
        """ Return whether ``arg`` matches the specification: it must have at
            least one tag in ``self.include`` and none in ``self.exclude`` for each tag category.
        """
        if not hasattr(test, 'test_tags'): # handle the case where the Test does not inherit from BaseCase and has no test_tags
            _logger.debug("Skipping test '%s' because no test_tag found.", test)
            return False

        test_module = test.test_module
        test_class = test.__class__.__name__
        test_tags = test.test_tags | {test_module}  # module as test_tags deprecated, keep for retrocompatibility,
        test_method = test._testMethodName
        test_module_path = test.__module__
        for prefix in ('odoo.addons', 'odoo.upgrade'):
            test_module_path = test_module_path.removeprefix(prefix)
        test_module_path = test_module_path.replace('.', '/') + '.py'

        test._test_params = []
        included_modules = set()
        excluded_modules = set()

        cross_module_test = hasattr(test, '_cross_module')

        if cross_module_test and not self.available_modules:
            _logger.debug("Skipping test '%s' because no available modules found.", test)
            return False

        def _is_matching(test_filter):
            (tag, module, klass, method, file_path) = test_filter
            if tag and tag not in test_tags:
                return False
            if file_path and not file_path.endswith(test_module_path):
                return False
            if not file_path and module and module != test_module and not cross_module_test:
                return False
            if klass and klass != test_class:
                return False
            if method and test_method and method != test_method:  # noqa: SIM103
                return False
            return True

        match_include = False
        for test_filter in self.include:
            if _is_matching(test_filter):
                match_include = True
                if cross_module_test:
                    test_filter_module = test_filter[1]
                    if test_filter_module:
                        included_modules.add(test_filter_module)
                    else:
                        included_modules |= self.available_modules
                else:
                    break

        if not match_include:
            return False

        for test_filter in self.exclude:
            if _is_matching(test_filter):
                if cross_module_test:
                    test_filter_module = test_filter[1]
                    if test_filter_module:
                        excluded_modules.add(test_filter_module)
                    else:
                        return False
                else:
                    return False

        for test_filter, parameter in self.parameters:
            if _is_matching(test_filter):
                test._test_params.append(parameter)

        test._test_modules = sorted(included_modules - excluded_modules)

        if cross_module_test and not test._test_modules:  # noqa: SIM103
            return False

        return True
