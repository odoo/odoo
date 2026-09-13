// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { getAggregateSpecifications } from "@web/model/relational_model/field_values";

describe.current.tags("headless");

function makeFields() {
    return {
        amount: { name: "amount", type: "monetary", aggregator: "sum" },
        currency_id: { name: "currency_id", type: "many2one" },
        qty: { name: "qty", type: "integer", aggregator: "sum" },
        name: { name: "name", type: "char" },
        untracked: { name: "untracked", type: "integer" },
    };
}

describe("getAggregateSpecifications", () => {
    test("scoping to field names matches picking those fields first", () => {
        const fields = makeFields();
        const names = ["amount", "qty", "name"];

        const scoped = getAggregateSpecifications(fields, names);
        const picked = getAggregateSpecifications(
            Object.fromEntries(
                names.map((n) => [n, /** @type {Record<string, any>} */ (fields)[n]]),
            ),
        );

        expect(scoped).toEqual(picked);
        expect(scoped).toEqual(["amount:sum", "amount:count", "qty:sum", "qty:count"]);
    });

    test("monetary fields still pull in their currency companions", () => {
        const fields = makeFields();
        fields.amount.currency_field = "currency_id";

        expect(getAggregateSpecifications(fields, ["amount"])).toEqual([
            "amount:sum",
            "amount:count",
            "currency_id:array_agg_distinct",
            "amount:sum_currency",
        ]);
    });

    test("a value-equal name list hits the cache, a different one does not", () => {
        const fields = makeFields();

        const first = getAggregateSpecifications(fields, ["amount", "qty"]);
        const second = getAggregateSpecifications(fields, ["amount", "qty"]);
        expect(second).toBe(first);

        const narrower = getAggregateSpecifications(fields, ["qty"]);
        expect(narrower).not.toBe(first);
        expect(narrower).toEqual(["qty:sum", "qty:count"]);

        const all = getAggregateSpecifications(fields);
        expect(all).not.toBe(first);
        expect(all).toEqual(["amount:sum", "amount:count", "qty:sum", "qty:count"]);
        expect(getAggregateSpecifications(fields)).toBe(all);
    });

    test("duplicate and unknown names are ignored, as pick() did", () => {
        const fields = makeFields();

        expect(getAggregateSpecifications(fields, ["qty", "qty", "nope"])).toEqual([
            "qty:sum",
            "qty:count",
        ]);
    });
});

describe("scope key isolation", () => {
    test("an empty scope does not share the all-fields cache slot", () => {
        const fields = makeFields();

        expect(getAggregateSpecifications(fields, [])).toEqual([]);
        expect(getAggregateSpecifications(fields)).toEqual([
            "amount:sum",
            "amount:count",
            "qty:sum",
            "qty:count",
        ]);
    });

    test("the collision is absent in the reverse order too", () => {
        const fields = makeFields();

        expect(getAggregateSpecifications(fields)).toEqual([
            "amount:sum",
            "amount:count",
            "qty:sum",
            "qty:count",
        ]);
        expect(getAggregateSpecifications(fields, [])).toEqual([]);
    });
});
