/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import { click, makeDeferred, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { makeView } from "../views/helpers";

const serviceRegistry = registry.category("services");

let serverData;

function hasGroup(group) {
    return group === "base.group_allow_export";
}

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

        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
    });

    QUnit.module("SelectionField");

    QUnit.skip("SelectionField in a list view", async function (assert) {
        assert.expect(3);

        this.data.partner.records.forEach(function (r) {
            r.color = "red";
        });

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree string="Colors" editable="top">' + '<field name="color"/>' + "</tree>",
        });

        assert.strictEqual(
            list.$("td:contains(Red)").length,
            3,
            "should have 3 rows with correct value"
        );
        await testUtils.dom.click(list.$("td:contains(Red):first"));

        var $td = list.$("tbody tr.o_selected_row td:not(.o_list_record_selector)");

        assert.strictEqual($td.find("select").length, 1, "td should have a child 'select'");
        assert.strictEqual($td.contents().length, 1, "select tag should be only child of td");
        list.destroy();
    });

    QUnit.skip("SelectionField, edition and on many2one field", async function (assert) {
        assert.expect(21);

        this.data.partner.onchanges = { product_id: function () {} };
        this.data.partner.records[0].product_id = 37;
        this.data.partner.records[0].trululu = false;

        var count = 0;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="product_id" widget="selection"/>' +
                '<field name="trululu" widget="selection"/>' +
                '<field name="color" widget="selection"/>' +
                "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                count++;
                assert.step(args.method);
                return this._super(route, args);
            },
        });

        assert.containsNone(form.$(".o_form_view"), "select");
        assert.strictEqual(
            form.$(".o_field_widget[name=product_id]").text(),
            "xphone",
            "should have rendered the many2one field correctly"
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=product_id]").attr("raw-value"),
            "37",
            "should have set the raw-value attr for many2one field correctly"
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=trululu]").text(),
            "",
            "should have rendered the unset many2one field correctly"
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=color]").text(),
            "Red",
            "should have rendered the selection field correctly"
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=color]").attr("raw-value"),
            "red",
            "should have set the raw-value attr for selection field correctly"
        );

        await testUtils.form.clickEdit(form);

        assert.containsN(form.$(".o_form_view"), "select", 3);
        assert.containsOnce(
            form,
            'select[name="product_id"] option:contains(xphone)',
            "should have fetched xphone option"
        );
        assert.containsOnce(
            form,
            'select[name="product_id"] option:contains(xpad)',
            "should have fetched xpad option"
        );
        assert.strictEqual(
            form.$('select[name="product_id"]').val(),
            "37",
            "should have correct product_id value"
        );
        assert.strictEqual(
            form.$('select[name="trululu"]').val(),
            "false",
            "should not have any value in trululu field"
        );
        await testUtils.fields.editSelect(form.$('select[name="product_id"]'), 41);

        assert.strictEqual(
            form.$('select[name="product_id"]').val(),
            "41",
            "should have a value of xphone"
        );

        assert.strictEqual(
            form.$('select[name="color"]').val(),
            '"red"',
            "should have correct value in color field"
        );

        assert.verifySteps(["read", "name_search", "name_search", "onchange"]);
        count = 0;
        await form.reload();
        assert.strictEqual(count, 1, "should not reload product_id relation");
        assert.verifySteps(["read"]);

        form.destroy();
    });

    QUnit.skip("unset selection field with 0 as key", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists.
        assert.expect(2);

        this.data.partner.fields.selection = {
            type: "selection",
            selection: [
                [0, "Value O"],
                [1, "Value 1"],
            ],
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners">' + '<field name="selection"/>' + "</form>",
            res_id: 1,
        });

        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "Value O",
            "the displayed value should be 'Value O'"
        );
        assert.doesNotHaveClass(
            form.$(".o_field_widget"),
            "o_field_empty",
            "should not have class o_field_empty"
        );

        form.destroy();
    });

    QUnit.skip("unset selection field with string keys", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists. In
        // this test, it doesn't exist as keys are strings.
        assert.expect(2);

        this.data.partner.fields.selection = {
            type: "selection",
            selection: [
                ["0", "Value O"],
                ["1", "Value 1"],
            ],
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners">' + '<field name="selection"/>' + "</form>",
            res_id: 1,
        });

        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "",
            "there should be no displayed value"
        );
        assert.hasClass(
            form.$(".o_field_widget"),
            "o_field_empty",
            "should have class o_field_empty"
        );

        form.destroy();
    });

    QUnit.skip("unset selection on a many2one field", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="trululu" widget="selection"/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "write") {
                    assert.strictEqual(
                        args.args[1].trululu,
                        false,
                        "should send 'false' as trululu value"
                    );
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        await testUtils.fields.editSelect(form.$(".o_form_view select"), "false");
        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.skip("field selection with many2ones and special characters", async function (assert) {
        assert.expect(1);

        // edit the partner with id=4
        this.data.partner.records[2].display_name = "<span>hey</span>";
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="trululu" widget="selection"/>' +
                "</form>",
            res_id: 1,
            viewOptions: { mode: "edit" },
        });
        assert.strictEqual(form.$('select option[value="4"]').text(), "<span>hey</span>");

        form.destroy();
    });

    QUnit.skip(
        "SelectionField on a many2one: domain updated by an onchange",
        async function (assert) {
            assert.expect(4);

            this.data.partner.onchanges = {
                int_field: function () {},
            };

            var domain = [];
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="int_field"/>' +
                    '<field name="trululu" widget="selection"/>' +
                    "</form>",
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "onchange") {
                        domain = [["id", "in", [10]]];
                        return Promise.resolve({
                            domain: {
                                trululu: domain,
                            },
                        });
                    }
                    if (args.method === "name_search") {
                        assert.deepEqual(args.args[1], domain, "sent domain should be correct");
                    }
                    return this._super(route, args);
                },
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.containsN(
                form,
                ".o_field_widget[name=trululu] option",
                4,
                "should be 4 options in the selection"
            );

            // trigger an onchange that will update the domain
            await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), 2);

            assert.containsOnce(
                form,
                ".o_field_widget[name=trululu] option",
                "should be 1 option in the selection"
            );

            form.destroy();
        }
    );

    QUnit.skip("required selection widget should not have blank option", async function (assert) {
        assert.expect(12);

        this.data.partner.fields.feedback_value = {
            type: "selection",
            required: true,
            selection: [
                ["good", "Good"],
                ["bad", "Bad"],
            ],
            default: "good",
            string: "Good",
        };
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="feedback_value"/>' +
                "<field name=\"color\" attrs=\"{'required': [('feedback_value', '=', 'bad')]}\"/>" +
                "</form>",
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        var $colorField = form.$(".o_field_widget[name=color]");
        assert.containsN($colorField, "option", 3, "Three options in non required field");

        assert.hasAttrValue(
            $colorField.find("option:first()"),
            "style",
            "",
            "Should not have display=none"
        );
        assert.hasAttrValue(
            $colorField.find("option:eq(1)"),
            "style",
            "",
            "Should not have display=none"
        );
        assert.hasAttrValue(
            $colorField.find("option:eq(2)"),
            "style",
            "",
            "Should not have display=none"
        );

        const $requiredSelect = form.$(".o_field_widget[name=feedback_value]");

        assert.containsN($requiredSelect, "option", 3, "Three options in required field");
        assert.hasAttrValue(
            $requiredSelect.find("option:first()"),
            "style",
            "display: none",
            "Should have display=none"
        );
        assert.hasAttrValue(
            $requiredSelect.find("option:eq(1)"),
            "style",
            "",
            "Should not have display=none"
        );
        assert.hasAttrValue(
            $requiredSelect.find("option:eq(2)"),
            "style",
            "",
            "Should not have display=none"
        );

        // change value to update widget modifier values
        await testUtils.fields.editSelect($requiredSelect, '"bad"');
        $colorField = form.$(".o_field_widget[name=color]");

        assert.containsN($colorField, "option", 3, "Three options in required field");
        assert.hasAttrValue(
            $colorField.find("option:first()"),
            "style",
            "display: none",
            "Should have display=none"
        );
        assert.hasAttrValue(
            $colorField.find("option:eq(1)"),
            "style",
            "",
            "Should not have display=none"
        );
        assert.hasAttrValue(
            $colorField.find("option:eq(2)"),
            "style",
            "",
            "Should not have display=none"
        );

        form.destroy();
    });
});
