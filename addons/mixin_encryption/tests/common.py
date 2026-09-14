"""A working Fernet key for any suite that touches encrypted material.

Every model built on ``mixin.encryption`` refuses to store anything without
``ODOO_API_ENCRYPTION_KEY`` in the process environment -- deliberately, because the
key must not live in the database. The consequence for tests is that a suite which
does not provide one does not skip: it fails, once per test that stores a secret,
with ``ValidationError: Encryption key not configured!``.

Measured on this workspace, that is 61 failures across ``credential`` and
``integration`` on a run where the variable happened to be unset -- and no CI lane
runs either suite, so nobody sees them go green anywhere else. Sixty-one red tests
in the two modules a change was just made to is exactly the shape of an
unattributable failure, and it costs a diagnostic detour every time.

This is where the copy belongs: the module that owns the variable is the one that
should say how a test gets one. Seventeen test files carried their own when that
was written; what is left references the variable for a reason this cannot serve
-- rotating between two named keys, or asserting what an invalid one does -- and
those keep managing their own.

One shape in particular is worth not going back to. A class that called
``os.environ.setdefault`` installed a key for the rest of the process and never
removed it, so three other suites in the same module passed only while it ran
before them, and a suite that should have failed for want of a key could not.
``patch.dict`` through ``enterClassContext`` ends with the class.

Usage::

    class TestSomething(EncryptionKeyCase, TransactionCase):
        pass

An environment that already has a key keeps it, so a developer running against a
real key still tests against that key.
"""

import os
from unittest.mock import patch

from cryptography.fernet import Fernet


class EncryptionKeyCase:
    """Mixin that guarantees a usable ``ODOO_API_ENCRYPTION_KEY`` for the class.

    Mix it in *before* the test case, so its ``setUpClass`` runs first and the key
    is in place before any fixture stores a secret.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not os.environ.get("ODOO_API_ENCRYPTION_KEY"):
            cls.enterClassContext(
                patch.dict(
                    os.environ,
                    {"ODOO_API_ENCRYPTION_KEY": Fernet.generate_key().decode()},
                )
            )
            # The key version is cached per process, so a suite that installs a key
            # after something already looked would otherwise keep the old answer.
            cls.env["mixin.encryption"]._invalidate_key_version_cache()
            cls.addClassCleanup(
                cls.env["mixin.encryption"]._invalidate_key_version_cache
            )
