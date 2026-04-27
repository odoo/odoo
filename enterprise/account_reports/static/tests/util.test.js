import { expect, test } from "@odoo/hoot";

import { buildLineId, parseLineId, removeTaxGroupingFromLineId } from "@account_reports/js/util";

test("can build a line id from a list of [markup, res_model, res_id]", () => {
    const values = [
        [false, "account.account", 72],
        [null, "account.move", "10"],
        [undefined, "account.move.line", "22"],
        ["name", false, null],
        ['{"groupby": "account"}', false, null],
    ];
    expect(buildLineId(values)).toBe(
        '~account.account~72|~account.move~10|~account.move.line~22|name~~|{"groupby": "account"}~~'
    );
});

test("can parse a line id from a generic id with a markup as object", () => {
    const genericId =
        '~account.account~72|~account.move~10|~account.move.line~22|name~~|{"groupby": "account"}~~';
    expect(parseLineId(genericId)).toEqual([
        [null, "account.account", 72],
        [null, "account.move", 10],
        [null, "account.move.line", 22],
        ["name", null, null],
        [{ groupby: "account" }, null, null],
    ]);
});

test("can parse a line id from a generic id with a markup as string", () => {
    const genericId =
        '~account.account~72|~account.move~10|~account.move.line~22|name~~|{"groupby": "account"}~~';
    expect(parseLineId(genericId, true)).toEqual([
        [null, "account.account", 72],
        [null, "account.move", 10],
        [null, "account.move.line", 22],
        ["name", null, null],
        ['{"groupby": "account"}', null, null],
    ]);
});

test("can parse and rebuild a line id to have the same one", () => {
    const genericId =
        '~account.account~72|~account.move~10|~account.move.line~22|name~~|{"groupby": "account"}~~';
    const parsedLineId = parseLineId(genericId);
    const buildedGenericId = buildLineId(parsedLineId);
    expect(buildedGenericId).toBe(genericId);
});

test("can remove tax grouping by account group", () => {
    const genericId =
        '{"groupby": "account_group_id"}~account.group~22|~account.account~21|~account.move.line~20';
    expect(removeTaxGroupingFromLineId(genericId)).toBe(
        "~account.account~21|~account.move.line~20"
    );
});
