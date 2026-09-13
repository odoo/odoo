// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeLogger } from "@web/core/debug/debug_logger";
import {
    compareRecords,
    computeNextOrderBy,
} from "@web/model/relational_model/static_list_utils";

describe.current.tags("headless");

const charFields = {
    name: { type: "char" },
    code: { type: "char" },
};

const m2oFields = {
    partner_id: { type: "many2one" },
};

/** @param {any} data */
function makeRecord(data) {
    return { resId: data.id, data };
}

test("unset selections have a consistent position across every input permutation", () => {
    const fields = { name: { type: "selection" } };
    const rows = [false, "a", "b"].map((name) => makeRecord({ name }));
    const permutations = [
        [0, 1, 2],
        [0, 2, 1],
        [1, 0, 2],
        [1, 2, 0],
        [2, 0, 1],
        [2, 1, 0],
    ];
    for (const asc of [true, false]) {
        for (const permutation of permutations) {
            const sorted = permutation
                .map((i) => rows[i])
                .sort((a, b) => compareRecords(a, b, [{ name: "name", asc }], fields))
                .map((row) => row.data.name);
            makeLogger("web.model.audit").logic("selection sort permutation", {
                asc,
                permutation,
                sorted,
            });
            expect(sorted).toEqual(asc ? [false, "a", "b"] : ["b", "a", false]);
        }
    }
});

describe("compareRecords — char ascending", () => {
    test("returns -1 when r1 < r2", () => {
        const r1 = makeRecord({ name: "Alice" });
        const r2 = makeRecord({ name: "Bob" });
        const result = compareRecords(
            r1,
            r2,
            [{ name: "name", asc: true }],
            charFields,
        );
        expect(result).toBe(-1);
    });

    test("returns 1 when r1 > r2", () => {
        const r1 = makeRecord({ name: "Zebra" });
        const r2 = makeRecord({ name: "Apple" });
        const result = compareRecords(
            r1,
            r2,
            [{ name: "name", asc: true }],
            charFields,
        );
        expect(result).toBe(1);
    });

    test("returns 0 when r1 == r2", () => {
        const r1 = makeRecord({ name: "Same" });
        const r2 = makeRecord({ name: "Same" });
        const result = compareRecords(
            r1,
            r2,
            [{ name: "name", asc: true }],
            charFields,
        );
        expect(result).toBe(0);
    });
});

describe("compareRecords — descending", () => {
    test("reverses sort direction", () => {
        const r1 = makeRecord({ name: "Alice" });
        const r2 = makeRecord({ name: "Bob" });
        const result = compareRecords(
            r1,
            r2,
            [{ name: "name", asc: false }],
            charFields,
        );
        expect(result).toBe(1);
    });

    test("r1 > r2 descending returns -1", () => {
        const r1 = makeRecord({ name: "Zebra" });
        const r2 = makeRecord({ name: "Apple" });
        const result = compareRecords(
            r1,
            r2,
            [{ name: "name", asc: false }],
            charFields,
        );
        expect(result).toBe(-1);
    });
});

describe("compareRecords — id field", () => {
    test("compares by resId when fieldName is 'id'", () => {
        const r1 = { resId: 1, data: {} };
        const r2 = { resId: 5, data: {} };
        const idFields = { id: { type: "integer" } };
        expect(compareRecords(r1, r2, [{ name: "id", asc: true }], idFields)).toBe(-1);
        expect(compareRecords(r2, r1, [{ name: "id", asc: true }], idFields)).toBe(1);
    });
});

describe("compareRecords — many2one", () => {
    test("compares by display_name", () => {
        const r1 = makeRecord({ partner_id: { id: 1, display_name: "Alice Co" } });
        const r2 = makeRecord({ partner_id: { id: 2, display_name: "Bob Ltd" } });
        const result = compareRecords(
            r1,
            r2,
            [{ name: "partner_id", asc: true }],
            m2oFields,
        );
        expect(result).toBe(-1);
    });

    test("treats falsy many2one as empty string", () => {
        const r1 = makeRecord({ partner_id: false });
        const r2 = makeRecord({ partner_id: { id: 1, display_name: "Bob" } });
        const result = compareRecords(
            r1,
            r2,
            [{ name: "partner_id", asc: true }],
            m2oFields,
        );
        expect(result).toBe(-1);
    });
});

describe("compareRecords — multi-criterion tie-break", () => {
    test("falls through to second criterion on equal first", () => {
        const fields = { name: { type: "char" }, code: { type: "char" } };
        const r1 = makeRecord({ name: "Same", code: "A" });
        const r2 = makeRecord({ name: "Same", code: "B" });
        const orderBy = [
            { name: "name", asc: true },
            { name: "code", asc: true },
        ];
        expect(compareRecords(r1, r2, orderBy, fields)).toBe(-1);
        expect(compareRecords(r2, r1, orderBy, fields)).toBe(1);
    });

    test("returns 0 when all criteria are equal", () => {
        const fields = { name: { type: "char" }, code: { type: "char" } };
        const r1 = makeRecord({ name: "X", code: "Y" });
        const r2 = makeRecord({ name: "X", code: "Y" });
        const orderBy = [
            { name: "name", asc: true },
            { name: "code", asc: true },
        ];
        expect(compareRecords(r1, r2, orderBy, fields)).toBe(0);
    });
});

describe("computeNextOrderBy — new field", () => {
    test("new field becomes primary sort ascending", () => {
        const result = computeNextOrderBy("name", [], false);
        expect(result).toEqual([{ name: "name", asc: true }]);
    });

    test("new field is prepended to existing orderBy", () => {
        const result = computeNextOrderBy("code", [{ name: "name", asc: true }], false);
        expect(result[0]).toEqual({ name: "code", asc: true });
        expect(result[1]).toEqual({ name: "name", asc: true });
    });

    test("existing occurrence of new field is removed from old position", () => {
        const orderBy = [
            { name: "name", asc: true },
            { name: "code", asc: false },
        ];
        const result = computeNextOrderBy("code", orderBy, false);
        expect(result.filter((o) => o.name === "code").length).toBe(1);
        expect(result[0].name).toBe("code");
    });
});

describe("computeNextOrderBy — same field cycles", () => {
    test("asc → desc when same field clicked again", () => {
        const result = computeNextOrderBy("name", [{ name: "name", asc: true }], false);
        expect(result[0]).toEqual({ name: "name", asc: false });
    });

    test("desc → reset to id asc", () => {
        const result = computeNextOrderBy(
            "name",
            [{ name: "name", asc: false }],
            false,
        );
        expect(result).toEqual([{ name: "id", asc: true }]);
    });
});

describe("computeNextOrderBy — needsReordering keeps direction", () => {
    test("does not cycle direction when reordering is pending", () => {
        const orderBy = [{ name: "name", asc: true }];
        const result = computeNextOrderBy("name", orderBy, true);
        expect(result[0].asc).toBe(true);
    });
});

describe("computeNextOrderBy — empty fieldName", () => {
    test("returns unchanged orderBy when no fieldName given", () => {
        const orderBy = [{ name: "name", asc: true }];
        const result = computeNextOrderBy("", orderBy, false);
        expect(result).toEqual(orderBy);
    });
});
