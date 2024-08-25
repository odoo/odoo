import { describe, expect, test } from "@odoo/hoot";

import { constants, helpers } from "@odoo/o-spreadsheet";
import { patchTranslations } from "@web/../tests/web_test_helpers";
const { pivotTimeAdapter, toNormalizedPivotValue, toNumber } = helpers;
const { DEFAULT_LOCALE } = constants;

describe.current.tags("headless");

describe("toNormalizedPivotValue", () => {
    test("parse values of a selection, char or text field", () => {
        for (const fieldType of ["selection", "text", "char"]) {
            const dimension = {
                type: fieldType,
                displayName: "A field",
                name: "my_field_name",
            };
            expect(toNormalizedPivotValue(dimension, "won")).toBe("won");
            expect(toNormalizedPivotValue(dimension, "1")).toBe("1");
            expect(toNormalizedPivotValue(dimension, 1)).toBe("1");
            expect(toNormalizedPivotValue(dimension, "11/2020")).toBe("11/2020");
            expect(toNormalizedPivotValue(dimension, "2020")).toBe("2020");
            expect(toNormalizedPivotValue(dimension, "01/11/2020")).toBe("01/11/2020");
            expect(toNormalizedPivotValue(dimension, "false")).toBe(false);
            expect(toNormalizedPivotValue(dimension, false)).toBe(false);
            expect(toNormalizedPivotValue(dimension, "true")).toBe("true");
        }
    });

    test("parse values of time fields", () => {
        for (const fieldType of ["date", "datetime"]) {
            const dimension = {
                type: fieldType,
                displayName: "A field",
                name: "my_field_name",
            };

            dimension.granularity = "day";
            expect(toNormalizedPivotValue(dimension, "1/11/2020")).toBe(43841);
            expect(toNormalizedPivotValue(dimension, "01/11/2020")).toBe(43841);
            expect(toNormalizedPivotValue(dimension, "11/2020")).toBe(44136);
            expect(toNormalizedPivotValue(dimension, "1")).toBe(1);
            expect(toNormalizedPivotValue(dimension, 1)).toBe(1);
            expect(toNormalizedPivotValue(dimension, "false")).toBe(false);
            expect(toNormalizedPivotValue(dimension, false)).toBe(false);

            dimension.granularity = "week";
            expect(toNormalizedPivotValue(dimension, "11/2020")).toBe("11/2020");
            expect(toNormalizedPivotValue(dimension, "1/2020")).toBe("1/2020");
            expect(toNormalizedPivotValue(dimension, "01/2020")).toBe("1/2020");
            expect(toNormalizedPivotValue(dimension, "false")).toBe(false);
            expect(toNormalizedPivotValue(dimension, false)).toBe(false);

            dimension.granularity = "month";
            expect(toNormalizedPivotValue(dimension, "11/2020")).toBe("11/2020");
            expect(toNormalizedPivotValue(dimension, "1/2020")).toBe("01/2020");
            expect(toNormalizedPivotValue(dimension, "01/2020")).toBe("01/2020");
            expect(toNormalizedPivotValue(dimension, "2/11/2020")).toBe("02/2020");
            expect(toNormalizedPivotValue(dimension, "2/1/2020")).toBe("02/2020");
            expect(toNormalizedPivotValue(dimension, 1)).toBe("12/1899");
            expect(toNormalizedPivotValue(dimension, "false")).toBe(false);
            expect(toNormalizedPivotValue(dimension, false)).toBe(false);
            expect(() => toNormalizedPivotValue(dimension, "true")).toThrow();
            expect(() => toNormalizedPivotValue(dimension, true)).toThrow();
            expect(() => toNormalizedPivotValue(dimension, "won")).toThrow();

            dimension.granularity = "quarter";
            // special quarter syntax:
            expect(toNormalizedPivotValue(dimension, "1/2020")).toBe("1/2020");
            expect(toNormalizedPivotValue(dimension, "2/2020")).toBe("2/2020");
            expect(toNormalizedPivotValue(dimension, "3/2020")).toBe("3/2020");
            expect(toNormalizedPivotValue(dimension, "4/2020")).toBe("4/2020");

            // falls back on regular date parsing:
            expect(toNormalizedPivotValue(dimension, "5/2020")).toBe("2/2020");
            expect(toNormalizedPivotValue(dimension, "01/01/2020")).toBe("1/2020");
            expect(toNormalizedPivotValue(dimension, toNumber("01/01/2020", DEFAULT_LOCALE))).toBe(
                "1/2020"
            );
            expect(() => toNormalizedPivotValue(dimension, "hello")).toThrow();

            dimension.granularity = "year";
            expect(toNormalizedPivotValue(dimension, "2020")).toBe(2020);
            expect(toNormalizedPivotValue(dimension, 2020)).toBe(2020);
            expect(toNormalizedPivotValue(dimension, "false")).toBe(false);
            expect(toNormalizedPivotValue(dimension, false)).toBe(false);
        }
    });

    test("parse values of numeric fields", () => {
        for (const fieldType of ["float", "integer", "monetary", "many2one", "many2many"]) {
            const dimension = {
                type: fieldType,
                displayName: "A field",
                name: "my_field_name",
            };
            expect(toNormalizedPivotValue(dimension, "2020")).toBe(2020);
            expect(toNormalizedPivotValue(dimension, "01/11/2020")).toBe(43841); // a date is actually a number in a spreadsheet
            expect(toNormalizedPivotValue(dimension, "11/2020")).toBe(44136); // 1st of november 2020
            expect(toNormalizedPivotValue(dimension, "1")).toBe(1);
            expect(toNormalizedPivotValue(dimension, 1)).toBe(1);
            expect(toNormalizedPivotValue(dimension, "false")).toBe(false);
            expect(toNormalizedPivotValue(dimension, false)).toBe(false);
            expect(() => toNormalizedPivotValue(dimension, "true")).toThrow();
            expect(() => toNormalizedPivotValue(dimension, true)).toThrow();
            expect(() => toNormalizedPivotValue(dimension, "won")).toThrow();
        }
    });
});

describe("pivot time adapters formatted value", () => {
    test("Week adapter", () => {
        patchTranslations();
        const adapter = pivotTimeAdapter("week");
        expect(adapter.toValueAndFormat("5/2024", DEFAULT_LOCALE)).toEqual({ value: "W5 2024" });
        expect(adapter.toValueAndFormat("51/2020", DEFAULT_LOCALE)).toEqual({
            value: "W51 2020",
        });
    });

    test("Month adapter", () => {
        patchTranslations();
        const adapter = pivotTimeAdapter("month");
        expect(adapter.toValueAndFormat("12/2020", DEFAULT_LOCALE)).toEqual({
            value: 44166,
            format: "mmmm yyyy",
        });
        expect(adapter.toValueAndFormat("02/2020", DEFAULT_LOCALE)).toEqual({
            value: 43862,
            format: "mmmm yyyy",
        });
    });

    test("Quarter adapter", () => {
        patchTranslations();
        const adapter = pivotTimeAdapter("quarter");
        expect(adapter.toValueAndFormat("1/2022", DEFAULT_LOCALE)).toEqual({ value: "Q1 2022" });
        expect(adapter.toValueAndFormat("3/1998", DEFAULT_LOCALE)).toEqual({ value: "Q3 1998" });
    });
});
