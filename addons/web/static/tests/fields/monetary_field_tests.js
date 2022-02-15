/** @odoo-module **/

import { setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        txt: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
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
                        trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                        document: { string: "Binary", type: "binary" },
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            selection: "blocked",
                            document: "coucou==\n",
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                            qux: 0,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            sequence: 4,
                            currency_id: 2,
                            selection: "normal",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            sequence: 9,
                            int_field: false,
                            qux: false,
                            selection: "done",
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, currency_id: 1 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
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
                    ],
                },
                "ir.translation": {
                    fields: {
                        lang: { type: "char" },
                        value: { type: "char" },
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 37,
                            value: "",
                            lang: "en_US",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("MonetaryField");

    QUnit.skipWOWL("MonetaryField in form view", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="monetary"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</sheet>" +
                "</form>",
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "$\u00a09.10",
            "The value should be displayed properly."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "9.10",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").parent().children().first().text(),
            "$",
            "The input should be preceded by a span containing the currency symbol."
        );

        await testUtils.fields.editInput(form.$(".o_field_monetary input"), "108.2458938598598");
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "108.2458938598598",
            "The value should not be formated yet."
        );

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "$\u00a0108.25",
            "The new value should be rounded properly."
        );

        form.destroy();
    });

    QUnit.skipWOWL("MonetaryField rounding using formula in form view", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="monetary"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</sheet>" +
                "</form>",
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        // Test computation and rounding
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$(".o_field_monetary input"), "=100/3");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "$\u00a033.33",
            "The new value should be calculated and rounded properly."
        );

        form.destroy();
    });

    QUnit.skipWOWL("MonetaryField with currency symbol after", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="monetary"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</sheet>" +
                "</form>",
            res_id: 2,
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "0.00\u00a0€",
            "The value should be displayed properly."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "0.00",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").parent().children().eq(1).text(),
            "€",
            "The input should be followed by a span containing the currency symbol."
        );

        await testUtils.fields.editInput(
            form.$(".o_field_widget[name=qux] input"),
            "108.2458938598598"
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "108.2458938598598",
            "The value should not be formated yet."
        );

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "108.25\u00a0€",
            "The new value should be rounded properly."
        );

        form.destroy();
    });

    QUnit.skipWOWL("MonetaryField with currency digits != 2", async function (assert) {
        assert.expect(5);

        this.data.partner.records = [
            {
                id: 1,
                bar: false,
                foo: "pouet",
                int_field: 68,
                qux: 99.1234,
                currency_id: 1,
            },
        ];
        this.data.currency.records = [
            {
                id: 1,
                display_name: "VEF",
                symbol: "Bs.F",
                position: "after",
                digits: [16, 4],
            },
        ];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="monetary"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</sheet>" +
                "</form>",
            res_id: 1,
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "99.1234\u00a0Bs.F",
            "The value should be displayed properly."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "99.1234",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").parent().children().eq(1).text(),
            "Bs.F",
            "The input should be followed by a span containing the currency symbol."
        );

        await testUtils.fields.editInput(form.$(".o_field_widget[name=qux] input"), "99.111111111");
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "99.111111111",
            "The value should not be formated yet."
        );

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "99.1111\u00a0Bs.F",
            "The new value should be rounded properly."
        );

        form.destroy();
    });

    QUnit.skipWOWL("MonetaryField in editable list view", async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                '<field name="qux" widget="monetary"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</tree>",
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        var dollarValues = list.$("td").filter(function () {
            return _.str.include($(this).text(), "$");
        });
        assert.strictEqual(dollarValues.length, 1, "Only one line has dollar as a currency.");

        var euroValues = list.$("td").filter(function () {
            return _.str.include($(this).text(), "€");
        });
        assert.strictEqual(euroValues.length, 1, "One one line has euro as a currency.");

        var zeroValues = list.$("td.o_data_cell").filter(function () {
            return $(this).text() === "";
        });
        assert.strictEqual(
            zeroValues.length,
            1,
            "Unset float values should be rendered as empty strings."
        );

        // switch to edit mode
        var $cell = list.$("tr.o_data_row td:not(.o_list_record_selector):contains($)");
        await testUtils.dom.click($cell);

        assert.strictEqual(
            $cell.children().length,
            1,
            "The cell td should only contain the special div of monetary widget."
        );
        assert.containsOnce(
            list,
            '[name="qux"] input',
            "The view should have 1 input for editable monetary float."
        );
        assert.strictEqual(
            list.$('[name="qux"] input').val(),
            "9.10",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            list.$('[name="qux"] input').parent().children().first().text(),
            "$",
            "The input should be preceded by a span containing the currency symbol."
        );

        await testUtils.fields.editInput(list.$('[name="qux"] input'), "108.2458938598598");
        assert.strictEqual(
            list.$('[name="qux"] input').val(),
            "108.2458938598598",
            "The typed value should be correctly displayed."
        );

        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.$("tr.o_data_row td:not(.o_list_record_selector):contains($)").text(),
            "$\u00a0108.25",
            "The new value should be rounded properly."
        );

        list.destroy();
    });

    QUnit.skipWOWL("MonetaryField with real monetary field in model", async function (assert) {
        assert.expect(7);

        this.data.partner.fields.qux.type = "monetary";
        this.data.partner.fields.quux = {
            string: "Quux",
            type: "monetary",
            digits: [16, 1],
            searchable: true,
            readonly: true,
        };

        _.find(this.data.partner.records, function (record) {
            return record.id === 5;
        }).quux = 4.2;

        this.data.partner.onchanges = {
            bar: function (obj) {
                obj.qux = obj.bar ? 100 : obj.qux;
            },
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux"/>' +
                '<field name="quux"/>' +
                '<field name="currency_id"/>' +
                '<field name="bar"/>' +
                "</sheet>" +
                "</form>",
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        assert.strictEqual(
            form.$(".o_field_monetary").first().html(),
            "$&nbsp;9.10",
            "readonly value should contain the currency"
        );
        assert.strictEqual(
            form.$(".o_field_monetary").first().next().html(),
            "$&nbsp;4.20",
            "readonly value should contain the currency"
        );

        await testUtils.form.clickEdit(form);

        assert.strictEqual(
            form.$(".o_field_monetary > input").val(),
            "9.10",
            "input value in edition should only contain the value, without the currency"
        );

        await testUtils.dom.click(form.$('input[type="checkbox"]'));
        assert.containsOnce(
            form,
            ".o_field_monetary > input",
            "After the onchange, the monetary <input/> should not have been duplicated"
        );
        assert.containsOnce(
            form,
            ".o_field_monetary[name=quux]",
            "After the onchange, the monetary readonly field should not have been duplicated"
        );

        await testUtils.fields.many2one.clickOpenDropdown("currency_id");
        await testUtils.fields.many2one.clickItem("currency_id", "€");
        assert.strictEqual(
            form.$(".o_field_monetary > span").html(),
            "€",
            "After currency change, the monetary field currency should have been updated"
        );
        assert.strictEqual(
            form.$(".o_field_monetary").first().next().html(),
            "4.20&nbsp;€",
            "readonly value should contain the updated currency"
        );

        form.destroy();
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

        var form = await createView({
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
            var form = await createView({
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
