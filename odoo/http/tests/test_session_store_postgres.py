import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from odoo.http._session_store import PostgresSessionStore
from odoo.http.constants import prepare_default_session
from odoo.http.session import Session

pytestmark = pytest.mark.skipif(
    not os.environ.get("ODOO_HTTP_SESSION_TEST_DB"),
    reason="set ODOO_HTTP_SESSION_TEST_DB to a scratch database",
)


def _store():
    return PostgresSessionStore(os.environ["ODOO_HTTP_SESSION_TEST_DB"], Session)


@pytest.fixture
def stores():
    first, second = _store(), _store()
    first.clear()
    yield first, second
    first.clear()


def _saved(store):
    session = store.new()
    session.update(prepare_default_session())
    store.save(session)
    return session


def test_two_connections_racing_on_one_family_serialize_and_lose_nothing(stores):
    first, second = stores
    origin = _saved(first)
    workers = 8
    rounds = 25

    def hammer(index):
        store = first if index % 2 else second
        for round_ in range(rounds):
            mine = store.get(origin.sid)
            mine[f"w{index}"] = round_
            store.save(mine)
        return index

    with ThreadPoolExecutor(max_workers=workers) as pool:
        assert sorted(pool.map(hammer, range(workers))) == list(range(workers))

    final = first.get(origin.sid)
    assert not final.is_new
    assert {k: v for k, v in final.items() if k.startswith("w")} == {
        f"w{i}": rounds - 1 for i in range(workers)
    }, "every writer's last value survived the merge under two connections"


def test_a_soft_rotation_seen_from_another_connection_is_adopted(stores):
    first, second = stores
    origin = _saved(first)
    origin.uid = None
    theirs = second.get(origin.sid)

    first.rotate(origin, None, soft=True)
    assert origin.sid != theirs.sid

    theirs["late"] = 1
    second.save(theirs)
    assert theirs.sid == origin.sid, "the late writer followed the successor"
    assert first.get(origin.sid)["late"] == 1


def test_a_hard_rotation_revokes_the_family_for_every_connection(stores):
    first, second = stores
    origin = _saved(first)
    stale = second.get(origin.sid)
    first.rotate(origin, None, soft=False)
    assert second.get(stale.sid).is_new, "the old id is gone on the other connection"
    assert not second.get(origin.sid).is_new


def test_a_rolled_back_first_transaction_does_not_brick_the_schema(stores):
    first, _ = stores
    fresh = _store()
    with first._cursor() as cr:
        cr.execute("DROP TABLE IF EXISTS http_session")
    with pytest.raises(RuntimeError, match="probe"):
        with fresh._cursor() as cr:
            cr.execute("SELECT count(*) FROM http_session")
            raise RuntimeError("probe: force the schema transaction to roll back")
    assert not fresh._schema_ready, "a rolled-back DDL must not be remembered"
    with fresh._cursor() as cr:
        cr.execute("SELECT count(*) FROM http_session")
        assert cr.fetchone()[0] == 0, "the schema was recreated on retry"


def test_vacuum_and_missing_identifiers_over_the_table(stores):
    first, _ = stores
    kept = _saved(first)
    gone = _saved(first)
    with first._cursor() as cr:
        cr.execute(
            "UPDATE http_session SET mtime = mtime - 10 * 24 * 3600 WHERE sid = %s",
            (gone.sid,),
        )
    first.vacuum(max_lifetime=7 * 24 * 3600)
    assert first.get(gone.sid).is_new
    assert not first.get(kept.sid).is_new
    missing = first.get_missing_session_identifiers([kept.sid[:42], gone.sid[:42]])
    assert missing == {gone.sid[:42]}
