import { expect, test } from "@odoo/hoot";
import { click, edit, queryOne, queryText, queryValue } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
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
    name = fields.Char({ string: "Display Name" });
    int_field = fields.Integer({
        string: "int_field",
    });
    int_field2 = fields.Integer({
        string: "int_field",
    });
    int_field3 = fields.Integer({
        string: "int_field",
    });
    float_field = fields.Float({
        string: "Float_field",
        digits: [16, 1],
    });
    _records = [
        {
            int_field: 10,
            float_field: 0.44444,
        },
    ];
}
defineModels([Partner]);

test("ProgressBarField: max_value should update", async () => {
    expect.assertions(3);
    Partner._records[0].float_field = 2;
    Partner._onChanges.name = (record) => {
        record.int_field = 999;
        record.float_field = 5;
    };

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual(
            { int_field: 999, float_field: 5, name: "new name" },
            { message: "New value of progress bar saved" }
        );
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="name" />
                <field name="float_field" invisible="1" />
                <field name="int_field" widget="progressbar" options="{'current_value': 'int_field', 'max_value': 'float_field'}" />
            </form>`,
        resId: 1,
    });

    expect(".o_progressbar").toHaveText("10\n/\n2");
    await click(".o_field_widget[name=name] input");
    await edit("new name", { confirm: "enter" });
    await clickSave();
    await animationFrame();
    expect(".o_progressbar").toHaveText("999\n/\n5");
});

test("ProgressBarField: value should update in edit mode when typing in input", async () => {
    expect.assertions(4);
    Partner._records[0].int_field = 99;
    onRpc("web_save", ({ args }) => expect(args[1].int_field).toBe(69));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="int_field" widget="progressbar" options="{'editable': true}"/>
            </form>`,
        resId: 1,
    });

    expect(queryValue(".o_progressbar_value .o_input") + queryText(".o_progressbar")).toBe("99%", {
        message: "Initial value should be correct",
    });
    await click(".o_progressbar_value .o_input");
    // wait for apply dom change
    await animationFrame();
    await edit("69", { confirm: "enter" });
    expect(".o_progressbar_value .o_input").toHaveValue("69", {
        message: "New value should be different after focusing out of the field",
    });
    // wait for apply dom change
    await animationFrame();
    await clickSave();
    // wait for rpc
    await animationFrame();
    expect(".o_progressbar_value .o_input").toHaveValue("69", {
        message: "New value is still displayed after save",
    });
});

test("ProgressBarField: value should update in edit mode when typing in input with field max value", async () => {
    expect.assertions(4);
    Partner._records[0].int_field = 99;

    onRpc("web_save", ({ args }) => expect(args[1].int_field).toBe(69));

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="float_field" invisible="1" />
                <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field'}" />
            </form>`,
        resId: 1,
    });
    expect(".o_form_view .o_form_editable").toHaveCount(1, { message: "Form in edit mode" });
    expect(queryValue(".o_progressbar_value .o_input") + queryText(".o_progressbar")).toBe(
        "99/\n0",
        { message: "Initial value should be correct" }
    );

    await click(".o_progressbar_value .o_input");
    await animationFrame();
    await edit("69", { confirm: "enter" });
    await animationFrame();
    await clickSave();
    await animationFrame();
    expect(queryValue(".o_progressbar_value .o_input") + queryText(".o_progressbar")).toBe(
        "69/\n0",
        { message: "New value should be different than initial after click" }
    );
});

test("ProgressBarField: max value should update in edit mode when typing in input with field max value", async () => {
    expect.assertions(5);
    Partner._records[0].int_field = 99;

    onRpc("web_save", ({ args }) => expect(args[1].float_field).toBe(69));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="float_field" invisible="1" />
                <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field', 'edit_max_value': true}" />
            </form>`,
        resId: 1,
    });

    expect(queryText(".o_progressbar") + queryValue(".o_progressbar_value .o_input")).toBe(
        "99\n/0",
        { message: "Initial value should be correct" }
    );
    expect(".o_form_view .o_form_editable").toHaveCount(1, { message: "Form in edit mode" });
    queryOne(".o_progressbar input").focus();
    await animationFrame();

    expect(queryText(".o_progressbar") + queryValue(".o_progressbar_value .o_input")).toBe(
        "99\n/0.44",
        { message: "Initial value is not formatted when focused" }
    );

    await click(".o_progressbar_value .o_input");
    await edit("69", { confirm: "enter" });
    await clickSave();

    expect(queryText(".o_progressbar") + queryValue(".o_progressbar_value .o_input")).toBe(
        "99\n/69",
        { message: "New value should be different than initial after click" }
    );
});

test("ProgressBarField: Standard readonly mode is readonly", async () => {
    Partner._records[0].int_field = 99;

    onRpc(({ method }) => expect.step(method));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form edit="0">
                <field name="float_field" invisible="1"/>
                <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field', 'edit_max_value': true}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_progressbar").toHaveText("99\n/\n0", {
        message: "Initial value should be correct",
    });

    await click(".o_progress");
    await animationFrame();

    expect(".o_progressbar_value .o_input").toHaveCount(0, {
        message: "no input in readonly mode",
    });
    expect.verifySteps(["get_views", "web_read"]);
});

