import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { makeMockEnv, serverState } from "@web/../tests/web_test_helpers";

import { formatCurrency } from "@web/core/currency";

describe.current.tags("headless");

beforeEach(async () => {
    await makeMockEnv(); // To start the localization service
});

test("formatCurrency", async () => {
    serverState.currencies = [
        { id: 1, position: "after", symbol: "€" },
        { id: 2, position: "before", symbol: "$" },
    ];

    expect(formatCurrency(200)).toBe("200.00");
    expect(formatCurrency(1234567.654, 1)).toBe("1,234,567.65\u00a0€");
    expect(formatCurrency(1234567.654, 2)).toBe("$\u00a01,234,567.65");
    expect(formatCurrency(1234567.654, 44)).toBe("1,234,567.65");
    expect(formatCurrency(1234567.654, 1, { noSymbol: true })).toBe("1,234,567.65");
    expect(formatCurrency(8.0, 1, { humanReadable: true })).toBe("8.00\u00a0€");
    expect(formatCurrency(1234567.654, 1, { humanReadable: true })).toBe("1.23M\u00a0€");
    expect(formatCurrency(1990000.001, 1, { humanReadable: true })).toBe("1.99M\u00a0€");
    expect(formatCurrency(1234567.654, 44, { digits: [69, 1] })).toBe("1,234,567.7");
    expect(formatCurrency(1234567.654, 2, { digits: [69, 1] })).toBe("$\u00a01,234,567.7", {
        message: "options digits should take over currency digits when both are defined",
    });
});

test("formatCurrency without currency", async () => {
    serverState.currencies = [];

    expect(formatCurrency(1234567.654, 10, { humanReadable: true })).toBe("1.23M");
    expect(formatCurrency(1234567.654, 10)).toBe("1,234,567.65");
});
