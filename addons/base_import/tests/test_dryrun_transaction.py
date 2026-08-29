"""What a dry-run import must leave behind: nothing.

``execute_import(dryrun=True)`` wraps the whole load in a savepoint and rolls it
back, so a user can check a mapping without touching their data. That promise
only holds if the rollback restores the ORM as well as the SQL, and nothing
checked that it did.

It did not. ``execute_import`` opened its savepoint with ``flush=False``, which
is exactly the case our own ``BaseCursor.savepoint`` docstring warns about: a
non-flushing savepoint undoes the SQL and leaves ORM state alone, so the caller
"must invalidate what it touched itself on the rollback path, or stale ORM state
can survive the SQL rollback". ``base_import`` never did -- there is not one
``invalidate`` call in the module. Two things went wrong, and the first is worse
than the feature it protects:

* **The caller's own pending write disappeared.** Anything written but not yet
  flushed before the import -- an ordinary ``record.field = value`` earlier in
  the same request -- was still in the ``towrite`` buffer when ``load()`` flushed
  it, which put the ``UPDATE`` *inside* the dry-run's savepoint. The rollback
  then took it along. The user edited a record, ran a test import, and the edit
  was silently gone.
* **The cache kept values the database had discarded.** A record the dry-run
  itself updated stayed in ``env.cache`` holding the rolled-back value for the
  rest of the transaction.

Both are asserted below against ``res.partner`` because ``base_import`` has no
models of its own; the behaviour is the transaction's, not the model's.
"""

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class DryRunLeavesNoTrace(TransactionCase):
    _OPTS = {"has_headers": True, "quoting": '"', "separator": ",", "encoding": "utf-8"}

    def _imp(self, csv, res_model="res.partner"):
        return self.env["base_import.import"].create(
            {
                "res_model": res_model,
                "file": csv,
                "file_type": "text/csv",
                "file_name": "dryrun.csv",
            }
        )

    def test_dryrun_keeps_a_pending_write_made_before_it(self):
        """An unflushed write from before the import survives the rollback."""
        partner = self.env["res.partner"].create({"name": "Before"})
        self.env.flush_all()

        # Not flushed on purpose: this is the ordinary shape of a write made
        # earlier in the same request, and it is what used to be lost.
        partner.name = "Pending"

        result = self._imp(b"name\nImported Row\n").execute_import(
            ["name"], ["Name"], dict(self._OPTS), dryrun=True
        )
        self.assertFalse(result["messages"])

        # Read through to the database: the point is what was committed to the
        # transaction, not what the cache still remembers.
        self.env.invalidate_all()
        self.assertEqual(
            partner.name,
            "Pending",
            "a dry-run import rolled back a write the caller made before it",
        )

    def test_dryrun_leaves_no_stale_value_in_cache(self):
        """A record the dry-run updated is not left cached with the lost value."""
        partner = self.env["res.partner"].create({"name": "Orig"})
        self.env.flush_all()

        csv = ("id,name\n%d,Updated\n" % partner.id).encode()
        result = self._imp(csv).execute_import(
            [".id", "name"], ["Id", "Name"], dict(self._OPTS), dryrun=True
        )
        self.assertFalse(result["messages"])

        # Deliberately no invalidate_all() here: reading straight after the
        # dry-run is what a caller does, and the cache is what answers.
        self.assertEqual(
            partner.name,
            "Orig",
            "a dry-run import left the rolled-back value in env.cache",
        )
