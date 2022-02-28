/** @odoo-module **/

import { makeView, setupViewRegistries } from "../views/helpers";
import { click, clickEdit, clickSave, editInput, patchWithCleanup } from "../helpers/utils";
import { session } from "@web/session";

let serverData;

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
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
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
                            qux: 0.44444,
                            p: [],
                        },
                        {
                            id: 2,
                            bar: true,
                            int_field: 0,
                            qux: 0,
                            p: [],
                            currency_id: 2,
                        },
                        {
                            id: 4,
                            int_field: false,
                            qux: false,
                        },
                        { id: 3, bar: true, int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, int_field: -4, qux: 9.1, currency_id: 1 },
                        { id: 6, qux: 3.9, monetary_field: 4.2, currency_id: 1 },
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

        setupViewRegistries();
    });

    QUnit.module("MonetaryField");

    QUnit.test("basic flow in form view", async function (assert) {
        assert.expect(5);

        const form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 5,
            arch: `
                <form>
                    <field name="qux" widget="monetary"/>
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "$\u00a09.10",
            "The value should be displayed properly."
        );

        await clickEdit(form);
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").value,
            "9.10",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").parentNode.childNodes[0]
                .textContent,
            "$",
            "The input should be preceded by a span containing the currency symbol."
        );

        await editInput(form.el, ".o_field_monetary input", "108.2458938598598");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").value,
            "108.25",
            "The new value should be rounded properly after the blur"
        );

        await clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "$\u00a0108.25",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("rounding using formula in form view", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 5,
            arch: `
                <form>
                    <field name="qux" widget="monetary"/>
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        // Test computation and rounding
        await clickEdit(form);
        await editInput(form.el, ".o_field_monetary input", "=100/3");
        await clickSave(form);
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "$\u00a033.33",
            "The new value should be calculated and rounded properly."
        );
    });

    QUnit.test("with currency symbol after", async function (assert) {
        const form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `
                <form>
                    <field name="qux" widget="monetary"/>
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "0.00\u00a0€",
            "The value should be displayed properly."
        );

        await clickEdit(form);
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").value,
            "0.00",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").parentNode.children[1]
                .textContent,
            "€",
            "The input should be followed by a span containing the currency symbol."
        );

        await editInput(form.el, ".o_field_widget[name=qux] input", "108.2458938598598");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").value,
            "108.25",
            "The value should be formatted on blur."
        );

        await clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "108.25\u00a0€",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("MonetaryField with currency digits != 2", async function (assert) {
        assert.expect(5);

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
                qux: 99.1234,
                currency_id: 3,
            },
        ];

        const form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="qux" widget="monetary"/>
                    <field name="currency_id" invisible="1"/>
                </form>`,
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "99.1234\u00a0Bs.F",
            "The value should be displayed properly."
        );

        await clickEdit(form);
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").value,
            "99.1234",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").parentNode.children[1]
                .textContent,
            "Bs.F",
            "The input should be followed by a span containing the currency symbol."
        );

        await editInput(form.el, ".o_field_widget[name=qux] input", "99.111111111");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").value,
            "99.1111",
            "The value should should be formatted on blur."
        );

        await clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "99.1111\u00a0Bs.F",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("basic flow in editable list view", async function (assert) {
        var list = await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `<tree editable="bottom">
                    <field name="qux" widget="monetary"/>
                    <field name="currency_id" invisible="1"/>
                </tree>`,
        });

        const dollarValues = Array.from(list.el.querySelectorAll("td")).filter((x) =>
            x.textContent.includes("$")
        );
        assert.strictEqual(dollarValues.length, 2, "Only 2 line has dollar as a currency.");

        const euroValues = Array.from(list.el.querySelectorAll("td")).filter((x) =>
            x.textContent.includes("€")
        );
        assert.strictEqual(euroValues.length, 1, "One one line has euro as a currency.");

        // switch to edit mode
        const dollarCell = list.el.querySelector("td[title='9.1']");
        await click(dollarCell);

        assert.strictEqual(
            dollarCell.childNodes.length,
            1,
            "The cell td should only contain the special div of monetary widget."
        );

        assert.containsOnce(
            list.el,
            '[name="qux"] input',
            "The view should have 1 input for editable monetary float."
        );

        assert.strictEqual(
            list.el.querySelector('[name="qux"] input').value,
            "9.10",
            "The input should be rendered without the currency symbol."
        );

        assert.strictEqual(
            list.el.querySelector('[name="qux"] input').parentNode.childNodes[0].textContent,
            "$",
            "The input should be preceded by a span containing the currency symbol."
        );

        await editInput(list.el, '[name="qux"] input', "108.2458938598598");
        assert.strictEqual(
            list.el.querySelector('[name="qux"] input').value,
            "108.25",
            "The typed value should be correctly displayed and formatted on blur"
        );

        await clickSave(list);
        assert.strictEqual(
            dollarCell.textContent,
            "$\u00a0108.25",
            "The new value should be correct"
        );
    });

    QUnit.test("with real monetary field in model", async function (assert) {
        const form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 6,
            arch: `
                <form>
                    <sheet>
                    <field name="monetary_field"/>
                    <field name="currency_id" invisible="1"/>
                    </sheet>
                </form>`,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_monetary").textContent,
            "$\u00a04.20",
            "value should contain the currency"
        );

        await clickEdit(form);
        await editInput(form.el, ".o_field_monetary input", 108.249);
        assert.strictEqual(
            form.el.querySelector(".o_field_monetary input").value,
            "108.25",
            "The value should be formatted on blur."
        );

        await clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.el.querySelector(".o_field_monetary").textContent,
            "$\u00a0108.25",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("changing the currency updates the monetary field", async function (assert) {
        const form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 6,
            arch: `
                <form>
                    <field name="monetary_field"/>
                    <field name="currency_id"/>
                </form>`,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_monetary").textContent,
            "$\u00a04.20",
            "readonly value should contain the currency"
        );

        await clickEdit(form);

        // replace bottom with new helpers when they exist
        await click(form.el, ".o_field_many2one_selection input");
        const euroM2OListItem = Array.from(
            form.el.querySelectorAll(".o_field_many2one_selection li")
        ).filter((li) => li.textContent === "€")[0];
        await click(euroM2OListItem);

        // TODO Qunit.skipWOWL => don't we have some kind of blur / event on m2o click ?
        // assert.strictEqual(
        //     form.el.querySelector(".o_field_monetary input").value,
        //     "4.20\u00a0€",
        //     "The value should be formatted with new currency on blur."
        // );

        await clickSave(form);

        assert.strictEqual(
            form.el.querySelector(".o_field_monetary").textContent,
            "4.20\u00a0€",
            "The new value should still be correct."
        );
    });

    QUnit.skipWOWL("MonetaryField with monetary field given in options", async function (assert) {
        assert.expect(1);

        this.data.partner.fields.qux.type = "monetary";
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
                "<field name=\"qux\" options=\"{'currency_field': 'company_currency_id'}\"/>" +
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
                        '<field name="qux" widget="monetary"/>' +
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
                $o2m.find(".o_field_widget[name=qux]").html(),
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
                $m2m.find(".o_field_widget[name=qux]").html(),
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
                '<field name="qux" widget="monetary"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</tree>",
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        await testUtils.dom.click(list.$buttons.find(".o_list_button_add"));
        assert.containsOnce(
            list,
            "div.o_field_widget[name=qux] input",
            "monetary field should have been rendered correctly (without currency)"
        );
        assert.containsNone(
            list,
            ".o_field_widget[name=qux] span",
            "monetary field should have been rendered correctly (without currency)"
        );

        // set a value for int_field -> should set the currency and re-render qux
        await testUtils.fields.editInput(list.$(".o_field_widget[name=int_field]"), "7");
        assert.containsOnce(
            list,
            "div.o_field_widget[name=qux] input",
            "monetary field should have been re-rendered correctly (with currency)"
        );
        assert.strictEqual(
            list.$(".o_field_widget[name=qux] span:contains(€)").length,
            1,
            "monetary field should have been re-rendered correctly (with currency)"
        );
        var $quxInput = list.$(".o_field_widget[name=qux] input");
        await testUtils.dom.click($quxInput);
        assert.strictEqual(
            document.activeElement,
            $quxInput[0],
            "focus should be on the qux field's input"
        );

        // unset the value of int_field -> should unset the currency and re-render qux
        await testUtils.dom.click(list.$(".o_field_widget[name=int_field]"));
        await testUtils.fields.editInput(list.$(".o_field_widget[name=int_field]"), "0");
        $quxInput = list.$("div.o_field_widget[name=qux] input");
        assert.strictEqual(
            $quxInput.length,
            1,
            "monetary field should have been re-rendered correctly (without currency)"
        );
        assert.containsNone(
            list,
            ".o_field_widget[name=qux] span",
            "monetary field should have been re-rendered correctly (without currency)"
        );
        await testUtils.dom.click($quxInput);
        assert.strictEqual(
            document.activeElement,
            $quxInput[0],
            "focus should be on the qux field's input"
        );

        list.destroy();
    });
});
