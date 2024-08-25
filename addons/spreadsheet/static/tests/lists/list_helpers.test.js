import { describe, expect, test } from "@odoo/hoot";

import { tokenize } from "@odoo/o-spreadsheet";
import { getFirstListFunction, getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";

function stringArg(value) {
    return { type: "STRING", value: `${value}` };
}

describe.current.tags("headless");

test("Basic formula extractor", async function () {
    const formula = `=SUM(3) + ODOO.LIST("2", "hello", "bla")`;
    const tokens = tokenize(formula);
    const { functionName, args } = getFirstListFunction(tokens);
    expect(functionName).toBe("ODOO.LIST");
    expect(args.length).toBe(3);
    expect(args[0]).toEqual(stringArg("2"));
    expect(args[1]).toEqual(stringArg("hello"));
    expect(args[2]).toEqual(stringArg("bla"));
});

test("Number of formulas", async function () {
    const formula = `=ODOO.LIST("1", "test") + ODOO.LIST("1", "bla")`;
    expect(getNumberOfListFormulas(tokenize(formula))).toBe(2);
    expect(getNumberOfListFormulas(tokenize("=1+1"))).toBe(0);
    expect(getNumberOfListFormulas(tokenize("=bla"))).toBe(0);
});

test("getFirstListFunction does not crash when given crap", async function () {
    expect(getFirstListFunction(tokenize("=SUM(A1)"))).toBe(undefined);
    expect(getFirstListFunction(tokenize("=1+1"))).toBe(undefined);
    expect(getFirstListFunction(tokenize("=bla"))).toBe(undefined);
    expect(getFirstListFunction(tokenize("bla"))).toBe(undefined);
});
