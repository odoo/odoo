from odoo.orm.components.storage import DictBackend
from odoo.orm.runtime._backend_memory import InMemoryBackend, InMemorySequenceStore
from odoo.orm.runtime.backend import (
    PostgresBackend,
    PostgresSequenceStore,
    SequenceStore,
)


def _store() -> InMemorySequenceStore:
    store = InMemoryBackend(DictBackend()).sequences
    assert isinstance(store, InMemorySequenceStore)
    return store


def test_both_backends_carry_a_sequence_store():
    assert isinstance(PostgresBackend.sequences, PostgresSequenceStore)
    assert isinstance(_store(), SequenceStore)
    assert isinstance(PostgresBackend.sequences, SequenceStore)


def test_next_values_start_at_the_start_value_and_step_by_the_increment():
    store = _store()
    store.create(None, "seq", increment=3, start=10)
    assert store.next_values(None, "seq", 1) == [10]
    assert store.next_values(None, "seq", 3) == [13, 16, 19]


def test_peek_answers_what_next_values_would_give_without_consuming_it():
    store = _store()
    store.create(None, "seq", increment=1, start=5)
    assert store.peek(None, ["seq", "absent"]) == {"seq": 5}
    assert store.next_values(None, "seq", 1) == [5]
    assert store.peek(None, ["seq"]) == {"seq": 6}
    assert store.next_values(None, "seq", 1) == [6]


def test_alter_restarts_and_changes_the_increment_like_postgres():
    store = _store()
    store.create(None, "seq", increment=1, start=1)
    store.next_values(None, "seq", 2)
    store.alter(None, "seq", restart=100)
    assert store.next_values(None, "seq", 1) == [100]
    store.alter(None, "seq", increment=10)
    assert store.next_values(None, "seq", 1) == [110]
    store.alter(None, "missing", restart=1)


def test_start_below_one_is_clamped_and_drop_forgets():
    store = _store()
    store.create(None, "seq", increment=1, start=0)
    assert store.next_values(None, "seq", 1) == [1]
    store.drop(None, ["seq", "absent"])
    assert store.peek(None, ["seq"]) == {}
