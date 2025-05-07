import { expect, getFixture, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    clickSave,
    contains,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Product extends models.Model {
    price = fields.Integer();
}

defineModels([Product]);

test("human readable format 1", async () => {
    Product._records = [{ id: 1, price: 3.756754e6 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" options="{'human_readable': 'true'}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("4M", {
        message: "The value should be rendered in human readable format (k, M, G, T)",
    });
});

test("human readable format 2", async () => {
    Product._records = [{ id: 1, price: 2.034e3 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" options="{'human_readable': 'true', 'decimals': 1}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("2.0k", {
        message: "The value should be rendered in human readable format (k, M, G, T)",
    });
});

test("human readable format 3", async () => {
    Product._records = [{ id: 1, price: 6.67543577586e12 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" options="{'human_readable': 'true', 'decimals': 4}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("6.6754T", {
        message: "The value should be rendered in human readable format (k, M, G, T)",
    });
});

test("still human readable when readonly", async () => {
    Product._records = [{ id: 1, price: 6.67543577586e12 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" readonly="true" options="{'human_readable': 'true', 'decimals': 4}"/></form>`,
    });
    expect(".o_field_widget span").toHaveText("6.6754T");
});

test("should be 0 when unset", async () => {
    Product._records = [{ id: 1 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="price"/></form>',
    });
    expect(".o_field_widget input").not.toHaveClass("o_field_empty");
    expect(".o_field_widget input").toHaveValue("0");
});

test("basic form view flow", async () => {
    Product._records = [{ id: 1, price: 10 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="price"/></form>',
    });

    expect(".o_field_widget input").toHaveValue("10");
    await fieldInput("price").edit("30");
    expect(".o_field_widget input").toHaveValue("30");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("30");
});

test("no need to focus out of the input to save the record after correcting an invalid input", async () => {
    Product._records = [{ id: 1, price: 10 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="price"/></form>',
    });

    expect(".o_field_widget input").toHaveValue("10");
    await fieldInput("price").edit("a");
    expect(".o_field_widget input").toHaveValue("a");
    expect(".o_form_status_indicator span i.fa-warning").toHaveCount(1);
    expect(".o_form_button_save[disabled]").toHaveCount(1);
    await fieldInput("price").edit("1");
    expect(".o_field_widget input").toHaveValue("1");
    expect(".o_form_status_indicator span i.fa-warning").toHaveCount(0);
    expect(".o_form_button_save[disabled]").toHaveCount(0);
    await clickSave(); // makes sure there is an enabled save button
});

test("rounded when using formula in form view", async () => {
    Product._records = [{ id: 1, price: 10 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="price"/></form>',
    });
    await fieldInput("price").edit("=100/3");
    expect(".o_field_widget input").toHaveValue("33");
});

test("with input type 'number' option", async () => {
    // `localization > grouping` required for this test is [3, 0], which is the default in mock server
    Product._records = [{ id: 1, price: 10 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" options="{'type': 'number'}"/></form>`,
    });
    expect(".o_field_widget input").toHaveAttribute("type", "number");
    await fieldInput("price").edit("1234567890");
    expect(".o_field_widget input").toHaveValue(1234567890, {
        message: "Integer value must be not formatted if input type is number",
    });
});

test("with 'step' option", async () => {
    Product._records = [{ id: 1, price: 10 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" options="{'type': 'number', 'step': 3}"/></form>`,
    });
    expect(".o_field_widget input").toHaveAttribute("step", "3");
});

test("without input type option", async () => {
    // `localization > grouping` required for this test is [3, 0], which is the default in mock server
    Product._records = [{ id: 1, price: 10 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="price"/></form>',
    });

    expect(".o_field_widget input").toHaveAttribute("type", "text");
    await fieldInput("price").edit("1234567890");
    expect(".o_field_widget input").toHaveValue("1,234,567,890");
});

test("is formatted by default", async () => {
    // `localization > grouping` required for this test is [3, 0], which is the default in mock server
    Product._records = [{ id: 1, price: 8069 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" options="{'enable_formatting': 'false'}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("8,069");
});

test("basic flow in editable list view", async () => {
    Product._records = [{ id: 1 }, { id: 2, price: 10 }];
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "product",
        arch: '<list editable="bottom"><field name="price"/></list>',
    });
    const zeroValues = queryAllTexts("td").filter((text) => text === "0");
    expect(zeroValues).toHaveLength(1, {
        message: "Unset integer values should not be rendered as zeros",
    });
    await contains("td.o_data_cell").click();
    expect('.o_field_widget[name="price"] input').toHaveCount(1);
    await contains('.o_field_widget[name="price"] input').edit("-28");
    expect("td.o_data_cell:first").toHaveText("-28");
    expect('.o_field_widget[name="price"] input').toHaveValue("10");
    await contains(getFixture()).click();
    expect(queryAllTexts("td.o_data_cell")).toEqual(["-28", "10"]);
});

test("with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "product",
        arch: `<form><field name="price" placeholder="Placeholder"/></form>`,
    });
    expect(".o_field_widget input").toHaveAttribute("placeholder", "Placeholder");
});

test("with enable_formatting option as false", async () => {
    // `localization > grouping` required for this test is [3, 0], which is the default in mock server
    Product._records = [{ id: 1, price: 8069 }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="price" options="{'enable_formatting': false}"/></form>`,
    });
    expect(".o_field_widget input").toHaveValue("8069");
    await fieldInput("price").edit("1234567890");
    expect(".o_field_widget input").toHaveValue("1234567890");
});

test("value is formatted on Enter", async () => {
    // `localization > grouping` required for this test is [3, 0], which is the default in mock server
    await mountView({
        type: "form",
        resModel: "product",
        arch: '<form><field name="price"/></form>',
    });

    expect(".o_field_widget input").toHaveValue("0");

    await fieldInput("price").edit("1000", { confirm: "Enter" });
    expect(".o_field_widget input").toHaveValue("1,000");
});

test("value is formatted on Enter (even if same value)", async () => {
    // `localization > grouping` required for this test is [3, 0], which is the default in mock server
    Product._records = [{ id: 1, price: 8069 }];

    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="price"/></form>',
    });

    expect(".o_field_widget input").toHaveValue("8,069");

    await fieldInput("price").edit("8069", { confirm: "Enter" });
    expect(".o_field_widget input").toHaveValue("8,069");
});

test("value is formatted on click out (even if same value)", async () => {
    // `localization > grouping` required for this test is [3, 0], which is the default in mock server
    Product._records = [{ id: 1, price: 8069 }];

    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="price"/></form>',
    });

    expect(".o_field_widget input").toHaveValue("8,069");

    await fieldInput("price").edit("8069", { confirm: false });
    expect(".o_field_widget input").toHaveValue("8069");

    await contains(".o_control_panel").click();
    expect(".o_field_widget input").toHaveValue("8,069");
});

test("Value should not be a boolean when enable_formatting is false", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "product",
        arch: `
            <list editable="bottom">
                <field name="id" options="{'enable_formatting': false}"/>
                <field name="price"/>
            </list>
        `,
    });
    await contains(`.o_list_button_add`).click();
    expect(".o_selected_row .o_field_integer").toHaveText("");
});
