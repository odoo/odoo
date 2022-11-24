from pylint import checkers, interfaces


class OdooBaseChecker(checkers.BaseChecker):
    __implements__ = interfaces.IAstroidChecker
    name = "odoo"

    msgs = {
        "E8602": (
            "Prefer `odoo.tools.groupby` instead of `itertools.groupby` "
            "or disable with `# pylint: disable=prefer-odoo-tools-groupby` if the iterable is sorted by the key",
            "prefer-odoo-tools-groupby",
            "See https://github.com/odoo/odoo/issues/105376",
        )
    }

    @checkers.utils.check_messages("prefer-odoo-tools-groupby")
    def visit_call(self, node):
        if "groupby" not in node.func.as_string():
            # safe_infer is a heavy method
            # So, call it only if the method name is related to "groupby" word
            return
        infer_node = checkers.utils.safe_infer(node.func)
        if infer_node and infer_node.qname() == "itertools.groupby":
            self.add_message("prefer-odoo-tools-groupby", node=node)


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
