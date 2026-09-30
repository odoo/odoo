import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";

import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    name = fields.Char();
    int_field = fields.Integer();
    float_field = fields.Float({
        digits: [16, 1],
    });
    p = fields.One2many({ relation: "partner" });
    currency_id = fields.Many2one({ relation: "res.currency" });
    monetary_field = fields.Monetary({ currency_field: "currency_id" });

    _records = [
        { id: 1, int_field: 10, float_field: 0.44444 },
        { id: 2, int_field: 0, float_field: 0, currency_id: 2 },
        { id: 3, int_field: 80, float_field: -3.89859 },
        { id: 4, int_field: 0, float_field: 0 },
        { id: 5, int_field: -4, float_field: 9.1, monetary_field: 9.1, currency_id: 1 },
        { id: 6, float_field: 3.9, monetary_field: 4.2, currency_id: 1 },
    ];
}

class Currency extends models.Model {
    _name = "res.currency";

    name = fields.Char();
    symbol = fields.Char({ string: "Currency Sumbol" });
    position = fields.Selection({
        selection: [
            ["after", "A"],
            ["before", "B"],
        ],
    });
    inverse_rate = fields.Float();

    _records = [
        { id: 1, name: "USD", symbol: "$", position: "before", inverse_rate: 1 },
        { id: 2, name: "EUR", symbol: "€", position: "after", inverse_rate: 0.5 },
        {
            id: 3,
            name: "VEF",
            symbol: "Bs.F",
            position: "after",
            inverse_rate: 0.3,
        },
    ];
}

defineModels([Partner, Currency]);

onRpc("has_group", () => true);

test("basic flow in form view - float field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5,
        arch: `
            <form>
                <field name="float_field" widget="monetary"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
    });

    expect(".o_field_monetary > div.text-nowrap").toHaveCount(1);
    expect(".o_field_widget input").toHaveValue("9.10", {
        message: "The input should be rendered without the currency symbol.",
    });
    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$", {
        message: "The input should be preceded by a span containing the currency symbol.",
    });

    await contains(".o_field_monetary input").edit("108.2458938598598");
    expect(".o_field_widget input").toHaveValue("108.25", {
        message: "The new value should be rounded properly after the blur",
    });

    await clickSave();
    expect(".o_field_widget input").toHaveValue("108.25", {
        message: "The new value should be rounded properly.",
    });
});

test("basic flow in form view - monetary field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5,
        arch: `
            <form>
                <field name="monetary_field"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
    });

    expect(".o_field_widget input").toHaveValue("9.10", {
        message: "The input should be rendered without the currency symbol.",
    });
    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$", {
        message: "The input should be preceded by a span containing the currency symbol.",
    });

    await contains(".o_field_monetary input").edit("108.2458938598598");
    expect(".o_field_widget input").toHaveValue("108.25", {
        message: "The new value should be rounded properly after the blur",
    });

    await clickSave();
    expect(".o_field_widget input").toHaveValue("108.25", {
        message: "The new value should be rounded properly.",
    });
});

test("rounding using formula in form view - float field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5,
        arch: `
            <form>
                <field name="float_field" widget="monetary"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
    });

    // Test computation and rounding
    await contains(".o_field_monetary input").edit("=100/3");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("33.33", {
        message: "The new value should be calculated and rounded properly.",
    });
});

test("rounding using formula in form view - monetary field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5,
        arch: `
            <form>
                <field name="monetary_field"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
    });

    // Test computation and rounding
    await contains(".o_field_monetary input").edit("=100/3");
    await clickSave();
    expect(".o_field_widget input").toHaveValue("33.33", {
        message: "The new value should be calculated and rounded properly.",
    });
});

