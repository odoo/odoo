import { beforeEach, expect, test } from "@odoo/hoot";
import { makeMockEnv, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { localization } from "@web/core/l10n/localization";
import { nbsp } from "@web/core/utils/strings";
import {
    parseFloat,
    parseFloatTime,
    parseInteger,
    parseMonetary,
    parsePercentage,
} from "@web/views/fields/parsers";

beforeEach(makeMockEnv);

test("parseFloat", () => {
    expect(parseFloat("")).toBe(0);
    expect(parseFloat("0")).toBe(0);
    expect(parseFloat("100.00")).toBe(100);
    expect(parseFloat("-100.00")).toBe(-100);
    expect(parseFloat("1,000.00")).toBe(1000);
    expect(parseFloat("1,000,000.00")).toBe(1000000);
    expect(parseFloat("1,234.567")).toBe(1234.567);
    expect(() => parseFloat("1.000.000")).toThrow();

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
    expect(parseFloat("1.234,567")).toBe(1234.567);

    // Can evaluate expression from locale with decimal point different from ".".
    expect(parseFloat("=1.000,1 + 2.000,2")).toBe(3000.3);
    expect(parseFloat("=1.000,00 + 11.121,00")).toBe(12121);
    expect(parseFloat("=1000,00 + 11122,00")).toBe(12122);
    expect(parseFloat("=1000 + 11123")).toBe(12123);

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: false });
    expect(parseFloat("1234,567")).toBe(1234.567);

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: nbsp });
    expect(parseFloat("9 876,543")).toBe(9876.543);
    expect(parseFloat("1  234 567,89")).toBe(1234567.89);
    expect(parseFloat(`98${nbsp}765 432,1`)).toBe(98765432.1);
});

test("parseFloatTime", () => {
    expect(parseFloatTime("0")).toBe(0);
    expect(parseFloatTime("100")).toBe(100);
    expect(parseFloatTime("100.00")).toBe(100);
    expect(parseFloatTime("7:15")).toBe(7.25);
    expect(parseFloatTime("-4:30")).toBe(-4.5);
    expect(parseFloatTime(":")).toBe(0);
    expect(parseFloatTime("1:")).toBe(1);
    expect(parseFloatTime(":12")).toBe(0.2);

    expect(() => parseFloatTime("a:1")).toThrow();
    expect(() => parseFloatTime("1:a")).toThrow();
    expect(() => parseFloatTime("1:1:")).toThrow();
    expect(() => parseFloatTime(":1:1")).toThrow();
});

test("parseInteger", () => {
    expect(parseInteger("")).toBe(0);
    expect(parseInteger("0")).toBe(0);
    expect(parseInteger("100")).toBe(100);
    expect(parseInteger("-100")).toBe(-100);
    expect(parseInteger("1,000")).toBe(1000);
    expect(parseInteger("1,000,000")).toBe(1000000);
    expect(parseInteger("-2,147,483,648")).toBe(-2147483648);
    expect(parseInteger("2,147,483,647")).toBe(2147483647);
    expect(() => parseInteger("1.000.000")).toThrow();
    expect(() => parseInteger("1,234.567")).toThrow();
    expect(() => parseInteger("-2,147,483,649")).toThrow();
    expect(() => parseInteger("2,147,483,648")).toThrow();

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    expect(parseInteger("1.000.000")).toBe(1000000);
    expect(() => parseInteger("1.234,567")).toThrow();
    // fallback to en localization
    expect(parseInteger("1,000,000")).toBe(1000000);

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: false });
    expect(parseInteger("1000000")).toBe(1000000);
});

test("parsePercentage", () => {
    expect(parsePercentage("")).toBe(0);
    expect(parsePercentage("0")).toBe(0);
    expect(parsePercentage("0.5")).toBe(0.005);
    expect(parsePercentage("1")).toBe(0.01);
    expect(parsePercentage("100")).toBe(1);
    expect(parsePercentage("50%")).toBe(0.5);
    expect(() => parsePercentage("50%40")).toThrow();

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    expect(parsePercentage("1.234,56")).toBe(12.3456);
    expect(parsePercentage("6,02")).toBe(0.0602);
});

test("parsers fallback on english localisation", () => {
    patchWithCleanup(localization, {
        decimalPoint: ",",
        thousandsSep: ".",
    });

    expect(parseInteger("1,000,000")).toBe(1000000);
    expect(parseFloat("1,000,000.50")).toBe(1000000.5);
});

