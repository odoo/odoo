# ruff: noqa: PGH004
# ruff: noqa
import odoo
from odoo.exceptions import ValidationError, LockError
from odoo.tools.translate import _, _lt

foo = "foo"
# ruleid: missing-gettext
odoo.exceptions.ValidationError("foo")
# ruleid: missing-gettext
ValidationError("foo")
# ruleid: missing-gettext
ValidationError(foo)
# ok: missing-gettext
LockError("foo")
# ok: missing-gettext
ValidationError(_("foo"))
# ok: missing-gettext
ValidationError("foo" + str(42))
def foo(key_response):
    # ruleid: missing-gettext
    ValidationError(f"Failed to get user delegation key: {key_response.content}")
    # ruleid: missing-gettext
    ValidationError(f"Failed to get user delegation key: {key_response.content}")  # nosem: gettext-variable
    # ruleid: missing-gettext
    ValidationError(f"Failed to get user delegation key: {key_response.content}")  # nosemgrep: gettext-variable
    # ok: missing-gettext
    ValidationError(f"Failed to get user delegation key: {key_response.content}")  # nosem: missing-gettext
    # ok: missing-gettext
    ValidationError(f"Failed to get user delegation key: {key_response.content}")  # nosemgrep: missing-gettext



# ruleid: gettext-variable
_("foo" + str(42))
# ruleid: gettext-variable
_(foo)
# ok: gettext-variable
_("foo")

# ok: gettext-placeholders
_("foo %s bar", 42)
# ok: gettext-placeholders
_("foo %(a)s %(b)s bar", a=1, b=2)
# ruleid: gettext-placeholders
_("foo %s %s bar", 1, 2)
def some_func(self, things):
    # ruleid: gettext-placeholders
    self.env._("something %s %s", *things)
# ok: gettext-placeholders
_("shouldn't match escaped %%s %%s")
# ruleid: gettext-placeholders
_lt("with fancy placeholders: %03.14d %-xL")

# ruleid: gettext-repr
_("foo %r bar", 42)
# ruleid: gettext-repr
_("foo %(a)r bar", a=42)
# ruleid: gettext-repr
_("foo %(a)s %(b)r bar", a=1, b=2)
# ruleid: gettext-repr
_("%r shouldn't be part of translated strings")
# ruleid: gettext-repr
_lt("%(with_placeholders_in_between)r")