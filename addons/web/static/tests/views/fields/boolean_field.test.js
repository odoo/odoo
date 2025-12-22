import { expect, test } from "@odoo/hoot";
import { check, click, press, uncheck } from "@odoo/hoot-dom";
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

    await uncheck(`.o_field_boolean input`);
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    await clickSave();
    expect(`.o_field_boolean input`).not.toBeChecked();

    await check(`.o_field_boolean input`);
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();

    await uncheck(`.o_field_boolean input`);
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    await click(`.o_form_view label:not(.form-check-label)`);
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();

    await click(`.o_form_view label:not(.form-check-label)`);
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    await press("enter");
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();

    await press("enter");
    await animationFrame();
    expect(`.o_field_boolean input`).not.toBeChecked();

    await press("enter");
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
        arch: `<list editable="bottom"><field name="bar"/></list>`,
    });
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input`).toHaveCount(5);
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input:checked`).toHaveCount(4);

    // Edit a line
    const cell = `tr.o_data_row td:not(.o_list_record_selector):first`;
    expect(`${cell} .o-checkbox input:only`).toBeChecked();
    expect(`${cell} .o-checkbox input:only`).not.toBeEnabled();

    await click(`${cell} .o-checkbox`);
    await animationFrame();
    expect(`tr.o_data_row:nth-child(1)`).toHaveClass("o_selected_row", {
        message: "the row is now selected, in edition",
    });
    expect(`${cell} .o-checkbox input:only`).not.toBeChecked();
    expect(`${cell} .o-checkbox input:only`).toBeEnabled();

    await click(`${cell} .o-checkbox`);
    await click(cell);
    await animationFrame();
    expect(`${cell} .o-checkbox input:only`).toBeChecked();
    expect(`${cell} .o-checkbox input:only`).toBeEnabled();

    await click(`${cell} .o-checkbox`);
    await animationFrame();

    await click(`.o_list_button_save`);
    await animationFrame();
    expect(`${cell} .o-checkbox input:only`).not.toBeChecked();
    expect(`${cell} .o-checkbox input:only`).not.toBeEnabled();
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input`).toHaveCount(5);
    expect(`tbody td:not(.o_list_record_selector) .o-checkbox input:checked`).toHaveCount(3);

    // Fake-check the checkbox
    await click(cell);
    await animationFrame();
    await click(`${cell} .o-checkbox`);
    await animationFrame();

    await click(`.o_list_button_save`);
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

    await click(`.o_field_boolean .o-checkbox`);
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();
    expect(`.o_field_boolean input`).not.toBeEnabled();
});

test("onchange return value before toggle checkbox", async () => {
    Partner._onChanges.bar = (record) => {
        record["bar"] = true;
    };

    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="bar"/></form>`,
    });
    expect(`.o_field_boolean input`).toBeChecked();

    await click(`.o_field_boolean .o-checkbox`);
    await animationFrame();
    await animationFrame();
    expect(`.o_field_boolean input`).toBeChecked();
});
