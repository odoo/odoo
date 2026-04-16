import { expect, test } from "@odoo/hoot";
import { click, press, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    icon = fields.Char();
}

defineModels([Partner]);

test("fa_icon in form view renders icon class value", async () => {
    Partner._records = [{ id: 1, icon: "fa fa-user" }];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="icon" widget="fa_icon"/></form>`,
    });

    const input = queryFirst(".o_select_menu_input");
    expect(input.value).toEqual("fa fa-user");
});

test("fa_icon updates value when selecting icon", async () => {
    Partner._records = [{ id: 1, icon: "" }];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="icon" widget="fa_icon"/></form>`,
    });

    const input = queryFirst(".o_select_menu_input");
    // placeholder should be visible when no icon is selected
    expect(input.placeholder).toEqual("Select icon");

    // open dropdown
    await click(input);
    await animationFrame();
    expect(".o_fa_icon_field_selector_menu").toHaveCount(1);

    // select fa-user icon
    await click(queryFirst(".fa-user"));
    await animationFrame();

    // value should now be set to "fa fa-user"
    expect(input.value).toEqual("fa fa-user");
});

test("fa_icon does not open dropdown if readonly", async () => {
    Partner._records = [{ id: 1, icon: "fa fa-user" }];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form>
            <field name="icon" widget="fa_icon" readonly="1"/>
        </form>`,
    });

    // dropdown should not appear
    expect(".o_select_menu_input").toHaveCount(0);
});

test.tags("desktop");
test("fa_icon clears value when backspace is pressed", async () => {
    Partner._records = [{ id: 1, icon: "fa fa-user" }];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="icon" widget="fa_icon"/></form>`,
    });

    const input = queryFirst(".o_select_menu_input");

    // Verify initial value
    expect(input.value).toEqual("fa fa-user");

    // Focus input and simulate backspace key press
    await click(input);
    await animationFrame();
    await press("Backspace");
    await animationFrame();

    // Input should now be cleared
    expect(input.value).toEqual("");
});
