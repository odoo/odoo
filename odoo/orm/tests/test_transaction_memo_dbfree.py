from odoo import fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.tools import TransactionMemo


class Rule(models.Model):
    _name = "memo.rule"
    _module = "odoo.addons.test_memo_harness"
    _description = "Memo rule"

    name = fields.Char()
    action = fields.Char()
    note = fields.Char()


class Other(models.Model):
    _name = "memo.other"
    _module = "odoo.addons.test_memo_harness"
    _description = "Memo other"

    name = fields.Char()


BY_ANY_WRITE = TransactionMemo("memo.test.any", invalidated_by=("memo.rule",))
BY_ACTION = TransactionMemo(
    "memo.test.action", invalidated_by={"memo.rule": ("action",)}
)
COUNTER = TransactionMemo("memo.test.counter", factory=list)


def _fill(env):
    BY_ANY_WRITE(env)["k"] = 1
    BY_ACTION(env)["k"] = 1
    COUNTER(env).append(1)


def test_a_memo_is_one_container_per_transaction():
    with model_test_env(Rule, Other) as env:
        assert BY_ANY_WRITE.peek(env) is None
        container = BY_ANY_WRITE(env)
        container["k"] = 1
        assert BY_ANY_WRITE(env) is container
        assert BY_ANY_WRITE.peek(env) == {"k": 1}
        assert COUNTER(env) == []
        BY_ANY_WRITE.discard(env)
        assert BY_ANY_WRITE.peek(env) is None


def test_create_write_and_unlink_of_the_model_discard_it():
    with model_test_env(Rule, Other) as env:
        _fill(env)
        rule = env["memo.rule"].create({"name": "r", "action": "buy"})
        assert BY_ANY_WRITE.peek(env) is None
        assert BY_ACTION.peek(env) is None
        assert COUNTER.peek(env) == [1]

        _fill(env)
        rule.write({"note": "n"})
        assert BY_ANY_WRITE.peek(env) is None
        assert BY_ACTION.peek(env) == {"k": 1}

        rule.write({"action": "manufacture"})
        assert BY_ACTION.peek(env) is None

        _fill(env)
        rule.unlink()
        assert BY_ANY_WRITE.peek(env) is None
        assert BY_ACTION.peek(env) is None


def test_another_model_and_an_empty_recordset_leave_it_alone():
    with model_test_env(Rule, Other) as env:
        _fill(env)
        other = env["memo.other"].create({"name": "o"})
        other.write({"name": "p"})
        other.unlink()
        env["memo.rule"].browse().write({"note": "n"})
        env["memo.rule"].create([])
        assert BY_ANY_WRITE.peek(env) == {"k": 1}
        assert BY_ACTION.peek(env) == {"k": 1}
