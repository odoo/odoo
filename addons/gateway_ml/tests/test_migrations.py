import importlib.util
from pathlib import Path

from odoo.tests import TransactionCase, tagged


def _load(version):
    path = Path(__file__).parent.parent / "migrations" / version / "post-migrate.py"
    spec = importlib.util.spec_from_file_location(f"api_ai_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seeded_row(env, provider_code, xmlid, code, **vals):
    provider = env["gateway.ml.provider"].search([("code", "=", provider_code)])
    row = env["gateway.ml.model"].create(
        {"provider_id": provider.id, "name": code, "code": code, **vals}
    )
    env["ir.model.data"].create(
        {
            "module": "gateway_ml",
            "name": xmlid,
            "model": "gateway.ml.model",
            "res_id": row.id,
            "noupdate": True,
        }
    )
    return row


@tagged("post_install", "-at_install")
class TestSeedPriceCorrection(TransactionCase):
    SEEDED = {
        "cost_per_1m_input": 2.50,
        "cost_per_1m_output": 10.00,
        "cost_per_1m_image": 2.125,
    }

    def setUp(self):
        super().setUp()
        self.migration = _load("1.17.0")
        self.mini = _seeded_row(
            self.env, "openai", "ai_model_openai_gpt_4o_mini", "gpt-4o-mini"
        )

    def _migrate(self, version="19.0.1.16.0"):
        self.env.flush_all()
        self.migration.migrate(self.env.cr, version)
        self.env.invalidate_all()

    def test_a_row_still_carrying_the_seed_is_corrected(self):
        self.mini.write(self.SEEDED)
        self._migrate()
        self.assertEqual(
            (self.mini.cost_per_1m_input, self.mini.cost_per_1m_output),
            (0.15, 0.60),
        )

    def test_a_row_an_administrator_touched_is_left_alone(self):
        self.mini.write({**self.SEEDED, "cost_per_1m_input": 2.40})
        self._migrate()
        self.assertEqual(
            (self.mini.cost_per_1m_input, self.mini.cost_per_1m_output),
            (2.40, 10.00),
        )

    def test_a_fresh_install_is_not_migrated(self):
        self.mini.write(self.SEEDED)
        self._migrate(version=None)
        self.assertEqual(self.mini.cost_per_1m_input, 2.50)


@tagged("post_install", "-at_install")
class TestFallbackRelationCarried(TransactionCase):
    def test_the_old_relation_becomes_ordered_hops(self):
        claude = self.env.ref("gateway_ml.ai_model_claude_sonnet_5")
        later_provider = self.env["gateway.ml.provider"].search(
            [("code", "=", "moonshot")]
        )
        earlier_provider = self.env["gateway.ml.provider"].search(
            [("code", "=", "deepseek")]
        )
        self.assertLess(earlier_provider.sequence, later_provider.sequence)
        created_first = self.env["gateway.ml.model"].create(
            {"provider_id": later_provider.id, "name": "Kimi hop", "code": "kimi-hop"}
        )
        created_second = self.env["gateway.ml.model"].create(
            {"provider_id": earlier_provider.id, "name": "DS hop", "code": "ds-hop"}
        )
        self.env.flush_all()
        cr = self.env.cr
        cr.execute("CREATE TABLE ai_model_fallback_rel (model_id int, fallback_id int)")
        cr.execute(
            "INSERT INTO ai_model_fallback_rel VALUES (%s, %s), (%s, %s), (%s, %s)",
            (
                claude.id,
                created_first.id,
                claude.id,
                created_second.id,
                claude.id,
                claude.id,
            ),
        )
        _load("1.18.0").migrate(cr, "19.0.1.17.0")
        self.env.invalidate_all()

        self.assertEqual(
            claude.fallback_model_ids.ids,
            [created_second.id, created_first.id],
            "hops run in provider order, which here is the reverse of creation "
            "order, and a self-hop is not carried",
        )
        cr.execute("SELECT to_regclass('ai_model_fallback_rel')")
        self.assertIsNone(cr.fetchone()[0])

    def test_providers_tied_on_sequence_keep_their_name_order(self):
        claude = self.env.ref("gateway_ml.ai_model_claude_sonnet_5")
        moonshot = self.env["gateway.ml.provider"].search([("code", "=", "moonshot")])
        groq = self.env["gateway.ml.provider"].search([("code", "=", "groq")])
        (moonshot | groq).endpoint_id.write({"sequence": 5})
        by_moonshot = self.env["gateway.ml.model"].create(
            {"provider_id": moonshot.id, "name": "A hop", "code": "a-hop"}
        )
        by_groq = self.env["gateway.ml.model"].create(
            {"provider_id": groq.id, "name": "Z hop", "code": "z-hop"}
        )
        self.env.flush_all()
        cr = self.env.cr
        cr.execute("CREATE TABLE ai_model_fallback_rel (model_id int, fallback_id int)")
        cr.execute(
            "INSERT INTO ai_model_fallback_rel VALUES (%s, %s), (%s, %s)",
            (claude.id, by_moonshot.id, claude.id, by_groq.id),
        )
        _load("1.18.0").migrate(cr, "19.0.1.17.0")
        self.env.invalidate_all()
        self.assertEqual(
            claude.fallback_model_ids.ids,
            [by_groq.id, by_moonshot.id],
            "the Many2many ordered tied providers by provider name, Groq before "
            "Moonshot, before it looked at the models' own names",
        )

    def test_a_database_without_the_relation_is_left_alone(self):
        _load("1.18.0").migrate(self.env.cr, "19.0.1.17.0")


@tagged("post_install", "-at_install")
class TestExperimentalGeminiRetired(TransactionCase):
    def setUp(self):
        super().setUp()
        self.google = self.env["gateway.ml.provider"].search([("code", "=", "gemini")])
        self.current = self.env.ref("gateway_ml.ai_model_gemini_3_5_flash_lite")
        self.experimental = self.env["gateway.ml.model"].create(
            {
                "provider_id": self.google.id,
                "name": "Gemini 2.0 Flash (experimental)",
                "code": "gemini-2.0-flash-exp",
                "has_vision": True,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "gateway_ml",
                "name": "ai_model_gemini_2_0_flash_exp",
                "model": "gateway.ml.model",
                "res_id": self.experimental.id,
                "noupdate": True,
            }
        )

    def test_a_provider_still_on_the_seed_moves_and_the_seed_is_archived(self):
        self.google.default_model_id = self.experimental
        _load("1.18.0").migrate(self.env.cr, "19.0.1.17.0")
        self.assertEqual(self.google.default_model_id, self.current)
        self.assertFalse(self.experimental.active)

    def test_an_administrators_default_is_kept(self):
        chosen = self.env["gateway.ml.model"].create(
            {"provider_id": self.google.id, "name": "Pro", "code": "gemini-pro-x"}
        )
        self.google.default_model_id = chosen
        _load("1.18.0").migrate(self.env.cr, "19.0.1.17.0")
        self.assertEqual(self.google.default_model_id, chosen)


@tagged("post_install", "-at_install")
class TestProviderChainsCarried(TransactionCase):
    def test_a_provider_chain_becomes_a_hop_between_default_models(self):
        claude = self.env["gateway.ml.provider"].search([("code", "=", "claude")])
        openai = self.env["gateway.ml.provider"].search([("code", "=", "openai")])
        cr = self.env.cr
        cr.execute(
            "CREATE TABLE ai_provider_fallback_rel (provider_id int, fallback_id int)"
        )
        cr.execute(
            "INSERT INTO ai_provider_fallback_rel VALUES (%s, %s)",
            (claude.id, openai.id),
        )
        _load("1.14.0").migrate(cr, "19.0.1.13.0")
        self.env.invalidate_all()
        self.assertEqual(
            claude.default_model_id.fallback_model_ids, openai.default_model_id
        )


@tagged("post_install", "-at_install")
class TestShutDownSeedsReplaced(TransactionCase):
    def setUp(self):
        super().setUp()
        self.deepseek = self.env["gateway.ml.provider"].search(
            [("code", "=", "deepseek")]
        )
        self.flash = self.env.ref("gateway_ml.ai_model_deepseek_flash")
        self.chat = _seeded_row(
            self.env, "deepseek", "ai_model_deepseek_chat", "deepseek-chat"
        )
        self.claude = self.env.ref("gateway_ml.ai_model_claude_sonnet_5")

    def _migrate(self):
        self.env.flush_all()
        _load("1.19.0").migrate(self.env.cr, "19.0.1.18.0")
        self.env.invalidate_all()

    def test_a_provider_on_the_dead_id_moves_and_the_row_is_archived(self):
        self.deepseek.default_model_id = self.chat
        self._migrate()
        self.assertEqual(self.deepseek.default_model_id, self.flash)
        self.assertFalse(self.chat.active)

    def _hops(self, model):
        self.env.cr.execute(
            "SELECT fallback_id FROM gateway_ml_model_fallback WHERE model_id = %s "
            "ORDER BY sequence, id",
            (model.id,),
        )
        return [row[0] for row in self.env.cr.fetchall()]

    def test_hops_to_and_from_the_dead_id_follow_its_replacement(self):
        self.claude.fallback_model_ids = self.chat
        self.chat.fallback_model_ids = self.claude
        self._migrate()
        self.assertEqual(self._hops(self.claude), [self.flash.id])
        self.assertEqual(self._hops(self.flash), [self.claude.id])
        self.assertEqual(self._hops(self.chat), [])

    def test_a_hop_the_replacement_already_has_is_not_duplicated(self):
        self.claude.fallback_model_ids = self.chat | self.flash
        self._migrate()
        self.assertEqual(
            self._hops(self.claude),
            [self.flash.id],
            "the hop to the archived row would otherwise stay behind, hidden by "
            "fallback_model_ids and never run",
        )

    def test_an_administrators_default_is_kept(self):
        chosen = self.env["gateway.ml.model"].create(
            {"provider_id": self.deepseek.id, "name": "Pro", "code": "deepseek-v4-pro"}
        )
        self.deepseek.default_model_id = chosen
        self._migrate()
        self.assertEqual(self.deepseek.default_model_id, chosen)

    def test_a_vision_model_with_no_successor_is_archived_unless_default(self):
        groq = self.env["gateway.ml.provider"].search([("code", "=", "groq")])
        scout = _seeded_row(
            self.env,
            "groq",
            "ai_model_groq_llama_4_scout",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            kind="vision",
            has_vision=True,
        )
        self.assertTrue(groq.has_vision)
        self._migrate()
        self.assertFalse(scout.active)
        self.assertFalse(groq.has_vision)

    def test_a_fresh_install_is_not_migrated(self):
        self.deepseek.default_model_id = self.chat
        _load("1.19.0").migrate(self.env.cr, None)
        self.assertEqual(self.deepseek.default_model_id, self.chat)


@tagged("post_install", "-at_install")
class TestSeedLimitsCorrected(TransactionCase):
    SEEDED = {
        "max_context_window": 131072,
        "max_output_tokens": 32768,
        "cost_per_1m_input": 0,
        "cost_per_1m_output": 0,
    }

    def setUp(self):
        super().setUp()
        self.kimi = self.env.ref("gateway_ml.ai_model_moonshot_kimi_k3")

    def _migrate(self):
        self.env.flush_all()
        _load("1.19.0").migrate(self.env.cr, "19.0.1.18.0")
        self.env.invalidate_all()

    def test_a_row_still_carrying_the_seed_is_corrected(self):
        self.kimi.write(self.SEEDED)
        self._migrate()
        self.assertEqual(
            (
                self.kimi.max_context_window,
                self.kimi.max_output_tokens,
                self.kimi.cost_per_1m_input,
                self.kimi.cost_per_1m_output,
            ),
            (1048576, 1048576, 3.00, 15.00),
        )

    def test_a_row_an_administrator_priced_is_left_alone(self):
        self.kimi.write({**self.SEEDED, "cost_per_1m_input": 2.00})
        self._migrate()
        self.assertEqual(
            (self.kimi.max_context_window, self.kimi.cost_per_1m_input),
            (131072, 2.00),
        )


@tagged("post_install", "-at_install")
class TestAdministratorsRowAdopted(TransactionCase):
    def test_a_row_the_administrator_added_takes_the_seeds_external_id(self):
        flash = self.env.ref("gateway_ml.ai_model_deepseek_flash")
        self.env["ir.model.data"].search(
            [("module", "=", "gateway_ml"), ("name", "=", "ai_model_deepseek_flash")]
        ).unlink()
        self.env.flush_all()
        pre = Path(__file__).parent.parent / "migrations" / "1.19.0" / "pre-migrate.py"
        spec = importlib.util.spec_from_file_location("api_ai_1_19_0_pre", pre)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.18.0")
        self.env.invalidate_all()
        self.assertEqual(
            self.env.ref(
                "gateway_ml.ai_model_deepseek_flash", raise_if_not_found=False
            ),
            flash,
        )


@tagged("post_install", "-at_install")
class TestTimestampColumnSeeded(TransactionCase):
    def test_audio_models_already_read_with_timing_are_marked_timed(self):
        whisper = self.env.ref("gateway_ml.ai_model_openai_whisper_1")
        transcribe = self.env.ref("gateway_ml.ai_model_openai_gpt_transcribe")
        claude = self.env.ref("gateway_ml.ai_model_claude_sonnet_5")
        self.env.flush_all()
        self.env.cr.execute("ALTER TABLE gateway_ml_model DROP COLUMN has_timestamps")
        pre = Path(__file__).parent.parent / "migrations" / "1.19.0" / "pre-migrate.py"
        spec = importlib.util.spec_from_file_location("api_ai_1_19_0_cols", pre)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.18.0")
        self.env.invalidate_all()
        self.assertEqual(
            (whisper.has_timestamps, transcribe.has_timestamps, claude.has_timestamps),
            (True, False, False),
        )
