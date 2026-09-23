from typing import Any, ClassVar, override

from docutils import nodes
from docutils.parsers.rst import directives, roles, states
from docutils.parsers.rst.directives.admonitions import Note
from docutils.statemachine import StringList

LITERAL_ROLES = (
    "attr",
    "class",
    "func",
    "meth",
    "ref",
    "const",
    "samp",
    "term",
)


def _role_literal(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: states.Inliner,
    options: dict[str, Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    return [nodes.literal(rawtext, text)], []


class _AdmonitionWithLead(Note):
    content: StringList
    lead: ClassVar[str] = "%s"
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True

    @override
    def run(self) -> list[nodes.Node]:
        if not self.content:
            self.content = StringList(
                [""], source=self.state_machine.document["source"]
            )
        produced = super().run()
        if self.arguments and produced:
            text = self.lead % self.arguments[0]
            produced[0].insert(0, nodes.paragraph("", "", nodes.strong(text, text)))
        return produced


class _Deprecated(_AdmonitionWithLead):
    lead = "Deprecated since version %s"


class _Attribute(_AdmonitionWithLead):
    lead = "Attribute %s"


def patch_module() -> None:
    for role in LITERAL_ROLES:
        roles.register_local_role(role, _role_literal)

    directives.register_directive("deprecated", _Deprecated)
    directives.register_directive("attribute", _Attribute)
