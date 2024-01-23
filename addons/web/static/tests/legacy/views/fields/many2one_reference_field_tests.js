/** @odoo-module alias=@web/../tests/views/fields/many2one_reference_field_tests default=false */

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

import {
    click,
    clickOpenedDropdownItem,
    clickSave,
    editInput,
    getFixture,
    getNodesTextContent,
    patchWithCleanup,
    selectDropdownItem,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        model: {
                            string: "Resource Model",
                            type: "char",
                        },
                        res_id: {
                            string: "Resource Id",
                            type: "many2one_reference",
                            model_field: "model",
                        },
                    },
                    records: [
                        { id: 1, model: "partner_type", res_id: 10 },
                        { id: 2, res_id: false },
                    ],
                },
                partner_type: {
                    fields: {
                        display_name: {
                            string: "Display name",
                            type: "char",
                        },
                    },
                    records: [
                        { id: 10, display_name: "gold" },
                        { id: 14, display_name: "silver" },
                    ],
                },
            },
        };

        setupViewRegistries();

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("Many2OneReferenceField");

    QUnit.test("Many2OneReferenceField in form view", async function (assert) {
        const fakeActionService = {
            dependencies: [],
            start() {
                return {
                    doAction() {
                        assert.step("doAction");
                    },
                };
            },
        };
        registry.category("services").add("action", fakeActionService, { force: true });

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="model" invisible="1"/>
                    <field name="res_id"/>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "get_formview_action") {
                    assert.step(`opening ${args.model} ${args.args[0][0]}`);
                    return false;
                }
            },
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "gold");
        assert.containsOnce(target, ".o_field_widget[name=res_id] .o_external_button");

        await click(target.querySelector(".o_field_widget[name=res_id] .o_external_button"));
        assert.verifySteps(["opening partner_type 10", "doAction"]);
    });

    QUnit.test("Many2OneReferenceField in list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <list>
                    <field name="model" column_invisible="1"/>
                    <field name="res_id"/>
                </list>`,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "gold",
            "",
        ]);
    });

    QUnit.test("Many2OneReferenceField with no_open option", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="model" invisible="1"/>
                    <field name="res_id" options="{'no_open': 1}"/>
                </form>`,
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "gold");
        assert.containsNone(target, ".o_field_widget[name=res_id] .o_external_button");
    });

    QUnit.test("Many2OneReferenceField edition: unset", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `
                <form>
                    <field name="model"/>
                    <field name="res_id"/>
                </form>`,
            mockRPC(route, { method, args }) {
                if (method === "web_save") {
                    assert.deepEqual(args, [[2], { model: "partner_type", res_id: 14 }]);
                }
            },
        });

        assert.containsNone(target.querySelector(".o_field_widget[name=res_id]"), "input");

        await editInput(target, ".o_field_widget[name=model] input", "partner_type");

        assert.containsOnce(target.querySelector(".o_field_widget[name=res_id]"), "input");

        await selectDropdownItem(target, "res_id", "silver");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=res_id] input").value,
            "silver"
        );

        await clickSave(target);
    });

    QUnit.test("Many2OneReferenceField set value with search more", async function (assert) {
        serverData.views = {
            "partner_type,false,list": `<list><field name="display_name"/></list>`,
            "partner_type,false,search": `<search/>`,
        };
        serverData.models.partner_type.records = [
            { id: 1, display_name: "type 1" },
            { id: 2, display_name: "type 2" },
            { id: 3, display_name: "type 3" },
            { id: 4, display_name: "type 4" },
            { id: 5, display_name: "type 5" },
            { id: 6, display_name: "type 6" },
            { id: 7, display_name: "type 7" },
            { id: 8, display_name: "type 8" },
            { id: 9, display_name: "type 9" },
        ];
        serverData.models.partner.records[0].res_id = 1;
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="model" invisible="1"/>
                    <field name="res_id"/>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "type 1");
        await selectDropdownItem(target, "res_id", "Search More...");
        assert.containsOnce(target, ".o_dialog .o_list_view");
        await click(target.querySelectorAll(".o_data_row .o_data_cell")[6]);
        assert.containsNone(target, ".o_dialog .o_list_view");
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "type 7");
        assert.verifySteps([
            "get_views", // form view
            "web_read", // partner id 1
            "name_search", // many2one
            "get_views", // Search More...
            "web_search_read", // SelectCreateDialog
            "web_read", // read selected value
        ]);
    });

    QUnit.test("Many2OneReferenceField: quick create a value", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="model" invisible="1"/>
                    <field name="res_id"/>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "gold");

        await editInput(target, ".o_field_widget[name='res_id'] input", "new value");
        assert.containsOnce(
            target,
            ".o_field_widget[name='res_id'] .dropdown-menu .o_m2o_dropdown_option_create"
        );

        await clickOpenedDropdownItem(target, "res_id", `Create "new value"`);
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "new value");
        assert.verifySteps(["get_views", "web_read", "name_search", "name_create"]);
    });

    QUnit.test("Many2OneReferenceField with no_create option", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="model" invisible="1"/>
                    <field name="res_id" options="{'no_create': 1}"/>
                </form>`,
        });

        await editInput(target, ".o_field_widget[name='res_id'] input", "new value");
        assert.containsNone(
            target,
            ".o_field_widget[name='res_id'] .dropdown-menu .o_m2o_dropdown_option_create"
        );
    });
});
