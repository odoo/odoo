"""Pure-Python value object for the non-I/O part of an Environment."""

from dataclasses import dataclass

from odoo.tools import frozendict


@dataclass(frozen=True, slots=True)
class EnvContext:
    """Pure-Python value object: the non-I/O subset of an Environment.

    Contains only data that requires no database connection — the current
    user id, context dict, and superuser flag. Derived properties (``lang``,
    ``tz``) read directly from the context dict without DB validation.

    The full :class:`~odoo.orm.runtime.environment.Environment` provides
    DB-backed versions (``env.lang`` validates against ``res.lang``;
    ``env.tz`` falls back to ``env.user.tz``). ``EnvContext`` is suitable
    for logic that needs identity and context but not record access::

        ctx = EnvContext(uid=1, context={'lang': 'es_MX', 'tz': 'America/Mexico_City'})
        assert ctx.lang == 'es_MX'
        assert ctx.tz == 'America/Mexico_City'
        ctx2 = ctx.with_context(no_recompute=True)
        assert ctx2.context['no_recompute'] is True
        assert ctx.context.get('no_recompute') is None   # original unchanged

    """

    uid: int
    context: frozendict
    su: bool = False

    def __post_init__(self):
        # Normalise context to frozendict so equality/hashing work correctly.
        if not isinstance(self.context, frozendict):
            object.__setattr__(self, "context", frozendict(self.context))

    @property
    def lang(self) -> str | None:
        """Language code from context only — no DB validation."""
        return self.context.get("lang")

    @property
    def tz(self) -> str:
        """Timezone string from context — defaults to ``'UTC'``."""
        return self.context.get("tz") or "UTC"

    def with_su(self, flag: bool = True) -> EnvContext:
        """Return a new EnvContext with the superuser flag set to *flag*."""
        return EnvContext(self.uid, self.context, flag)

    def with_context(self, **overrides) -> EnvContext:
        """Return a new EnvContext with *overrides* merged into the context."""
        return EnvContext(self.uid, frozendict(self.context | overrides), self.su)
