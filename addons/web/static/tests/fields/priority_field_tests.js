/** @odoo-module **/

import { registry } from "@web/core/registry";
import { click, getFixture, nextTick, triggerEvent } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

// WOWL remove after adapting tests
let makeLegacyCommandService,
    createWebClient,
    triggerHotkey,
    legacyExtraNextTick,
    doAction,
    core,
    makeTestEnvironment;

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

    QUnit.module("PriorityField");

    QUnit.test("PriorityField when not set", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="selection" widget="priority" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        assert.containsOnce(
            target,
            ".o_field_widget .o_priority:not(.o_field_empty)",
            "widget should be considered set, even though there is no value for this field"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should have no full star since there is no value"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            2,
            "should have two empty stars since there is no value"
        );
    });

    QUnit.test("PriorityField tooltip", async function (assert) {
        assert.expect(2);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `<form string="Partners">
                    <sheet>
                        <group>
                            <field name="selection" widget="priority"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        // check data-tooltip attribute (used by the tooltip service)
        const stars = target.querySelectorAll(".o_field_widget .o_priority a.o_priority_star");
        assert.strictEqual(
            stars[0].dataset["tooltip"],
            "Selection: Blocked",
            "Should set field label and correct selection label as title attribute (tooltip)"
        );
        assert.strictEqual(
            stars[1].dataset["tooltip"],
            "Selection: Done",
            "Should set field label and correct selection label as title attribute (tooltip)"
        );
    });

    QUnit.test("PriorityField in form view", async function (assert) {
        assert.expect(25);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="selection" widget="priority" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        assert.containsOnce(
            target,
            ".o_field_widget .o_priority:not(.o_field_empty)",
            "widget should be considered set"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // hover last star
        let stars = target.querySelectorAll(
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o"
        );
        await triggerEvent(stars[stars.length - 1], null, "mouseenter");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            2,
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should temporary have no empty star since we are hovering the third value"
        );

        await triggerEvent(stars[stars.length - 1], null, "mouseleave");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should temporary have no empty star since we are hovering the third value"
        );

        // switch to edit mode and check the result
        await click(target, ".o_form_button_edit");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should still have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should still have one empty star since the value is the second value"
        );

        // save
        await click(target, ".o_form_button_save");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should still have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should still have one empty star since the value is the second value"
        );

        // switch to edit mode to check that the new value was properly written
        await click(target, ".o_form_button_edit");

        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should still have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should still have one empty star since the value is the second value"
        );

        // click on the second star in edit mode
        stars = target.querySelectorAll(".o_field_widget .o_priority a.o_priority_star.fa-star-o");
        await click(stars[stars.length - 1]);

        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );

        // save
        await click(target, ".o_form_button_save");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );
    });

    QUnit.test("PriorityField in editable list view", async function (assert) {
        assert.expect(25);

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="selection" widget="priority" />
                </tree>
            `,
        });

        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority:not(.o_field_empty)",
            "widget should be considered set"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // switch to edit mode and check the result
        await click(target.querySelector("tbody td:not(.o_list_record_selector)"));

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // save
        await click(target, ".o_list_button_save");

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // hover last star
        await triggerEvent(
            target.querySelector(".o_data_row"),
            ".o_priority a.o_priority_star.fa-star-o",
            "mouseenter"
        );

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            "a.o_priority_star.fa-star",
            2,
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.containsNone(
            target.querySelectorAll(".o_data_row")[0],
            "a.o_priority_star.fa-star-o",
            "should temporary have no empty star since we are hovering the third value"
        );

        // click on the first star in readonly mode
        await click(target.querySelector(".o_priority a.o_priority_star.fa-star"));

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsNone(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should now have no full star since the value is the first value"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            2,
            "should now have two empty stars since the value is the first value"
        );

        // re-enter edit mode to force re-rendering the widget to check if the value was correctly saved
        await click(target.querySelector("tbody td:not(.o_list_record_selector)"));

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsNone(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should now only have no full star since the value is the first value"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            2,
            "should now have two empty stars since the value is the first value"
        );

        // Click on second star in edit mode
        let stars = target.querySelectorAll(".o_priority a.o_priority_star.fa-star-o");
        await click(stars[stars.length - 1]);

        let rows = target.querySelectorAll(".o_data_row");
        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );

        // save
        await click(target, ".o_list_button_save");
        rows = target.querySelectorAll(".o_data_row");

        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );
    });

    QUnit.test("PriorityField with readonly attribute", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: '<form><field name="selection" widget="priority" readonly="1"/></form>',
            mockRPC(route, args) {
                if (args.method === "write") {
                    throw new Error("should not save");
                }
            },
        });

        assert.containsN(
            target,
            "span.o_priority_star.fa.fa-star-o",
            2,
            "stars of priority widget should rendered with span tag if readonly"
        );

        await click(target.querySelectorAll(".o_priority_star.fa-star-o")[1]);

        assert.containsN(
            target,
            "span.o_priority_star.fa.fa-star-o",
            2,
            "should still have two stars"
        );
    });

    QUnit.skipWOWL(
        'PriorityField edited by the smart action "Set priority..."',
        async function (assert) {
            assert.expect(4);

            const legacyEnv = makeTestEnvironment({ bus: core.bus });
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

            const views = {
                "partner,false,form":
                    "<form>" + '<field name="selection" widget="priority"/>' + "</form>",
                "partner,false,search": "<search></search>",
            };
            const serverData = { models: this.data, views };
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                res_id: 1,
                type: "ir.actions.act_window",
                target: "current",
                res_model: "partner",
                view_mode: "form",
                views: [[false, "form"]],
            });
            assert.containsOnce(webClient, ".fa-star");

            triggerHotkey("control+k");
            await nextTick();
            const idx = [...webClient.el.querySelectorAll(".o_command")]
                .map((el) => el.textContent)
                .indexOf("Set priority...ALT + R");
            assert.ok(idx >= 0);

            await click([...webClient.el.querySelectorAll(".o_command")][idx]);
            await nextTick();
            assert.deepEqual(
                [...webClient.el.querySelectorAll(".o_command")].map((el) => el.textContent),
                ["Normal", "Blocked", "Done"]
            );
            await click(webClient.el, "#o_command_2");
            await legacyExtraNextTick();
            assert.containsN(webClient, ".fa-star", 2);
        }
    );
});
