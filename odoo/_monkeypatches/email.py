import email.message
import email.policy
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:
    _EmailPolicyBase = email.policy.EmailPolicy[email.message.EmailMessage[Any, Any]]
else:
    _EmailPolicyBase = email.policy.EmailPolicy

RFC5322_IDENTIFICATION_HEADERS = {
    "message-id",
    "in-reply-to",
    "references",
    "resent-message-id",
}
USER_DEFINED_HEADERS = {"bcc", "cc", "from", "reply-to", "subject", "to"}


class IdentificationFieldsNoFoldPolicy(_EmailPolicyBase):
    _no_fold_policy: Any
    _max_fold_policy: Any

    @override
    def _fold(self, name: str, value: str, *args, **kwargs) -> str:  # type: ignore[misc]
        lname = name.lower()
        if lname in RFC5322_IDENTIFICATION_HEADERS:
            return self._no_fold_policy._fold(name, value, *args, **kwargs)
        if lname in USER_DEFINED_HEADERS:
            return self._max_fold_policy._fold(name, value, *args, **kwargs)
        return super()._fold(name, value, *args, **kwargs)  # type: ignore[misc]


def patch_module() -> None:
    if isinstance(email.policy.SMTP, IdentificationFieldsNoFoldPolicy):
        return

    stdlib_smtp = email.policy.SMTP
    IdentificationFieldsNoFoldPolicy._no_fold_policy = stdlib_smtp.clone(
        max_line_length=None
    )
    IdentificationFieldsNoFoldPolicy._max_fold_policy = stdlib_smtp.clone(
        max_line_length=998
    )
    email.policy.SMTP = IdentificationFieldsNoFoldPolicy(linesep=stdlib_smtp.linesep)
