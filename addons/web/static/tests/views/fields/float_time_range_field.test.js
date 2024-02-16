import { expect, test } from "@odoo/hoot";
import { mockTimeZone } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Product extends models.Model {
    time_start = fields.Float({ string: "Start" });
    time_end = fields.Float({ string: "End" });
}

defineModels([Product]);

test("set a time range", async () => {
    mockTimeZone(0);
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ time_start: 9.15 });
    });
    Product._records = [{ id: 1, time_start: 12.5 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="time_start" widget="float_time_range" options="{'end_time_field': 'time_end'}"/></form>`,
    });
    expect(".o_field_float_time_range input[type=time]").toHaveCount(2);
    expect("input:nth-of-type(1)").toHaveValue("12:30");
    expect("input:nth-of-type(2)").toHaveValue("00:00");
    await contains("input:nth-of-type(1)").edit("09:09", { instantly: true });
    await clickSave();
});
