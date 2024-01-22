/** @odoo-module **/

import {editInput, getFixture} from "@web/../tests/helpers/utils";
import {makeView, setupViewRegistries} from "@web/../tests/views/helpers";
const {QUnit} = window;

let serverData = {};
let target = getFixture();

QUnit.module("web_widget_dropdown_dynamic", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                "sale.order": {
                    fields: {
                        content_string: {string: "Content", type: "char"},
                        bool_field: {string: "Boolean", type: "boolean"},
                        content_integer: {string: "Integer", type: "integer"},
                        change_field: {string: "Change", type: "char"},
                        content_selection: {
                            string: "Selection",
                            type: "selection",
                            selection: [["default", "Default"]],
                        },
                    },
                    records: [
                        {id: 1, bool_field: false, change_field: ""},
                        {id: 2, bool_field: true, change_field: ""},
                    ],
                    methods: {
                        method_name() {
                            return Promise.resolve([["value a", "Value A"]]);
                        },
                    },
                },
            },
        };
        setupViewRegistries();
    });
    QUnit.test("values are fetched with changing context", async function (assert) {
        assert.expect(13);

        await makeView({
            type: "form",
            resModel: "sale.order",
            serverData,
            arch: `
                <form>
                    <field name="change_field"/>
                    <field name="content_string" widget="dynamic_dropdown" options="{'values':'method_name'}" context="{'depending_on': change_field}" />
                </form>`,
            resId: 1,
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === "method_name") {
                    if (args.kwargs.context.depending_on === "step-1") {
                        return Promise.resolve([["value", "Title"]]);
                    } else if (args.kwargs.context.depending_on === "step-2") {
                        return Promise.resolve([
                            ["value", "Title"],
                            ["value_2", "Title 2"],
                        ]);
                    }
                    return Promise.resolve([]);
                }
            },
        });

        await editInput(target, ".o_field_widget[name='change_field'] input", "step-1");
        assert.containsN(target, "option", 2);
        assert.containsOnce(target, "option[value='\"value\"']");
        await editInput(target, ".o_field_widget[name='change_field'] input", "step-2");

        assert.containsN(target, "option", 3);
        assert.containsOnce(target, "option[value='\"value\"']");
        assert.containsOnce(target, "option[value='\"value_2\"']");
        await editInput(
            target,
            ".o_field_widget[name='change_field'] input",
            "step-other"
        );

        assert.containsN(target, "option", 1);
        assert.verifySteps([
            "get_views",
            "read",
            "method_name",
            "method_name",
            "method_name",
            "method_name",
        ]);
    });
    QUnit.test("values are fetched w/o context (char)", async (assert) => {
        assert.expect(6);
        console.log("Start assert", serverData);
        console.log("Start makeView");
        await makeView({
            type: "form",
            resModel: "sale.order",
            serverData,
            arch: `
                <form>
                    <field name="bool_field"/>
                    <field name="content_string" widget="dynamic_dropdown" options="{'values':'method_name'}" context="{'depending_on': bool_field}" />
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "method_name") {
                    if (args.kwargs.context.depending_on) {
                        return Promise.resolve([["value b", "Value B"]]);
                    }
                }
            },
        });
        const field_target = target.querySelector("div[name='content_string']");
        assert.verifySteps(["get_views", "read", "method_name"]);
        assert.containsN(field_target, "option", 2);
        assert.containsOnce(
            field_target,
            "option[value='\"value b\"']",
            "got `value b` "
        );

        console.log("Ending makeView", target);
    });

    QUnit.test("values are fetched w/o context (integer)", async (assert) => {
        assert.expect(6);
        await makeView({
            type: "form",
            resModel: "sale.order",
            serverData,
            arch: `
                <form>
                    <field name="bool_field"/>
                    <field name="content_integer" widget="dynamic_dropdown" options="{'values':'method_name'}" context="{'depending_on': bool_field}" />
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "method_name") {
                    if (args.kwargs.context.depending_on) {
                        return Promise.resolve([["10", "Value B"]]);
                    }
                }
            },
        });
        const field_target = target.querySelector("div[name='content_integer']");
        assert.verifySteps(["get_views", "read", "method_name"]);
        assert.containsN(field_target, "option", 2);
        assert.containsOnce(field_target, 'option[value="10"]');
    });

    QUnit.test("values are fetched w/o context (selection)", async (assert) => {
        assert.expect(6);
        await makeView({
            type: "form",
            resModel: "sale.order",
            serverData,
            arch: `
                <form>
                    <field name="bool_field"/>
                    <field name="content_selection" widget="dynamic_dropdown" options="{'values':'method_name'}" context="{'depending_on': bool_field}" />
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "method_name") {
                    if (args.kwargs.context.depending_on) {
                        return Promise.resolve([["choice b", "Choice B"]]);
                    }
                }
            },
        });
        const field_target = target.querySelector("div[name='content_selection']");
        assert.verifySteps(["get_views", "read", "method_name"]);
        assert.containsN(field_target, "option", 2);
        assert.containsOnce(field_target, "option[value='\"choice b\"']");
    });
});
