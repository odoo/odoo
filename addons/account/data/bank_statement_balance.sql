CREATE OR REPLACE FUNCTION anchor_accumulator
-- Calculate the sum of a list of numbers, replacing the calculated value with the anchor(check) points when available.
    (
    cur_bal NUMERIC,
    amount NUMERIC,
    is_anchor BOOL,
    anchor_value NUMERIC
    )
    RETURNS NUMERIC AS
$$
SELECT (CASE WHEN is_anchor = TRUE THEN anchor_value ELSE cur_bal+amount END);
$$ LANGUAGE 'sql' CALLED ON NULL INPUT;

-- compatibility for postgres < 14, which does not have the 'CREATE OR REPLACE AGGREGATE' syntax
DROP AGGREGATE IF EXISTS anchor_sum ( numeric, boolean, numeric);

CREATE AGGREGATE anchor_sum(NUMERIC,BOOL,NUMERIC)
(
    INITCOND = 0,
    STYPE = NUMERIC,
    SFUNC = anchor_accumulator
);

