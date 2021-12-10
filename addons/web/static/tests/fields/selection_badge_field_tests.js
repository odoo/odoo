/** @odoo-module **/

import { setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        qux: { string: "Qux", type: "float", digits: [16, 1] },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "trululu",
                        },
                        turtles: {
                            string: "one2many turtle field",
                            type: "one2many",
                            relation: "turtle",
                            relation_field: "turtle_trululu",
                        },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                        color: {
                            type: "selection",
                            selection: [
                                ["red", "Red"],
                                ["black", "Black"],
                            ],
                            default: "red",
                            string: "Color",
                        },
                        date: { string: "Some Date", type: "date" },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        user_id: { string: "User", type: "many2one", relation: "user" },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner_type", "Partner Type"],
                                ["partner", "Partner"],
                            ],
                        },
                        model_id: { string: "Model", type: "many2one", relation: "ir.model" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44,
                            p: [],
                            turtles: [2],
                            timmy: [],
                            trululu: 4,
                            user_id: 17,
                            reference: "product,37",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            product_id: 37,
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                            user_id: 17,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            bar: false,
                        },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
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
                        name: { string: "Partner Type", type: "char" },
                        color: { string: "Color index", type: "integer" },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                turtle: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        turtle_foo: { string: "Foo", type: "char" },
                        turtle_bar: { string: "Bar", type: "boolean", default: true },
                        turtle_int: { string: "int", type: "integer", sortable: true },
                        turtle_description: { string: "Description", type: "text" },
                        turtle_trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                        },
                        turtle_ref: {
                            string: "Reference",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner", "Partner"],
                            ],
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            required: true,
                        },
                        partner_ids: { string: "Partner", type: "many2many", relation: "partner" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "leonardo",
                            turtle_bar: true,
                            turtle_foo: "yop",
                            partner_ids: [],
                        },
                        {
                            id: 2,
                            display_name: "donatello",
                            turtle_bar: true,
                            turtle_foo: "blip",
                            turtle_int: 9,
                            partner_ids: [2, 4],
                        },
                        {
                            id: 3,
                            display_name: "raphael",
                            product_id: 37,
                            turtle_bar: false,
                            turtle_foo: "kawa",
                            turtle_int: 21,
                            partner_ids: [],
                            turtle_ref: "product,37",
                        },
                    ],
                    onchanges: {},
                },
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: {
                            string: "one2many partners field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "user_id",
                        },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Aline",
                            partner_ids: [1, 2],
                        },
                        {
                            id: 19,
                            name: "Christine",
                        },
                    ],
                },
                "ir.model": {
                    fields: {
                        model: { string: "Model", type: "char" },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Partner",
                            model: "partner",
                        },
                        {
                            id: 20,
                            name: "Product",
                            model: "product",
                        },
                        {
                            id: 21,
                            name: "Partner Type",
                            model: "partner_type",
                        },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("SelectionBadgeField");

    QUnit.skip(
        "FieldSelectionBadgeField widget on a many2one in a new record",
        async function (assert) {
            assert.expect(6);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: "<form>" + '<field name="product_id" widget="selection_badge"/>' + "</form>",
            });

            assert.ok(form.$("span.o_selection_badge").length, "should have rendered outer div");
            assert.containsN(form, "span.o_selection_badge", 2, "should have 2 possible choices");
            assert.ok(
                form.$("span.o_selection_badge:contains(xphone)").length,
                "one of them should be xphone"
            );
            assert.containsNone(form, "span.active", "none of the input should be checked");

            await testUtils.dom.click($("span.o_selection_badge:first"));

            assert.containsOnce(form, "span.active", "one of the input should be checked");

            await testUtils.form.clickSave(form);

            var newRecord = _.last(this.data.partner.records);
            assert.strictEqual(
                newRecord.product_id,
                37,
                "should have saved record with correct value"
            );
            form.destroy();
        }
    );

    QUnit.skip(
        "FieldSelectionBadgeField widget on a selection in a new record",
        async function (assert) {
            assert.expect(4);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: "<form>" + '<field name="color" widget="selection_badge"/>' + "</form>",
            });

            assert.ok(form.$("span.o_selection_badge").length, "should have rendered outer div");
            assert.containsN(form, "span.o_selection_badge", 2, "should have 2 possible choices");
            assert.ok(
                form.$("span.o_selection_badge:contains(Red)").length,
                "one of them should be Red"
            );

            // click on 2nd option
            await testUtils.dom.click(form.$("span.o_selection_badge").eq(1));

            await testUtils.form.clickSave(form);

            var newRecord = _.last(this.data.partner.records);
            assert.strictEqual(
                newRecord.color,
                "black",
                "should have saved record with correct value"
            );
            form.destroy();
        }
    );

    QUnit.skip(
        "FieldSelectionBadgeField widget on a selection in a readonly mode",
        async function (assert) {
            assert.expect(1);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="color" widget="selection_badge" readonly="1"/>' +
                    "</form>",
            });

            assert.containsOnce(
                form,
                "span.o_readonly_modifier",
                "should have 1 possible value in readonly mode"
            );
            form.destroy();
        }
    );
});
