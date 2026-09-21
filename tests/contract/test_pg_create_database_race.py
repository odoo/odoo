import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest

from .._pg import dropdb_path
from .conftest import requires_createdb, requires_pg

RACERS = 4


def _drop(name: str) -> None:
    subprocess.run(
        [dropdb_path(), "--if-exists", "--force", name],
        check=False,
        capture_output=True,
    )


@pytest.fixture
def race_name():
    if dropdb_path() is None:
        pytest.skip("dropdb not on PATH")
    name = f"odoo_race_{uuid.uuid4().hex[:12]}"
    try:
        yield name
    finally:
        _drop(name)


def _race(name: str) -> list[str | psycopg.Error]:
    barrier = threading.Barrier(RACERS)

    def attempt(_):
        with psycopg.connect(dbname="postgres", autocommit=True) as conn:
            barrier.wait(timeout=30)
            try:
                conn.execute(f'CREATE DATABASE "{name}" TEMPLATE template0')
                return "created"
            except psycopg.Error as exc:
                return exc

    with ThreadPoolExecutor(max_workers=RACERS) as pool:
        return list(pool.map(attempt, range(RACERS)))


@requires_pg
@requires_createdb
class TestConcurrentCreateDatabaseSqlstate:
    def test_exactly_one_racer_wins(self, race_name):
        outcomes = _race(race_name)
        assert outcomes.count("created") == 1, outcomes

    def test_losers_get_unique_violation_not_duplicate_database(self, race_name):
        losers = [o for o in _race(race_name) if o != "created"]
        assert losers, "no racer lost — the barrier failed to overlap them"
        assert {type(e) for e in losers} == {psycopg.errors.UniqueViolation}, [
            (type(e).__name__, e.sqlstate) for e in losers
        ]
        assert {e.sqlstate for e in losers} == {"23505"}

    def test_unique_violation_is_not_a_duplicate_database(self):
        assert not issubclass(
            psycopg.errors.UniqueViolation, psycopg.errors.DuplicateDatabase
        )
        assert psycopg.errors.DuplicateDatabase.sqlstate == "42P04"
        assert psycopg.errors.UniqueViolation.sqlstate == "23505"

    def test_sequential_duplicate_still_uses_42p04(self, race_name):
        subprocess.run(
            ["createdb", "-T", "template0", race_name], check=True, capture_output=True
        )
        with psycopg.connect(dbname="postgres", autocommit=True) as conn:
            with pytest.raises(psycopg.errors.DuplicateDatabase) as excinfo:
                conn.execute(f'CREATE DATABASE "{race_name}" TEMPLATE template0')
        assert excinfo.value.sqlstate == "42P04"


@requires_pg
@requires_createdb
class TestCreateEmptyDatabaseAnswersUniformly:
    def test_every_losing_racer_gets_database_exists(self, race_name):
        from odoo.service.db import DatabaseExists, create_empty_database

        barrier = threading.Barrier(RACERS)

        def attempt(_):
            barrier.wait(timeout=30)
            try:
                create_empty_database(
                    race_name, template="template0", setup_if_exists=False
                )
                return "created"
            except DatabaseExists:
                return "DatabaseExists"
            except BaseException as exc:
                return f"{type(exc).__module__}.{type(exc).__name__}"

        with ThreadPoolExecutor(max_workers=RACERS) as pool:
            outcomes = list(pool.map(attempt, range(RACERS)))

        assert outcomes.count("created") == 1, outcomes
        losers = [o for o in outcomes if o != "created"]
        assert set(losers) == {"DatabaseExists"}, (
            f"a racing create leaked a raw driver error instead of the canonical "
            f"DatabaseExists: {sorted(set(losers))}"
        )