test("parseMonetary", () => {
    expect(parseMonetary("")).toBe(0);
    expect(parseMonetary("0")).toBe(0);
    expect(parseMonetary("100.00\u00a0€")).toBe(100);
    expect(parseMonetary("-100.00")).toBe(-100);
    expect(parseMonetary("1,000.00")).toBe(1000);
    expect(parseMonetary(".1")).toBe(0.1);
    expect(parseMonetary("1,000,000.00")).toBe(1000000);
    expect(parseMonetary("$\u00a0125.00")).toBe(125);
    expect(parseMonetary("1,000.00\u00a0€")).toBe(1000);

    expect(parseMonetary("\u00a0")).toBe(0);
    expect(parseMonetary("1\u00a0")).toBe(1);
    expect(parseMonetary("\u00a01")).toBe(1);

    expect(parseMonetary("12.00 €")).toBe(12);
    expect(parseMonetary("$ 12.00")).toBe(12);
    expect(parseMonetary("1\u00a0$")).toBe(1);
    expect(parseMonetary("$\u00a01")).toBe(1);

    expect(() => parseMonetary("1$\u00a01")).toThrow();
    expect(() => parseMonetary("$\u00a012.00\u00a034")).toThrow();

    // nbsp as thousands separator
    patchWithCleanup(localization, { thousandsSep: "\u00a0", decimalPoint: "," });
    expect(parseMonetary("1\u00a0000,06\u00a0€")).toBe(1000.06);
    expect(parseMonetary("$\u00a01\u00a0000,07")).toBe(1000.07);
    expect(parseMonetary("1000000,08")).toBe(1000000.08);
    expect(parseMonetary("$ -1\u00a0000,09")).toBe(-1000.09);

    // symbol not separated from the value
    expect(parseMonetary("1\u00a0000,08€")).toBe(1000.08);
    expect(parseMonetary("€1\u00a0000,09")).toBe(1000.09);
    expect(parseMonetary("$1\u00a0000,10")).toBe(1000.1);
    expect(parseMonetary("$-1\u00a0000,11")).toBe(-1000.11);

    // any symbol
    expect(parseMonetary("1\u00a0000,11EUROS")).toBe(1000.11);
    expect(parseMonetary("EUR1\u00a0000,12")).toBe(1000.12);
    expect(parseMonetary("DOL1\u00a0000,13")).toBe(1000.13);
    expect(parseMonetary("1\u00a0000,14DOLLARS")).toBe(1000.14);
    expect(parseMonetary("DOLLARS+1\u00a0000,15")).toBe(1000.15);
    expect(parseMonetary("EURO-1\u00a0000,16DOGE")).toBe(-1000.16);

    // comma as decimal point and dot as thousands separator
    patchWithCleanup(localization, { thousandsSep: ".", decimalPoint: "," });
    expect(parseMonetary("10,08")).toBe(10.08);
    expect(parseMonetary("")).toBe(0);
    expect(parseMonetary("0")).toBe(0);
    expect(parseMonetary("100,12\u00a0€")).toBe(100.12);
    expect(parseMonetary("-100,12")).toBe(-100.12);
    expect(parseMonetary("1.000,12")).toBe(1000.12);
    expect(parseMonetary(",1")).toBe(0.1);
    expect(parseMonetary("1.000.000,12")).toBe(1000000.12);
    expect(parseMonetary("$\u00a0125,12")).toBe(125.12);
    expect(parseMonetary("1.000,00\u00a0€")).toBe(1000);
    expect(parseMonetary(",")).toBe(0);
    expect(parseMonetary("1\u00a0")).toBe(1);
    expect(parseMonetary("\u00a01")).toBe(1);
    expect(parseMonetary("12,34 €")).toBe(12.34);
    expect(parseMonetary("$ 12,34")).toBe(12.34);

    // Can evaluate expression
    expect(parseMonetary("=1.000,1 + 2.000,2")).toBe(3000.3);
    expect(parseMonetary("=1.000,00 + 11.121,00")).toBe(12121);
    expect(parseMonetary("=1000,00 + 11122,00")).toBe(12122);
    expect(parseMonetary("=1000 + 11123")).toBe(12123);
});
