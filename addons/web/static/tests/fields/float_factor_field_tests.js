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

    QUnit.module("FloatFactorField");

    QUnit.skipWOWL("FloatFactorField in form view", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="float_factor" options="{\'factor\': 0.5}" digits="[16,2]"/>' +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    // 16.4 / 2 = 8.2
                    assert.strictEqual(
                        args.args[1].qux,
                        4.6,
                        "the correct float value should be saved"
                    );
                }
                return this._super.apply(this, arguments);
            },
            res_id: 5,
        });
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "4.55", // 9.1 / 0.5
            "The formatted value should be displayed properly."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$("input[name=qux]").val(),
            "4.55",
            "The value should be rendered correctly in the input."
        );

        await testUtils.fields.editInput(form.$("input[name=qux]"), "2.3");

        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "2.30",
            "The new value should be saved and displayed properly."
        );

        form.destroy();
    });
});
