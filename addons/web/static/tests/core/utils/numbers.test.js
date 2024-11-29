import { describe, expect, test } from "@odoo/hoot";
import { patchTranslations, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { localization } from "@web/core/l10n/localization";
import {
    clamp,
    floatIsZero,
    formatFloat,
    range,
    roundDecimals,
    roundPrecision,
} from "@web/core/utils/numbers";

describe.current.tags("headless");

test("clamp", () => {
    expect(clamp(-5, 0, 10)).toBe(0);
    expect(clamp(0, 0, 10)).toBe(0);
    expect(clamp(2, 0, 10)).toBe(2);
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(7, 0, 10)).toBe(7);
    expect(clamp(10, 0, 10)).toBe(10);
    expect(clamp(15, 0, 10)).toBe(10);
});

test("range", () => {
    expect(range(0, 10)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    expect(range(0, 35, 5)).toEqual([0, 5, 10, 15, 20, 25, 30]);
    expect(range(-10, 6, 2)).toEqual([-10, -8, -6, -4, -2, 0, 2, 4]);
    expect(range(0, -10, -1)).toEqual([0, -1, -2, -3, -4, -5, -6, -7, -8, -9]);
    expect(range(4, -4, -1)).toEqual([4, 3, 2, 1, 0, -1, -2, -3]);
    expect(range(1, 4, -1)).toEqual([]);
    expect(range(1, -4, 1)).toEqual([]);
});

describe("roundPrecision", () => {
    test("default method (HALF-UP)", () => {
        expect(roundPrecision(1.0, 1)).toBe(1);
        expect(roundPrecision(1.0, 0.1)).toBe(1);
        expect(roundPrecision(1.0, 0.01)).toBe(1);
        expect(roundPrecision(1.0, 0.001)).toBe(1);
        expect(roundPrecision(1.0, 0.0001)).toBe(1);
        expect(roundPrecision(1.0, 0.00001)).toBe(1);
        expect(roundPrecision(1.0, 0.000001)).toBe(1);
        expect(roundPrecision(1.0, 0.0000001)).toBe(1);
        expect(roundPrecision(1.0, 0.00000001)).toBe(1);
        expect(roundPrecision(0.5, 1)).toBe(1);
        expect(roundPrecision(-0.5, 1)).toBe(-1);
        expect(roundPrecision(2.6745, 0.001)).toBe(2.675);
        expect(roundPrecision(-2.6745, 0.001)).toBe(-2.675);
        expect(roundPrecision(2.6744, 0.001)).toBe(2.674);
        expect(roundPrecision(-2.6744, 0.001)).toBe(-2.674);
        expect(roundPrecision(0.0004, 0.001)).toBe(0);
        expect(roundPrecision(-0.0004, 0.001)).toBe(0);
        expect(roundPrecision(357.4555, 0.001)).toBe(357.456);
        expect(roundPrecision(-357.4555, 0.001)).toBe(-357.456);
        expect(roundPrecision(457.4554, 0.001)).toBe(457.455);
        expect(roundPrecision(-457.4554, 0.001)).toBe(-457.455);
        expect(roundPrecision(-457.4554, 0.05)).toBe(-457.45);
        expect(roundPrecision(457.444, 0.5)).toBe(457.5);
        expect(roundPrecision(457.3, 5)).toBe(455);
        expect(roundPrecision(457.5, 5)).toBe(460);
        expect(roundPrecision(457.1, 3)).toBe(456);

        expect(roundPrecision(2.6735, 0.001)).toBe(2.674);
        expect(roundPrecision(-2.6735, 0.001)).toBe(-2.674);
        expect(roundPrecision(2.6745, 0.001)).toBe(2.675);
        expect(roundPrecision(-2.6745, 0.001)).toBe(-2.675);
        expect(roundPrecision(2.6744, 0.001)).toBe(2.674);
        expect(roundPrecision(-2.6744, 0.001)).toBe(-2.674);
        expect(roundPrecision(0.0004, 0.001)).toBe(0);
        expect(roundPrecision(-0.0004, 0.001)).toBe(-0);
        expect(roundPrecision(357.4555, 0.001)).toBe(357.456);
        expect(roundPrecision(-357.4555, 0.001)).toBe(-357.456);
        expect(roundPrecision(457.4554, 0.001)).toBe(457.455);
        expect(roundPrecision(-457.4554, 0.001)).toBe(-457.455);
    });

    test("DOWN", () => {
        // We use 2.425 because when normalizing 2.425 with precision=0.001 it gives
        // us 2424.9999999999995 as value, and if not handle correctly the rounding DOWN
        // value will be incorrect (should be 2.425 and not 2.424)
        expect(roundPrecision(2.425, 0.001, "DOWN")).toBe(2.425);
        expect(roundPrecision(2.4249, 0.001, "DOWN")).toBe(2.424);
        expect(roundPrecision(-2.425, 0.001, "DOWN")).toBe(-2.425);
        expect(roundPrecision(-2.4249, 0.001, "DOWN")).toBe(-2.424);
        expect(roundPrecision(-2.5, 0.001, "DOWN")).toBe(-2.5);
        expect(roundPrecision(1.8, 1, "DOWN")).toBe(1);
        expect(roundPrecision(-1.8, 1, "DOWN")).toBe(-1);
    });

    test("HALF-DOWN", () => {
        expect(roundPrecision(2.6735, 0.001, "HALF-DOWN")).toBe(2.673);
        expect(roundPrecision(-2.6735, 0.001, "HALF-DOWN")).toBe(-2.673);
        expect(roundPrecision(2.6745, 0.001, "HALF-DOWN")).toBe(2.674);
        expect(roundPrecision(-2.6745, 0.001, "HALF-DOWN")).toBe(-2.674);
        expect(roundPrecision(2.6744, 0.001, "HALF-DOWN")).toBe(2.674);
        expect(roundPrecision(-2.6744, 0.001, "HALF-DOWN")).toBe(-2.674);
        expect(roundPrecision(0.0004, 0.001, "HALF-DOWN")).toBe(0);
        expect(roundPrecision(-0.0004, 0.001, "HALF-DOWN")).toBe(-0);
        expect(roundPrecision(357.4555, 0.001, "HALF-DOWN")).toBe(357.455);
        expect(roundPrecision(-357.4555, 0.001, "HALF-DOWN")).toBe(-357.455);
        expect(roundPrecision(457.4554, 0.001, "HALF-DOWN")).toBe(457.455);
        expect(roundPrecision(-457.4554, 0.001, "HALF-DOWN")).toBe(-457.455);
    });

    test("HALF-UP", () => {
        expect(roundPrecision(2.6735, 0.001, "HALF-UP")).toBe(2.674);
        expect(roundPrecision(-2.6735, 0.001, "HALF-UP")).toBe(-2.674);
        expect(roundPrecision(2.6745, 0.001, "HALF-UP")).toBe(2.675);
        expect(roundPrecision(-2.6745, 0.001, "HALF-UP")).toBe(-2.675);
        expect(roundPrecision(2.6744, 0.001, "HALF-UP")).toBe(2.674);
        expect(roundPrecision(-2.6744, 0.001, "HALF-UP")).toBe(-2.674);
        expect(roundPrecision(0.0004, 0.001, "HALF-UP")).toBe(0);
        expect(roundPrecision(-0.0004, 0.001, "HALF-UP")).toBe(-0);
        expect(roundPrecision(357.4555, 0.001, "HALF-UP")).toBe(357.456);
        expect(roundPrecision(-357.4555, 0.001, "HALF-UP")).toBe(-357.456);
        expect(roundPrecision(457.4554, 0.001, "HALF-UP")).toBe(457.455);
        expect(roundPrecision(-457.4554, 0.001, "HALF-UP")).toBe(-457.455);
    });

    test("HALF-EVEN", () => {
        expect(roundPrecision(5.015, 0.01, "HALF-EVEN")).toBe(5.02);
        expect(roundPrecision(-5.015, 0.01, "HALF-EVEN")).toBe(-5.02);
        expect(roundPrecision(5.025, 0.01, "HALF-EVEN")).toBe(5.02);
        expect(roundPrecision(-5.025, 0.01, "HALF-EVEN")).toBe(-5.02);
        expect(roundPrecision(2.6735, 0.001, "HALF-EVEN")).toBe(2.674);
        expect(roundPrecision(-2.6735, 0.001, "HALF-EVEN")).toBe(-2.674);
        expect(roundPrecision(2.6745, 0.001, "HALF-EVEN")).toBe(2.674);
        expect(roundPrecision(-2.6745, 0.001, "HALF-EVEN")).toBe(-2.674);
        expect(roundPrecision(2.6744, 0.001, "HALF-EVEN")).toBe(2.674);
        expect(roundPrecision(-2.6744, 0.001, "HALF-EVEN")).toBe(-2.674);
        expect(roundPrecision(0.0004, 0.001, "HALF-EVEN")).toBe(0);
        expect(roundPrecision(-0.0004, 0.001, "HALF-EVEN")).toBe(-0);
        expect(roundPrecision(357.4555, 0.001, "HALF-EVEN")).toBe(357.456);
        expect(roundPrecision(-357.4555, 0.001, "HALF-EVEN")).toBe(-357.456);
        expect(roundPrecision(457.4554, 0.001, "HALF-EVEN")).toBe(457.455);
        expect(roundPrecision(-457.4554, 0.001, "HALF-EVEN")).toBe(-457.455);
    });

    test("UP", () => {
        // We use 8.175 because when normalizing 8.175 with precision=0.001 it gives
        // us 8175,0000000001234 as value, and if not handle correctly the rounding UP
        // value will be incorrect (should be 8,175 and not 8,176)
        expect(roundPrecision(8.175, 0.001, "UP")).toBe(8.175);
        expect(roundPrecision(8.1751, 0.001, "UP")).toBe(8.176);
        expect(roundPrecision(-8.175, 0.001, "UP")).toBe(-8.175);
        expect(roundPrecision(-8.1751, 0.001, "UP")).toBe(-8.176);
        expect(roundPrecision(-6.0, 0.001, "UP")).toBe(-6);
        expect(roundPrecision(1.8, 1, "UP")).toBe(2);
        expect(roundPrecision(-1.8, 1, "UP")).toBe(-2);
    });
});

test("roundDecimals", () => {
    expect(roundDecimals(1.0, 0)).toBe(1);
    expect(roundDecimals(1.0, 1)).toBe(1);
    expect(roundDecimals(1.0, 2)).toBe(1);
    expect(roundDecimals(1.0, 3)).toBe(1);
    expect(roundDecimals(1.0, 4)).toBe(1);
    expect(roundDecimals(1.0, 5)).toBe(1);
    expect(roundDecimals(1.0, 6)).toBe(1);
    expect(roundDecimals(1.0, 7)).toBe(1);
    expect(roundDecimals(1.0, 8)).toBe(1);
    expect(roundDecimals(0.5, 0)).toBe(1);
    expect(roundDecimals(-0.5, 0)).toBe(-1);
    expect(roundDecimals(2.6745, 3)).toBe(2.675);
    expect(roundDecimals(-2.6745, 3)).toBe(-2.675);
    expect(roundDecimals(2.6744, 3)).toBe(2.674);
    expect(roundDecimals(-2.6744, 3)).toBe(-2.674);
    expect(roundDecimals(0.0004, 3)).toBe(0);
    expect(roundDecimals(-0.0004, 3)).toBe(0);
    expect(roundDecimals(357.4555, 3)).toBe(357.456);
    expect(roundDecimals(-357.4555, 3)).toBe(-357.456);
    expect(roundDecimals(457.4554, 3)).toBe(457.455);
    expect(roundDecimals(-457.4554, 3)).toBe(-457.455);
});

test("floatIsZero", () => {
    expect(floatIsZero(1, 0)).toBe(false);
    expect(floatIsZero(0.9999, 0)).toBe(false);
    expect(floatIsZero(0.50001, 0)).toBe(false);
    expect(floatIsZero(0.5, 0)).toBe(false);
    expect(floatIsZero(0.49999, 0)).toBe(true);
    expect(floatIsZero(0, 0)).toBe(true);
    expect(floatIsZero(-0.49999, 0)).toBe(true);
    expect(floatIsZero(-0.50001, 0)).toBe(false);
    expect(floatIsZero(-0.5, 0)).toBe(false);
    expect(floatIsZero(-0.9999, 0)).toBe(false);
    expect(floatIsZero(-1, 0)).toBe(false);

    expect(floatIsZero(0.1, 1)).toBe(false);
    expect(floatIsZero(0.099999, 1)).toBe(false);
    expect(floatIsZero(0.050001, 1)).toBe(false);
    expect(floatIsZero(0.05, 1)).toBe(false);
    expect(floatIsZero(0.049999, 1)).toBe(true);
    expect(floatIsZero(0, 1)).toBe(true);
    expect(floatIsZero(-0.049999, 1)).toBe(true);
    expect(floatIsZero(-0.05, 1)).toBe(false);
    expect(floatIsZero(-0.050001, 1)).toBe(false);
    expect(floatIsZero(-0.099999, 1)).toBe(false);
    expect(floatIsZero(-0.1, 1)).toBe(false);

    expect(floatIsZero(0.01, 2)).toBe(false);
    expect(floatIsZero(0.0099999, 2)).toBe(false);
    expect(floatIsZero(0.005, 2)).toBe(false);
    expect(floatIsZero(0.0050001, 2)).toBe(false);
    expect(floatIsZero(0.0049999, 2)).toBe(true);
    expect(floatIsZero(0, 2)).toBe(true);
    expect(floatIsZero(-0.0049999, 2)).toBe(true);
    expect(floatIsZero(-0.0050001, 2)).toBe(false);
    expect(floatIsZero(-0.005, 2)).toBe(false);
    expect(floatIsZero(-0.0099999, 2)).toBe(false);
    expect(floatIsZero(-0.01, 2)).toBe(false);

    // 4 and 5 decimal places are mentioned as special cases in `roundDecimals` method.
    expect(floatIsZero(0.0001, 4)).toBe(false);
    expect(floatIsZero(0.000099999, 4)).toBe(false);
    expect(floatIsZero(0.00005, 4)).toBe(false);
    expect(floatIsZero(0.000050001, 4)).toBe(false);
    expect(floatIsZero(0.000049999, 4)).toBe(true);
    expect(floatIsZero(0, 4)).toBe(true);
    expect(floatIsZero(-0.000049999, 4)).toBe(true);
    expect(floatIsZero(-0.000050001, 4)).toBe(false);
    expect(floatIsZero(-0.00005, 4)).toBe(false);
    expect(floatIsZero(-0.000099999, 4)).toBe(false);
    expect(floatIsZero(-0.0001, 4)).toBe(false);

    expect(floatIsZero(0.00001, 5)).toBe(false);
    expect(floatIsZero(0.0000099999, 5)).toBe(false);
    expect(floatIsZero(0.000005, 5)).toBe(false);
    expect(floatIsZero(0.0000050001, 5)).toBe(false);
    expect(floatIsZero(0.0000049999, 5)).toBe(true);
    expect(floatIsZero(0, 5)).toBe(true);
    expect(floatIsZero(-0.0000049999, 5)).toBe(true);
    expect(floatIsZero(-0.0000050001, 5)).toBe(false);
    expect(floatIsZero(-0.000005, 5)).toBe(false);
    expect(floatIsZero(-0.0000099999, 5)).toBe(false);
    expect(floatIsZero(-0.00001, 5)).toBe(false);

    expect(floatIsZero(0.0000001, 7)).toBe(false);
    expect(floatIsZero(0.000000099999, 7)).toBe(false);
    expect(floatIsZero(0.00000005, 7)).toBe(false);
    expect(floatIsZero(0.000000050001, 7)).toBe(false);
    expect(floatIsZero(0.000000049999, 7)).toBe(true);
    expect(floatIsZero(0, 7)).toBe(true);
    expect(floatIsZero(-0.000000049999, 7)).toBe(true);
    expect(floatIsZero(-0.000000050001, 7)).toBe(false);
    expect(floatIsZero(-0.00000005, 7)).toBe(false);
    expect(floatIsZero(-0.000000099999, 7)).toBe(false);
    expect(floatIsZero(-0.0000001, 7)).toBe(false);
});

describe("formatFloat", () => {
    test("localized", () => {
        patchWithCleanup(localization, {
            decimalPoint: ".",
            grouping: [3, 0],
            thousandsSep: ",",
        });
        expect(formatFloat(1000000)).toBe("1,000,000.00");

        const options = { grouping: [3, 2, -1], decimalPoint: "?", thousandsSep: "€" };
        expect(formatFloat(106500, options)).toBe("1€06€500?00");

        expect(formatFloat(1500, { thousandsSep: "" })).toBe("1500.00");
        expect(formatFloat(-1.01)).toBe("-1.01");
        expect(formatFloat(-0.01)).toBe("-0.01");

        expect(formatFloat(38.0001, { trailingZeros: false })).toBe("38");
        expect(formatFloat(38.1, { trailingZeros: false })).toBe("38.1");
        expect(formatFloat(38.0001, { digits: [16, 0], trailingZeros: false })).toBe("38");

        patchWithCleanup(localization, { grouping: [3, 3, 3, 3] });
        expect(formatFloat(1000000)).toBe("1,000,000.00");

        patchWithCleanup(localization, { grouping: [3, 2, -1] });
        expect(formatFloat(106500)).toBe("1,06,500.00");

        patchWithCleanup(localization, { grouping: [1, 2, -1] });
        expect(formatFloat(106500)).toBe("106,50,0.00");

        patchWithCleanup(localization, {
            decimalPoint: "!",
            grouping: [2, 0],
            thousandsSep: "@",
        });
        expect(formatFloat(6000)).toBe("60@00!00");
    });

    test("humanReadable", () => {
        patchTranslations();
        patchWithCleanup(localization, {
            decimalPoint: ".",
            grouping: [3, 0],
            thousandsSep: ",",
        });

        const options = { humanReadable: true };
        expect(formatFloat(1e18, options)).toBe("1E");
        expect(formatFloat(-1e18, options)).toBe("-1E");

        Object.assign(options, { decimals: 2, minDigits: 1 });
        expect(formatFloat(1020, options)).toBe("1.02k");
        expect(formatFloat(1002, options)).toBe("1.00k");
        expect(formatFloat(101, options)).toBe("101.00");
        expect(formatFloat(64.2, options)).toBe("64.20");
        expect(formatFloat(1020, options)).toBe("1.02k");
        expect(formatFloat(1e21, options)).toBe("1e+21");
        expect(formatFloat(1.0045e22, options)).toBe("1e+22");
        expect(formatFloat(1.012e43, options)).toBe("1.01e+43");
        expect(formatFloat(-1020, options)).toBe("-1.02k");
        expect(formatFloat(-1020, options)).toBe("-1.02k");
        expect(formatFloat(-1002, options)).toBe("-1.00k");
        expect(formatFloat(-101, options)).toBe("-101.00");
        expect(formatFloat(-64.2, options)).toBe("-64.20");
        expect(formatFloat(-1e21, options)).toBe("-1e+21");
        expect(formatFloat(-1.0045e22, options)).toBe("-1e+22");
        expect(formatFloat(-1.012e43, options)).toBe("-1.01e+43");

        Object.assign(options, { decimals: 2, minDigits: 2 });
        expect(formatFloat(1020000, options)).toBe("1,020k");
        expect(formatFloat(10200000, options)).toBe("10.20M");
        expect(formatFloat(1.012e43, options)).toBe("1.01e+43");
        expect(formatFloat(-1020000, options)).toBe("-1,020k");
        expect(formatFloat(-10200000, options)).toBe("-10.20M");
        expect(formatFloat(-1.012e43, options)).toBe("-1.01e+43");

        Object.assign(options, { decimals: 3, minDigits: 1 });
        expect(formatFloat(1.0045e22, options)).toBe("1.005e+22");
        expect(formatFloat(-1.0045e22, options)).toBe("-1.004e+22");
    });
});
