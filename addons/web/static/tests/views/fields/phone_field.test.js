import {
    clickSave,
    contains,
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
    foo = fields.Char({ default: "My little Foo Value", trim: true });
    name = fields.Char();

    _records = [{ foo: "yop" }, { foo: "blip" }];
}

defineModels([Partner]);

test("PhoneField in form view on normal screens (readonly)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        readonly: true,
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
    await click(`input[type="tel"]`);
    await edit("new");
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
        arch: '<list editable="bottom"><field name="foo" widget="phone"/></list>',
    });
    expect("tbody td:not(.o_list_record_selector).o_data_cell").toHaveCount(2);
    expect("tbody td:not(.o_list_record_selector) a:first").toHaveText("yop");
    expect(".o_field_widget a.o_form_uri").toHaveCount(2);

    // Edit a line and check the result
    const cell = queryFirst("tbody td:not(.o_list_record_selector)");
    await click(cell);
    await animationFrame();
    expect(cell.parentElement).toHaveClass("o_selected_row");
    expect(`tbody td:not(.o_list_record_selector) input`).toHaveValue("yop");

    await click(`tbody td:not(.o_list_record_selector) input`);
    await edit("new");
    await animationFrame();
    await click(".o_control_panel_main_buttons .o_list_button_save");
    await animationFrame();

    expect(".o_selected_row").toHaveCount(0);
    expect("tbody td:not(.o_list_record_selector) a:first").toHaveText("new");
    expect(".o_field_widget a.o_form_uri").toHaveCount(2);
});

test("use TAB to navigate to a PhoneField", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="foo" widget="phone"/>
                    </group>
                </sheet>
            </form>`,
    });

    await pointerDown(".o_field_widget[name=name] input");

    expect(".o_field_widget[name=name] input").toBeFocused();
    expect(queryOne`[name="foo"] input:only`).toBe(getNextTabableElement());
});

test("phone field with placeholder", async () => {
    Partner._fields.foo.default = false;
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

test("placeholder_field shows as placeholder", async () => {
    Partner._fields.char = fields.Char({
        default: "My Placeholder",
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form>
            <field name="foo" widget="phone" options="{'placeholder_field' : 'char'}"/>
            <field name="char"/>
        </form>`,
    });
    expect(`.o_field_phone input`).toHaveAttribute("placeholder", "My Placeholder");
});

test("unset and readonly PhoneField", async () => {
    Partner._fields.foo.default = false;
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
        readonly: true,
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

test("New record, fill in phone field, then click on call icon and save", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="name" required="1"/>
                        <field name="foo" widget="phone"/>
                    </group>
                </sheet>
            </form>`,
    });

    await contains(".o_field_widget[name=name] input").edit("TEST");
    await contains(".o_field_widget[name=foo] input").edit("+12345678900");

    await click(`input[type="tel"]`);

    expect(`.o_form_status_indicator_buttons`).not.toHaveClass("invisible");

    await clickSave();

    expect(".o_field_widget[name=name] input").toHaveValue("TEST");
    expect(".o_field_widget[name=foo] input").toHaveValue("+12345678900");
    expect(`.o_form_status_indicator_buttons`).toHaveClass("invisible");
});
