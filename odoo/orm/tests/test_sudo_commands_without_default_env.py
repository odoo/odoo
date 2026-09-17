import unittest

from odoo import Command, fields, models
from odoo.exceptions import AccessError
from odoo.orm.domain import Domain
from odoo.orm.model_test_env import model_test_env
from odoo.orm.runtime import Environment

_MOD = "test_sudo_commands_without_default_env"


class SGuardLine(models.Model):
    _name = "s.guard.line"
    _module = _MOD
    _description = "Guarded line"
    _allow_sudo_commands = False

    name = fields.Char()
    host_id = fields.Many2one("s.guard.host")


class SGuardHost(models.Model):
    _name = "s.guard.host"
    _module = _MOD
    _description = "Guard host"

    name = fields.Char()
    line_ids = fields.One2many("s.guard.line", "host_id")
    shadow_line_ids = fields.One2many(
        "s.guard.line", compute="_compute_shadow_line_ids"
    )

    def _compute_shadow_line_ids(self):
        for host in self:
            host.shadow_line_ids = host.line_ids


class OpenLine(models.Model):
    _name = "s.open.line"
    _module = _MOD
    _description = "Unguarded line"

    name = fields.Char()
    host_id = fields.Many2one("s.open.host")


class OpenHost(models.Model):
    _name = "s.open.host"
    _module = _MOD
    _description = "Open host"

    name = fields.Char()
    line_ids = fields.One2many("s.open.line", "host_id")


class IrModelAccess(models.AbstractModel):
    _name = "ir.model.access"
    _module = _MOD + "_access"
    _description = "ir.model.access (test stub): everything allowed"

    def check(self, model, mode="read", raise_exception=True):
        return True


class IrRule(models.AbstractModel):
    _name = "ir.rule"
    _module = _MOD + "_rules"
    _description = "ir.rule (test stub): no record rules"

    def _get_domain_accessible_records(self, model_name, mode="read"):
        return Domain.TRUE

    def _prepare_access_error(self, operation, records):
        return AccessError(f"{operation} denied on {records}")


class TestSudoCommandsWithoutDefaultEnv(unittest.TestCase):
    MODELS = (SGuardHost, SGuardLine, OpenHost, OpenLine)

    def test_the_state_is_reachable(self):
        with model_test_env(*self.MODELS) as env:
            transaction = env.transaction
            transaction.default_env = None
            Environment(env.cr, 0, {})
            self.assertIsNone(
                transaction.default_env,
                "uid 0 must not become the transaction's default environment",
            )

    def test_a_guarded_comodel_refuses_instead_of_raising_AttributeError(self):
        with model_test_env(*self.MODELS) as env:
            env.transaction.default_env = None
            field = env["s.guard.host"]._fields["line_ids"]
            with self.assertRaises(AccessError) as capture:
                field._check_sudo_commands(env["s.guard.line"].sudo())
            self.assertIn("s.guard.line", str(capture.exception))

    def test_an_unguarded_comodel_is_untouched_without_a_default_env(self):
        with model_test_env(*self.MODELS) as env:
            env.transaction.default_env = None
            field = env["s.open.host"]._fields["line_ids"]
            comodel = env["s.open.line"]
            self.assertIs(field._check_sudo_commands(comodel), comodel)

    def test_an_unguarded_comodel_is_untouched(self):
        with model_test_env(*self.MODELS) as env:
            field = env["s.open.host"]._fields["line_ids"]
            comodel = env["s.open.line"]
            self.assertIs(field._check_sudo_commands(comodel), comodel)

    def test_a_cache_only_write_on_an_unstored_field_is_not_demoted(self):
        with model_test_env(*self.MODELS) as env:
            host = env["s.guard.host"].create({"name": "h"})
            line = env["s.guard.line"].create({"name": "l", "host_id": host.id})
            env.transaction.default_env = None
            field = env["s.guard.host"]._fields["shadow_line_ids"]
            field.write_batch([(host, [Command.set([line.id])])])
            self.assertEqual(host.shadow_line_ids, line)
            field.write_batch([(host, [Command.clear()])])
            self.assertFalse(host.shadow_line_ids)

    def test_a_computed_unstored_field_needs_no_default_env(self):
        with model_test_env(*self.MODELS) as env:
            host = env["s.guard.host"].create({"name": "h"})
            line = env["s.guard.line"].create({"name": "l", "host_id": host.id})
            env.transaction.default_env = None
            self.assertEqual(host.shadow_line_ids, line)

    def test_a_create_command_on_an_unstored_field_still_refuses(self):
        with model_test_env(*self.MODELS) as env:
            host = env["s.guard.host"].create({"name": "h"})
            env.transaction.default_env = None
            field = env["s.guard.host"]._fields["shadow_line_ids"]
            with self.assertRaises(AccessError):
                field.write_batch([(host.sudo(), [Command.create({"name": "new"})])])

    def test_a_set_on_a_stored_field_still_refuses(self):
        with model_test_env(*self.MODELS) as env:
            host = env["s.guard.host"].create({"name": "h"})
            line = env["s.guard.line"].create({"name": "l"})
            env.transaction.default_env = None
            field = env["s.guard.host"]._fields["line_ids"]
            with self.assertRaises(AccessError):
                field.write_batch([(host.sudo(), [Command.set([line.id])])])

    def test_a_real_default_env_still_downgrades(self):
        with model_test_env(*self.MODELS) as env:
            user_env = Environment(env.cr, 7, {})
            env.transaction.default_env = user_env
            field = env["s.guard.host"]._fields["line_ids"]
            downgraded = field._check_sudo_commands(env["s.guard.line"].sudo())
            self.assertFalse(downgraded.env.su, "sudo must be dropped")
            self.assertEqual(downgraded.env.uid, 7, "and the real user adopted")

    def test_a_non_su_writer_is_not_demoted(self):
        with model_test_env(*self.MODELS) as env:
            field = env["s.guard.host"]._fields["line_ids"]
            comodel = env(user=7, su=False)["s.guard.line"]
            self.assertIs(
                field._check_sudo_commands(comodel),
                comodel,
                "a real user needs no demotion, even to another real user",
            )

    def test_a_non_su_writer_keeps_its_own_uid_end_to_end(self):
        # the transaction's default env is the base one (uid 1); the writer
        # is another real user, and the comodel row must record THAT user
        with model_test_env(*self.MODELS, IrModelAccess, IrRule) as env:
            user = env["res.users"].create({"name": "writer"})
            host = env["s.guard.host"].create({"name": "h"})
            env.flush_all()
            uenv = env(user=user.id, su=False)
            uenv["s.guard.host"].browse(host.id).write(
                {"line_ids": [Command.create({"name": "made-by-writer"})]}
            )
            env.flush_all()
            line = env["s.guard.line"].search([("name", "=", "made-by-writer")])
            self.assertEqual(line.create_uid.id, user.id)


if __name__ == "__main__":
    unittest.main()