test("with currency digits != 2 - float field", async () => {
    serverState.currencies = [
        { id: 1, name: "USD", symbol: "$", position: "before" },
        { id: 2, name: "EUR", symbol: "€", position: "after" },
        {
            id: 3,
            name: "VEF",
            symbol: "Bs.F",
            position: "after",
            digits: [0, 4],
        },
    ];

    Partner._records = [
        {
            id: 1,
            float_field: 99.1234,
            currency_id: 3,
        },
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="float_field" widget="monetary"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
    });

    expect(".o_field_widget input").toHaveValue("99.1234", {
        message: "The input should be rendered without the currency symbol.",
    });
    expect(".o_field_widget .o_input span:eq(1)").toHaveText("Bs.F", {
        message: "The input should be superposed with a span containing the currency symbol.",
    });

    await contains(".o_field_widget input").edit("99.111111111");
    expect(".o_field_widget input").toHaveValue("99.1111", {
        message: "The value should should be formatted on blur.",
    });

    await clickSave();
    expect(".o_field_widget input").toHaveValue("99.1111", {
        message: "The new value should be rounded properly.",
    });
});

test("with currency digits != 2 - monetary field", async () => {
    serverState.currencies = [
        { id: 1, name: "USD", symbol: "$", position: "before" },
        { id: 2, name: "EUR", symbol: "€", position: "after" },
        {
            id: 3,
            name: "VEF",
            symbol: "Bs.F",
            position: "after",
            digits: [0, 4],
        },
    ];

    Partner._records = [
        {
            id: 1,
            float_field: 99.1234,
            monetary_field: 99.1234,
            currency_id: 3,
        },
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="monetary_field"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
    });

    expect(".o_field_widget input").toHaveValue("99.1234", {
        message: "The input should be rendered without the currency symbol.",
    });
    expect(".o_field_widget .o_input span:eq(1)").toHaveText("Bs.F", {
        message: "The input should be superposed with a span containing the currency symbol.",
    });

    await contains(".o_field_widget input").edit("99.111111111");
    expect(".o_field_widget input").toHaveValue("99.1111", {
        message: "The value should should be formatted on blur.",
    });

    await clickSave();
    expect(".o_field_widget input").toHaveValue("99.1111", {
        message: "The new value should be rounded properly.",
    });
});

