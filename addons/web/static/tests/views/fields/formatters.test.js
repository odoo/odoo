import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { patchTranslations, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { markup } from "@odoo/owl";
import { currencies } from "@web/core/currency";
import { localization } from "@web/core/l10n/localization";
import {
    formatFloat,
    formatFloatFactor,
    formatFloatTime,
    formatJson,
    formatInteger,
    formatMany2one,
    formatMany2oneReference,
    formatMonetary,
    formatPercentage,
    formatReference,
    formatText,
    formatX2many,
} from "@web/views/fields/formatters";

describe.current.tags("headless");

beforeEach(() => {
    patchTranslations();
    patchWithCleanup(localization, {
        decimalPoint: ".",
        thousandsSep: ",",
        grouping: [3, 0],
    });
});

test("formatFloat", () => {
    expect(formatFloat(false)).toBe("");
});

test("formatFloatFactor", () => {
    expect(formatFloatFactor(false)).toBe("");
    expect(formatFloatFactor(6000)).toBe("6,000.00");
    expect(formatFloatFactor(6000, { factor: 3 })).toBe("18,000.00");
    expect(formatFloatFactor(6000, { factor: 0.5 })).toBe("3,000.00");
});

test("formatFloatTime", () => {
    expect(formatFloatTime(2)).toBe("02:00");
    expect(formatFloatTime(3.5)).toBe("03:30");
    expect(formatFloatTime(0.25)).toBe("00:15");
    expect(formatFloatTime(0.58)).toBe("00:35");
    expect(formatFloatTime(2 / 60, { displaySeconds: true })).toBe("00:02:00");
    expect(formatFloatTime(2 / 60 + 1 / 3600, { displaySeconds: true })).toBe("00:02:01");
    expect(formatFloatTime(2 / 60 + 2 / 3600, { displaySeconds: true })).toBe("00:02:02");
    expect(formatFloatTime(2 / 60 + 3 / 3600, { displaySeconds: true })).toBe("00:02:03");
    expect(formatFloatTime(0.25, { displaySeconds: true })).toBe("00:15:00");
    expect(formatFloatTime(0.25 + 15 / 3600, { displaySeconds: true })).toBe("00:15:15");
    expect(formatFloatTime(0.25 + 45 / 3600, { displaySeconds: true })).toBe("00:15:45");
    expect(formatFloatTime(56 / 3600, { displaySeconds: true })).toBe("00:00:56");
    expect(formatFloatTime(-0.5)).toBe("-00:30");

    const options = { noLeadingZeroHour: true };
    expect(formatFloatTime(2, options)).toBe("2:00");
    expect(formatFloatTime(3.5, options)).toBe("3:30");
    expect(formatFloatTime(3.5, { ...options, displaySeconds: true })).toBe("3:30:00");
    expect(formatFloatTime(3.5 + 15 / 3600, { ...options, displaySeconds: true })).toBe("3:30:15");
    expect(formatFloatTime(3.5 + 45 / 3600, { ...options, displaySeconds: true })).toBe("3:30:45");
    expect(formatFloatTime(56 / 3600, { ...options, displaySeconds: true })).toBe("0:00:56");
    expect(formatFloatTime(-0.5, options)).toBe("-0:30");
});

test("formatJson", () => {
    expect(formatJson(false)).toBe("");
    expect(formatJson({})).toBe("{}");
    expect(formatJson({ 1: 111 })).toBe('{"1":111}');
    expect(formatJson({ 9: 11, 666: 42 })).toBe('{"9":11,"666":42}');
});

test("formatInteger", () => {
    expect(formatInteger(false)).toBe("");
    expect(formatInteger(0)).toBe("0");

    patchWithCleanup(localization, { grouping: [3, 3, 3, 3] });
    expect(formatInteger(1000000)).toBe("1,000,000");

    patchWithCleanup(localization, { grouping: [3, 2, -1] });
    expect(formatInteger(106500)).toBe("1,06,500");

    patchWithCleanup(localization, { grouping: [1, 2, -1] });
    expect(formatInteger(106500)).toBe("106,50,0");

    const options = { grouping: [2, 0], thousandsSep: "€" };
    expect(formatInteger(6000, options)).toBe("60€00");
});

test("formatMany2one", () => {
    expect(formatMany2one(false)).toBe("");
    expect(formatMany2one([false, "M2O value"])).toBe("M2O value");
    expect(formatMany2one([1, false])).toBe("Unnamed");
    expect(formatMany2one([1, "M2O value"])).toBe("M2O value");
    expect(formatMany2one([1, "M2O value"], { escape: true })).toBe("M2O%20value");
});

test("formatText", () => {
    expect(formatText(false)).toBe("");
    expect(formatText("value")).toBe("value");
    expect(formatText(1)).toBe("1");
    expect(formatText(1.5)).toBe("1.5");
    expect(formatText(markup("<p>This is a Test</p>"))).toBe("<p>This is a Test</p>");
    expect(formatText([1, 2, 3, 4, 5])).toBe("1,2,3,4,5");
    expect(formatText({ a: 1, b: 2 })).toBe("[object Object]");
});

test("formatX2many", () => {
    // Results are cast as strings since they're lazy translated.
    expect(String(formatX2many({ currentIds: [] }))).toBe("No records");
    expect(String(formatX2many({ currentIds: [1] }))).toBe("1 record");
    expect(String(formatX2many({ currentIds: [1, 3] }))).toBe("2 records");
});

test("formatMonetary", () => {
    patchWithCleanup(currencies, {
        10: {
            digits: [69, 2],
            position: "after",
            symbol: "€",
        },
        11: {
            digits: [69, 2],
            position: "before",
            symbol: "$",
        },
        12: {
            digits: [69, 2],
            position: "after",
            symbol: "&",
        },
    });

    expect(formatMonetary(false)).toBe("");

    const field = {
        type: "monetary",
        currency_field: "c_x",
    };
    let data = {
        c_x: [11],
        c_y: 12,
    };
    expect(formatMonetary(200, { field, currencyId: 10, data })).toBe("200.00\u00a0€");
    expect(formatMonetary(200, { field, data })).toBe("$\u00a0200.00");
    expect(formatMonetary(200, { field, currencyField: "c_y", data })).toBe("200.00\u00a0&");

    const floatField = { type: "float" };
    data = {
        currency_id: [11],
    };
    expect(formatMonetary(200, { field: floatField, data })).toBe("$\u00a0200.00");
});

test("formatPercentage", () => {
    expect(formatPercentage(false)).toBe("0%");
    expect(formatPercentage(0)).toBe("0%");
    expect(formatPercentage(0.5)).toBe("50%");

    expect(formatPercentage(1)).toBe("100%");

    expect(formatPercentage(-0.2)).toBe("-20%");
    expect(formatPercentage(2.5)).toBe("250%");

    expect(formatPercentage(0.125)).toBe("12.5%");
    expect(formatPercentage(0.666666)).toBe("66.67%");
    expect(formatPercentage(125)).toBe("12500%");

    expect(formatPercentage(50, { humanReadable: true })).toBe("5k%");
    expect(formatPercentage(0.5, { noSymbol: true })).toBe("50");

    patchWithCleanup(localization, { grouping: [3, 0], decimalPoint: ",", thousandsSep: "." });
    expect(formatPercentage(0.125)).toBe("12,5%");
    expect(formatPercentage(0.666666)).toBe("66,67%");
});

test("formatReference", () => {
    expect(formatReference(false)).toBe("");
    const value = { resModel: "product", resId: 2, displayName: "Chair" };
    expect(formatReference(value)).toBe("Chair");
});

test("formatMany2oneReference", () => {
    expect(formatMany2oneReference(false)).toBe("");
    expect(formatMany2oneReference({ resId: 9, displayName: "Chair" })).toBe("Chair");
});
