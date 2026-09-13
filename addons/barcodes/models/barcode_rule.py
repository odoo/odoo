import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# A group that is itself quantified and whose body contains an unbounded
# quantifier -- `(x+x+)+`, `(a+)*`, `(\d{2,})+` -- is the shape that turns a
# linear match into an exponential one. Patterns run on every scan, so they are
# rejected on write rather than relied upon to be well-behaved.
_NESTED_QUANTIFIER = re.compile(
    r"""\(                          # a group -- capturing, (?:...), either way
        [^()]*
        (?: [+*] | \{\d+,\d*\} )    # whose body contains an unbounded repetition
        [^()]*
        \)
        \s*
        (?: [+*] | \{\d+,\d*\} )    # and which is itself repeated
    """,
    re.VERBOSE,
)

# A quantified group whose alternatives are plain literals is a second
# ReDoS shape `_NESTED_QUANTIFIER` does not see: none of `(a|aa)`'s branches
# contains its own quantifier, yet one alternative being a prefix of another
# (`a` of `aa`) lets the engine account for the same input two ways, and
# `+`/`*` turns that ambiguity exponential on a non-matching tail.
_QUANTIFIED_GROUP = re.compile(
    r"""\(
        (?P<body>[^()]*)
        \)
        \s*
        (?: [+*] | \{\d+,\d*\} )
    """,
    re.VERBOSE,
)
_LITERAL_ALTERNATIVE = re.compile(r"^[A-Za-z0-9]+$")


def _has_ambiguous_alternation(pattern):
    """Detect a quantified group whose literal alternatives share a prefix.

    Only plain-literal alternatives (no regex metacharacters) are checked:
    prefix analysis on an arbitrary sub-pattern is not sound in general, so
    this only raises the bar rather than closing the class of bug for good.
    """
    for group in _QUANTIFIED_GROUP.finditer(pattern):
        alternatives = group.group("body").split("|")
        if len(alternatives) < 2 or not all(
            _LITERAL_ALTERNATIVE.match(alt) for alt in alternatives
        ):
            continue
        for i, alt in enumerate(alternatives):
            if any(
                alt.startswith(other) or other.startswith(alt)
                for other in alternatives[i + 1 :]
            ):
                return True
    return False


class BarcodeRule(models.Model):
    _name = "barcode.rule"
    _description = "Barcode Rule"
    _order = "sequence asc, id"

    name = fields.Char(
        string="Rule Name",
        required=True,
        help="An internal identification for this barcode nomenclature rule",
    )
    barcode_nomenclature_id = fields.Many2one(
        comodel_name="barcode.nomenclature",
        index="btree_not_null",
    )
    sequence = fields.Integer(
        help="Used to order rules such that rules with a smaller sequence match first"
    )
    encoding = fields.Selection(
        selection=[
            ("any", "Any"),
            ("ean13", "EAN-13"),
            ("ean8", "EAN-8"),
            ("upca", "UPC-A"),
        ],
        default="any",
        required=True,
        help="This rule will apply only if the barcode is encoded with the specified encoding",
    )
    type = fields.Selection(
        selection=[
            ("alias", "Alias"),
            ("product", "Unit Product"),
        ],
        default="product",
        required=True,
    )
    pattern = fields.Char(
        string="Barcode Pattern",
        default=".*",
        required=True,
        help="The barcode matching pattern",
    )
    alias = fields.Char(help="The matched pattern will alias to this barcode")

    @api.constrains("type", "alias")
    def _check_alias(self):
        for rule in self:
            if rule.type == "alias" and not rule.alias:
                raise ValidationError(
                    _(
                        "Barcode rule %(name)s is an alias rule, so it needs an alias to point at.",
                        name=rule.name,
                    )
                )

    @api.constrains("pattern")
    def _check_pattern(self):
        for rule in self:
            p = (
                rule.pattern.replace("\\\\", "X")
                .replace("\\{", "X")
                .replace("\\}", "X")
            )
            findall = re.findall(r"[{]|[}]", p)  # p does not contain escaped { or }
            if len(findall) == 2:
                if not re.search(r"[{][N]*[D]*[}]", p):
                    raise ValidationError(
                        _(
                            "There is a syntax error in the barcode pattern %(pattern)s: braces can only contain N's followed by D's.",
                            pattern=rule.pattern,
                        )
                    )
                if re.search(r"[{][}]", p):
                    raise ValidationError(
                        _(
                            "There is a syntax error in the barcode pattern %(pattern)s: empty braces.",
                            pattern=rule.pattern,
                        )
                    )
            elif len(findall) != 0:
                raise ValidationError(
                    _(
                        "There is a syntax error in the barcode pattern %(pattern)s: a rule can only contain one pair of braces.",
                        pattern=rule.pattern,
                    )
                )
            elif p == "*":
                raise ValidationError(
                    _(" '*' is not a valid Regex Barcode Pattern. Did you mean '.*'?")
                )
            bare_pattern = re.sub(r"{N*D*}", "", p)
            try:
                re.compile(bare_pattern)
            except re.error as e:
                raise ValidationError(
                    _(
                        "The barcode pattern %(pattern)s does not lead to a valid regular expression.",
                        pattern=rule.pattern,
                    )
                ) from e
            if _NESTED_QUANTIFIER.search(bare_pattern):
                raise ValidationError(
                    _(
                        "The barcode pattern %(pattern)s nests one repetition inside another (for instance '(x+x+)+'). "
                        "Such a pattern can take exponentially long to match and would block the server on every scan.",
                        pattern=rule.pattern,
                    )
                )
            if _has_ambiguous_alternation(bare_pattern):
                raise ValidationError(
                    _(
                        "The barcode pattern %(pattern)s repeats a group whose alternatives share a prefix (for instance '(a|aa)+'). "
                        "Such a pattern can take exponentially long to match and would block the server on every scan.",
                        pattern=rule.pattern,
                    )
                )
