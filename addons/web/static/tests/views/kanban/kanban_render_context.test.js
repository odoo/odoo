// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { validateType } from "@odoo/owl";
import { getFormattedRecord } from "@web/views/kanban/kanban_record";

describe.current.tags("headless");

function makeRecord(
    /** @type {{ data: Record<string, any>, activeFields: Record<string, any> }} */ {
        data,
        activeFields,
    },
) {
    const fields = Object.fromEntries(
        Object.keys(data).map((name) => [name, { type: "char" }]),
    );
    let reads = 0;
    return {
        resId: 7,
        data,
        fields,
        activeFields,
        get fieldNamesReads() {
            return reads;
        },
        get fieldNames() {
            reads++;
            return Object.keys(this.activeFields);
        },
    };
}

describe("getFormattedRecord", () => {
    test("exposes value / raw_value per active field, plus id", () => {
        const record = makeRecord({
            data: { name: "abc", other: "xyz" },
            activeFields: { name: {}, other: {} },
        });
        const formatted = getFormattedRecord(record);
        expect(formatted.name.value).toBe("abc");
        expect(formatted.name.raw_value).toBe("abc");
        expect(formatted.id.value).toBe(7);
    });

    test("reports membership through `in` and ownKeys", () => {
        const record = makeRecord({
            data: { name: "abc" },
            activeFields: { name: {} },
        });
        const formatted = getFormattedRecord(record);
        expect("name" in formatted).toBe(true);
        expect("nope" in formatted).toBe(false);
        expect(Object.keys(formatted).sort()).toEqual(["id", "name"]);
    });

    test("is a plain object to a component prop typed Object", () => {
        const record = makeRecord({
            data: { name: "abc" },
            activeFields: { name: {} },
        });
        const formatted = getFormattedRecord(record);
        expect(formatted instanceof Object).toBe(true);
        expect(validateType("record", formatted, Object)).toBe(null);
    });

    test("a non-field property does not resolve to a field entry", () => {
        const record = makeRecord({
            data: { name: "abc" },
            activeFields: { name: {} },
        });
        const formatted = getFormattedRecord(record);
        expect(formatted.notAField).toBe(undefined);
    });

    test("fieldNames is derived once, not once per property access", () => {
        const record = makeRecord({
            data: { a: 1, b: 2, c: 3 },
            activeFields: { a: {}, b: {}, c: {} },
        });
        const formatted = getFormattedRecord(record);
        for (let i = 0; i < 50; i++) {
            void formatted.a;
            void formatted.b;
            void formatted.c;
        }
        expect(record.fieldNamesReads).toBe(1);
    });

    test("swapping activeFields invalidates the memo", () => {
        const record = makeRecord({
            data: { a: 1, b: 2 },
            activeFields: { a: {}, b: {} },
        });
        const formatted = getFormattedRecord(record);
        expect("b" in formatted).toBe(true);

        record.activeFields = { a: {} };
        expect("b" in formatted).toBe(false);
        expect("a" in formatted).toBe(true);
    });
});
