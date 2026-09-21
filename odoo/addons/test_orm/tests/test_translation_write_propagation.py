import odoo.tests
from odoo import Command


@odoo.tests.tagged("post_install", "-at_install")
class TestTranslationWritePropagation(odoo.tests.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.Model = cls.env["test_orm.prefetch"]

    def stored(self, record):
        record.flush_recordset(["name"])
        self.env.cr.execute(
            "SELECT name FROM test_orm_prefetch WHERE id = %s", (record.id,)
        )
        return self.env.cr.fetchone()[0]

    def test_echo_language_follows_the_write(self):
        record = self.Model.with_context(lang="fr_FR").create({"name": "Couteau"})
        self.assertEqual(
            self.stored(record),
            {"en_US": "Couteau", "fr_FR": "Couteau"},
            "sanity: creating in fr_FR materialises both keys",
        )

        record.with_context(lang="fr_FR").name = "Grand Couteau"

        self.assertEqual(
            self.stored(record), {"en_US": "Grand Couteau", "fr_FR": "Grand Couteau"}
        )

    def test_authored_translation_is_never_clobbered(self):
        record = self.Model.create({"name": "Knife"})
        record.with_context(lang="fr_FR").name = "Couteau"

        record.with_context(lang="fr_FR").name = "Petit Couteau"

        self.assertEqual(
            self.stored(record), {"en_US": "Knife", "fr_FR": "Petit Couteau"}
        )

    def test_authored_translation_survives_a_source_write(self):
        record = self.Model.create({"name": "Knife"})
        record.with_context(lang="fr_FR").name = "Couteau"

        record.with_context(lang="en_US").name = "Steel Knife"

        self.assertEqual(
            self.stored(record), {"en_US": "Steel Knife", "fr_FR": "Couteau"}
        )

    def test_first_translation_of_a_source_only_record_creates_it(self):
        record = self.Model.create({"name": "Knife"})
        self.assertEqual(
            self.stored(record), {"en_US": "Knife"}, "sanity: only the source key"
        )

        record.with_context(lang="fr_FR").name = "Couteau"

        self.assertEqual(self.stored(record), {"en_US": "Knife", "fr_FR": "Couteau"})

    def test_update_field_translations_still_writes_one_language(self):
        record = self.Model.with_context(lang="fr_FR").create({"name": "Couteau"})

        record.update_field_translations("name", {"fr_FR": "Couteau de Chef"})

        self.assertEqual(
            self.stored(record), {"en_US": "Couteau", "fr_FR": "Couteau de Chef"}
        )

    def test_batch_write_decides_per_record(self):
        echo = self.Model.with_context(lang="fr_FR").create({"name": "Couteau"})
        translated = self.Model.create({"name": "Knife"})
        translated.with_context(lang="fr_FR").name = "Fourchette"
        source_only = self.Model.create({"name": "Spoon"})

        records = echo | translated | source_only
        records.with_context(lang="fr_FR").write({"name": "Commun"})

        self.assertEqual(
            self.stored(echo),
            {"en_US": "Commun", "fr_FR": "Commun"},
            "the echo follows",
        )
        self.assertEqual(
            self.stored(translated),
            {"en_US": "Knife", "fr_FR": "Commun"},
            "the authored translation keeps its source term",
        )
        self.assertEqual(
            self.stored(source_only),
            {"en_US": "Spoon", "fr_FR": "Commun"},
            "a source-only record gains a translation",
        )

    def test_single_language_database_is_untouched(self):
        record = self.Model.create({"name": "Knife"})

        record.with_context(lang="en_US").name = "Steel Knife"

        self.assertEqual(self.stored(record), {"en_US": "Steel Knife"})

    def _deactivate_source_language(self):
        english = self.env.ref("base.lang_en")
        replacement = self.env["res.lang"].search(
            [("code", "!=", "en_US"), ("active", "=", True)], limit=1
        )
        self.assertTrue(replacement, "setUpClass activates fr_FR")
        self.env["res.partner"].with_context(active_test=False).search([]).write(
            {"lang": replacement.code}
        )
        websites = self.env.get("website")
        if websites is not None:
            for website in websites.sudo().with_context(active_test=False).search([]):
                if english in website.language_ids:
                    website.write(
                        {
                            "default_lang_id": replacement.id,
                            "language_ids": [
                                Command.set((website.language_ids - english).ids)
                                if website.language_ids - english
                                else Command.set(replacement.ids)
                            ],
                        }
                    )
        english.active = False

    def test_uninstalled_source_language_is_not_an_echo_anchor(self):
        self.env["res.lang"]._activate_lang("es_ES")
        self._deactivate_source_language()
        record = self.Model.create({"name": "Knife"})

        record.with_context(lang="fr_FR").name = "Couteau"
        record.with_context(lang="es_ES").name = "Cuchillo"
        self.assertEqual(
            self.stored(record),
            {"en_US": "Cuchillo", "es_ES": "Cuchillo", "fr_FR": "Couteau"},
            "sanity: the es_ES write mirrored itself into the unused source key",
        )

        record.with_context(lang=None).name = "Sans Langue"

        self.assertEqual(
            self.stored(record),
            {"en_US": "Sans Langue", "es_ES": "Cuchillo", "fr_FR": "Couteau"},
            "the authored Spanish term must survive a write to the source key",
        )

    def test_one_installed_language_costs_no_mirroring_read(self):
        """A follower is another INSTALLED language holding the same term, so
        with one language there is nobody to follow. The read that looks for
        one used to run per write, which made a loop writing one record at a
        time cost one SELECT per record."""
        records = self.Model.create([{"name": f"n{i}"} for i in range(20)])
        self.env.flush_all()

        english_only = self.env["res.lang"].search([("code", "!=", "en_US")])
        english_only.write({"active": False})
        self.env.registry.clear_all_caches()
        self.assertEqual(
            self.env["res.lang"].get_installed(),
            [("en_US", "English (US)")],
            "test premise: one language installed",
        )

        before = self.env.cr.sql_statement_count
        for index, record in enumerate(records):
            record.with_context(lang="en_US").name = f"edited{index}"
        self.env.flush_all()
        statements = self.env.cr.sql_statement_count - before

        self.assertLess(
            statements,
            len(records),
            f"{len(records)} single-record writes cost {statements} statements; "
            f"a per-record mirroring read is back",
        )
        self.assertEqual(self.stored(records[0]), {"en_US": "edited0"})

    def test_a_second_language_still_follows_the_edit(self):
        """The single-language short-circuit must not reach a database that
        has a second language.

        Only the follower half is asserted here: that a language holding the
        same term still follows. The other half, that an authored translation
        survives a source write, is `test_authored_translation_survives_a_
        source_write` above, and it exercises the same code path.
        """
        follower = self.Model.with_context(lang="fr_FR").create({"name": "Same"})
        self.assertEqual(
            self.stored(follower),
            {"en_US": "Same", "fr_FR": "Same"},
            "sanity: creating in fr_FR materialises both keys, equal",
        )

        follower.with_context(lang="en_US").name = "Edited"

        self.assertEqual(
            self.stored(follower),
            {"en_US": "Edited", "fr_FR": "Edited"},
            "a language holding the same term still follows the edit",
        )
