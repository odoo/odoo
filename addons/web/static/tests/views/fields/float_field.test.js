import { expect, test } from "@odoo/hoot";
import {
    clickSave,
    contains,
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class Partner extends models.Model {
    float_field = fields.Float({ string: "Float field" });

    _records = [
        { id: 1, float_field: 0.36 },
        { id: 2, float_field: 0 },
        { id: 3, float_field: -3.89859 },
        { id: 4, float_field: 0 },
        { id: 5, float_field: 9.1 },
        { id: 100, float_field: 2.034567e3 },
        { id: 101, float_field: 3.75675456e6 },
        { id: 102, float_field: 6.67543577586e12 },
    ];
}

defineModels([Partner]);

onRpc("has_group", () => true);

test("human readable format 1", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 101,
        arch: `<form><field name="float_field" options="{'human_readable': 'true'}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("4M", {
        message: "The value should be rendered in human readable format (k, M, G, T).",
    });
});

test("human readable format 2", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 100,
        arch: `<form><field name="float_field" options="{'human_readable': 'true', 'decimals': 1}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("2.0k", {
        message: "The value should be rendered in human readable format (k, M, G, T).",
    });
});

test("human readable format 3", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 102,
        arch: `<form><field name="float_field" options="{'human_readable': 'true', 'decimals': 4}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("6.6754T", {
        message: "The value should be rendered in human readable format (k, M, G, T).",
    });
});

test("still human readable when readonly", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 102,
        arch: `<form><field readonly="true" name="float_field" options="{'human_readable': 'true', 'decimals': 4}"/></form>`,
    });
    expect(".o_field_widget span").toHaveText("6.6754T", {
        message: "The value should be rendered in human readable format when input is readonly.",
    });
});

test("unset field should be set to 0", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 4,
        arch: '<form><field name="float_field"/></form>',
    });

    expect(".o_field_widget").not.toHaveClass("o_field_empty", {
        message: "Non-set float field should be considered as 0.00",
    });

    expect(".o_field_widget input").toHaveValue("0.00", {
        message: "Non-set float field should be considered as 0.",
    });
});

test("use correct digit precision from field definition", async () => {
    Partner._fields.float_field = fields.Float({ string: "Float field", digits: [0, 1] });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: '<form><field name="float_field"/></form>',
    });

    expect(".o_field_float input").toHaveValue("0.4", {
        message: "should contain a number rounded to 1 decimal",
    });
});

test("use correct digit precision from options", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="float_field" options="{ 'digits': [0, 1] }" /></form>`,
    });

    expect(".o_field_float input").toHaveValue("0.4", {
        message: "should contain a number rounded to 1 decimal",
    });
});

test("use correct digit precision from field attrs", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: '<form><field name="float_field" digits="[0, 1]" /></form>',
    });

    expect(".o_field_float input").toHaveValue("0.4", {
        message: "should contain a number rounded to 1 decimal",
    });
});

test("with 'step' option", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="float_field" options="{'type': 'number', 'step': 0.3}"/></form>`,
    });

    expect(".o_field_widget input").toHaveAttribute("step", "0.3", {
        message: 'Integer field with option type must have a step attribute equals to "3".',
    });
});

test("basic flow in form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
    });

    expect(".o_field_widget").not.toHaveClass("o_field_empty", {
        message: "Float field should be considered set for value 0.",
    });
    expect(".o_field_widget input").toHaveValue("0.000", {
        message: "The value should be displayed properly.",
    });

    await contains('div[name="float_field"] input').edit("108.2451938598598");
    expect(".o_field_widget[name=float_field] input").toHaveValue("108.245", {
        message: "The value should have been formatted on blur.",
    });

    await contains(".o_field_widget[name=float_field] input").edit("18.8958938598598");
    await clickSave();

    expect(".o_field_widget input").toHaveValue("18.896", {
        message: "The new value should be rounded properly.",
    });
});

test("use a formula", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
    });

    await contains(".o_field_widget[name=float_field] input").edit("=20+3*2");
    await clickSave();

    expect(".o_field_widget input").toHaveValue("26.000", {
        message: "The new value should be calculated properly.",
    });

    await contains(".o_field_widget[name=float_field] input").edit("=2**3");
    await clickSave();

    expect(".o_field_widget input").toHaveValue("8.000", {
        message: "The new value should be calculated properly.",
    });

    await contains(".o_field_widget[name=float_field] input").edit("=2^3");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("8.000", {
        message: "The new value should be calculated properly.",
    });

    await contains(".o_field_widget[name=float_field] input").edit("=100/3");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("33.333", {
        message: "The new value should be calculated properly.",
    });
});

test("use incorrect formula", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
    });

    await contains(".o_field_widget[name=float_field] input").edit("=abc", { confirm: false });
    await clickSave();

    expect(".o_field_widget[name=float_field]").toHaveClass("o_field_invalid", {
        message: "fload field should be displayed as invalid",
    });
    expect(".o_form_editable").toHaveCount(1, { message: "form view should still be editable" });

    await contains(".o_field_widget[name=float_field] input").edit("=3:2?+4", { confirm: false });
    await clickSave();

    expect(".o_form_editable").toHaveCount(1, { message: "form view should still be editable" });
    expect(".o_field_widget[name=float_field]").toHaveClass("o_field_invalid", {
        message: "float field should be displayed as invalid",
    });
});

test.tags("desktop")("float field in editable list view", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="float_field" widget="float" digits="[5,3]" />
            </list>`,
    });

    // switch to edit mode
    await contains("tr.o_data_row td:not(.o_list_record_selector)").click();

    expect('div[name="float_field"] input').toHaveCount(1, {
        message: "The view should have 1 input for editable float.",
    });

    await contains('div[name="float_field"] input').edit("108.2458938598598", { confirm: "blur" });
    expect(".o_field_widget:eq(0)").toHaveText("108.246", {
        message: "The value should have been formatted on blur.",
    });

    await contains("tr.o_data_row td:not(.o_list_record_selector)").click();
    await contains('div[name="float_field"] input').edit("18.8958938598598", { confirm: false });
    await contains(".o_control_panel_main_buttons .o_list_button_save").click();
    expect(".o_field_widget:eq(0)").toHaveText("18.896", {
        message: "The new value should be rounded properly.",
    });
});

