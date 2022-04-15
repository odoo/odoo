/** @odoo-module **/

import { makeView, setupViewRegistries } from "../views/helpers";
import {
    click,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "../helpers/utils";

let serverData;
let target;

// WOWL remove after adapting tests
let testUtils;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
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

    QUnit.module("DomainField");

    QUnit.test(
        "The domain editor should not crash the view when given a dynamic filter",
        async function (assert) {
            //dynamic filters (containing variables, such as uid, parent or today)
            //are not handled by the domain editor, but it shouldn't crash the view
            assert.expect(1);

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
                    </form>
                `,
            });

            assert.strictEqual(
                target.querySelector(".o_read_mode").textContent,
                "This domain is not supported.",
                "The widget should not crash the view, but gracefully admit its failure."
            );
        }
    );

    QUnit.test("basic domain field usage is ok", async function (assert) {
        assert.expect(7);

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
                </form>
            `,
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
        assert.expect(7);

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
                </form>
            `,
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
        const input = target.querySelector(".o_field_widget[name='bar'] input");
        await click(input);
        input.value = "partner_type";
        await triggerEvent(input, null, "change");

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
            assert.expect(2);

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
                    </form>
                `,
            });
            await click(target, ".o_form_button_edit");

            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "5 record(s)",
                "the domain being empty, there should be 5 records"
            );

            // update display_name to trigger the onchange and reset foo
            const input = target.querySelector(".o_field_widget[name='display_name'] input");
            input.value = "new value";
            await triggerEvent(input, null, "change");

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
                </form>
            `,
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
        assert.expect(2);

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
                </form>
            `,
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
        await click(target, ".modal .o_list_view .o_data_row .o_data_cell[title='gold']");
    });

    QUnit.test("field context is propagated when opening selection", async function (assert) {
        assert.expect(1);

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
                </form>
            `,
        });

        await click(target, ".o_domain_show_selection_button");
        assert.deepEqual(
            [...target.querySelectorAll(".modal .o_data_row")].map((x) => x.textContent),
            ["12", "14"],
            "should have picked the correct list view"
        );
    });

    QUnit.skipWOWL("domain field: manually edit domain with textarea", async function (assert) {
        assert.expect(9);

        patchWithCleanup(odoo, { debug: true });

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
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>
            `,
            mockRPC(route, { method, args }) {
                if (method === "search_count") {
                    assert.step(JSON.stringify(args[0]));
                }
            },
        });
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

    QUnit.skipWOWL(
        "domain field: manually set an invalid domain with textarea",
        async function (assert) {
            assert.expect(9);

            patchWithCleanup(odoo, { debug: true });

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
                        <field name="bar"/>
                        <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                    </form>
                `,
                mockRPC(route, { method, args }) {
                    if (method === "search_count") {
                        assert.step(JSON.stringify(args[0]));
                    }
                    if (method === "write") {
                        throw new Error("should not save");
                    }
                },
            });
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
            assert.hasClass(
                target.querySelector(".o_form_view"),
                "o_form_editable",
                "the view is still in edit mode"
            );
            assert.verifySteps(['[["abc"]]']);
        }
    );

    QUnit.skipWOWL(
        "domain field: reload count by clicking on the refresh button",
        async function (assert) {
            assert.expect(7);

            patchWithCleanup(odoo, { debug: true });

            serverData.models.partner.records[0].foo = "[]";
            serverData.models.partner.fields.bar.type = "char";
            serverData.models.partner.records[0].bar = "product";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                    </form>
                `,
                mockRPC(route, { method, args }) {
                    if (method === "search_count") {
                        assert.step(JSON.stringify(args[0]));
                    }
                },
            });
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
            await testUtils.dom.click(target.querySelector(".o_refresh_count"));
            assert.strictEqual(
                target.querySelector(".o_domain_show_selection_button").textContent.trim(),
                "1 record(s)"
            );
            assert.verifySteps(['[["id","<",40]]']);
        }
    );

    QUnit.test("domain field: does not wait for the count to render", async function (assert) {
        assert.expect(5);

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
                </form>
            `,
            async mockRPC(route, { method }, performRPC) {
                const result = performRPC(...arguments);
                if (method === "search_count") {
                    await def;
                }
                return result;
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

    QUnit.skipWOWL("domain field: edit domain with dynamic content", async function (assert) {
        assert.expect(2);

        patchWithCleanup(odoo, { debug: true });

        let rawDomain = `
            [
                ["date", ">=", datetime.datetime.combine(context_today() + relativedelta(days = -365), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")]
            ]
        `;
        serverData.models.partner.records[0].foo = rawDomain;
        serverData.models.partner.fields.bar.type = "char";
        serverData.models.partner.records[0].bar = "partner";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.strictEqual(args[1].foo, rawDomain);
                }
            },
        });
        await click(target, ".o_form_button_edit");

        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, rawDomain);

        rawDomain = `
            [
                ["date", ">=", datetime.datetime.combine(context_today() + relativedelta(days = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")]
            ]
        `;
        await editInput(target, ".o_domain_debug_input", rawDomain);
        await click(target, ".o_form_button_save");
    });
});
