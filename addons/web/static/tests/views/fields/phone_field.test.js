import {
    clickSave,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { expect, test } from "@odoo/hoot";
import { click, edit, pointerDown, queryFirst, queryOne } from "@odoo/hoot-dom";
import { getNextTabableElement } from "@web/core/utils/ui";
import { animationFrame } from "@odoo/hoot-mock";

class Partner extends models.Model {
    foo = fields.Char({ string: "Foo", default: "My little Foo Value", trim: true });
    _records = [{ foo: "yop" }, { foo: "blip" }];
}

defineModels([Partner]);

test("PhoneField in form view on normal screens (readonly)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        mode: "readonly",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="phone"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect(".o_field_phone a").toHaveCount(1);
    expect(".o_field_phone a").toHaveText("yop");
    expect(".o_field_phone a").toHaveAttribute("href", "tel:yop");
});

test("PhoneField in form view on normal screens (edit)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="phone"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect(`input[type="tel"]`).toHaveCount(1);
    expect(`input[type="tel"]`).toHaveValue("yop");
    expect(".o_field_phone a").toHaveCount(1);
    expect(".o_field_phone a").toHaveText("Call");
    expect(".o_field_phone a").toHaveAttribute("href", "tel:yop");

    // change value in edit mode
    click(`input[type="tel"]`);
    edit("new");
    await animationFrame();
    // save
    await clickSave();
    expect(`input[type="tel"]`).toHaveValue("new");
});

test("PhoneField in editable list view on normal screens", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
    });
    expect("tbody td:not(.o_list_record_selector).o_data_cell").toHaveCount(2);
    expect("tbody td:not(.o_list_record_selector) a:first").toHaveText("yop");
    expect(".o_field_widget a.o_form_uri").toHaveCount(2);

    // Edit a line and check the result
    const cell = queryFirst("tbody td:not(.o_list_record_selector)");
    click(cell);
    await animationFrame();
    expect(cell.parentElement).toHaveClass("o_selected_row");
    expect(`tbody td:not(.o_list_record_selector) input`).toHaveValue("yop");

    click(`tbody td:not(.o_list_record_selector) input`);
    edit("new");
    click(".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_save");
    await animationFrame();

    expect(".o_selected_row").toHaveCount(0);
    expect("tbody td:not(.o_list_record_selector) a:first").toHaveText("new");
    expect(".o_field_widget a.o_form_uri").toHaveCount(2);
});

test("use TAB to navigate to a PhoneField", async () => {
    Partner._fields.display_name = fields.Char();
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="display_name"/>
                        <field name="foo" widget="phone"/>
                    </group>
                </sheet>
            </form>`,
    });

    pointerDown(".o_field_widget[name=display_name] input");

    expect(".o_field_widget[name=display_name] input").toBeFocused();
    expect(queryOne`[name="foo"] input:only`).toBe(getNextTabableElement());
});

test("phone field with placeholder", async () => {
    Partner._fields.foo = fields.Char({ string: "Foo", default: false, trim: true });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="phone" placeholder="Placeholder"/>
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_field_widget[name='foo'] input").toHaveProperty("placeholder", "Placeholder");
});

test("unset and readonly PhoneField", async () => {
    Partner._fields.foo = fields.Char({ string: "Foo", default: false, trim: true });
    await mountView({
        type: "form",
        resModel: "partner",

        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="phone" readonly="1" placeholder="Placeholder"/>
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_field_widget[name='foo'] a").toHaveCount(0);
});

test("href is correctly formatted", async () => {
    Partner._records[0].foo = "+12 345 67 89 00";
    await mountView({
        type: "form",
        resModel: "partner",
        mode: "readonly",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="phone"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect(".o_field_phone a").toHaveText("+12 345 67 89 00");
    expect(".o_field_phone a").toHaveAttribute("href", "tel:+12345678900");
});
