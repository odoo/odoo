import re
from pathlib import Path

from lxml import etree

from odoo.tests import tagged

from .lint_case import LintCase

_PARSER = etree.XMLParser(remove_comments=True)

ACTION_MODELS = frozenset(
    {
        "ir.actions.act_window",
        "ir.actions.server",
        "ir.actions.report",
        "ir.actions.client",
        "ir.actions.act_url",
    }
)

MINOR_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "from",
        "in",
        "into",
        "nor",
        "of",
        "on",
        "onto",
        "or",
        "over",
        "per",
        "the",
        "to",
        "upon",
        "via",
        "vs",
        "with",
    }
)

WORD = re.compile(r"(?<![\w(])[^\W\d_][\w'’.&-]*")

NON_ENGLISH_LABELS = frozenset({"Fiche de paye"})


def _fields(record):
    return {
        field.get("name"): field
        for field in record.iterfind("field")
        if field.get("name")
    }


def _is_bound(fields):
    binding = fields.get("binding_model_id")
    if binding is None:
        return False
    return bool(binding.get("ref")) or binding.get("eval") not in (
        None,
        "False",
        "0",
        "None",
    )


def _title_case_violations(name):
    violations = []
    sentence_start = True
    for token in name.split():
        for word in WORD.findall(token):
            if (
                word[0].islower()
                and not any(char.isupper() for char in word[1:])
                and (sentence_start or word not in MINOR_WORDS)
            ):
                violations.append(word)
            sentence_start = False
        if token.endswith(":"):
            sentence_start = True
    return violations


def iter_bound_actions(paths):
    for path in paths:
        try:
            tree = etree.parse(str(path), _PARSER)
        except etree.XMLSyntaxError, OSError:
            continue
        for record in tree.iter("record"):
            if record.get("model") not in ACTION_MODELS:
                continue
            fields = _fields(record)
            name = fields.get("name")
            if name is None or not _is_bound(fields):
                continue
            yield path, record, fields, (name.text or "").strip()


@tagged("post_install", "-at_install")
class ContextualMenuLinter(LintCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.data_files = [
            Path(path)
            for path in cls.iter_module_files("*.xml")
            if "/static/" not in path and "/tests/" not in path
        ]
        cls.bound = list(iter_bound_actions(cls.data_files))

    def test_bound_action_names_are_title_case(self):
        findings = [
            f"{path}:{record.sourceline} {record.get('id')}: {name!r} "
            f"(lowercase {', '.join(words)})"
            for path, record, _fields, name in self.bound
            if name not in NON_ENGLISH_LABELS
            and (words := _title_case_violations(name))
        ]
        self.assert_ratchet(
            findings,
            "contextual_menu_title_case",
            "bound actions whose name is not Title Case",
            "Capitalize every word of the menu label except articles, conjunctions "
            "and short prepositions (coding_guidelines.rst, contextual menus).",
        )

    def test_bound_dialog_actions_end_with_an_ellipsis(self):
        findings = [
            f"{path}:{record.sourceline} {record.get('id')}: {name!r}"
            for path, record, fields, name in self.bound
            if record.get("model") == "ir.actions.act_window"
            and (fields.get("target") is not None)
            and (fields["target"].text or "").strip() == "new"
            and (
                fields.get("binding_type") is None
                or (fields["binding_type"].text or "").strip() == "action"
            )
            and not name.endswith("…")
        ]
        self.assert_ratchet(
            findings,
            "contextual_menu_dialog_ellipsis",
            "bound actions opening a dialog whose label does not end with '…'",
            "Append '…' to the label of a contextual action that asks for more "
            "input before it acts.",
        )

    def test_view_buttons_leave_the_gear_hotkey_free(self):
        findings = []
        for path in self.data_files:
            try:
                tree = etree.parse(str(path), _PARSER)
            except etree.XMLSyntaxError, OSError:
                continue
            findings.extend(
                f"{path}:{button.sourceline} {button.get('name') or button.get('string')}"
                for button in tree.iter("button")
                if button.get("data-hotkey") == "u" and button.get("close") is None
            )
        self.assert_ratchet(
            findings,
            "contextual_menu_hotkey_u",
            "view buttons bound to 'u', the gear menu's hotkey",
            "Pick another data-hotkey; 'u' opens the gear menu and the first "
            "visible match wins.",
        )
