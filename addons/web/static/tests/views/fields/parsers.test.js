import { beforeEach, expect, test } from "@odoo/hoot";
import { clearMemoizeCaches } from "@web/core/utils/functions";
import { makeTestApp, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { localization } from "@web/core/l10n/localization";
import { nbsp } from "@web/core/utils/strings";
import {
    parseFloat,
    parseFloatTime,
    parseInteger,
    parsePercentage,
} from "@web/views/fields/parsers";

beforeEach(() => makeTestApp());

test("parseFloat", () => {
    // Basic parsing
    expect(parseFloat("")).toBe(0);
    expect(parseFloat("0")).toBe(0);
    expect(parseFloat("100.00")).toBe(100);
    expect(parseFloat("-100.00")).toBe(-100);

    // Default locale thousands/decimal separator
    expect(parseFloat("1,000.00")).toBe(1000);
    expect(parseFloat("1,000,000.00")).toBe(1000000);
    expect(parseFloat("1,234.567")).toBe(1234.567);
    expect(parseFloat("1.000.000")).toBe(1000000);

    // Locale-specific decimal point / thousands separator
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
    expect(parseFloat("1.234,567")).toBe(1234.567);

    // Formulas
    expect(parseFloat("=1.000,1 + 2.000,2")).toBe(3000.3);
    expect(parseFloat("=1.000,00 + 11.121,00")).toBe(12121);
    expect(parseFloat("=1000,00 + 11122,00")).toBe(12122);
    expect(parseFloat("=1000 + 11123")).toBe(12123);
    expect(parseFloat(" =3+4")).toBe(7);
    expect(parseFloat("=3+4 ")).toBe(7);

    // No thousands separator configured
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: false });
    expect(parseFloat("1234,567")).toBe(1234.567);

    // Whitespace as thousands separator
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: nbsp });
    expect(parseFloat("9 876,543")).toBe(9876.543);
    expect(parseFloat("1  234 567,89")).toBe(1234567.89);
    expect(parseFloat(`98${nbsp}765 432,1`)).toBe(98765432.1);

    // . , and ٫ all work as decimal separator, whatever the locale's own is
    expect(parseFloat(",5")).toBe(0.5);
    expect(parseFloat(".5")).toBe(0.5);
    expect(parseFloat("1.5")).toBe(1.5);
    expect(parseFloat("1,5")).toBe(1.5);
    expect(parseFloat("1٫5")).toBe(1.5);

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
    expect(parseFloat("1.23")).toBe(1.23);
    expect(parseFloat("10.000")).toBe(10);
    expect(parseFloat("1.000.000")).toBe(1000000);
    expect(parseFloat("1 0 0 0 0")).toBe(10000);
    expect(parseFloat("1.0 0 0.0 0 0")).toBe(1000000);
    // . and , still both work here too
    expect(parseFloat("1.3")).toBe(1.3);
    expect(parseFloat("1,3")).toBe(1.3);
    expect(parseFloat("1.000.000,12")).toBe(1000000.12);

    // Apostrophe as thousands separator
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "'" });
    expect(parseFloat("1'000")).toBe(1000);
    expect(parseFloat("1'000'000")).toBe(1000000);
    expect(parseFloat("1'234.56")).toBe(1234.56);
    expect(parseFloat("1'234,56")).toBe(1234.56);

    // Indian grouping (2-3)
    patchWithCleanup(localization, { decimalPoint: ".", thousandsSep: ",", grouping: [3, 2, 0] });
    expect(parseFloat("1,23,456.78")).toBe(123456.78);
    expect(parseFloat("12,34,567")).toBe(1234567);

    // Unrecognized decimal point: just stripped as noise
    patchWithCleanup(localization, { decimalPoint: "@" });
    expect(parseFloat("1@5")).toBe(15);
    patchWithCleanup(localization, { decimalPoint: "@", thousandsSep: false });
    expect(parseFloat("1000@5")).toBe(10005);

    // Scientific notation
    expect(parseFloat("1e5")).toBe(100000);
    expect(parseFloat("1e-3")).toBe(0.001);
    expect(parseFloat("1,3e3")).toBe(1300);
    expect(parseFloat("1.3e-3")).toBe(0.0013);
    expect(parseFloat("1,3e3e2")).toBe(1.332);
    expect(parseFloat("e22")).toBe(22);
    expect(parseFloat("-e22")).toBe(-22);
    expect(parseFloat("1.3e-3e2")).toBe(1.332);

    // Mixed separators: the singular one is the decimal separator
    expect(parseFloat("1,2,3,4,5,6.1,2,3,5")).toBe(1234561235);
    expect(parseFloat("1,000.000,00")).toBe(100000000);
    expect(parseFloat("1.000.000,00")).toBe(1000000);
    expect(parseFloat("1.000,000,000")).toBe(1000000000);
    // Both repeat: no decimal separator
    expect(parseFloat("1.000.000,000,000")).toBe(1000000000000);
    expect(parseFloat("1,000,000.000.000")).toBe(1000000000000);

    // Arabic decimal/thousands separator
    patchWithCleanup(localization, { decimalPoint: "٫", thousandsSep: "٬" });
    expect(parseFloat("1٫5")).toBe(1.5);
    expect(parseFloat("1٬000٫5")).toBe(1000.5);
    // . and , still work too
    expect(parseFloat("1.5")).toBe(1.5);
    expect(parseFloat("1,5")).toBe(1.5);

    // Letters are stripped, not rejected, including trailing noise after a valid number
    expect(parseFloat("a2v3c4")).toBe(234);
    expect(parseFloat("123eee")).toBe(123);

    expect(() => parseFloat("abbc")).toThrow();
    expect(() => parseFloat("-")).toThrow();
    expect(() => parseFloat("12e22222")).toThrow(); // Too big
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

    expect(parseFloatTime("a:12")).toBe(0.2);
    expect(parseFloatTime("1:a")).toBe(1);
    expect(parseFloatTime("1:12:")).toBe(1.2);
    expect(parseFloatTime(":30:45")).toBe(0.5125);

    expect(parseFloatTime("1h 30m 45s")).toBe(1.5125);
    expect(parseFloatTime("1h 45s")).toBe(1.0125);
    expect(parseFloatTime("45s 30m 1h")).toBe(1.5125);
    expect(parseFloatTime("45s 20s 55s")).toBe(0.0125);
    expect(parseFloatTime("1h30")).toBe(1.5);
    expect(parseFloatTime("-1h 30m 45s")).toBe(-1.5125);

    expect(() => parseFloatTime("qwerwqer")).toThrow("Couldn't parse 'qwerwqer'.");

    clearMemoizeCaches();
    localization.locale = "fr-FR";
    expect(parseFloatTime("2h 30m 45s")).toBe(2.5125);
    expect(parseFloatTime("2h 30min 45s")).toBe(2.5125);

    clearMemoizeCaches();
    localization.locale = "zh-CN";
    expect(parseFloatTime("2小时 30分钟 45秒")).toBe(2.5125);

    clearMemoizeCaches();
    localization.locale = "ar-SY";
    expect(parseFloatTime("٢س ٣٠د ٤٥ث")).toBe(2.5125);
    // Arabic decimal separator as a plain single number, like parseFloat accepts
    expect(parseFloatTime("1٫5")).toBe(1.5);

    clearMemoizeCaches();
    localization.thousandsSep = ".";
    localization.decimalPoint = ",";
    expect(parseFloatTime("0,5")).toBe(0.5);
});