test("basic flow in editable list view - float field", async () => {
    Partner._records = [
        {
            id: 1,
            float_field: 9.1,
            monetary_field: 9.1,
            currency_id: 1,
        },
        {
            id: 2,
            float_field: 15.3,
            monetary_field: 15.3,
            currency_id: 2,
        },
        {
            id: 3,
            float_field: 0,
            monetary_field: 0,
            currency_id: 1,
        },
        {
            id: 4,
            float_field: 5.0,
            monetary_field: 5.0,
        },
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="float_field" widget="monetary"/>
                <field name="currency_id" column_invisible="1"/>
            </list>`,
    });

    const dollarValues = queryAll("td:contains($)");
    expect(dollarValues).toHaveLength(2, { message: "Only 2 line has dollar as a currency." });

    const euroValues = queryAll("td:contains(€)");
    expect(euroValues).toHaveLength(1, { message: "Only 1 line has euro as a currency." });

    const noCurrencyValues = queryAll("td.o_data_cell").filter(
        (x) => !(x.textContent.includes("€") || x.textContent.includes("$"))
    );
    expect(noCurrencyValues).toHaveLength(1, { message: "Only 1 line has no currency." });

    // switch to edit mode
    const dollarCell = queryFirst("td.o_field_cell");
    await contains(dollarCell).click();

    expect(dollarCell.children).toHaveLength(1, {
        message: "The cell td should only contain the special div of monetary widget.",
    });

    expect(".o_field_widget input").toHaveCount(1, {
        message: "The view should have 1 input for editable monetary float.",
    });
    expect(".o_field_widget input").toHaveValue("9.10", {
        message: "The input should be rendered without the currency symbol.",
    });

    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$", {
        message: "The input should be preceded by a span containing the currency symbol.",
    });

    await contains(".o_field_widget input").edit("108.2458938598598", { confirm: "blur" });
    expect(dollarCell).toHaveText("$ 108.25", { message: "The new value should be correct" });
});

test("basic flow in editable list view - monetary field", async () => {
    Partner._records = [
        {
            id: 1,
            float_field: 9.1,
            monetary_field: 9.1,
            currency_id: 1,
        },
        {
            id: 2,
            float_field: 15.3,
            monetary_field: 15.3,
            currency_id: 2,
        },
        {
            id: 3,
            float_field: 0,
            monetary_field: 0,
            currency_id: 1,
        },
        {
            id: 4,
            float_field: 5.0,
            monetary_field: 5.0,
        },
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="monetary_field"/>
                <field name="currency_id" column_invisible="1"/>
            </list>`,
    });

    const dollarValues = queryAll("td:contains($)");
    expect(dollarValues).toHaveLength(2, { message: "Only 2 line has dollar as a currency." });

    const euroValues = queryAll("td:contains(€)");
    expect(euroValues).toHaveLength(1, { message: "Only 1 line has euro as a currency." });

    const noCurrencyValues = queryAll("td.o_data_cell").filter(
        (x) => !(x.textContent.includes("€") || x.textContent.includes("$"))
    );
    expect(noCurrencyValues).toHaveLength(1, { message: "Only 1 line has no currency." });

    // switch to edit mode
    const dollarCell = queryFirst("td.o_field_cell");
    await contains(dollarCell).click();

    expect(dollarCell.children).toHaveLength(1, {
        message: "The cell td should only contain the special div of monetary widget.",
    });

    expect(".o_field_widget input").toHaveCount(1, {
        message: "The view should have 1 input for editable monetary float.",
    });
    expect(".o_field_widget input").toHaveValue("9.10", {
        message: "The input should be rendered without the currency symbol.",
    });

    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$", {
        message: "The input should be preceded by a span containing the currency symbol.",
    });

    await contains(".o_field_widget input").edit("108.2458938598598", { confirm: "blur" });
    expect(dollarCell).toHaveText("$ 108.25", { message: "The new value should be correct" });
});

test.tags("desktop");
test("changing currency updates the field - float field", async () => {
    Partner._records = [
        {
            id: 1,
            float_field: 4.2,
            monetary_field: 4.2,
            currency_id: 1,
        },
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="float_field" widget="monetary"/>
                <field name="currency_id"/>
            </form>`,
    });

    await contains(".o_field_many2one_selection input").click();
    await contains(".o-autocomplete--dropdown-item:contains(EUR)").click();
    expect(".o_field_widget .o_input span:eq(1)").toHaveText("€", {
        message:
            "The input should be preceded by a span containing the currency symbol added on blur.",
    });
    expect(".o_field_monetary input").toHaveValue("4.20");

    await clickSave();
    expect(".o_field_monetary input").toHaveValue("4.20", {
        message: "The new value should still be correct.",
    });
});

test.tags("desktop");
test("changing currency updates the field - monetary field", async () => {
    Partner._records = [
        {
            id: 1,
            float_field: 4.2,
            monetary_field: 4.2,
            currency_id: 1,
        },
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="monetary_field"/>
                <field name="currency_id"/>
            </form>`,
    });

    await contains(".o_field_many2one_selection input").click();
    await contains(".o-autocomplete--dropdown-item:contains(EUR)").click();

    expect(".o_field_widget .o_input span:eq(1)").toHaveText("€", {
        message:
            "The input should be preceded by a span containing the currency symbol added on blur.",
    });
    expect(".o_field_monetary input").toHaveValue("4.20");

    await clickSave();
    expect(".o_field_monetary input").toHaveValue("4.20", {
        message: "The new value should still be correct.",
    });
});

