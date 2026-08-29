"""How much of the ormcache a dry-run is allowed to throw away.

A dry-run rolls its rows back, so any registry cache it refilled from those rows
has to go. The module took the widest possible reading of that and called
``clear_all_caches()``, which drops every group in ``CACHES_BY_KEY`` -- including
``assets`` and ``routing``, the two most expensive caches in the process and the
two a data import cannot have touched. The worker that served the import then
paid to rebuild its routing map and its asset bundles, on every dry-run, for
nothing.

Clearing only ``default``, ``groups`` and ``stable`` is enough, and the reason is
not that imports never invalidate ``assets`` -- it is that when they do, they say
so. ``ir.asset`` calls ``clear_cache("assets")`` in its own ``write``, which puts
the group in ``registry.cache_invalidated``, and the ``reset_changes()`` on the
next line re-clears everything in that set. The narrow clear plus
``reset_changes()`` therefore still drops exactly what the import dirtied.

Both halves are asserted below, because only the second one makes the first
safe: the sentinels survive an ordinary import, and do not survive one that
writes the model feeding the cache.
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.constants import CACHES_BY_KEY

_NARROW_KEYS = ("default", "groups", "stable")


@tagged("post_install", "-at_install")
class DryRunClearsOnlyWhatItDirtied(TransactionCase):
    _OPTS = {"has_headers": True, "quoting": '"', "separator": ",", "encoding": "utf-8"}

    def _seed_sentinels(self):
        """Put a recognisable entry in every ormcache LRU, and take it out after.

        The LRUs are process-global and not transactional, so a sentinel is the
        only way to see what a rollback did to them -- and it has to be cleaned
        up by hand, since nothing else will.
        """
        lrus = self.env.registry.ormcache_lrus
        for name, lru in lrus.items():
            lru[("SENTINEL", name)] = 1
        self.addCleanup(self._drop_sentinels)
        return lrus

    def _drop_sentinels(self):
        for name, lru in self.env.registry.ormcache_lrus.items():
            lru.pop(("SENTINEL", name), None)

    def _survivors(self):
        return {
            name
            for name, lru in self.env.registry.ormcache_lrus.items()
            if ("SENTINEL", name) in lru
        }

    def _dryrun(self, res_model, csv, fields_, columns):
        imp = self.env["base_import.import"].create(
            {
                "res_model": res_model,
                "file": csv,
                "file_type": "text/csv",
                "file_name": "dryrun.csv",
            }
        )
        result = imp.execute_import(fields_, columns, dict(self._OPTS), dryrun=True)
        self.assertFalse(result["messages"])

    def test_dryrun_keeps_the_caches_it_cannot_have_dirtied(self):
        """Importing partners leaves the asset and routing caches alone."""
        lrus = self._seed_sentinels()

        self._dryrun("res.partner", b"name\nImported Row\n", ["name"], ["Name"])

        cleared = set()
        for key in _NARROW_KEYS:
            cleared |= set(CACHES_BY_KEY[key])
        expected = set(lrus) - cleared

        self.assertEqual(
            self._survivors(),
            expected,
            "a dry-run cleared more of the ormcache than the rows it rolled back",
        )
        # Named explicitly: these two are the whole point of the change, and an
        # expression-only assertion would not say so if CACHES_BY_KEY moved.
        self.assertIn("routing", expected)
        self.assertIn("assets", expected)

    def test_dryrun_still_clears_a_cache_the_import_invalidated(self):
        """Importing ir.asset drops `assets`, because the write reported it.

        Unlike the test above, this one passes both before and after the
        narrowing -- `clear_all_caches()` dropped `assets` too, just for a
        cruder reason. It is a guard, not the proof: it fails if someone
        narrows the set further, or if `ir.asset` stops reporting what it
        dirtied, which are the two ways the narrowing could later turn unsafe.

        Asserted at the seam rather than by counting survivors. The sentinels
        cannot carry this one on their own: `reset_changes()` also has a
        registry-reload branch, and `_setup_models__` opens with
        `self._caches.clear_all()`, so whenever a module update leaves the
        registry flagged -- which is exactly the case while this suite runs
        under `-u base_import` -- every LRU is wiped for a reason that has
        nothing to do with the narrowing. Checking what reached
        `cache_invalidated` states the actual guarantee and survives that.
        """
        self._seed_sentinels()
        seen = {}
        registry_cls = type(self.env.registry)
        original = registry_cls.reset_changes

        def spy(registry):
            seen.setdefault("cache_invalidated", set(registry.cache_invalidated))
            return original(registry)

        self.patch(registry_cls, "reset_changes", spy)

        self._dryrun(
            "ir.asset",
            b"name,bundle,path\nzzz_probe,web.assets_backend,/web/static/src/probe.js\n",
            ["name", "bundle", "path"],
            ["name", "bundle", "path"],
        )

        self.assertIn(
            "assets",
            seen.get("cache_invalidated", set()),
            "ir.asset.write must report `assets` so reset_changes() re-clears it",
        )
        self.assertNotIn(
            "assets",
            self._survivors(),
            "the import wrote ir.asset, so the assets cache had to be dropped",
        )