test("parseInteger", () => {
    // Basic parsing
    expect(parseInteger("")).toBe(0);
    expect(parseInteger("0")).toBe(0);
    expect(parseInteger("100")).toBe(100);
    expect(parseInteger("-100")).toBe(-100);

    // Unlike parseFloat, . and , are always grouping noise, never a decimal point
    expect(parseInteger("1,000")).toBe(1000);
    expect(parseInteger("1,000,000")).toBe(1000000);
    expect(parseInteger("1.000.000")).toBe(1000000);
    expect(parseInteger("1,234.567")).toBe(1234567);

    // 32-bit integer bounds
    expect(parseInteger("-2,147,483,648")).toBe(-2147483648);
    expect(parseInteger("2,147,483,647")).toBe(2147483647);
    expect(() => parseInteger("-2,147,483,649")).toThrow();
    expect(() => parseInteger("2,147,483,648")).toThrow();

    // Locale doesn't change that
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
    expect(parseInteger("1.000.000")).toBe(1000000);
    expect(parseInteger("1.234,567")).toBe(1234567);
    // fallback to en localization
    expect(parseInteger("1,000,000")).toBe(1000000);

    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: false });
    expect(parseInteger("1000000")).toBe(1000000);

    // Same permissive letter-stripping as parseFloat
    expect(parseInteger("a2v3c4")).toBe(234);
    expect(parseInteger("123eee")).toBe(123);

    expect(() => parseInteger("abbc")).toThrow();
    expect(() => parseInteger("-")).toThrow();
    expect(() => parseInteger("12e22222")).toThrow(); // Too big
});