test("MonetaryField with monetary field given in options", async () => {
    Partner._fields.company_currency_id = fields.Many2one({
        string: "Company Currency",
        relation: "res.currency",
    });
    Partner._records[4].company_currency_id = 2;
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form edit="0">
                <sheet>
                    <field name="monetary_field" options="{'currency_field': 'company_currency_id'}"/>
                    <field name="company_currency_id"/>
                </sheet>
            </form>`,
        resId: 5,
    });

    expect(".o_field_monetary").toHaveText("9.10 €", {
        message: "field monetary should be formatted with correct currency",
    });
});

test("should keep the focus when being edited in x2many lists", async () => {
    Partner._fields.currency_id.default = 1;
    Partner._fields.m2m = fields.Many2many({
        relation: "partner",
        default: [[4, 2]],
    });
    Partner._views = {
        list: `
            <list editable="bottom">
                <field name="float_field" widget="monetary"/>
                <field name="currency_id" invisible="1"/>
            </list>`,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="p"/>
                    <field name="m2m"/>
                </sheet>
            </form>`,
    });

    // test the monetary field inside the one2many
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_field_widget[name=float_field] input").edit("22", { confirm: "blur" });

    expect(".o_field_widget[name=p] .o_field_widget[name=float_field] span").toHaveInnerHTML(
        "$&nbsp;22.00",
        { type: "html" }
    );

    // test the monetary field inside the many2many
    await contains(".o_field_widget[name=m2m] .o_data_cell").click();
    await contains(".o_field_widget[name=float_field] input").edit("22", { confirm: "blur" });
    expect(".o_field_widget[name=m2m] .o_field_widget[name=float_field] span").toHaveInnerHTML(
        "22.00&nbsp;€",
        { type: "html" }
    );
});

test("MonetaryField with currency set by an onchange", async () => {
    // this test ensures that the monetary field can be re-rendered with and
    // without currency (which can happen as the currency can be set by an
    // onchange)
    Partner._onChanges = {
        int_field: function (obj) {
            obj.currency_id = obj.int_field ? 2 : null;
        },
    };

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="int_field"/>
                <field name="float_field" widget="monetary"/>
                <field name="currency_id" invisible="1"/>
            </list>`,
    });

    await contains(".o_control_panel_main_buttons .o_list_button_add").click();
    expect(".o_selected_row .o_field_widget[name=float_field] input").toHaveCount(1, {
        message: "monetary field should have been rendered correctly (without currency)",
    });
    expect(".o_selected_row .o_field_widget[name=float_field] span").toHaveCount(2, {
        message: "monetary field should have been rendered correctly (without currency)",
    });

    // set a value for int_field -> should set the currency and re-render float_field
    await contains(".o_field_widget[name=int_field] input").edit("7", { confirm: "blur" });
    await contains(".o_field_cell[name=int_field]").click();
    expect(".o_selected_row .o_field_widget[name=float_field] input").toHaveCount(1, {
        message: "monetary field should have been re-rendered correctly (with currency)",
    });
    expect(
        queryAllTexts(".o_selected_row .o_field_widget[name=float_field] .o_input span")
    ).toEqual(["0.00", "€"], {
        message: "monetary field should have been re-rendered correctly (with currency)",
    });
    await contains(".o_field_widget[name=float_field] input").click();
    expect(".o_field_widget[name=float_field] input").toBeFocused({
        message: "focus should be on the float_field field's input",
    });

    // unset the value of int_field -> should unset the currency and re-render float_field
    await contains(".o_field_widget[name=int_field]").click();
    await contains(".o_field_widget[name=int_field] input").edit("0", { confirm: "blur" });
    await contains(".o_field_cell[name=int_field]").click();
    expect(".o_selected_row .o_field_widget[name=float_field] input").toHaveCount(1, {
        message: "monetary field should have been re-rendered correctly (without currency)",
    });
    expect(".o_selected_row .o_field_widget[name=float_field] span").toHaveCount(2, {
        message: "monetary field should have been re-rendered correctly (without currency)",
    });
    await contains(".o_field_widget[name=float_field] input").click();
    expect(".o_field_widget[name=float_field] input").toBeFocused({
        message: "focus should be on the float_field field's input",
    });
});

test("float widget on monetary field", async () => {
    Partner._fields.monetary = fields.Monetary({ currency_field: "currency_id" });
    Partner._records[0].monetary = 9.99;
    Partner._records[0].currency_id = 1;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form edit="0">
                <sheet>
                    <field name="monetary" widget="float"/>
                    <field name="currency_id" invisible="1"/>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=monetary]").toHaveText("9.99", {
        message: "value should be correctly formatted (with the float formatter)",
    });
});

test("float field with monetary widget and decimal precision", async () => {
    Partner._records = [
        {
            id: 1,
            float_field: -8.89859,
            currency_id: 1,
        },
    ];
    serverState.currencies = [
        { id: 1, name: "USD", symbol: "$", position: "before", digits: [0, 4] },
        { id: 2, name: "EUR", symbol: "€", position: "after" },
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="float_field" widget="monetary" options="{'field_digits': True}"/>
                    <field name="currency_id" invisible="1"/>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget[name=float_field] input").toHaveValue("-8.9", {
        message: "The input should be rendered without the currency symbol.",
    });
    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$", {
        message: "The input should be preceded by a span containing the currency symbol.",
    });

    await contains(".o_field_monetary input").edit("109.2458938598598");
    expect(".o_field_widget[name=float_field] input").toHaveValue("109.2", {
        message: "The value should should be formatted on blur.",
    });

    await clickSave();
    expect(".o_field_widget input").toHaveValue("109.2", {
        message: "The new value should be rounded properly.",
    });
});

test("MonetaryField without currency symbol", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5,
        arch: `
            <form>
                <sheet>
                    <field name="float_field" widget="monetary" options="{'no_symbol': True}" />
                    <field name="currency_id" invisible="1" />
                </sheet>
            </form>`,
    });

    // Non-breaking space between the currency and the amount
    expect(".o_field_widget[name=float_field] input").toHaveValue("9.10", {
        message: "The currency symbol is not displayed",
    });
});

test("required monetary field with zero value", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="monetary_field" required="1"/>
            </form>`,
    });

    expect(".o_form_editable").toHaveCount(1);
    expect("[name=monetary_field] input").toHaveValue("0.00");
});