test("float field with type number option", async () => {
    defineParams({
        lang_parameters: {
            grouping: [3, 0],
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="float_field" options="{'type': 'number'}"/>
            </form>`,
        resId: 4,
    });
    expect(".o_field_widget input").toHaveAttribute("type", "number", {
        message: 'Float field with option type must have a type attribute equals to "number".',
    });
    await contains(".o_field_widget input").fill("123456.7890", { instantly: true });
    await clickSave();
    expect(".o_field_widget input").toHaveValue(123456.789, {
        message:
            "Float value must be not formatted if input type is number. (but the trailing 0 is gone)",
    });
});

test("float field with type number option and comma decimal separator", async () => {
    defineParams({
        lang_parameters: {
            thousands_sep: ".",
            decimal_point: ",",
            grouping: [3, 0],
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="float_field" options="{'type': 'number'}"/>
                </form>`,
        resId: 4,
    });

    expect(".o_field_widget input").toHaveAttribute("type", "number", {
        message: 'Float field with option type must have a type attribute equals to "number".',
    });
    await contains(".o_field_widget[name=float_field] input").fill("123456.789", {
        instantly: true,
    });
    await clickSave();
    expect(".o_field_widget input").toHaveValue(123456.789, {
        message: "Float value must be not formatted if input type is number.",
    });
});

test("float field without type number option", async () => {
    defineParams({
        lang_parameters: {
            grouping: [3, 0],
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="float_field"/></form>',
        resId: 4,
    });
    expect(".o_field_widget input").toHaveAttribute("type", "text", {
        message: "Float field with option type must have a text type (default type).",
    });

    await contains(".o_field_widget[name=float_field] input").edit("123456.7890");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("123,456.79", {
        message: "Float value must be formatted if input type isn't number.",
    });
});

test("field with enable_formatting option as false", async () => {
    defineParams({
        lang_parameters: {
            grouping: [3, 0],
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="float_field" options="{'enable_formatting': false}"/></form>`,
    });

    expect(".o_field_widget input").toHaveValue("0.36", {
        message: "Integer value must not be formatted",
    });

    await contains(".o_field_widget[name=float_field] input").edit("123456.789");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("123456.789", {
        message: "Integer value must be not formatted if input type is number.",
    });
});

test.tags("desktop")(
    "field with enable_formatting option as false in editable list view",
    async () => {
        await mountView({
            type: "list",
            resModel: "partner",
            arch: `
            <list editable="bottom">
                <field name="float_field" widget="float" digits="[5,3]" options="{'enable_formatting': false}" />
            </list>`,
        });

        // switch to edit mode
        await contains("tr.o_data_row td:not(.o_list_record_selector)").click();

        expect('div[name="float_field"] input').toHaveCount(1, {
            message: "The view should have 1 input for editable float.",
        });

        await contains('div[name="float_field"] input').edit("108.2458938598598", {
            confirm: "blur",
        });
        expect(".o_field_widget:eq(0)").toHaveText("108.2458938598598", {
            message: "The value should not be formatted on blur.",
        });

        await contains("tr.o_data_row td:not(.o_list_record_selector)").click();
        await contains('div[name="float_field"] input').edit("18.8958938598598", {
            confirm: false,
        });
        await contains(".o_control_panel_main_buttons .o_list_button_save").click();
        expect(".o_field_widget:eq(0)").toHaveText("18.8958938598598", {
            message: "The new value should not be rounded as well.",
        });
    }
);

test("float_field field with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="float_field" placeholder="Placeholder"/></form>',
    });

    await contains(".o_field_widget[name='float_field'] input").clear();
    expect(".o_field_widget[name='float_field'] input").toHaveAttribute(
        "placeholder",
        "Placeholder"
    );
});

test("float field can be updated by another field/widget", async () => {
    class MyWidget extends Component {
        static template = xml`<button t-on-click="onClick">do it</button>`;
        static props = ["*"];
        onClick() {
            const val = this.props.record.data.float_field;
            this.props.record.update({ float_field: val + 1 });
        }
    }
    const myWidget = {
        component: MyWidget,
    };
    registry.category("view_widgets").add("wi", myWidget);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="float_field"/>
                <field name="float_field"/>
                <widget name="wi"/>
            </form>`,
    });

    await contains(".o_field_widget[name=float_field] input").edit("40");

    expect(".o_field_widget[name=float_field] input:eq(0)").toHaveValue("40.00");
    expect(".o_field_widget[name=float_field] input:eq(1)").toHaveValue("40.00");

    await contains(".o_widget button").click();

    expect(".o_field_widget[name=float_field] input:eq(0)").toHaveValue("41.00");
    expect(".o_field_widget[name=float_field] input:eq(1)").toHaveValue("41.00");
});