test("ProgressBarField: field is editable in kanban", async () => {
    expect.assertions(7);
    Partner._records[0].int_field = 99;

    onRpc("web_save", ({ args }) => expect(args[1].int_field).toBe(69));
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="int_field" title="ProgressBarTitle" widget="progressbar" options="{'editable': true, 'max_value': 'float_field'}" />
                        </t>
                    </templates>
                </kanban>`,
        resId: 1,
    });

    expect(".o_progressbar_value .o_input").toHaveValue("99", {
        message: "Initial input value should be correct",
    });
    expect(".o_progressbar_value span").toHaveText("100", {
        message: "Initial max value should be correct",
    });
    expect(".o_progressbar_title").toHaveText("ProgressBarTitle");

    await click(".o_progressbar_value .o_input");
    await edit("69", { confirm: "enter" });
    await animationFrame();

    expect(".o_progressbar_value .o_input").toHaveValue("69");
    expect(".o_progressbar_value span").toHaveText("100", {
        message: "Max value is still the same be correct",
    });
    expect(".o_progressbar_title").toHaveText("ProgressBarTitle");
});

test("force readonly in kanban", async (assert) => {
    expect.assertions(2);
    Partner._records[0].int_field = 99;
    onRpc("web_save", () => {
        throw new Error("Not supposed to write");
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
        <kanban>
            <templates>
                <t t-name="card">
                    <field name="int_field" widget="progressbar" options="{'editable': true, 'max_value': 'float_field', 'readonly': True}" />
                </t>
            </templates>
        </kanban>`,
        resId: 1,
    });
    expect(".o_progressbar").toHaveText("99\n/\n100");
    expect(".o_progressbar_value .o_input").toHaveCount(0);
});

test("ProgressBarField: readonly and editable attrs/options in kanban", async () => {
    expect.assertions(4);
    Partner._records[0].int_field = 29;
    Partner._records[0].int_field2 = 59;
    Partner._records[0].int_field3 = 99;

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="int_field" readonly="1" widget="progressbar" options="{'max_value': 'float_field'}" />
                        <field name="int_field2" widget="progressbar" options="{'max_value': 'float_field'}" />
                        <field name="int_field3" widget="progressbar" options="{'editable': true, 'max_value': 'float_field'}" />
                    </t>
                </templates>
            </kanban>`,
        resId: 1,
    });

    expect("[name='int_field'] .o_progressbar_value .o_input").toHaveCount(0, {
        message: "the field is still in readonly since there is readonly attribute",
    });
    expect("[name='int_field2'] .o_progressbar_value .o_input").toHaveCount(0, {
        message: "the field is still in readonly since there is readonly attribute",
    });
    expect("[name='int_field3'] .o_progressbar_value .o_input").toHaveCount(1, {
        message: "the field is still in readonly since there is readonly attribute",
    });

    await click(".o_field_progressbar[name='int_field3'] .o_progressbar_value .o_input");
    await edit("69", { confirm: "enter" });
    await animationFrame();
    expect(".o_field_progressbar[name='int_field3'] .o_progressbar_value .o_input").toHaveValue(
        "69",
        { message: "New value should be different than initial after click" }
    );
});

test("ProgressBarField: write float instead of int works, in locale", async () => {
    expect.assertions(4);
    Partner._records[0].int_field = 99;
    defineParams({
        lang_parameters: {
            decimal_point: ":",
            thousands_sep: "#",
        },
    });
    onRpc("web_save", ({ args }) => expect(args[1].int_field).toBe(1037));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="int_field" widget="progressbar" options="{'editable': true}"/>
            </form>`,
        resId: 1,
    });

    expect(queryValue(".o_progressbar_value .o_input") + queryText(".o_progressbar")).toBe("99%", {
        message: "Initial value should be correct",
    });

    expect(".o_form_view .o_form_editable").toHaveCount(1, { message: "Form in edit mode" });

    await click(".o_field_widget input");
    await animationFrame();
    await edit("1#037:9", { confirm: "enter" });
    await animationFrame();
    await clickSave();
    await animationFrame();
    expect(".o_progressbar_value .o_input").toHaveValue("1k", {
        message: "New value should be different than initial after click",
    });
});

test("ProgressBarField: write gibberish instead of int throws warning", async () => {
    Partner._records[0].int_field = 99;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="int_field" widget="progressbar" options="{'editable': true}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_progressbar_value .o_input").toHaveValue("99", {
        message: "Initial value in input is correct",
    });

    await click(".o_progressbar_value .o_input");
    await animationFrame();
    await edit("trente sept virgule neuf", { confirm: "enter" });
    await animationFrame();
    await click(".o_form_button_save");
    await animationFrame();
    expect(".o_form_status_indicator span.text-danger").toHaveCount(1, {
        message: "The form has not been saved",
    });
    expect(".o_form_button_save").toHaveProperty("disabled", true, {
        message: "save button is disabled",
    });
});

test("ProgressBarField: color is correctly set when value > max value", async () => {
    Partner._records[0].float_field = 101;
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="float_field" widget="progressbar" options="{'overflow_class': 'bg-warning'}"/>
            </form>`,
        resId: 1,
    });
    expect(".o_progressbar .bg-warning").toHaveCount(1, {
        message: "As the value has excedded the max value, the color should be set to bg-warning",
    });
});
