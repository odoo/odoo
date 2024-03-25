import { expect, test } from "@odoo/hoot";
import { check, click, press, queryAll, queryOne, uncheck } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    bar = fields.Boolean({ default: true });

    _records = [
        { id: 1, bar: true },
        { id: 2, bar: true },
        { id: 3, bar: true },
        { id: 4, bar: true },
        { id: 5, bar: false },
    ];
}

defineModels([Partner]);

test("boolean field in form view", async () => {
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <label for="bar" string="Awesome checkbox"/>
                <field name="bar"/>
            </form>
        `,
    });
    expect(`.o_field_boolean input`).toBeChecked();
    expect(`.o_field_boolean input`).toBeEnabled();

    uncheck(`.o_field_boolean input`);
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    await clickSave();
    expect(`.o_field_boolean input`).not.toBeChecked();

    check(`.o_field_boolean input`);
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();

    uncheck(`.o_field_boolean input`);
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    click(`.o_form_view label:not(.form-check-label)`);
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();

    click(`.o_form_view label:not(.form-check-label)`);
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    press("enter");
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();

    press("enter");
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    press("enter");
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();

    await clickSave();
    expect(`.o_field_boolean input`).toBeChecked();
});

test("boolean field in editable list view", async () => {
    onRpc("has_group", () => true);

    await mountView({
        resModel: "partner",
        type: "list",
        arch: `<tree editable="bottom"><field name="bar"/></tree>`,
    });
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input`).toHaveCount(5);
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input:checked`).toHaveCount(4);

    // Edit a line
    let cell = queryAll`tr.o_data_row td:not(.o_list_record_selector)`[0];
    expect(queryOne(`.o-checkbox input`, { root: cell })).toBeChecked();
    expect(queryOne(`.o-checkbox input`, { root: cell })).not.toBeEnabled();

    click(`.o-checkbox`, { root: cell });
    await animationFrame();
    expect(`tr.o_data_row:nth-child(1)`).toHaveClass("o_selected_row", {
        message: "the row is now selected, in edition",
    });
    expect(queryOne(`.o-checkbox input`, { root: cell })).not.toBeChecked();
    expect(queryOne(`.o-checkbox input`, { root: cell })).toBeEnabled();

    click(`.o-checkbox`, { root: cell });
    click(cell);
    await animationFrame();
    expect(queryOne(`.o-checkbox input`, { root: cell })).toBeChecked();
    expect(queryOne(`.o-checkbox input`, { root: cell })).toBeEnabled();

    click(`.o-checkbox`, { root: cell });
    await animationFrame();

    click(`.o_list_button_save`);
    await animationFrame();
    cell = queryAll`tr.o_data_row td:not(.o_list_record_selector)`[0];
    expect(queryOne(`.o-checkbox input`, { root: cell })).not.toBeChecked();
    expect(queryOne(`.o-checkbox input`, { root: cell })).not.toBeEnabled();
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input`).toHaveCount(5);
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input:checked`).toHaveCount(3);

    // Fake-check the checkbox
    click(cell);
    await animationFrame();
    click(`.o-checkbox`, { root: cell });
    await animationFrame();

    click(`.o_list_button_save`);
    await animationFrame();
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input`).toHaveCount(5);
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input:checked`).toHaveCount(3);
});

test("readonly boolean field", async () => {
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="bar" readonly="1"/></form>`,
    });
    expect(`.o_field_boolean input`).toBeChecked();
    expect(`.o_field_boolean input`).not.toBeEnabled();

    click(`.o_field_boolean .o-checkbox`);
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();
    expect(`.o_field_boolean input`).not.toBeEnabled();
});

test("onchange return value before toggle checkbox", async () => {
    Partner._fields.bar = fields.Boolean({
        onChange(record) {
            record["bar"] = true;
        },
    });

    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="bar"/></form>`,
    });
    expect(`.o_field_boolean input`).toBeChecked();

    click(`.o_field_boolean .o-checkbox`);
    await animationFrame();
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();
});
