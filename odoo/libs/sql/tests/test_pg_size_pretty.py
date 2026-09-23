import pytest

from odoo.libs.sql.utils import pg_size_pretty

# read from PostgreSQL 18's own pg_size_pretty(bigint)
POSTGRESQL_ANSWERS = {
    10239: "10239 bytes",
    10240: "10 kB",
    20479: "20 kB",
    20480: "20 kB",
    10485247: "10239 kB",
    10485248: "10 MB",
    10485760: "10 MB",
    10737418239: "10 GB",
    10737418240: "10 GB",
    21474836479: "20 GB",
    -10239: "-10239 bytes",
    -10240: "-10 kB",
    -20000: "-20 kB",
    -10485248: "-10 MB",
    9223372036854775807: "8192 PB",
    -9223372036854775808: "-8192 PB",
}


@pytest.mark.parametrize(("size", "expected"), POSTGRESQL_ANSWERS.items())
def test_it_answers_what_postgresql_answers(size, expected):
    assert pg_size_pretty(size) == expected
