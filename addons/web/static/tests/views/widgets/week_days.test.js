import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import {
    clickSave,
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    sun = fields.Boolean();
    mon = fields.Boolean();
    tue = fields.Boolean();
    wed = fields.Boolean();
    thu = fields.Boolean();
    fri = fields.Boolean();
    sat = fields.Boolean();

    _records = [
        {
            id: 1,
            sun: false,
            mon: false,
            tue: false,
            wed: false,
            thu: false,
            fri: false,
            sat: false,
        },
    ];
}

defineModels([Partner]);

test("simple week recurrence widget", async () => {
    expect.assertions(13);
    defineParams({ lang_parameters: { week_start: 1 } });
    let writeCall = 0;
    onRpc("web_save", ({ args }) => {
        writeCall++;
        if (writeCall === 1) {
            expect(args[1].sun).toBe(true);
        }
        if (writeCall === 2) {
            expect(args[1].sun).not.toBe(true);
            expect(args[1].mon).toBe(true);
            expect(args[1].tue).toBe(true);
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><sheet><group><widget name="week_days" /></group></sheet></form>`,
    });

    expect(queryAllTexts(".o_recurrent_weekday_label")).toEqual(
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        { message: "labels should be short week names" }
    );
    expect(".form-check input:disabled").toHaveCount(0, {
        message: "all inputs should be enabled in edit mode",
    });

    await click("td:nth-child(7) input");
    expect("td:nth-child(7) input").toBeChecked({
        message: "sunday checkbox should be checked",
    });

    await clickSave();

    await click("td:nth-child(1) input");
    expect("td:nth-child(1) input").toBeChecked({
        message: "monday checkbox should be checked",
    });

    await click("td:nth-child(2) input");
    expect("td:nth-child(2) input").toBeChecked({
        message: "tuesday checkbox should be checked",
    });

    // uncheck Sunday checkbox and check write call
    await click("td:nth-child(7) input");
    expect("td:nth-child(7) input").not.toBeChecked({
        message: "sunday checkbox should be unchecked",
    });

    await clickSave();

    expect("td:nth-child(7) input").not.toBeChecked({
        message: "sunday checkbox should be unchecked",
    });
    expect("td:nth-child(1) input").toBeChecked({ message: "monday checkbox should be checked" });
    expect("td:nth-child(2) input").toBeChecked({
        message: "tuesday checkbox should be checked",
    });
});

test("week recurrence widget readonly modifiers", async () => {
    defineParams({ lang_parameters: { week_start: 1 } });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><sheet><group><widget name="week_days" readonly="1"/></group></sheet></form>`,
    });

    expect(queryAllTexts(".o_recurrent_weekday_label")).toEqual(
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        { message: "labels should be short week names" }
    );
    expect(".form-check input:disabled").toHaveCount(7, {
        message: "all inputs should be disabled in readonly mode",
    });
});

test("week recurrence widget show week start as per language configuration", async () => {
    defineParams({ lang_parameters: { week_start: 5 } });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><sheet><group><widget name="week_days"/></group></sheet></form>`,
    });

    expect(queryAllTexts(".o_recurrent_weekday_label")).toEqual(
        ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"],
        { message: "labels should be short week names" }
    );
});
