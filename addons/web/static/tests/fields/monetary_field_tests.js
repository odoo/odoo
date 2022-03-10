/** @odoo-module **/

import { makeView, setupViewRegistries } from "../views/helpers";
import {
    click,
    clickEdit,
    clickSave,
    editInput,
    getFixture,
    patchWithCleanup,
} from "../helpers/utils";
import { session } from "@web/session";

let serverData, target;

// WOWL remove after adapting tests
let createView, FormView, testUtils, ListView;

function getFieldArch(fieldName, widget) {
    return `<field name="${fieldName}" ` + (widget ? `widget="${widget}"` : "") + `/>`;
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        float_field: {
                            string: "float_field",
                            type: "float",
                            digits: [16, 1],
                            searchable: true,
                        },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        monetary_field: {
                            string: "Monetary Field",
                            type: "monetary",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            bar: true,
                            int_field: 10,
                            float_field: 0.44444,
                            p: [],
                        },
                        {
                            id: 2,
                            bar: true,
                            int_field: 0,
                            float_field: 0,
                            p: [],
                            currency_id: 2,
                        },
                        {
                            id: 4,
                            int_field: false,
                            float_field: false,
                        },
                        { id: 3, bar: true, int_field: 80, float_field: -3.89859 },
                        { id: 5, bar: false, int_field: -4, float_field: 9.1, currency_id: 1 },
                        { id: 6, float_field: 3.9, monetary_field: 4.2, currency_id: 1 },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
                        },
                        {
                            id: 2,
                            display_name: "€",
                            symbol: "€",
                            position: "after",
                        },
                        {
                            id: 3,
                            display_name: "VEF",
                            symbol: "Bs.F",
                            position: "after",
                            digits: [0, 4],
                        },
                    ],
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("MonetaryField");

    async function basicFlowInFormView(assert, fieldName, widget) {
        serverData.models.partner.records = [
            {
                id: 1,
                float_field: 9.1,
                monetary_field: 9.1,
                currency_id: 1,
            },
        ];

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    ${getFieldArch(fieldName, widget)}
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "$\u00a09.10",
            "The value should be displayed properly."
        );

        await clickEdit(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "9.10",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget input").parentNode.childNodes[0].textContent,
            "$",
            "The input should be preceded by a span containing the currency symbol."
        );

        await editInput(target, ".o_field_monetary input", "108.2458938598598");
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "108.25",
            "The new value should be rounded properly after the blur"
        );

        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "$\u00a0108.25",
            "The new value should be rounded properly."
        );
    }

    QUnit.test("basic flow in form view - float field", async function (assert) {
        return basicFlowInFormView(assert, "float_field", "monetary");
    });
    QUnit.test("basic flow in form view - monetary field", async function (assert) {
        return basicFlowInFormView(assert, "monetary_field");
    });

    async function RoundingUsingFormulaInFormView(assert, fieldName, widget) {
        serverData.models.partner.records = [
            {
                id: 1,
                float_field: 9.1,
                monetary_field: 9.1,
                currency_id: 1,
            },
        ];

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    ${getFieldArch(fieldName, widget)}
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        // Test computation and rounding
        await clickEdit(target);
        await editInput(target, ".o_field_monetary input", "=100/3");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "$\u00a033.33",
            "The new value should be calculated and rounded properly."
        );
    }

    QUnit.test("rounding using formula in form view - float field", async function (assert) {
        return RoundingUsingFormulaInFormView(assert, "float_field", "monetary");
    });

    QUnit.test("rounding using formula in form view - monetary field", async function (assert) {
        return RoundingUsingFormulaInFormView(assert, "monetary_field");
    });

    async function withCurrencySymbolAfter(assert, fieldName, widget) {
        serverData.models.partner.records = [
            {
                id: 1,
                float_field: 0,
                monetary_field: 0,
                currency_id: 2,
            },
        ];

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    ${getFieldArch(fieldName, widget)}
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "0.00\u00a0€",
            "The value should be displayed properly."
        );

        await clickEdit(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "0.00",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget input").parentNode.children[1].textContent,
            "€",
            "The input should be followed by a span containing the currency symbol."
        );

        await editInput(target, ".o_field_widget input", "108.2458938598598");
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "108.25",
            "The value should be formatted on blur."
        );

        await clickSave(target);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "108.25\u00a0€",
            "The new value should be rounded properly."
        );
    }

    QUnit.test("with currency symbol after - float field", async function (assert) {
        return withCurrencySymbolAfter(assert, "float_field", "monetary");
    });
    QUnit.test("with currency symbol after - monetary field", async function (assert) {
        return withCurrencySymbolAfter(assert, "monetary_field");
    });

    async function withCurrencyDigitsNot2(assert, fieldName, widget) {
        // need to also add it to the session (as currencies are loaded there)
        patchWithCleanup(session, {
            currencies: {
                ...session.currencies,
                3: {
                    name: "VEF",
                    symbol: "Bs.F",
                    position: "after",
                    digits: [0, 4],
                },
            },
        });

        serverData.models.partner.records = [
            {
                id: 1,
                float_field: 99.1234,
                monetary_field: 99.1234,
                currency_id: 3,
            },
        ];

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    ${getFieldArch(fieldName, widget)}
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "99.1234\u00a0Bs.F",
            "The value should be displayed properly."
        );

        await clickEdit(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "99.1234",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget input").parentNode.children[1].textContent,
            "Bs.F",
            "The input should be followed by a span containing the currency symbol."
        );

        await editInput(target, ".o_field_widget input", "99.111111111");
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "99.1111",
            "The value should should be formatted on blur."
        );

        await clickSave(target);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "99.1111\u00a0Bs.F",
            "The new value should be rounded properly."
        );
    }

    QUnit.test("with currency digits != 2 - float field", async function (assert) {
        return withCurrencyDigitsNot2(assert, "float_field", "monetary");
    });
    QUnit.test("with currency digits != 2 - monetary field", async function (assert) {
        return withCurrencyDigitsNot2(assert, "monetary_field");
    });

    async function basicFlowInEditableListView(assert, fieldName, widget) {
        serverData.models.partner.records = [
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
                float_field: false,
                monetary_field: false,
                currency_id: 1,
            },
            {
                id: 4,
                float_field: 5.0,
                monetary_field: 5.0,
            },
        ];

        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `<tree editable="bottom">
                    ${getFieldArch(fieldName, widget)}
                    <field name="currency_id" invisible="1"/>
                </tree>`,
        });

        const dollarValues = Array.from(target.querySelectorAll("td")).filter((x) =>
            x.textContent.includes("$")
        );
        assert.strictEqual(dollarValues.length, 2, "Only 2 line has dollar as a currency.");

        const euroValues = Array.from(target.querySelectorAll("td")).filter((x) =>
            x.textContent.includes("€")
        );
        assert.strictEqual(euroValues.length, 1, "Only 1 line has euro as a currency.");

        const noCurrencyValues = Array.from(target.querySelectorAll("td.o_data_cell")).filter(
            (x) => !(x.textContent.includes("€") || x.textContent.includes("$"))
        );
        assert.strictEqual(noCurrencyValues.length, 1, "Only 1 line has no currency.");

        // switch to edit mode
        const dollarCell = target.querySelectorAll("td.o_field_cell")[0];
        await click(dollarCell);

        assert.strictEqual(
            dollarCell.childNodes.length,
            1,
            "The cell td should only contain the special div of monetary widget."
        );

        assert.containsOnce(
            target,
            ".o_field_widget input",
            "The view should have 1 input for editable monetary float."
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget  input").value,
            "9.10",
            "The input should be rendered without the currency symbol."
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget input").parentNode.childNodes[0].textContent,
            "$",
            "The input should be preceded by a span containing the currency symbol."
        );

        await editInput(target, ".o_field_widget input", "108.2458938598598");
        assert.strictEqual(
            target.querySelector(".o_field_widget  input").value,
            "108.25",
            "The typed value should be correctly displayed and formatted on blur"
        );

        await clickSave(target);
        assert.strictEqual(
            dollarCell.textContent,
            "$\u00a0108.25",
            "The new value should be correct"
        );
    }

    QUnit.test("basic flow in editable list view - float field", async function (assert) {
        return basicFlowInEditableListView(assert, "float_field", "monetary");
    });
    QUnit.test("basic flow in editable list view - monetary field", async function (assert) {
        return basicFlowInEditableListView(assert, "monetary_field");
    });

    async function changingCurrencyUpdatesTheField(assert, fieldName, widget) {
        serverData.models.partner.records = [
            {
                id: 1,
                float_field: 4.2,
                monetary_field: 4.2,
                currency_id: 1,
            },
        ];

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    ${getFieldArch(fieldName, widget)}
                    <field name="currency_id"/>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_monetary").textContent,
            "$\u00a04.20",
            "readonly value should contain the currency"
        );

        await clickEdit(target);

        // replace bottom with new helpers when they exist
        await click(target, ".o_field_many2one_selection input");
        const euroM2OListItem = Array.from(
            target.querySelectorAll(".o_field_many2one_selection li")
        ).filter((li) => li.textContent === "€")[0];
        await click(euroM2OListItem);

        // TODO Qunit.skipWOWL => don't we have some kind of blur / event on m2o click ?
        // assert.strictEqual(
        //     form.el.querySelector(".o_field_monetary input").value,
        //     "4.20\u00a0€",
        //     "The value should be formatted with new currency on blur."
        // );

        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_monetary").textContent,
            "4.20\u00a0€",
            "The new value should still be correct."
        );
    }

    QUnit.test("changing currency updates the field - float field", async function (assert) {
        return changingCurrencyUpdatesTheField(assert, "float_field", "monetary");
    });
    QUnit.test("changing currency updates the field - monetary field", async function (assert) {
        return changingCurrencyUpdatesTheField(assert, "monetary_field");
    });

    QUnit.skipWOWL("MonetaryField with monetary field given in options", async function (assert) {
        assert.expect(1);

        this.data.partner.fields.float_field.type = "monetary";
        this.data.partner.fields.company_currency_id = {
            string: "Company Currency",
            type: "many2one",
            relation: "currency",
        };
        this.data.partner.records[4].company_currency_id = 2;

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<field name=\"float_field\" options=\"{'currency_field': 'company_currency_id'}\"/>" +
                '<field name="company_currency_id"/>' +
                "</sheet>" +
                "</form>",
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        assert.strictEqual(
            form.$(".o_field_monetary").html(),
            "9.10&nbsp;€",
            "field monetary should be formatted with correct currency"
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "should keep the focus when being edited in x2many lists",
        async function (assert) {
            assert.expect(6);

            this.data.partner.fields.currency_id.default = 1;
            this.data.partner.fields.m2m = {
                string: "m2m",
                type: "many2many",
                relation: "partner",
                default: [[6, false, [2]]],
            };
            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    '<field name="p"/>' +
                    '<field name="m2m"/>' +
                    "</sheet>" +
                    "</form>",
                archs: {
                    "partner,false,list":
                        '<tree editable="bottom">' +
                        '<field name="float_field" widget="monetary"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                        "</tree>",
                },
                session: {
                    currencies: _.indexBy(this.data.currency.records, "id"),
                },
            });

            // test the monetary field inside the one2many
            var $o2m = form.$(".o_field_widget[name=p]");
            await testUtils.dom.click($o2m.find(".o_field_x2many_list_row_add a"));
            await testUtils.fields.editInput($o2m.find(".o_field_widget input"), "22");

            assert.strictEqual(
                $o2m.find(".o_field_widget input").get(0),
                document.activeElement,
                "the focus should still be on the input"
            );
            assert.strictEqual(
                $o2m.find(".o_field_widget input").val(),
                "22",
                "the value should not have been formatted yet"
            );

            await testUtils.dom.click(form.$el);

            assert.strictEqual(
                $o2m.find(".o_field_widget[name=float_field]").html(),
                "$&nbsp;22.00",
                "the value should have been formatted after losing the focus"
            );

            // test the monetary field inside the many2many
            var $m2m = form.$(".o_field_widget[name=m2m]");
            await testUtils.dom.click($m2m.find(".o_data_row td:first"));
            await testUtils.fields.editInput($m2m.find(".o_field_widget input"), "22");

            assert.strictEqual(
                $m2m.find(".o_field_widget input").get(0),
                document.activeElement,
                "the focus should still be on the input"
            );
            assert.strictEqual(
                $m2m.find(".o_field_widget input").val(),
                "22",
                "the value should not have been formatted yet"
            );

            await testUtils.dom.click(form.$el);

            assert.strictEqual(
                $m2m.find(".o_field_widget[name=float_field]").html(),
                "22.00&nbsp;€",
                "the value should have been formatted after losing the focus"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL("MonetaryField with currency set by an onchange", async function (assert) {
        // this test ensures that the monetary field can be re-rendered with and
        // without currency (which can happen as the currency can be set by an
        // onchange)
        assert.expect(8);

        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.currency_id = obj.int_field ? 2 : null;
            },
        };

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch:
                '<tree editable="top">' +
                '<field name="int_field"/>' +
                '<field name="float_field" widget="monetary"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</tree>",
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        await testUtils.dom.click(list.$buttons.find(".o_list_button_add"));
        assert.containsOnce(
            list,
            "div.o_field_widget[name=float_field] input",
            "monetary field should have been rendered correctly (without currency)"
        );
        assert.containsNone(
            list,
            ".o_field_widget[name=float_field] span",
            "monetary field should have been rendered correctly (without currency)"
        );

        // set a value for int_field -> should set the currency and re-render float_field
        await testUtils.fields.editInput(list.$(".o_field_widget[name=int_field]"), "7");
        assert.containsOnce(
            list,
            "div.o_field_widget[name=float_field] input",
            "monetary field should have been re-rendered correctly (with currency)"
        );
        assert.strictEqual(
            list.$(".o_field_widget[name=float_field] span:contains(€)").length,
            1,
            "monetary field should have been re-rendered correctly (with currency)"
        );
        var $float_fieldInput = list.$(".o_field_widget[name=float_field] input");
        await testUtils.dom.click($float_fieldInput);
        assert.strictEqual(
            document.activeElement,
            $float_fieldInput[0],
            "focus should be on the float_field field's input"
        );

        // unset the value of int_field -> should unset the currency and re-render float_field
        await testUtils.dom.click(list.$(".o_field_widget[name=int_field]"));
        await testUtils.fields.editInput(list.$(".o_field_widget[name=int_field]"), "0");
        $float_fieldInput = list.$("div.o_field_widget[name=float_field] input");
        assert.strictEqual(
            $float_fieldInput.length,
            1,
            "monetary field should have been re-rendered correctly (without currency)"
        );
        assert.containsNone(
            list,
            ".o_field_widget[name=float_field] span",
            "monetary field should have been re-rendered correctly (without currency)"
        );
        await testUtils.dom.click($float_fieldInput);
        assert.strictEqual(
            document.activeElement,
            $float_fieldInput[0],
            "focus should be on the float_field field's input"
        );

        list.destroy();
    });
});