test("parsePercentage", () => {
    // Basic parsing
    expect(parsePercentage("")).toBe(0);
    expect(parsePercentage("0")).toBe(0);
    expect(parsePercentage("0.5")).toBe(0.005);
    expect(parsePercentage("1")).toBe(0.01);
    expect(parsePercentage("100")).toBe(1);
    expect(parsePercentage("50%")).toBe(0.5);
    // "%" is just stripped like any other character
    expect(parsePercentage("50%40")).toBe(50.4);

    // Locale-specific decimal point / thousands separator
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
    expect(parseFloat("1,234.567")).toBe(1234.567);
});

test("monetary (parseFloat)", () => {
    expect(parseFloat("")).toBe(0);
    expect(parseFloat("0")).toBe(0);
    expect(parseFloat("100.00\u00a0€")).toBe(100);
    expect(parseFloat("-100.00")).toBe(-100);
    expect(parseFloat("1,000.00")).toBe(1000);
    expect(parseFloat(".1")).toBe(0.1);
    expect(parseFloat("1,000,000.00")).toBe(1000000);
    expect(parseFloat("$\u00a0125.00")).toBe(125);
    expect(parseFloat("1,000.00\u00a0€")).toBe(1000);

    expect(parseFloat("\u00a0")).toBe(0);
    expect(parseFloat("1\u00a0")).toBe(1);
    expect(parseFloat("\u00a01")).toBe(1);

    expect(parseFloat("12.00 €")).toBe(12);
    expect(parseFloat("$ 12.00")).toBe(12);
    expect(parseFloat("1\u00a0$")).toBe(1);
    expect(parseFloat("$\u00a01")).toBe(1);

    expect(parseFloat("1$\u00a01")).toBe(11);
    expect(parseFloat("$\u00a012.00\u00a034")).toBe(12.0034);

    expect(parseFloat("1 2345:50 kr")).toBe(1234550);
    expect(parseFloat("€ 50,-")).toBe(50);

    // nbsp as thousands separator
    patchWithCleanup(localization, { thousandsSep: "\u00a0", decimalPoint: "," });
    expect(parseFloat("1\u00a0000,06\u00a0€")).toBe(1000.06);
    expect(parseFloat("$\u00a01\u00a0000,07")).toBe(1000.07);
    expect(parseFloat("1000000,08")).toBe(1000000.08);
    expect(parseFloat("$ -1\u00a0000,09")).toBe(-1000.09);

    // symbol not separated from the value
    expect(parseFloat("1\u00a0000,08€")).toBe(1000.08);
    expect(parseFloat("€1\u00a0000,09")).toBe(1000.09);
    expect(parseFloat("$1\u00a0000,10")).toBe(1000.1);
    expect(parseFloat("$-1\u00a0000,11")).toBe(-1000.11);

    // any symbol
    expect(parseFloat("1\u00a0000,11EUROS")).toBe(1000.11);
    expect(parseFloat("EUR1\u00a0000,12")).toBe(1000.12);
    expect(parseFloat("DOL1\u00a0000,13")).toBe(1000.13);
    expect(parseFloat("1\u00a0000,14DOLLARS")).toBe(1000.14);
    expect(parseFloat("DOLLARS+1\u00a0000,15")).toBe(1000.15);
    expect(parseFloat("EURO-1\u00a0000,16DOGE")).toBe(-1000.16);

    // comma as decimal point and dot as thousands separator
    patchWithCleanup(localization, { thousandsSep: ".", decimalPoint: "," });
    expect(parseFloat("10,08")).toBe(10.08);
    expect(parseFloat("")).toBe(0);
    expect(parseFloat("0")).toBe(0);
    expect(parseFloat("100,12\u00a0€")).toBe(100.12);
    expect(parseFloat("-100,12")).toBe(-100.12);
    expect(parseFloat("1.000,12")).toBe(1000.12);
    expect(parseFloat(",1")).toBe(0.1);
    expect(parseFloat("1.000.000,12")).toBe(1000000.12);
    expect(parseFloat("$\u00a0125,12")).toBe(125.12);
    expect(parseFloat("1.000,00\u00a0€")).toBe(1000);
    expect(() => parseFloat(",")).toThrow();
    expect(parseFloat("1\u00a0")).toBe(1);
    expect(parseFloat("\u00a01")).toBe(1);
    expect(parseFloat("12,34 €")).toBe(12.34);
    expect(parseFloat("$ 12,34")).toBe(12.34);

    // Can evaluate expression
    expect(parseFloat("=1.000,1 + 2.000,2")).toBe(3000.3);
    expect(parseFloat("=1.000,00 + 11.121,00")).toBe(12121);
    expect(parseFloat("=1000,00 + 11122,00")).toBe(12122);
    expect(parseFloat("=1000 + 11123")).toBe(12123);
});
