/** @odoo-module **/

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import {
    click,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date" },
                        display_name: { string: "Displayed name", type: "char" },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                        },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            int_field: false,
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80 },
                        { id: 5, bar: false, foo: "blop", int_field: -4 },
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
            },
        };

        setupViewRegistries();
    });

    QUnit.module("DomainField");

    QUnit.test(
        "The domain editor should not crash the view when given a dynamic filter",
        async function (assert) {
            // dynamic filters (containing variables, such as uid, parent or today)
            // are not handled by the domain editor, but it shouldn't crash the view
            serverData.models.partner.records[0].foo = `[("int_field", "=", uid)]`;

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="foo" widget="domain" options="{'model': 'partner'}" />
                        <field name="int_field" invisible="1" />
                    </form>`,
            });

            assert.strictEqual(
                target.querySelector(".o_read_mode").textContent,
                "This domain is not supported.",
                "The widget should not crash the view, but gracefully admit its failure."
            );
        }
    );

    QUnit.test("basic domain field usage is ok", async function (assert) {
        serverData.models.partner.records[0].foo = "[]";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="domain" options="{'model': 'partner_type'}" />
                        </group>
                    </sheet>
                </form>`,
        });
        await click(target, ".o_form_button_edit");

        // As the domain is empty, there should be a button to add the first
        // domain part
        assert.containsOnce(
            target,
            ".o_domain_add_first_node_button",
            "there should be a button to create first domain element"
        );

        // Clicking on the button should add the [["id", "=", "1"]] domain, so
        // there should be a field selector in the DOM
        await click(target, ".o_domain_add_first_node_button");
        assert.containsOnce(target, ".o_field_selector", "there should be a field selector");

        // Focusing the field selector input should open the field selector
        // popover
        await click(target, ".o_field_selector");
        assert.containsOnce(
            document.body,
            ".o_field_selector_popover",
            "field selector popover should be visible"
        );
        assert.containsOnce(
            document.body,
            ".o_field_selector_search input",
            "field selector popover should contain a search input"
        );

        // The popover should contain the list of partner_type fields and so
        // there should be the "Color index" field
        assert.strictEqual(
            document.body.querySelector(".o_field_selector_item").textContent,
            "Color index",
            "field selector popover should contain 'Color index' field"
        );

        // Clicking on this field should close the popover, then changing the
        // associated value should reveal one matched record
        await click(document.body.querySelector(".o_field_selector_item"));

        const input = target.querySelector(".o_domain_leaf_value_input");
        input.value = 2;
        await triggerEvent(input, null, "change");

        assert.strictEqual(
            target.querySelector(".o_domain_show_selection_button").textContent.trim().substr(0, 2),
            "1 ",
            "changing color value to 2 should reveal only one record"
        );

        // Saving the form view should show a readonly domain containing the
        // "color" field
        await click(target, ".o_form_button_save");
        assert.ok(
            target.querySelector(".o_field_domain").textContent.includes("Color index"),
            "field selector readonly value should now contain 'Color index'"
        );
    });

    QUnit.test("domain field is correctly reset on every view change", async function (assert) {
        serverData.models.partner.records[0].foo = `[("id", "=", 1)]`;
        serverData.models.partner.fields.bar.type = "char";
        serverData.models.partner.records[0].bar = "product";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="bar" />
                            <field name="foo" widget="domain" options="{'model': 'bar'}" />
                        </group>
                    </sheet>
                </form>`,
        });
        await click(target, ".o_form_button_edit");

        // As the domain is equal to [["id", "=", 1]] there should be a field
        // selector to change this
        assert.containsOnce(
            target,
            ".o_field_domain .o_field_selector",
            "there should be a field selector"
        );

        // Focusing its input should open the field selector popover
        await click(target.querySelector(".o_field_selector"));
        assert.containsOnce(
            document.body,
            ".o_field_selector_popover",
            "field selector popover should be visible"
        );

        // As the value of the "bar" field is "product", the field selector
        // popover should contain the list of "product" fields
        assert.containsOnce(
            document.body,
            ".o_field_selector_item",
            "field selector popover should contain only one field"
        );
        assert.strictEqual(
            document.body.querySelector(".o_field_selector_item").textContent,
            "Product Name",
            "field selector popover should contain 'Product Name' field"
        );

        // Now change the value of the "bar" field to "partner_type"
        await editInput(target, ".o_field_widget[name='bar'] input", "partner_type");

        // Refocusing the field selector input should open the popover again
        await click(target.querySelector(".o_field_selector"));
        assert.containsOnce(
            document.body,
            ".o_field_selector_popover",
            "field selector popover should be visible"
        );

        // Now the list of fields should be the ones of the "partner_type" model
        assert.containsN(
            document.body,
            ".o_field_selector_item",
            2,
            "field selector popover should contain two fields"
        );
        assert.strictEqual(
            document.body.querySelector(".o_field_selector_item").textContent,
            "Color index",
            "field selector popover should contain 'Color index' field"
        );
    });

    QUnit.test(
        "domain field can be reset with a new domain (from onchange)",
        async function (assert) {
            serverData.models.partner.records[0].foo = "[]";
            serverData.models.partner.onchanges = {
                display_name(obj) {
                    obj.foo = `[("id", "=", 1)]`;
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="display_name" />
                        <field name="foo" widget="domain" options="{'model': 'partner'}" />
                    </form>`,
            });
            await click(target, ".o_form_button_edit");

            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "5 record(s)",
                "the domain being empty, there should be 5 records"
            );

            // update display_name to trigger the onchange and reset foo
            await editInput(target, ".o_field_widget[name='display_name'] input", "new value");
            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "1 record(s)",
                "the domain has changed, there should be only 1 record"
            );
        }
    );

    QUnit.test("domain field: handle false domain as []", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].foo = false;
        serverData.models.partner.fields.bar.type = "char";
        serverData.models.partner.records[0].bar = "product";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="bar" />
                            <field name="foo" widget="domain" options="{'model': 'bar'}" />
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, { args, method }) {
                if (method === "search_count") {
                    assert.deepEqual(args[0], [], "should send a valid domain");
                }
            },
        });
        assert.containsOnce(
            target,
            ".o_field_widget[name='foo']:not(.o_field_empty)",
            "there should be a domain field, not considered empty"
        );

        await click(target, ".o_form_button_edit");
        assert.containsNone(
            target,
            ".o_field_widget[name='foo'] .text-warning",
            "should not display that the domain is invalid"
        );
    });

    QUnit.test("basic domain field: show the selection", async function (assert) {
        serverData.models.partner.records[0].foo = "[]";
        serverData.views = {
            "partner_type,false,list": `<tree><field name="display_name" /></tree>`,
            "partner_type,false,search": `<search><field name="name" string="Name" /></search>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="domain" options="{'model': 'partner_type'}" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.equal(
            target.querySelector(".o_domain_show_selection_button").textContent.trim().substr(0, 2),
            "2 ",
            "selection should contain 2 records"
        );

        // open the selection
        await click(target, ".o_domain_show_selection_button");
        assert.strictEqual(
            target.querySelectorAll(".modal .o_list_view .o_data_row").length,
            2,
            "should have open a list view with 2 records in a dialog"
        );

        // click on a record -> should not open the record
        // we don't actually check that it doesn't open the record because even
        // if it tries to, it will crash as we don't define an arch in this test
        await click(target, ".modal .o_list_view .o_data_row .o_data_cell[data-tooltip='gold']");
    });

    QUnit.test("field context is propagated when opening selection", async function (assert) {
        serverData.models.partner.records[0].foo = "[]";
        serverData.views = {
            "partner_type,false,list": `<tree><field name="display_name" /></tree>`,
            "partner_type,3,list": `<tree><field name="id" /></tree>`,
            "partner_type,false,search": `<search><field name="name" string="Name" /></search>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" widget="domain" options="{'model': 'partner_type'}" context="{'tree_view_ref': 3}"/>
                </form>`,
        });

        await click(target, ".o_domain_show_selection_button");
        assert.deepEqual(
            [...target.querySelectorAll(".modal .o_data_row")].map((x) => x.textContent),
            ["12", "14"],
            "should have picked the correct list view"
        );
    });

    QUnit.test("domain field: manually edit domain with textarea", async function (assert) {
        patchWithCleanup(odoo, { debug: true });

        serverData.models.partner.records[0].foo = false;
        serverData.models.partner.fields.bar.type = "char";
        serverData.models.partner.records[0].bar = "product";

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
            "partner,false,search": `<search />`,
        };

        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_id: 1,
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
        };

        const webClient = await createWebClient({
            serverData,
            mockRPC(route, { method, args }) {
                if (method === "search_count") {
                    assert.step(JSON.stringify(args[0]));
                }
            },
        });

        await doAction(webClient, 1);
        assert.verifySteps(["[]"]);

        await click(target, ".o_form_button_edit");

        assert.strictEqual(
            target.querySelector(".o_domain_show_selection_button").textContent.trim(),
            "2 record(s)"
        );
        assert.verifySteps(["[]"]);

        await editInput(target, ".o_domain_debug_input", "[['id', '<', 40]]");
        // the count should not be re-computed when editing with the textarea
        assert.strictEqual(
            target.querySelector(".o_domain_show_selection_button").textContent.trim(),
            "2 record(s)"
        );
        assert.verifySteps([]);

        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_domain_show_selection_button").textContent.trim(),
            "1 record(s)"
        );
        assert.verifySteps([
            '[["id","<",40]]', // to validate the domain, before saving
            '[["id","<",40]]', // to render in readonly once it has been saved
        ]);
    });

    QUnit.test(
        "domain field: manually set an invalid domain with textarea",
        async function (assert) {
            patchWithCleanup(odoo, { debug: true });

            serverData.models.partner.records[0].foo = false;
            serverData.models.partner.fields.bar.type = "char";
            serverData.models.partner.records[0].bar = "product";

            serverData.views = {
                "partner,false,form": `
                    <form>
                        <field name="bar"/>
                        <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                    </form>`,
                "partner,false,search": `<search />`,
            };

            serverData.actions = {
                1: {
                    id: 1,
                    name: "test",
                    res_id: 1,
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
            };

            const webClient = await createWebClient({
                serverData,
                mockRPC(route, { method, args }) {
                    if (method === "search_count") {
                        assert.step(JSON.stringify(args[0]));
                    }
                    if (method === "write") {
                        throw new Error("should not save");
                    }
                },
            });

            await doAction(webClient, 1);
            assert.verifySteps(["[]"]);

            await click(target, ".o_form_button_edit");

            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "2 record(s)"
            );
            assert.verifySteps(["[]"]);

            await editInput(target, ".o_domain_debug_input", "[['abc']]");
            // the count should not be re-computed when editing with the textarea
            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "2 record(s)"
            );
            assert.verifySteps([]);

            await click(target, ".o_form_button_save");
            assert.hasClass(
                target.querySelector(".o_field_domain"),
                "o_field_invalid",
                "the field is marked as invalid"
            );
            assert.containsOnce(
                target,
                ".o_form_view .o_form_editable",
                "the view is still in edit mode"
            );
            assert.verifySteps(['[["abc"]]']);
        }
    );

    QUnit.test(
        "domain field: reload count by clicking on the refresh button",
        async function (assert) {
            patchWithCleanup(odoo, { debug: true });

            serverData.models.partner.records[0].foo = "[]";
            serverData.models.partner.fields.bar.type = "char";
            serverData.models.partner.records[0].bar = "product";

            serverData.views = {
                "partner,false,form": `
                    <form>
                        <field name="bar"/>
                        <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                    </form>`,
                "partner,false,search": `<search />`,
            };

            serverData.actions = {
                1: {
                    id: 1,
                    name: "test",
                    res_id: 1,
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
            };

            const webClient = await createWebClient({
                serverData,
                mockRPC(route, { method, args }) {
                    if (method === "search_count") {
                        assert.step(JSON.stringify(args[0]));
                    }
                },
            });

            await doAction(webClient, 1);
            assert.verifySteps(["[]"]);

            await click(target, ".o_form_button_edit");

            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "2 record(s)"
            );

            await editInput(target, ".o_domain_debug_input", "[['id', '<', 40]]");
            // the count should not be re-computed when editing with the textarea
            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "2 record(s)"
            );
            assert.verifySteps(["[]"]);

            // click on the refresh button
            await click(target, ".o_refresh_count");
            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "1 record(s)"
            );
            assert.verifySteps(['[["id","<",40]]']);
        }
    );

    QUnit.test("domain field: does not wait for the count to render", async function (assert) {
        serverData.models.partner.records[0].foo = "[]";
        serverData.models.partner.fields.bar.type = "char";
        serverData.models.partner.records[0].bar = "product";

        const def = makeDeferred();
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
            async mockRPC(route, { method }) {
                if (method === "search_count") {
                    await def;
                }
            },
        });

        assert.containsOnce(target, ".o_field_domain_panel .fa-circle-o-notch.fa-spin");
        assert.containsNone(target, ".o_field_domain_panel .o_domain_show_selection_button");

        def.resolve();
        await nextTick();

        assert.containsNone(target, ".o_field_domain_panel .fa-circle-o-notch .fa-spin");
        assert.containsOnce(target, ".o_field_domain_panel .o_domain_show_selection_button");
        assert.strictEqual(
            target.querySelector(".o_domain_show_selection_button").textContent.trim(),
            "2 record(s)"
        );
    });

    QUnit.test("domain field: edit domain with dynamic content", async function (assert) {
        assert.expect(3);

        patchWithCleanup(odoo, { debug: true });

        let rawDomain = `
            [
                ["date", ">=", datetime.datetime.combine(context_today() + relativedelta(days = -365), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")]
            ]
        `;
        serverData.models.partner.records[0].foo = rawDomain;
        serverData.models.partner.fields.bar.type = "char";
        serverData.models.partner.records[0].bar = "partner";

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
            "partner,false,search": `<search />`,
        };

        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_id: 1,
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
        };

        const webClient = await createWebClient({
            serverData,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.strictEqual(args[1].foo, rawDomain);
                }
            },
        });

        await doAction(webClient, 1);
        await click(target, ".o_form_button_edit");
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);

        rawDomain = `
            [
                ["date", ">=", datetime.datetime.combine(context_today() + relativedelta(days = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")]
            ]
        `;
        await editInput(target, ".o_domain_debug_input", rawDomain);
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);

        await click(target, ".o_form_button_save");
    });

    QUnit.test("domain field: edit through selector (dynamic content)", async function (assert) {
        patchWithCleanup(odoo, { debug: true });

        let rawDomain = `[("date", ">=", context_today())]`;
        serverData.models.partner.records[0].foo = rawDomain;
        serverData.models.partner.fields.bar.type = "char";
        serverData.models.partner.records[0].bar = "partner";

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
            "partner,false,search": `<search />`,
        };

        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_id: 1,
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
        };

        const webClient = await createWebClient({
            serverData,
            mockRPC(route, { method }) {
                assert.step(method || route);
            },
        });
        assert.verifySteps(["/web/webclient/load_menus"]);

        await doAction(webClient, 1);
        assert.verifySteps(["/web/action/load", "get_views", "read", "search_count", "fields_get"]);

        await click(target, ".o_form_button_edit");
        assert.verifySteps(["search_count"]);
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);
        assert.containsOnce(target, ".o_datepicker", "there should be a datepicker");

        // Open and close the datepicker
        await click(target, ".o_datepicker_input");
        assert.containsOnce(document.body, ".bootstrap-datetimepicker-widget");
        await triggerEvent(window, null, "scroll");
        assert.containsNone(document.body, ".bootstrap-datetimepicker-widget");
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);
        assert.verifySteps([]);

        // Save
        await click(target, ".o_form_button_save");
        assert.verifySteps(["search_count"]);

        // Edit again
        await click(target, ".o_form_button_edit");
        assert.verifySteps(["search_count"]);
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);

        // Manually input a date
        rawDomain = `[("date", ">=", "2020-09-09")]`;
        await editInput(target, ".o_datepicker_input", "09/09/2020");
        assert.verifySteps(["search_count"]);
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);

        // Save
        await click(target, ".o_form_button_save");
        assert.verifySteps(["write", "read", "search_count"]);

        // Edit again
        await click(target, ".o_form_button_edit");
        assert.verifySteps(["search_count"]);
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);
    });

    QUnit.test("domain field without model", async function (assert) {
        serverData.models.partner.fields.model_name = { string: "Model name", type: "char" };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="model_name"/>
                    <field name="display_name" widget="domain" options="{'model': 'model_name'}"/>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "search_count") {
                    assert.step(args.model);
                }
            },
        });

        assert.strictEqual(
            target.querySelector('.o_field_widget[name="display_name"]').innerText,
            "Select a model to add a filter.",
            "should contain an error message saying the model is missing"
        );
        assert.verifySteps([]);
        await editInput(target, ".o_field_widget[name=model_name] input", "test");
        assert.notStrictEqual(
            target.querySelector('.o_field_widget[name="display_name"]').innerText,
            "Select a model to add a filter.",
            "should not contain an error message anymore"
        );
        assert.verifySteps(["test"]);
    });

    QUnit.test("domain field in kanban view", async function (assert) {
        serverData.models.partner.records[0].foo = "[]";
        serverData.views = {
            "partner_type,false,list": `<tree><field name="display_name" /></tree>`,
            "partner_type,false,search": `<search><field name="name" string="Name" /></search>`,
        };

        await makeView({
            type: "kanban",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <kanban>
                    <field name="bar" />
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="foo" widget="domain" options="{'model': 'partner_type'}" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            selectRecord: (resId) => {
                assert.step(`open record ${resId}`);
            },
        });

        assert.strictEqual(target.querySelector(".o_read_mode").textContent, "Match all records");

        await click(target.querySelector(".o_domain_show_selection_button"));
        assert.containsOnce(
            target,
            ".o_dialog .o_list_view",
            "selected records are listed in a dialog"
        );

        await click(target.querySelector(".o_domain_selector"));
        assert.verifySteps(
            ["open record 1"],
            "record should not open when clicked on the 'N record(s)' button"
        );
    });

    QUnit.test("domain field with 'inDialog' options", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="display_name" widget="domain" options="{'model': 'partner', 'in_dialog': True}"/>
                </form>`,
        });
        assert.containsNone(target, ".o_domain_leaf");
        assert.containsNone(target, ".modal");
        await click(target, ".o_field_domain_dialog_button");
        assert.containsOnce(target, ".modal");
        await click(target, ".modal .o_domain_add_first_node_button");
        await click(target, ".modal-footer .btn-primary");
        assert.containsOnce(target, ".o_domain_leaf");
        assert.strictEqual(target.querySelector(".o_domain_leaf").textContent, "ID = 1");
    });
});
