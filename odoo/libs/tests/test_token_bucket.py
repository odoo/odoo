import pytest

from odoo.libs import token_bucket


class TestRefill:
    def test_tokens_grow_with_elapsed_time_at_the_rate(self):
        assert (
            token_bucket.refill(
                2.0, 3.0, rate=0.5, capacity=10.0, max_elapsed_seconds=3600
            )
            == 3.5
        )

    def test_refill_stops_at_capacity(self):
        assert (
            token_bucket.refill(
                9.0, 100.0, rate=1.0, capacity=10.0, max_elapsed_seconds=3600
            )
            == 10.0
        )

    def test_a_long_idle_gap_counts_only_up_to_the_elapsed_cap(self):
        assert token_bucket.refill(
            0.0, 10_000.0, rate=0.001, capacity=100.0, max_elapsed_seconds=3600
        ) == pytest.approx(3.6)

    def test_a_clock_that_went_backwards_adds_nothing(self):
        assert (
            token_bucket.refill(
                4.0, -30.0, rate=1.0, capacity=10.0, max_elapsed_seconds=3600
            )
            == 4.0
        )

    def test_a_lowered_capacity_takes_effect_at_the_next_refill(self):
        assert (
            token_bucket.refill(
                50.0, 0.0, rate=1.0, capacity=10.0, max_elapsed_seconds=3600
            )
            == 10.0
        )

    def test_a_negative_rate_is_refused(self):
        with pytest.raises(ValueError, match="rate"):
            token_bucket.refill(
                1.0, 1.0, rate=-1.0, capacity=10.0, max_elapsed_seconds=3600
            )


class TestTake:
    def test_a_token_is_taken_when_one_is_there(self):
        assert token_bucket.take(1.0) == 0.0

    def test_nothing_is_taken_below_the_cost(self):
        assert token_bucket.take(0.99) is None

    def test_the_cost_can_be_more_than_one(self):
        assert token_bucket.take(5.0, cost=2.5) == 2.5
