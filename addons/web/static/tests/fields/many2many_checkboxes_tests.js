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

    QUnit.module("Many2ManyCheckBoxesField");

    QUnit.skip("Many2ManyCheckBoxesField", async function (assert) {
        assert.expect(10);

        this.data.partner.records[0].timmy = [12];
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<group><field name="timmy" widget="many2many_checkboxes"/></group>' +
                "</form>",
            res_id: 1,
        });

        assert.containsN(
            form,
            "div.o_field_widget div.custom-checkbox",
            2,
            "should have fetched and displayed the 2 values of the many2many"
        );

        assert.ok(
            form.$("div.o_field_widget div.custom-checkbox input").eq(0).prop("checked"),
            "first checkbox should be checked"
        );
        assert.notOk(
            form.$("div.o_field_widget div.custom-checkbox input").eq(1).prop("checked"),
            "second checkbox should not be checked"
        );

        assert.notOk(
            form.$("div.o_field_widget div.custom-checkbox input").prop("disabled"),
            "the checkboxes should not be disabled"
        );

        await testUtils.form.clickEdit(form);

        assert.notOk(
            form.$("div.o_field_widget div.custom-checkbox input").prop("disabled"),
            "the checkboxes should not be disabled"
        );

        // add a m2m value by clicking on input
        await testUtils.dom.click(form.$("div.o_field_widget div.custom-checkbox input").eq(1));
        await testUtils.form.clickSave(form);
        assert.deepEqual(
            this.data.partner.records[0].timmy,
            [12, 14],
            "should have added the second element to the many2many"
        );
        assert.containsN(form, "input:checked", 2, "both checkboxes should be checked");

        // remove a m2m value by clinking on label
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$("div.o_field_widget div.custom-checkbox > label").eq(0));
        await testUtils.form.clickSave(form);
        assert.deepEqual(
            this.data.partner.records[0].timmy,
            [14],
            "should have removed the first element to the many2many"
        );
        assert.notOk(
            form.$("div.o_field_widget div.custom-checkbox input").eq(0).prop("checked"),
            "first checkbox should be checked"
        );
        assert.ok(
            form.$("div.o_field_widget div.custom-checkbox input").eq(1).prop("checked"),
            "second checkbox should not be checked"
        );

        form.destroy();
    });

    QUnit.skip("Many2ManyCheckBoxesField (readonly)", async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form string="Partners">
                    <group>
                        <field name="timmy" widget="many2many_checkboxes"
                            attrs="{'readonly': true}"/>
                    </group>
                </form>`,
            res_id: 1,
        });

        assert.containsN(
            form,
            "div.o_field_widget div.custom-checkbox",
            2,
            "should have fetched and displayed the 2 values of the many2many"
        );

        assert.ok(
            form.$("div.o_field_widget div.custom-checkbox input").eq(0).prop("checked"),
            "first checkbox should be checked"
        );
        assert.notOk(
            form.$("div.o_field_widget div.custom-checkbox input").eq(1).prop("checked"),
            "second checkbox should not be checked"
        );

        assert.ok(
            form.$("div.o_field_widget div.custom-checkbox input").prop("disabled"),
            "the checkboxes should be disabled"
        );

        await testUtils.form.clickEdit(form);

        assert.ok(
            form.$("div.o_field_widget div.custom-checkbox input").prop("disabled"),
            "the checkboxes should be disabled"
        );

        await testUtils.dom.click(form.$("div.o_field_widget div.custom-checkbox > label").eq(1));

        assert.ok(
            form.$("div.o_field_widget div.custom-checkbox input").eq(0).prop("checked"),
            "first checkbox should be checked"
        );
        assert.notOk(
            form.$("div.o_field_widget div.custom-checkbox input").eq(1).prop("checked"),
            "second checkbox should not be checked"
        );

        form.destroy();
    });

    QUnit.skip(
        "Many2ManyCheckBoxesField: start non empty, then remove twice",
        async function (assert) {
            assert.expect(2);

            this.data.partner.records[0].timmy = [12, 14];
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<group><field name="timmy" widget="many2many_checkboxes"/></group>' +
                    "</form>",
                res_id: 1,
                viewOptions: { mode: "edit" },
            });

            await testUtils.dom.click(form.$("div.o_field_widget div.custom-checkbox input").eq(0));
            await testUtils.dom.click(form.$("div.o_field_widget div.custom-checkbox input").eq(1));
            await testUtils.form.clickSave(form);
            assert.notOk(
                form.$("div.o_field_widget div.custom-checkbox input").eq(0).prop("checked"),
                "first checkbox should not be checked"
            );
            assert.notOk(
                form.$("div.o_field_widget div.custom-checkbox input").eq(1).prop("checked"),
                "second checkbox should not be checked"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "Many2ManyCheckBoxesField: values are updated when domain changes",
        async function (assert) {
            assert.expect(5);

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `<form>
                    <field name="int_field"/>
                    <field name="timmy" widget="many2many_checkboxes" domain="[['id', '>', int_field]]"/>
                </form>`,
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.strictEqual(form.$(".o_field_widget[name=int_field]").val(), "10");
            assert.containsN(form, ".o_field_widget[name=timmy] .custom-checkbox", 2);
            assert.strictEqual(
                form.$(".o_field_widget[name=timmy] .o_form_label").text(),
                "goldsilver"
            );

            await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), 13);

            assert.containsOnce(form, ".o_field_widget[name=timmy] .custom-checkbox");
            assert.strictEqual(
                form.$(".o_field_widget[name=timmy] .o_form_label").text(),
                "silver"
            );

            form.destroy();
        }
    );

    QUnit.skip("Many2ManyCheckBoxesField with 40+ values", async function (assert) {
        // 40 is the default limit for x2many fields. However, the many2many_checkboxes is a
        // special field that fetches its data through the fetchSpecialData mechanism, and it
        // uses the name_search server-side limit of 100. This test comes with a fix for a bug
        // that occurred when the user (un)selected a checkbox that wasn't in the 40 first checkboxes,
        // because the piece of data corresponding to that checkbox hadn't been processed by the
        // BasicModel, whereas the code handling the change assumed it had.
        assert.expect(3);

        const records = [];
        for (let id = 1; id <= 90; id++) {
            records.push({
                id,
                display_name: `type ${id}`,
                color: id % 7,
            });
        }
        this.data.partner_type.records = records;
        this.data.partner.records[0].timmy = records.map((r) => r.id);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="timmy" widget="many2many_checkboxes"/></form>',
            res_id: 1,
            async mockRPC(route, args) {
                if (args.method === "write") {
                    const expectedIds = records.map((r) => r.id);
                    expectedIds.pop();
                    assert.deepEqual(args.args[1].timmy, [[6, false, expectedIds]]);
                }
                return this._super(...arguments);
            },
            viewOptions: {
                mode: "edit",
            },
        });

        assert.containsN(form, ".o_field_widget[name=timmy] input[type=checkbox]:checked", 90);

        // toggle the last value
        await testUtils.dom.click(form.$(".o_field_widget[name=timmy] input[type=checkbox]:last"));
        assert.notOk(
            form.$(".o_field_widget[name=timmy] input[type=checkbox]:last").is(":checked")
        );

        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.skip("Many2ManyCheckBoxesField with 100+ values", async function (assert) {
        // The many2many_checkboxes widget limits the displayed values to 100 (this is the
        // server-side name_search limit). This test encodes a scenario where there are more than
        // 100 records in the co-model, and all values in the many2many relationship aren't
        // displayed in the widget (due to the limit). If the user (un)selects a checkbox, we don't
        // want to remove all values that aren't displayed from the relation.
        assert.expect(5);

        const records = [];
        for (let id = 1; id < 150; id++) {
            records.push({
                id,
                display_name: `type ${id}`,
                color: id % 7,
            });
        }
        this.data.partner_type.records = records;
        this.data.partner.records[0].timmy = records.map((r) => r.id);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="timmy" widget="many2many_checkboxes"/></form>',
            res_id: 1,
            async mockRPC(route, args) {
                if (args.method === "write") {
                    const expectedIds = records.map((r) => r.id);
                    expectedIds.shift();
                    assert.deepEqual(args.args[1].timmy, [[6, false, expectedIds]]);
                }
                const result = await this._super(...arguments);
                if (args.method === "name_search") {
                    assert.strictEqual(
                        result.length,
                        100,
                        "sanity check: name_search automatically sets the limit to 100"
                    );
                }
                return result;
            },
            viewOptions: {
                mode: "edit",
            },
        });

        assert.containsN(
            form,
            ".o_field_widget[name=timmy] input[type=checkbox]",
            100,
            "should only display 100 checkboxes"
        );
        assert.ok(form.$(".o_field_widget[name=timmy] input[type=checkbox]:first").is(":checked"));

        // toggle the first value
        await testUtils.dom.click(form.$(".o_field_widget[name=timmy] input[type=checkbox]:first"));
        assert.notOk(
            form.$(".o_field_widget[name=timmy] input[type=checkbox]:first").is(":checked")
        );

        await testUtils.form.clickSave(form);

        form.destroy();
    });
});
