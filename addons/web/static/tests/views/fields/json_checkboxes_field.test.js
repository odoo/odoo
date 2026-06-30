import { expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    int_field = fields.Integer({ sortable: true });
    json_checkboxes_field = fields.Json({ string: "Json Checkboxes Field" });
    _records = [
        {
            id: 1,
            int_field: 10,
            json_checkboxes_field: {
                key1: { checked: true, label: "First Key" },
                key2: { checked: false, label: "Second Key" },
            },
        },
    ];
}

defineModels([Partner]);

test("JsonCheckBoxesField", async () => {
    const commands = [
        {
            key1: { checked: true, label: "First Key" },
            key2: { checked: true, label: "Second Key" },
        },
        {
            key1: { checked: false, label: "First Key" },
            key2: { checked: true, label: "Second Key" },
        },
    ];
    onRpc("web_save", (args) => {
        expect.step("web_save");
        expect(args.args[1].json_checkboxes_field).toEqual(commands.shift());
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="json_checkboxes_field" widget="json_checkboxes" />
                </group>
            </form>`,
    });

    expect("div.o_field_widget div.form-check").toHaveCount(2);

    expect("div.o_field_widget div.form-check input:eq(0)").toBeChecked();
    expect("div.o_field_widget div.form-check input:eq(1)").not.toBeChecked();

    expect("div.o_field_widget div.form-check input:disabled").toHaveCount(0);

    // check a value by clicking on input
    await contains("div.o_field_widget div.form-check input:eq(1)").click();
    await runAllTimers();
    await clickSave();
    expect("div.o_field_widget div.form-check input:checked").toHaveCount(2);

    // uncheck a value by clicking on label
    await contains("div.o_field_widget div.form-check > label").click();
    await runAllTimers();
    await clickSave();
    expect("div.o_field_widget div.form-check input:eq(0)").not.toBeChecked();
    expect("div.o_field_widget div.form-check input:eq(1)").toBeChecked();

    expect.verifySteps(["web_save", "web_save"]);
});

test("JsonCheckBoxesField (readonly field)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="json_checkboxes_field" widget="json_checkboxes" readonly="True" />
                </group>
            </form>`,
    });

    expect("div.o_field_widget div.form-check").toHaveCount(2, {
        message: "should have fetched and displayed the 2 values of the many2many",
    });
    expect("div.o_field_widget div.form-check input:disabled").toHaveCount(2, {
        message: "the checkboxes should be disabled",
    });

    await contains("div.o_field_widget div.form-check > label:eq(1)").click();

    expect("div.o_field_widget div.form-check input:eq(0)").toBeChecked();
    expect("div.o_field_widget div.form-check input:eq(1)").not.toBeChecked();
});

test("JsonCheckBoxesField (some readonly)", async () => {
    Partner._records[0].json_checkboxes_field = {
        key1: { checked: true, label: "First Key" },
        key2: { checked: false, readonly: true, label: "Second Key" },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="json_checkboxes_field" widget="json_checkboxes" />
                </group>
            </form>`,
    });

    expect("div.o_field_widget div.form-check").toHaveCount(2, {
        message: "should have fetched and displayed the 2 values of the many2many",
    });
    expect("div.o_field_widget div.form-check input:eq(0):enabled").toHaveCount(1, {
        message: "first checkbox should be enabled",
    });
    expect("div.o_field_widget div.form-check input:eq(1):disabled").toHaveCount(1, {
        message: "second checkbox should be disabled",
    });

    await contains("div.o_field_widget div.form-check > label:eq(1)").click();

    expect("div.o_field_widget div.form-check input:eq(0)").toBeChecked();
    expect("div.o_field_widget div.form-check input:eq(1)").not.toBeChecked();
});

test("JsonCheckBoxesField (question circle)", async () => {
    Partner._records[0].json_checkboxes_field = {
        key1: { checked: true, label: "First Key" },
        key2: { checked: false, label: "Second Key", question_circle: "Some info about this" },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="json_checkboxes_field" widget="json_checkboxes" />
                </group>
            </form>`,
    });

    expect("div.o_field_widget div.form-check:eq(0) ~ i.fa-question-circle").toHaveCount(0, {
        message: "first checkbox should not have a question circle",
    });
    expect(
        "div.o_field_widget div.form-check:eq(1) ~ i.fa-question-circle[title='Some info about this']"
    ).toHaveCount(1, {
        message: "second checkbox should have a question circle",
    });
});

test("JsonCheckBoxesField (implicit inline mode)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="json_checkboxes_field" widget="json_checkboxes" />
                </group>
            </form>`,
    });

    expect("div.o_field_widget .d-inline-block div.form-check").toHaveCount(2, {
        message: "should show the checkboxes in inlined mode",
    });
});

test("JsonCheckBoxesField (explicit inline mode)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="json_checkboxes_field" widget="json_checkboxes" options="{'stacked': 0}" />
                </group>
            </form>`,
    });

    expect("div.o_field_widget .d-inline-block div.form-check").toHaveCount(2, {
        message: "should show the checkboxes in inlined mode",
    });
});

test("JsonCheckBoxesField (stacked mode)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="json_checkboxes_field" widget="json_checkboxes" options="{'stacked': 1}" />
                </group>
            </form>`,
    });

    expect("div.o_field_widget .d-block div.form-check").toHaveCount(2, {
        message: "should show the checkboxes in stacked mode",
    });
});
