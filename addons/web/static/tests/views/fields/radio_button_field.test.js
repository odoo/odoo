import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { clickSave, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
    });
}

defineModels([Partner]);

test("radio button field on a selection in a new record", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="color" widget="radio_button"/></form>`,
    });

    expect("div.o_radio_item").toHaveCount(2);
    expect("input.btn-check").toHaveCount(2, { message: "should have 2 possible choices" });
    expect("label").toHaveClass("btn btn-primary");
    expect(queryAllTexts("label")).toEqual(["Red", "Black"]);

    // click on 2nd option
    click("input.btn-check:eq(1)");
    await animationFrame();

    await clickSave();

    expect("input.btn-check:checked").toHaveAttribute("data-value", "black", {
        message: "should have saved record with correct value",
    });
});