test("uses 'currency_id' as currency field by default", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="monetary_field"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
        resId: 6,
    });

    expect(".o_form_editable").toHaveCount(1);
    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$", {
        message: "The input should be preceded by a span containing the currency symbol.",
    });
});

test("automatically uses currency_field if defined", async () => {
    Partner._fields.custom_currency_id = fields.Many2one({
        string: "Currency",
        relation: "res.currency",
    });
    Partner._fields.monetary_field.currency_field = "custom_currency_id";
    Partner._records[5].custom_currency_id = 1;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="monetary_field"/>
                <field name="custom_currency_id" invisible="1"/>
            </form>`,
        resId: 6,
    });

    expect(".o_form_editable").toHaveCount(1);
    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$", {
        message: "The input should be preceded by a span containing the currency symbol.",
    });
});

test("monetary field with pending onchange", async () => {
    const def = new Deferred();
    Partner._onChanges = {
        async name(record) {
            record.float_field = 132;
        },
    };
    onRpc("onchange", async () => {
        await def;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="float_field" widget="monetary"/>
                <field name="name"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_widget[name='name'] input").edit("test", { confirm: "blur" });
    await contains(".o_field_widget[name='float_field'] input").edit("1", { confirm: false });
    def.resolve();
    await animationFrame();
    expect(".o_field_monetary .o_monetary_ghost_value").toHaveText("1");
});

test("with 'hide_trailing_zeros' option", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5,
        arch: `
            <form>
                <field name="float_field" widget="monetary" options="{'hide_trailing_zeros': true}"/>
                <field name="currency_id" invisible="1"/>
            </form>`,
    });
    expect(".o_field_widget input").toHaveValue("9.1");
    expect(".o_field_widget .o_input span:eq(0)").toHaveText("$");
});
