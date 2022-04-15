/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerEvents,
    triggerScroll,
} from "../helpers/utils";
import { applyFilter, toggleAddCustomFilter, toggleFilterMenu } from "../search/helpers";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

// WOWL remove after adapting tests
let createView,
    FormView,
    testUtils,
    cpHelpers,
    Widget,
    BasicModel,
    StandaloneFieldManagerMixin,
    relationalFields;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer", sortable: true },
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
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
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
                        display_name: { string: "Partner Type", type: "char" },
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
            },
        };

        setupViewRegistries();

        patchWithCleanup(AutoComplete, {
            delay: 0,
        });
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("Many2oneField");

    QUnit.test("many2ones in form views", async function (assert) {
        assert.expect(5);

        function createMockActionService(assert) {
            return {
                dependencies: [],
                start() {
                    return {
                        doAction(params) {
                            assert.strictEqual(
                                params.res_id,
                                17,
                                "should do a do_action with correct parameters"
                            );
                        },
                        loadState() {},
                    };
                },
            };
        }
        registry
            .category("services")
            .add("action", createMockActionService(assert), { force: true });

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name" />
                </form>
            `,
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
                            <field name="trululu" string="custom label" />
                        </group>
                    </sheet>
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "get_formview_action") {
                    assert.deepEqual(
                        args[0],
                        [4],
                        "should call get_formview_action with correct id"
                    );
                    return Promise.resolve({
                        res_id: 17,
                        type: "ir.actions.act_window",
                        target: "current",
                        res_model: "res.partner",
                    });
                }
                if (method === "get_formview_id") {
                    assert.deepEqual(args[0], [4], "should call get_formview_id with correct id");
                    return Promise.resolve(false);
                }
            },
        });

        assert.containsOnce(target, "a.o_form_uri:contains(aaa)", "should contain a link");
        await click(target, "a.o_form_uri");

        await click(target, ".o_form_button_edit");

        await click(target, ".o_external_button");
        assert.strictEqual(
            document.body.querySelector(".modal .modal-title").textContent.trim(),
            "Open: custom label",
            "dialog title should display the custom string label"
        );

        // TODO: test that we can edit the record in the dialog, and that
        // the value is correctly updated on close
    });

    QUnit.test("editing a many2one, but not changing anything", async function (assert) {
        assert.expect(2);

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name" />
                </form>
            `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            resIds: [1, 2],
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="trululu" />
                    </sheet>
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "get_formview_id") {
                    assert.deepEqual(args[0], [4], "should call get_formview_id with correct id");
                    return Promise.resolve(false);
                }
            },
        });

        await click(target, ".o_form_button_edit");

        // click on the external button (should do an RPC)
        await click(target, ".o_external_button");
        // save and close modal
        await click(document.body, ".modal .modal-footer .btn-primary");
        // save form
        await click(target, ".o_form_button_save");
        // click next on pager
        await click(target, ".o_pager .o_pager_next");

        // this checks that the view did not ask for confirmation that the
        // record is dirty
        assert.strictEqual(
            target.querySelector(".o_pager").textContent.trim(),
            "2 / 2",
            "pager should be at second page"
        );
    });

    QUnit.test("context in many2one and default get", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.int_field.default = 14;
        serverData.models.partner.fields.trululu.default = 2;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field" />
                    <field name="trululu" context="{'blip': int_field}" options="{'always_reload': 1}" />
                </form>
            `,
            mockRPC(route, { method, kwargs }) {
                if (method === "name_get") {
                    assert.strictEqual(
                        kwargs.context.blip,
                        14,
                        "context should have been properly sent to the nameget rpc"
                    );
                }
            },
        });
    });

    QUnit.test(
        "editing a many2one (with form view opened with external button)",
        async function (assert) {
            assert.expect(1);

            serverData.views = {
                "partner,false,form": `
                    <form>
                        <field name="foo" />
                    </form>
                `,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                resIds: [1, 2],
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="trululu" />
                        </sheet>
                    </form>
                `,
                mockRPC(route, { method }) {
                    if (method === "get_formview_id") {
                        return Promise.resolve(false);
                    }
                },
            });

            await click(target, ".o_form_button_edit");

            // click on the external button (should do an RPC)
            await click(target, ".o_external_button");

            const input = document.body.querySelector(".modal .o_field_widget[name='foo'] input");
            input.value = "brandon";
            await triggerEvent(input, null, "change");

            // save and close modal
            await click(document.body, ".modal .modal-footer .btn-primary");
            // save form
            await click(target, ".o_form_button_save");
            // click next on pager
            await click(target, ".o_pager .o_pager_next");

            // this checks that the view did not ask for confirmation that the
            // record is dirty
            assert.strictEqual(
                target.querySelector(".o_pager").textContent.trim(),
                "2 / 2",
                "pager should be at second page"
            );
        }
    );

    QUnit.test("many2ones in form views with show_address", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="trululu" context="{'show_address': 1}" options="{'always_reload': 1}" />
                        </group>
                    </sheet>
                </form>
            `,
            mockRPC(route, { method }, performRPC) {
                if (method === "name_get") {
                    return performRPC(...arguments).then((result) => {
                        result[0][1] += "\nStreet\nCity ZIP";
                        return result;
                    });
                }
            },
        });

        assert.strictEqual(
            target.querySelector("a.o_form_uri").innerHTML,
            "<span>aaa</span><br><span>Street</span><br><span>City ZIP</span>",
            "input should have a multi-line content in readonly due to show_address"
        );

        await click(target, ".o_form_button_edit");
        assert.strictEqual(target.querySelector("input.o_input").value, "aaa");
        assert.strictEqual(
            target.querySelector(".o_field_many2one_extra").innerHTML,
            "<span>Street</span><br><span>City ZIP</span>"
        );
        assert.containsOnce(
            target,
            "button.o_external_button",
            "should have an open record button"
        );
    });

    QUnit.test("many2one show_address in edit", async function (assert) {
        assert.expect(6);

        const addresses = {
            aaa: "\nAAA\nRecord",
            "first record": "\nFirst\nRecord",
            "second record": "\nSecond\nRecord",
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
                            <field name="trululu" context="{'show_address': 1}" options="{'always_reload': 1}"/>
                        </group>
                    </sheet>
                </form>
            `,
            mockRPC(route, { method }, performRPC) {
                if (method === "name_get") {
                    return performRPC(...arguments).then((result) => {
                        result[0][1] += addresses[result[0][1]];
                        return result;
                    });
                }
            },
        });

        await click(target, ".o_form_button_edit");
        const input = target.querySelector("input");

        assert.strictEqual(input.value, "aaa");
        assert.strictEqual(
            target.querySelector(".o_field_many2one_extra").innerHTML,
            "<span>AAA</span><br><span>Record</span>"
        );

        input.value = "first record";
        await triggerEvent(input, null, "input");
        await click(document.body.querySelector(".dropdown-menu li"));

        assert.strictEqual(input.value, "first record");
        assert.strictEqual(
            target.querySelector(".o_field_many2one_extra").innerHTML,
            "<span>First</span><br><span>Record</span>"
        );

        input.value = "second record";
        await triggerEvent(input, null, "input");
        await click(document.body.querySelector(".dropdown-menu li"));

        assert.strictEqual(input.value, "second record");
        assert.strictEqual(
            target.querySelector(".o_field_many2one_extra").innerHTML,
            "<span>Second</span><br><span>Record</span>"
        );
    });

    QUnit.skipWOWL(
        "show_address works in a view embedded in a view of another type",
        async function (assert) {
            assert.expect(2);

            serverData.models.turtle.records[1].turtle_trululu = 2;
            serverData.views = {
                "turtle,false,form": `
                    <form>
                        <field name="display_name" />
                        <field name="turtle_trululu" context="{'show_address': 1}" options="{'always_reload': 1}" />
                    </form>
                `,
                "turtle,false,list": `
                    <tree>
                        <field name="display_name" />
                    </tree>
                `,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <field name="display_name" />
                        <field name="turtles" />
                    </form>
                `,
                mockRPC(route, { kwargs, method, model }, performRPC) {
                    if (method === "name_get") {
                        return performRPC(...arguments).then((result) => {
                            if (model === "partner" && kwargs.context.show_address) {
                                result[0][1] += "\nrue morgue\nparis 75013";
                            }
                            return result;
                        });
                    }
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            await click(target, ".o_data_row td.o_data_cell");

            assert.strictEqual(
                document.body.querySelector('[name="turtle_trululu"] .o_input').value,
                "second record",
                "many2one value should be displayed in input"
            );
            assert.strictEqual(
                document.body.querySelector('[name="turtle_trululu"] .o_field_many2one_extra')
                    .textContent,
                "rue morgueparis 75013",
                "The partner's address should be displayed"
            );
        }
    );

    QUnit.skipWOWL(
        "many2one data is reloaded if there is a context to take into account",
        async function (assert) {
            assert.expect(2);

            serverData.models.turtle.records[1].turtle_trululu = 2;
            serverData.views = {
                "turtle,false,form": `
                    <form>
                        <field name="display_name" />
                        <field name="turtle_trululu" context="{'show_address': 1}" options="{'always_reload': 1}" />
                    </form>
                `,
                "turtle,false,list": `
                    <tree>
                        <field name="display_name" />
                        <field name="turtle_trululu" />
                    </tree>
                `,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <field name="display_name" />
                        <field name="turtles" />
                    </form>
                `,
                mockRPC(route, { kwargs, method, model }, performRPC) {
                    if (method === "name_get") {
                        return performRPC(...arguments).then((result) => {
                            if (model === "partner" && kwargs.context.show_address) {
                                result[0][1] += "\nrue morgue\nparis 75013";
                            }
                            return result;
                        });
                    }
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            await click(target, ".o_data_row");

            assert.strictEqual(
                document.body.querySelector('.modal [name="turtle_trululu"] .o_input').value,
                "second record",
                "many2one value should be displayed in input"
            );
            assert.strictEqual(
                document.body.querySelector(".modal [name=turtle_trululu] .o_field_many2one_extra")
                    .textContent,
                "rue morgueparis 75013",
                "The partner's address should be displayed"
            );
        }
    );

    QUnit.test("many2ones in form views with search more", async function (assert) {
        assert.expect(3);

        for (let i = 5; i < 11; i++) {
            serverData.models.partner.records.push({ id: i, display_name: `Partner ${i}` });
        }
        serverData.models.partner.fields.datetime.searchable = true;
        serverData.views = {
            "partner,false,search": `
                <search>
                    <field name="datetime" />
                </search>
            `,
            "partner,false,list": `
                <tree>
                    <field name="display_name" />
                </tree>
            `,
        };

        // add custom filter needs this
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="trululu" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        await click(target, ".o_form_button_edit");

        await selectDropdownItem(target, "trululu", "Search More...");

        assert.strictEqual($("tr.o_data_row").length, 9, "should display 9 records");

        const modal = document.body.querySelector(".modal");

        await toggleFilterMenu(modal);
        await toggleAddCustomFilter(modal);
        assert.strictEqual(
            modal.querySelector(".o_generator_menu_field").value,
            "datetime",
            "datetime field should be selected"
        );
        await applyFilter(modal);

        assert.strictEqual($("tr.o_data_row").length, 0, "should display 0 records");
    });

    QUnit.skipWOWL(
        "onchanges on many2ones trigger when editing record in form view",
        async function (assert) {
            assert.expect(10);

            serverData.models.partner.onchanges.user_id = function () {};
            serverData.models.user.fields.other_field = { string: "Other Field", type: "char" };
            serverData.views = {
                "user,false,form": `
                    <form>
                        <field name="other_field" />
                    </form>
                `,
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
                                <field name="user_id" />
                            </group>
                        </sheet>
                    </form>
                `,
                mockRPC(route, { args, method }) {
                    assert.step(method);
                    if (method === "get_formview_id") {
                        return Promise.resolve(false);
                    }
                    if (method === "onchange") {
                        assert.strictEqual(
                            args[1].user_id,
                            17,
                            "onchange is triggered with correct user_id"
                        );
                    }
                },
            });

            // open the many2one in form view and change something
            await click(target, ".o_form_button_edit");
            await click(target, ".o_external_button");
            await testUtils.fields.editInput($('.modal-body input[name="other_field"]'), "wood");

            // save the modal and make sure an onchange is triggered
            await click(document.body, ".modal .modal-footer .btn-primary");
            assert.verifySteps([
                "read",
                "get_formview_id",
                "get_views",
                "read",
                "write",
                "read",
                "onchange",
            ]);

            // save the main record, and check that no extra rpcs are done (record
            // is not dirty, only a related record was modified)
            await click(target, ".o_form_button_save");
            assert.verifySteps([]);
        }
    );

    QUnit.skipWOWL(
        "many2one doesn't trigger field_change when being emptied",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                <tree multi_edit="1">
                    <field name="trululu"/>
                </tree>
            `,
            });

            // Select two records
            await click(target.querySelectorAll(".o_data_row")[0], ".o_list_record_selector input");
            await click(target.querySelectorAll(".o_data_row")[1], ".o_list_record_selector input");

            await click(target.querySelector(".o_data_row .o_data_cell"));

            const $input = target.querySelector(".o_field_widget[name=trululu] input");

            await testUtils.fields.editInput($input, "");
            await testUtils.dom.triggerEvents($input, ["keyup"]);

            assert.containsNone(
                document.body,
                ".modal",
                "No save should be triggered when removing value"
            );

            await testUtils.fields.many2one.clickHighlightedItem("trululu");

            assert.containsOnce(
                document.body,
                ".modal",
                "Saving should be triggered when selecting a value"
            );
            await click(document.body, ".modal .btn-primary");
        }
    );

    QUnit.skipWOWL("focus tracking on a many2one in a list", async function (assert) {
        assert.expect(4);

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="foo" />
                </form>
            `,
        };

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="trululu"/>
                </tree>
            `,
        });

        // Select two records
        await click(target.querySelectorAll(".o_data_row")[0], ".o_list_record_selector input");
        await click(target.querySelectorAll(".o_data_row")[1], ".o_list_record_selector input");

        await click(list, ".o_data_row .o_data_cell");

        const input = list.$(".o_data_row:first() .o_data_cell:first() input")[0];

        assert.strictEqual(document.activeElement, input, "Input should be focused when activated");

        await testUtils.fields.many2one.createAndEdit("trululu", "ABC");

        // At this point, if the focus is correctly registered by the m2o, there
        // should be only one modal (the "Create" one) and none for saving changes.
        assert.containsOnce(document.body, ".modal", "There should be only one modal");

        await click(document.body, ".modal .btn:not(.btn-primary)");

        assert.strictEqual(
            document.activeElement,
            input,
            "Input should be focused after dialog closes"
        );
        assert.strictEqual(input.value, "", "Input should be empty after discard");
    });

    QUnit.test('many2one fields with option "no_open"', async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="trululu" options="{'no_open': 1}" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        assert.containsOnce(
            target,
            ".o_field_widget[name='trululu'] > span",
            "should be displayed inside a span (sanity check)"
        );
        assert.containsNone(target, "span.o_form_uri", "should not have an anchor");

        await click(target, ".o_form_button_edit");
        assert.containsNone(
            target,
            ".o_field_widget[name='trululu'] .o_external_button",
            "should not have the button to open the record"
        );
    });

    QUnit.test("empty many2one field", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="trululu" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        await click(target, ".o_field_many2one input");
        assert.containsNone(
            document.body,
            ".dropdown-menu li.o_m2o_dropdown_option",
            "autocomplete should not contains dropdown options"
        );
        assert.containsOnce(
            document.body,
            ".dropdown-menu li.o_m2o_start_typing",
            "autocomplete should contains start typing option"
        );

        const input = target.querySelector(".o_field_many2one[name='trululu'] input");
        input.value = "abc";
        await triggerEvents(input, null, ["input", "change"]);

        assert.containsN(
            document.body,
            ".dropdown-menu li.o_m2o_dropdown_option",
            2,
            "autocomplete should contains 2 dropdown options"
        );
        assert.containsNone(
            document.body,
            ".dropdown-menu li.o_m2o_start_typing",
            "autocomplete should not contains start typing option"
        );
    });

    QUnit.test("empty many2one field with node options", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="trululu" options="{'no_create_edit': 1}" />
                            <field name="product_id" options="{'no_create_edit': 1, 'no_quick_create': 1}" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        await click(target, ".o_field_many2one[name='trululu'] input");
        assert.containsOnce(
            target.querySelector(".o_field_many2one[name='trululu'] .dropdown-menu"),
            "li.o_m2o_start_typing",
            "autocomplete should contains start typing option"
        );

        await click(target, ".o_field_many2one[name='product_id'] input");
        assert.containsNone(
            target.querySelector(".o_field_many2one[name='product_id'] .dropdown-menu"),
            "li.o_m2o_start_typing",
            "autocomplete should contains start typing option"
        );
    });

    QUnit.skipWOWL(
        "empty many2one should not be considered modified on onchange if still empty",
        async function (assert) {
            assert.expect(6);

            this.data.partner.onchanges = {
                foo: function () {},
            };

            assert.strictEqual(
                this.data.partner.records[2].trululu,
                undefined,
                "no value must be provided for trululu to make sure the test works as expected"
            );

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    "<group>" +
                    '<field name="trululu"/>' +
                    '<field name="foo"/>' + // onchange will be triggered on this field
                    "</group>" +
                    "</sheet>" +
                    "</form>",
                res_id: 4, // trululu m2o must be empty
                viewOptions: { mode: "edit" },
                mockRPC: function (route, args) {
                    if (args.method === "onchange") {
                        assert.step("onchange");
                        return Promise.resolve({
                            value: {
                                trululu: false,
                            },
                        });
                    } else if (args.method === "write") {
                        assert.step("write");
                        // non modified trululu should not be sent
                        // as write value
                        assert.deepEqual(args.args[1], { foo: "3" });
                    }
                    return this._super.apply(this, arguments);
                },
            });

            // trigger the onchange
            await testUtils.fields.editInput($('input[name="foo"]'), "3");
            assert.verifySteps(["onchange"]);

            // save
            await testUtils.form.clickSave(form);
            assert.verifySteps(["write"]);
            form.destroy();
        }
    );

    QUnit.skipWOWL("many2one in edit mode", async function (assert) {
        assert.expect(17);

        // create 10 partners to have the 'Search More' option in the autocomplete dropdown
        for (let i = 0; i < 10; i++) {
            const id = 20 + i;
            serverData.models.partner.records.push({ id, display_name: `Partner ${id}` });
        }

        serverData.views = {
            "partner,false,list": `
                <list>
                    <field name="display_name" />
                </list>
            `,
            "partner,false,search": `
                <search>
                    <field name="display_name" string="Name" />
                </search>
            `,
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="trululu" />
                        </group>
                    </sheet>
                </form>
            `,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(args[1].trululu, 20, "should write the correct id");
                }
            },
        });

        // the SelectCreateDialog requests the session, so intercept its custom
        // event to specify a fake session to prevent it from crashing
        testUtils.mock.intercept(form, "get_session", function (event) {
            event.data.callback({ user_context: {} });
        });

        await click(target, ".o_form_button_edit");

        var $dropdown = target.querySelectorAll(".o_field_many2one input").autocomplete("widget");

        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        assert.ok(
            $dropdown.is(":visible"),
            "clicking on the m2o input should open the dropdown if it is not open yet"
        );
        assert.strictEqual(
            $dropdown.find("li:not(.o_m2o_dropdown_option)").length,
            7,
            "autocomplete should contains 8 suggestions"
        );
        assert.strictEqual(
            $dropdown.find("li.o_m2o_dropdown_option").length,
            1,
            'autocomplete should contain "Search More"'
        );
        assert.containsNone(
            $dropdown,
            "li.o_m2o_start_typing",
            "autocomplete should not contains start typing option if value is available"
        );

        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        assert.ok(
            !$dropdown.is(":visible"),
            "clicking on the m2o input should close the dropdown if it is open"
        );

        // change the value of the m2o with a suggestion of the dropdown
        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        await testUtils.fields.many2one.clickHighlightedItem("trululu");
        assert.ok(!$dropdown.is(":visible"), "clicking on a value should close the dropdown");
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2one input").value,
            "first record",
            "value of the m2o should have been correctly updated"
        );

        // change the value of the m2o with a record in the 'Search More' modal
        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        // click on 'Search More' (mouseenter required by ui-autocomplete)
        await testUtils.fields.many2one.clickItem("trululu", "Search");
        assert.containsOnce(
            document.body,
            ".modal .o_list_view",
            "should have opened a list view in a modal"
        );
        assert.containsNone(
            document.body,
            ".modal .o_list_view .o_list_record_selector",
            "there should be no record selector in the list view"
        );
        assert.containsNone(
            document.body,
            ".modal .modal-footer .o_select_button",
            "there should be no 'Select' button in the footer"
        );
        assert.ok(
            document.body.querySelectorAll(".modal tbody tr").length > 10,
            "list should contain more than 10 records"
        );
        const modal = document.body.querySelector(".modal");
        await cpHelpers.editSearch(modal, "P");
        await cpHelpers.validateSearch(modal);
        assert.containsN(
            document.body,
            ".modal tbody tr",
            10,
            "list should be restricted to records containing a P (10 records)"
        );
        // choose a record
        await click(document.body, ".modal tbody tr:contains(Partner 20)");
        assert.containsNone(document.body, ".modal", "should have closed the modal");
        assert.ok(!$dropdown.is(":visible"), "should have closed the dropdown");
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "Partner 20",
            "value of the m2o should have been correctly updated"
        );

        // save
        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector("a.o_form_uri").textContent,
            "Partner 20",
            "should display correct value after save"
        );
    });

    QUnit.test("many2one in non edit mode", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
        });

        assert.containsOnce(target, "a.o_form_uri", "should display 1 m2o link in form");
        assert.hasAttrValue(
            target.querySelector("a.o_form_uri"),
            "href",
            "#id=4&model=partner",
            "href should contain id and model"
        );

        // Remove value from many2one and then save, there should not have href with id and model on m2o anchor
        await click(target, ".o_form_button_edit");

        const input = target.querySelector(".o_field_many2one input");
        input.value = "";
        await triggerEvent(input, null, "change");

        await click(target, ".o_form_button_save");
        assert.hasAttrValue(
            target.querySelector("a.o_form_uri"),
            "href",
            "#",
            "href should have #"
        );
    });

    QUnit.skipWOWL(
        "many2one with co-model whose name field is a many2one",
        async function (assert) {
            assert.expect(4);

            serverData.models.product.fields.name = {
                string: "User Name",
                type: "many2one",
                relation: "user",
            };

            serverData.views = {
                "product,false,form": `
                <form>
                    <field name="name" />
                </form>
            `,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="product_id" />
                </form>
            `,
            });

            await testUtils.fields.many2one.createAndEdit("product_id", "ABC");
            assert.containsOnce(document.body, ".modal .o_form_view");

            // quick create 'new value'
            await testUtils.fields.many2one.searchAndClickItem("name", { search: "new value" });
            assert.strictEqual(
                document.body.querySelector(".modal .o_field_many2one input").value,
                "new value"
            );

            await click(document.body, ".modal .modal-footer .btn-primary"); // save in modal
            assert.containsNone(document.body, ".modal .o_form_view");
            assert.strictEqual(target.querySelector(".o_field_many2one input").value, "new value");
        }
    );

    QUnit.test("many2one searches with correct value", async function (assert) {
        assert.expect(6);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="trululu" />
                    </sheet>
                </form>
            `,
            mockRPC(route, { method, kwargs }) {
                if (method === "name_search") {
                    assert.step(`search: ${kwargs.name}`);
                }
            },
        });
        await click(target, ".o_form_button_edit");

        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "aaa",
            "should be initially set to 'aaa'"
        );

        const input = target.querySelector(".o_field_many2one input");
        await click(input);

        // unset the many2one -> should search again with ''
        input.value = "";
        await triggerEvents(input, null, ["input", "change"]);

        input.value = "p";
        await triggerEvents(input, null, ["input", "change"]);

        // close and re-open the dropdown -> should search with 'p' again
        await click(input);
        await click(input);

        assert.verifySteps(["search: ", "search: ", "search: p", "search: p"]);
    });

    QUnit.test("many2one search with trailing and leading spaces", async function (assert) {
        assert.expect(10);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>`,
            mockRPC(route, { kwargs, method }) {
                if (method === "name_search") {
                    assert.step("search: " + kwargs.name);
                }
            },
        });

        const input = target.querySelector(".o_field_many2one[name='trululu'] input");
        await click(input);

        const dropdown = target.querySelector(".o_field_many2one[name='trululu'] .dropdown-menu");

        assert.isVisible(dropdown);
        assert.containsN(
            dropdown,
            "li:not(.o_m2o_dropdown_option)",
            4,
            "autocomplete should contains 4 suggestions"
        );

        // search with leading spaces
        input.value = "   first";
        await triggerEvents(input, null, ["input", "change"]);
        assert.containsOnce(
            dropdown,
            "li:not(.o_m2o_dropdown_option)",
            "autocomplete should contains 1 suggestion"
        );

        // search with trailing spaces
        input.value = "first  ";
        await triggerEvents(input, null, ["input", "change"]);
        assert.containsOnce(
            dropdown,
            "li:not(.o_m2o_dropdown_option)",
            "autocomplete should contains 1 suggestion"
        );

        // search with leading and trailing spaces
        input.value = "   first   ";
        await triggerEvents(input, null, ["input", "change"]);
        assert.containsOnce(
            dropdown,
            "li:not(.o_m2o_dropdown_option)",
            "autocomplete should contains 1 suggestion"
        );

        assert.verifySteps(["search: ", "search: first", "search: first", "search: first"]);
    });

    QUnit.test("many2one field with option always_reload", async function (assert) {
        assert.expect(4);

        let count = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <field name="trululu" options="{'always_reload': 1}" />
                </form>
            `,
            mockRPC(route, { method }) {
                if (method === "name_get") {
                    count++;
                    return Promise.resolve([[1, "first record\nand some address"]]);
                }
            },
        });

        assert.strictEqual(count, 1, "an extra name_get should have been done");
        assert.ok(
            target.querySelector("a").textContent.includes("and some address"),
            "should display additional result"
        );

        await click(target, ".o_form_button_edit");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='trululu'] input").value,
            "first record",
            "actual field value should be displayed to be edited"
        );

        await click(target, ".o_form_button_save");
        assert.ok(
            target.querySelector("a").textContent.includes("and some address"),
            "should still display additional result"
        );
    });

    QUnit.skipWOWL("many2one field and list navigation", async function (assert) {
        assert.expect(3);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="trululu"/>
                </tree>
            `,
        });

        // edit first input, to trigger autocomplete
        await click(target, ".o_data_row .o_data_cell");
        await testUtils.fields.editInput(list.$(".o_data_cell input"), "");

        // press keydown, to select first choice
        await testUtils.fields.triggerKeydown(list.$(".o_data_cell input").focus(), "down");

        // we now check that the dropdown is open (and that the focus did not go
        // to the next line)
        var $dropdown = list.$(".o_field_many2one input").autocomplete("widget");
        assert.ok($dropdown.is(":visible"), "dropdown should be visible");
        assert.hasClass(
            target.querySelector(".o_data_row"),
            "o_selected_row",
            "first data row should still be selected"
        );
        assert.doesNotHaveClass(
            target.querySelectorAll(".o_data_row")[1],
            "o_selected_row",
            "second data row should not be selected"
        );
    });

    QUnit.skipWOWL("standalone many2one field", async function (assert) {
        assert.expect(4);

        var model = await testUtils.createModel({
            Model: BasicModel,
            serverData,
        });
        var record;
        model
            .makeRecord("coucou", [
                {
                    name: "partner_id",
                    relation: "partner",
                    type: "many2one",
                    value: [1, "first partner"],
                },
            ])
            .then(function (recordID) {
                record = model.get(recordID);
            });
        await nextTick();
        // create a new widget that uses the StandaloneFieldManagerMixin
        var StandaloneWidget = Widget.extend(StandaloneFieldManagerMixin, {
            init: function (parent) {
                this._super.apply(this, arguments);
                StandaloneFieldManagerMixin.init.call(this, parent);
            },
        });
        var parent = new StandaloneWidget(model);
        model.setParent(parent);
        await testUtils.mock.addMockEnvironment(parent, {
            // data: self.data,
            mockRPC(route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        var relField = new relationalFields.FieldMany2One(parent, "partner_id", record, {
            mode: "edit",
            noOpen: true,
        });

        relField.appendTo(target);
        await nextTick();
        await testUtils.fields.editInput($("input.o_input"), "xyzzrot");

        await testUtils.fields.many2one.clickItem("partner_id", "Create");

        assert.containsNone(
            relField,
            ".o_external_button",
            "should not have the button to open the record"
        );
        assert.verifySteps(["name_search", "name_create"]);
    });

    // QUnit.skipWOWL('onchange on a many2one to a different model', async function (assert) {
    // This test is commented because the mock server does not give the correct response.
    // It should return a couple [id, display_name], but I don't know the logic used
    // by the server, so it's hard to emulate it correctly
    //     assert.expect(2);

    //     serverData.models.partner.records[0].product_id = 41;
    //     serverData.models.partner.onchanges = {
    //         foo: function(obj) {
    //             obj.product_id = 37;
    //         },
    //     };

    //     const form = await makeView({
    //         type: "form",
    //         resModel: "partner",
    //         serverData,
    //         arch: '<form>' +
    //                 '<field name="foo"/>' +
    //                 '<field name="product_id"/>' +
    //             '</form>',
    //         resId: 1,
    //     });
    //     await click(target, ".o_form_button_edit");
    //     assert.strictEqual(target.querySelectorAll('input').eq(1).value, 'xpad', "initial product_id val should be xpad");

    //     testUtils.fields.editInput(target.querySelectorAll('input').eq(0), "let us trigger an onchange");

    //     assert.strictEqual(target.querySelectorAll('input').eq(1).value, 'xphone', "onchange should have been applied");
    // });

    QUnit.skipWOWL("form: quick create then save directly", async function (assert) {
        assert.expect(5);

        const def = makeDeferred();
        let newRecordId;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
            mockRPC(route, { args, method }, performRPC) {
                if (method === "name_create") {
                    assert.step("name_create");
                    return def.then(performRPC(...arguments)).then((nameGet) => {
                        newRecordId = nameGet[0];
                        return nameGet;
                    });
                }
                if (method === "create") {
                    assert.step("create");
                    assert.strictEqual(
                        args[0].trululu,
                        newRecordId,
                        "should create with the correct m2o id"
                    );
                }
            },
        });
        await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "b" });
        await click(target, ".o_form_button_save");

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );

        await def.resolve();
        await nextTick();

        assert.verifySteps(["create"]);
    });

    QUnit.skipWOWL(
        "form: quick create for field that returns false after name_create call",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="trululu" />
                    </form>
                `,
                mockRPC(route, { method }) {
                    if (method === "name_create") {
                        assert.step("name_create");
                        // Resolve the name_create call to false. This is possible if
                        // _rec_name for the model of the field is unassigned.
                        return Promise.resolve(false);
                    }
                },
            });
            await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "beam" });
            assert.verifySteps(["name_create"], "attempt to name_create");
            assert.strictEqual(
                target.querySelectorAll(".o_input_dropdown input").value,
                "",
                "the input should contain no text after search and click"
            );
        }
    );

    QUnit.skipWOWL("list: quick create then save directly", async function (assert) {
        assert.expect(8);

        const def = makeDeferred();
        let newRecordId;

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="trululu" />
                </tree>
            `,
            mockRPC(route, { args, method }, performRPC) {
                if (method === "name_create") {
                    assert.step("name_create");
                    return def.then(performRPC(...arguments)).then((nameGet) => {
                        newRecordId = nameGet[0];
                        return nameGet;
                    });
                }
                if (method === "create") {
                    assert.step("create");
                    assert.strictEqual(
                        args[0].trululu,
                        newRecordId,
                        "should create with the correct m2o id"
                    );
                }
            },
        });

        await click(target, ".o_list_button_add");

        await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "b" });
        list.$buttons.find(".o_list_button_add").show();
        click(target, ".o_list_button_add");

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );
        assert.containsN(
            target,
            ".o_data_row",
            4,
            "should wait for the name_create before adding the new row"
        );

        await def.resolve();
        await nextTick();

        assert.verifySteps(["create"]);
        assert.strictEqual(
            target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell").textContent,
            "b",
            "created row should have the correct m2o value"
        );
        assert.containsN(list, ".o_data_row", 5, "should have added the fifth row");
    });

    QUnit.skipWOWL("list in form: quick create then save directly", async function (assert) {
        assert.expect(6);

        const def = makeDeferred();
        let newRecordId;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="trululu" />
                            </tree>
                        </field>
                    </sheet>
                </form>
            `,
            mockRPC(route, { args, method }, performRPC) {
                if (method === "name_create") {
                    assert.step("name_create");
                    return def.then(performRPC(...arguments)).then((nameGet) => {
                        newRecordId = nameGet[0];
                        return nameGet;
                    });
                }
                if (method === "create") {
                    assert.step("create");
                    assert.strictEqual(
                        args[0].p[0][2].trululu,
                        newRecordId,
                        "should create with the correct m2o id"
                    );
                }
            },
        });

        await click(target, ".o_field_x2many_list_row_add a");
        await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "b" });
        await click(target, ".o_form_button_save");

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );

        await def.resolve();
        await nextTick();

        assert.verifySteps(["create"]);
        assert.strictEqual(
            target.querySelector(".o_data_row .o_data_cell").textContent,
            "b",
            "first row should have the correct m2o value"
        );
    });

    QUnit.skipWOWL(
        "list in form: quick create then add a new line directly",
        async function (assert) {
            // required many2one inside a one2many list: directly after quick creating
            // a new many2one value (before the name_create returns), click on add an item:
            // at this moment, the many2one has still no value, and as it is required,
            // the row is discarded if a saveLine is requested. However, it should
            // wait for the name_create to return before trying to save the line.
            assert.expect(8);

            serverData.models.partner.onchanges = {
                trululu: function () {},
            };

            const def = makeDeferred();
            let newRecordId;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <sheet>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="trululu" required="1" />
                            </tree>
                        </field>
                    </sheet>
                </form>
            `,
                mockRPC(route, { args, method }, performRPC) {
                    if (method === "name_create") {
                        assert.step("name_create");
                        return def.then(performRPC(...arguments)).then((nameGet) => {
                            newRecordId = nameGet[0];
                            return nameGet;
                        });
                    }
                    if (method === "create") {
                        assert.deepEqual(args[0].p[0][2].trululu, newRecordId);
                    }
                },
            });

            await click(target, ".o_field_x2many_list_row_add a");
            await testUtils.fields.editAndTrigger(
                target.querySelectorAll(".o_field_many2one input"),
                "b",
                "keydown"
            );
            await testUtils.fields.many2one.clickHighlightedItem("trululu");
            await click(target, ".o_field_x2many_list_row_add a");

            assert.containsOnce(form, ".o_data_row", "there should still be only one row");
            assert.hasClass(
                target.querySelectorAll(".o_data_row"),
                "o_selected_row",
                "the row should still be in edition"
            );

            await def.resolve();
            await nextTick();

            assert.strictEqual(
                target.querySelector(".o_data_row .o_data_cell").textContent,
                "b",
                "first row should have the correct m2o value"
            );
            assert.containsN(form, ".o_data_row", 2, "there should now be 2 rows");
            assert.hasClass(
                target.querySelectorAll(".o_data_row")[1],
                "o_selected_row",
                "the second row should be in edition"
            );

            await click(target, ".o_form_button_save");

            assert.containsOnce(
                form,
                ".o_data_row",
                "there should be 1 row saved (the second one was empty and invalid)"
            );
            assert.strictEqual(
                target.querySelector(".o_data_row .o_data_cell").textContent,
                "b",
                "should have the correct m2o value"
            );
        }
    );

    QUnit.skipWOWL("list in form: create with one2many with many2one", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.p.default = [
            [0, 0, { display_name: "new record", p: [] }],
        ];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name" />
                                <field name="trululu" />
                            </tree>
                        </field>
                    </sheet>
                </form>
            `,
            mockRPC(route, { method }) {
                if (method === "name_get") {
                    throw new Error("Nameget should not be called");
                }
            },
        });

        assert.strictEqual(
            target.querySelector("td.o_data_cell").textContent,
            "new record",
            "should have created the new record in the o2m with the correct name"
        );
    });

    QUnit.skipWOWL(
        "list in form: create with one2many with many2one (version 2)",
        async function (assert) {
            // This test simulates the exact same scenario as the previous one,
            // except that the value for the many2one is explicitely set to false,
            // which is stupid, but this happens, so we have to handle it
            assert.expect(1);

            serverData.models.partner.fields.p.default = [
                [0, 0, { display_name: "new record", trululu: false, p: [] }],
            ];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="p">
                                <tree editable="bottom">
                                    <field name="display_name" />
                                    <field name="trululu" />
                                </tree>
                            </field>
                        </sheet>
                    </form>
                `,
                mockRPC(route, { method }) {
                    if (method === "name_get") {
                        throw new Error("Nameget should not be called");
                    }
                },
            });

            assert.strictEqual(
                target.querySelector("td.o_data_cell").textContent,
                "new record",
                "should have created the new record in the o2m with the correct name"
            );
        }
    );

    QUnit.skipWOWL(
        "item not dropped on discard with empty required field (default_get)",
        async function (assert) {
            // This test simulates discarding a record that has been created with
            // one of its required field that is empty. When we discard the changes
            // on this empty field, it should not assume that this record should be
            // abandonned, since it has been added (even though it is a new record).
            assert.expect(8);

            serverData.models.partner.fields.p.default = [
                [0, 0, { display_name: "new record", trululu: false, p: [] }],
            ];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="p">
                                <tree editable="bottom">
                                    <field name="display_name" />
                                    <field name="trululu" required="1" />
                                </tree>
                            </field>
                        </sheet>
                    </form>
                `,
            });

            assert.containsOnce(
                target,
                "tr.o_data_row",
                "should have created the new record in the o2m"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().textContent,
                "new record",
                "should have the correct displayed name"
            );

            var requiredElement = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredElement.length,
                1,
                "should have a required field on this record"
            );
            assert.strictEqual(
                requiredElement.textContent,
                "",
                "should have empty string in the required field on this record"
            );

            click(requiredElement);
            // discard by clicking on body
            click($("body"));

            assert.strictEqual(
                $("tr.o_data_row").length,
                1,
                "should still have the record in the o2m"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().textContent,
                "new record",
                "should still have the correct displayed name"
            );

            // update selector of required field element
            requiredElement = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredElement.length,
                1,
                "should still have the required field on this record"
            );
            assert.strictEqual(
                requiredElement.textContent,
                "",
                "should still have empty string in the required field on this record"
            );
        }
    );

    QUnit.skipWOWL("list in form: name_get with unique ids (default_get)", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[0].display_name = "MyTrululu";
        serverData.models.partner.fields.p.default = [
            [0, 0, { trululu: 1, p: [] }],
            [0, 0, { trululu: 1, p: [] }],
        ];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="trululu" />
                            </tree>
                        </field>
                    </sheet>
                </form>
            `,
            mockRPC(route, { method }) {
                if (method === "name_get") {
                    throw new Error("should not call name_get");
                }
            },
        });

        assert.strictEqual(
            target.querySelector("td.o_data_cell").textContent,
            "MyTrululuMyTrululu",
            "both records should have the correct display_name for trululu field"
        );
    });

    QUnit.skipWOWL(
        "list in form: show name of many2one fields in multi-page (default_get)",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.fields.p.default = [
                [0, 0, { display_name: "record1", trululu: 1, p: [] }],
                [0, 0, { display_name: "record2", trululu: 2, p: [] }],
            ];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="p">
                                <tree editable="bottom" limit="1">
                                    <field name="display_name" />
                                    <field name="trululu" />
                                </tree>
                            </field>
                        </sheet>
                    </form>
                `,
            });

            assert.strictEqual(
                target.querySelectorAll("td.o_data_cell")[0].textContent,
                "record1",
                "should show display_name of 1st record"
            );
            assert.strictEqual(
                target.querySelectorAll("td.o_data_cell")[1].textContent,
                "first record",
                "should show display_name of trululu of 1st record"
            );

            await click(target, "button.o_pager_next");

            assert.strictEqual(
                target.querySelectorAll("td.o_data_cell")[0].textContent,
                "record2",
                "should show display_name of 2nd record"
            );
            assert.strictEqual(
                target.querySelectorAll("td.o_data_cell")[1].textContent,
                "second record",
                "should show display_name of trululu of 2nd record"
            );
        }
    );

    QUnit.skipWOWL(
        "list in form: item not dropped on discard with empty required field (onchange in default_get)",
        async function (assert) {
            // variant of the test "list in form: discard newly added element with
            // empty required field (default_get)", in which the `default_get`
            // performs an `onchange` at the same time. This `onchange` may create
            // some records, which should not be abandoned on discard, similarly
            // to records created directly by `default_get`
            assert.expect(7);

            serverData.models.partner.fields.product_id.default = 37;
            serverData.models.partner.onchanges = {
                product_id(obj) {
                    if (obj.product_id === 37) {
                        obj.p = [[0, 0, { display_name: "entry", trululu: false }]];
                    }
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="product_id" />
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name" />
                                <field name="trululu" required="1" />
                            </tree>
                        </field>
                    </form>
                `,
            });

            // check that there is a record in the editable list with empty string as required field
            assert.containsOnce(form, ".o_data_row", "should have a row in the editable list");
            assert.strictEqual(
                $("td.o_data_cell").first().textContent,
                "entry",
                "should have the correct displayed name"
            );
            var requiredField = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredField.length,
                1,
                "should have a required field on this record"
            );
            assert.strictEqual(
                requiredField.textContent,
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            click(requiredField);
            // click off so that the required field still stay empty
            click($("body"));

            // record should not be dropped
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped record in the editable list"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().textContent,
                "entry",
                "should still have the correct displayed name"
            );
            assert.strictEqual(
                $("td.o_data_cell.o_required_modifier").textContent,
                "",
                "should still have empty string in the required field"
            );
        }
    );

    QUnit.skipWOWL(
        "list in form: item not dropped on discard with empty required field (onchange on list after default_get)",
        async function (assert) {
            // discarding a record from an `onchange` in a `default_get` should not
            // abandon the record. This should not be the case for following
            // `onchange`, except if an onchange make some changes on the list:
            // in particular, if an onchange make changes on the list such that
            // a record is added, this record should not be dropped on discard
            assert.expect(8);

            serverData.models.partner.onchanges = {
                product_id(obj) {
                    if (obj.product_id === 37) {
                        obj.p = [[0, 0, { display_name: "entry", trululu: false }]];
                    }
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="product_id" />
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name" />
                                <field name="trululu" required="1" />
                            </tree>
                        </field>
                    </form>
                `,
            });

            // check no record in list
            assert.containsNone(form, ".o_data_row", "should have no row in the editable list");

            // select product_id to force on_change in editable list
            await click(target, '.o_field_widget[name="product_id"] .o_input');
            await click($(".ui-menu-item").first());

            // check that there is a record in the editable list with empty string as required field
            assert.containsOnce(form, ".o_data_row", "should have a row in the editable list");
            assert.strictEqual(
                $("td.o_data_cell").first().textContent,
                "entry",
                "should have the correct displayed name"
            );
            var requiredField = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredField.length,
                1,
                "should have a required field on this record"
            );
            assert.strictEqual(
                requiredField.textContent,
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            await click(requiredField);
            // click off so that the required field still stay empty
            await click($("body"));

            // record should not be dropped
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped record in the editable list"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().textContent,
                "entry",
                "should still have the correct displayed name"
            );
            assert.strictEqual(
                $("td.o_data_cell.o_required_modifier").textContent,
                "",
                "should still have empty string in the required field"
            );
        }
    );

    QUnit.skipWOWL(
        'item dropped on discard with empty required field with "Add an item" (invalid on "ADD")',
        async function (assert) {
            // when a record in a list is added with "Add an item", it should
            // always be dropped on discard if some required field are empty
            // at the record creation.
            assert.expect(6);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name" />
                                <field name="trululu" required="1" />
                            </tree>
                        </field>
                    </form>
                `,
            });

            // Click on "Add an item"
            await click(target, ".o_field_x2many_list_row_add a");
            var charField = target.querySelector(
                '.o_field_widget.o_field_char[name="display_name"]'
            );
            var requiredField = target.querySelector(
                '.o_field_widget.o_required_modifier[name="trululu"]'
            );
            charField.val("some text");
            assert.strictEqual(
                charField.length,
                1,
                "should have a char field 'display_name' on this record"
            );
            assert.doesNotHaveClass(
                charField,
                "o_required_modifier",
                "the char field should not be required on this record"
            );
            assert.strictEqual(
                charField.value,
                "some text",
                "should have entered text in the char field on this record"
            );
            assert.strictEqual(
                requiredField.length,
                1,
                "should have a required field 'trululu' on this record"
            );
            assert.strictEqual(
                requiredField.value.trim(),
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            await click(requiredField);
            // click off so that the required field still stay empty
            await click($("body"));

            // record should be dropped
            assert.containsNone(
                form,
                ".o_data_row",
                "should have dropped record in the editable list"
            );
        }
    );

    QUnit.skipWOWL(
        'item not dropped on discard with empty required field with "Add an item" (invalid on "UPDATE")',
        async function (assert) {
            // when a record in a list is added with "Add an item", it should
            // be temporarily added to the list when it is valid (e.g. required
            // fields are non-empty). If the record is updated so that the required
            // field is empty, and it is discarded, then the record should not be
            // dropped.
            assert.expect(8);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name" />
                                <field name="trululu" required="1" />
                            </tree>
                        </field>
                    </form>
                `,
            });

            assert.containsNone(
                form,
                ".o_data_row",
                "should initially not have any record in the list"
            );

            // Click on "Add an item"
            await click(target, ".o_field_x2many_list_row_add a");
            assert.containsOnce(form, ".o_data_row", "should have a temporary record in the list");

            var $inputEditMode = target.querySelectorAll(
                '.o_field_widget.o_required_modifier[name="trululu"] input'
            );
            assert.strictEqual(
                $inputEditMode.length,
                1,
                "should have a required field 'trululu' on this record"
            );
            assert.strictEqual(
                $inputEditMode.value,
                "",
                "should have empty string in the required field on this record"
            );

            // add something to required field and leave edit mode of the record
            await click($inputEditMode);
            await click($("li.ui-menu-item").first());
            await click($("body"));

            var $inputReadonlyMode = target.querySelectorAll(".o_data_cell.o_required_modifier");
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped valid record when leaving edit mode"
            );
            assert.strictEqual(
                $inputReadonlyMode.textContent,
                "first record",
                "should have put some content in the required field on this record"
            );

            // remove the required field and leave edit mode of the record
            await click($(".o_data_row"));
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped record in the list on discard (invalid on UPDATE)"
            );
            assert.strictEqual(
                $inputReadonlyMode.textContent,
                "first record",
                "should keep previous valid required field content on this record"
            );
        }
    );

    // WARNING: this does not seem to be a many2one field test
    QUnit.skipWOWL("list in form: default_get with x2many create", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.timmy.default = [
            [0, 0, { display_name: "brandon is the new timmy", name: "brandon" }],
        ];
        serverData.models.partner.onchanges.timmy = (obj) => {
            obj.int_field = obj.timmy.length;
        };
        let displayName = "brandon is the new timmy";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="timmy">
                            <tree editable="bottom">
                                <field name="display_name" />
                            </tree>
                        </field>
                        <field name="int_field" />
                    </sheet>
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(
                        args[0],
                        {
                            int_field: 2,
                            timmy: [
                                [6, false, []],
                                // LPE TODO 1 taskid-2261084: remove this entire comment including code snippet
                                // when the change in behavior has been thoroughly tested.
                                // We can't distinguish a value coming from a default_get
                                // from one coming from the onchange, and so we can either store and
                                // send it all the time, or never.
                                // [0, args[0].timmy[1][1], { display_name: displayName, name: 'brandon' }],
                                [0, args[0].timmy[1][1], { display_name: displayName }],
                            ],
                        },
                        "should send the correct values to create"
                    );
                }
            },
        });

        assert.strictEqual(
            $("td.o_data_cell:first").textContent,
            "brandon is the new timmy",
            "should have created the new record in the m2m with the correct name"
        );
        assert.strictEqual(
            $("input.o_field_integer").value,
            "1",
            "should have called and executed the onchange properly"
        );

        // edit the subrecord and save
        displayName = "new value";
        await click(target, ".o_data_cell");
        await testUtils.fields.editInput(
            target.querySelectorAll(".o_data_cell input"),
            displayName
        );
        await click(target, ".o_form_button_save");
    });

    // WARNING: this does not seem to be a many2one field test
    QUnit.skipWOWL(
        "list in form: default_get with x2many create and onchange",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.fields.turtles.default = [[6, 0, [2, 3]]];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="turtles">
                                <tree editable="bottom">
                                    <field name="turtle_foo" />
                                </tree>
                            </field>
                            <field name="int_field" />
                        </sheet>
                    </form>
                `,
                mockRPC(route, { args, method }) {
                    if (method === "create") {
                        assert.deepEqual(
                            args[0].turtles,
                            [
                                [4, 2, false],
                                [4, 3, false],
                            ],
                            "should send proper commands to create method"
                        );
                    }
                },
            });

            await click(target, ".o_form_button_save");
        }
    );

    QUnit.skipWOWL("list in form: call button in sub view", async function (assert) {
        assert.expect(11);

        serverData.models.partner.records[0].p = [2];
        serverData.views = {
            "product,false,form": `
                <form>
                    <header>
                        <button name="action" type="action" string="Just do it !" />
                        <button name="object" type="object" string="Just don't do it !" />
                        <field name="display_name" />
                    </header>
                </form>
            `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="product_id" />
                            </tree>
                        </field>
                    </sheet>
                </form>
            `,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return Promise.resolve(false);
                }
            },
            intercepts: {
                execute_action(event) {
                    assert.strictEqual(
                        event.data.env.model,
                        "product",
                        "should call with correct model in env"
                    );
                    assert.strictEqual(
                        event.data.env.currentID,
                        37,
                        "should call with correct currentID in env"
                    );
                    assert.deepEqual(
                        event.data.env.resIDs,
                        [37],
                        "should call with correct resIDs in env"
                    );
                    assert.step(event.data.action_data.name);
                },
            },
        });

        await click(target, ".o_form_button_edit");
        await click(target.querySelector("td.o_data_cell"));
        await click(target, ".o_external_button");
        await click($('button:contains("Just do it !")'));
        assert.verifySteps(["action"]);
        await click($('button:contains("Just don\'t do it !")'));
        assert.verifySteps([]); // the second button is disabled, it can't be clicked

        await click(document.body.querySelector(".modal .btn-secondary:contains(Discard)"));
        await click(target, ".o_external_button");
        await click($('button:contains("Just don\'t do it !")'));
        assert.verifySteps(["object"]);
    });

    QUnit.skipWOWL("X2Many sequence list in modal", async function (assert) {
        assert.expect(5);

        serverData.models.partner.fields.sequence = { string: "Sequence", type: "integer" };
        serverData.models.partner.records[0].sequence = 1;
        serverData.models.partner.records[1].sequence = 2;
        serverData.models.partner.onchanges = {
            sequence(obj) {
                if (obj.id === 2) {
                    obj.sequence = 1;
                    assert.step("onchange sequence");
                }
            },
        };

        serverData.models.product.fields.turtle_ids = {
            string: "Turtles",
            type: "one2many",
            relation: "turtle",
        };
        serverData.models.product.records[0].turtle_ids = [1];

        serverData.models.turtle.fields.partner_types_ids = {
            string: "Partner",
            type: "one2many",
            relation: "partner",
        };
        serverData.models.turtle.fields.type_id = {
            string: "Partner Type",
            type: "many2one",
            relation: "partner_type",
        };

        serverData.models.partner_type.fields.partner_ids = {
            string: "Partner",
            type: "one2many",
            relation: "partner",
        };
        serverData.models.partner_type.records[0].partner_ids = [1, 2];

        serverData.views = {
            "partner_type,false,form": `
                <form>
                    <field name="partner_ids" />
                </form>
            `,
            "partner,false,list": `
                <tree>
                    <field name="display_name" />
                    <field name="sequence" widget="handle" />
                </tree>
            `,
        };

        await makeView({
            type: "form",
            resModel: "product",
            resId: 37,
            serverData,
            arch: `
                <form>
                    <field name="name" />
                    <field name="turtle_ids" widget="one2many">
                        <tree editable="bottom">
                            <field name="type_id" />
                        </tree>
                    </field>
                </form>
            `,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/product/read") {
                    return Promise.resolve([
                        { id: 37, name: "xphone", display_name: "leonardo", turtle_ids: [1] },
                    ]);
                }
                if (route === "/web/dataset/call_kw/turtle/read") {
                    return Promise.resolve([{ id: 1, type_id: [12, "gold"] }]);
                }
                if (route === "/web/dataset/call_kw/partner_type/get_formview_id") {
                    return Promise.resolve(false);
                }
                if (route === "/web/dataset/call_kw/partner_type/read") {
                    return Promise.resolve([{ id: 12, partner_ids: [1, 2], display_name: "gold" }]);
                }
                if (route === "/web/dataset/call_kw/partner_type/write") {
                    assert.step("partner_type write");
                }
            },
        });

        await click(target, ".o_form_button_edit");
        await click(target, ".o_data_cell");
        await click(target, ".o_external_button");

        var $modal = document.body.querySelector(".modal");
        assert.equal($modal.length, 1, "There should be 1 modal opened");

        var $handles = $modal.find(".ui-sortable-handle");
        assert.equal($handles.length, 2, "There should be 2 sequence handlers");

        await testUtils.dom.dragAndDrop($handles.eq(1), $modal.find("tbody tr").first(), {
            position: "top",
        });

        // Saving the modal and then the original model
        await click($modal.find(".modal-footer .btn-primary"));
        await click(target, ".o_form_button_save");

        assert.verifySteps(["onchange sequence", "partner_type write"]);
    });

    QUnit.test("autocompletion in a many2one, in form view with a domain", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            domain: [["trululu", "=", 4]],
            arch: `
                <form>
                    <field name="product_id" />
                </form>
            `,
            mockRPC(route, { kwargs, method }) {
                if (method === "name_search") {
                    assert.deepEqual(kwargs.args, [], "should not have a domain");
                }
            },
        });
        await click(target, ".o_form_button_edit");

        click(target, ".o_field_widget[name=product_id] input");
    });

    QUnit.test(
        "autocompletion in a many2one, in form view with a date field",
        async function (assert) {
            assert.expect(1);

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 2,
                serverData,
                arch: `
                    <form>
                        <field name="bar" />
                        <field name="date" />
                        <field name="trululu" domain="[('bar', '=', True)]" />
                    </form>
                `,
                mockRPC(route, { kwargs, method }) {
                    if (method === "name_search") {
                        assert.deepEqual(kwargs.args, [["bar", "=", true]], "should have a domain");
                    }
                },
            });
            await click(target, ".o_form_button_edit");

            click(target, ".o_field_widget[name='trululu'] input");
        }
    );

    QUnit.test("creating record with many2one with option always_reload", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.trululu.default = 1;
        serverData.models.partner.onchanges = {
            trululu(obj) {
                obj.trululu = 2; //[2, "second record"];
            },
        };

        let count = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" options="{'always_reload': 1}" />
                </form>
            `,
            mockRPC(route, { args, method }) {
                count++;
                if (method === "name_get" && args[0][0] === 2) {
                    return Promise.resolve([[2, "hello world\nso much noise"]]);
                }
            },
        });

        assert.strictEqual(count, 2, "should have done 2 rpcs (onchange and name_get)");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='trululu'] input").value,
            "hello world",
            "should have taken the correct display name"
        );
    });

    QUnit.test("selecting a many2one, then discarding", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="product_id" />
                </form>
            `,
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id']").textContent,
            "",
            "the tag a should be empty"
        );
        await click(target, ".o_form_button_edit");

        await click(target, ".o_field_widget[name='product_id'] input");
        await click(target.querySelector(".o_field_widget[name='product_id'] .dropdown-item"));
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] input").value,
            "xphone",
            "should have selected xphone"
        );

        await click(target, ".o_form_button_cancel");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id']").textContent,
            "",
            "the tag a should be empty"
        );
    });

    QUnit.skipWOWL(
        "domain and context are correctly used when doing a name_search in a m2o",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.records[0].timmy = [12];

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="product_id" domain="[('foo', '=', 'bar'), ('foo', '=', foo)]" context="{'hello': 'world', 'test': foo}" />
                        <field name="foo" />
                        <field name="trululu" context="{'timmy': timmy}" domain="[('id', 'in', timmy)]" />
                        <field name="timmy" widget="many2many_tags" invisible="1" />
                    </form>
                `,
                session: { user_context: { hey: "ho" } },
                mockRPC(route, { kwargs, method, model }) {
                    if (method === "name_search" && model === "product") {
                        assert.deepEqual(
                            kwargs.args,
                            [
                                ["foo", "=", "bar"],
                                ["foo", "=", "yop"],
                            ],
                            "the field attr domain should have been used for the RPC (and evaluated)"
                        );
                        assert.deepEqual(
                            kwargs.context,
                            { hey: "ho", hello: "world", test: "yop" },
                            "the field attr context should have been used for the RPC (evaluated and merged with the session one)"
                        );
                        return Promise.resolve([]);
                    }
                    if (method === "name_search" && model === "partner") {
                        assert.deepEqual(
                            kwargs.args,
                            [["id", "in", [12]]],
                            "the field attr domain should have been used for the RPC (and evaluated)"
                        );
                        assert.deepEqual(
                            kwargs.context,
                            { hey: "ho", timmy: [[6, false, [12]]] },
                            "the field attr context should have been used for the RPC (and evaluated)"
                        );
                        return Promise.resolve([]);
                    }
                },
            });

            await click(target, ".o_form_button_edit");
            click(target, ".o_field_widget[name='poduct_id'] input");
            click(target, ".o_field_widget[name='trululu'] input");
        }
    );

    QUnit.skipWOWL("quick create on a many2one", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="product_id" />
                    </sheet>
                </form>
            `,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/product/name_create") {
                    assert.strictEqual(args[0], "new partner", "should name create a new product");
                }
            },
        });

        await testUtils.dom.triggerEvent(
            target.querySelectorAll(".o_field_many2one input"),
            "focus"
        );
        await testUtils.fields.editAndTrigger(
            target.querySelectorAll(".o_field_many2one input"),
            "new partner",
            ["keyup", "blur"]
        );
        await click(document.body, ".modal .modal-footer .btn-primary");
        assert.strictEqual(
            document.body.querySelector(".modal .modal-body").textContent.trim(),
            "Create new partner as a new Product?"
        );
    });

    QUnit.skipWOWL("failing quick create on a many2one", async function (assert) {
        assert.expect(4);

        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="name" />
                </form>
            `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="product_id" />
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "name_create") {
                    return Promise.reject();
                }
                if (method === "create") {
                    assert.deepEqual(args[0], { name: "xyz" });
                }
            },
        });

        await testUtils.fields.many2one.searchAndClickItem("product_id", {
            search: "abcd",
            item: 'Create "abcd"',
        });
        assert.containsOnce(document.body, ".modal .o_form_view");
        assert.strictEqual(
            document.body.querySelector(".o_field_widget[name='name']").value,
            "abcd"
        );

        await testUtils.fields.editInput(
            document.body.querySelector(".modal .o_field_widget[name=name]"),
            "xyz"
        );
        await click(document.body, ".modal .modal-footer .btn-primary");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] input").value,
            "xyz"
        );
    });

    QUnit.skipWOWL("failing quick create on a many2one inside a one2many", async function (assert) {
        assert.expect(4);

        serverData.views = {
            "partner,false,list": `
                <tree editable="bottom">
                    <field name="product_id" />
                </tree>
            `,
            "product,false,form": `
                <form>
                    <field name="name" />
                </form>
            `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" />
                </form>
            `,
            mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject();
                }
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], { name: "xyz" });
                }
                return this._super(...arguments);
            },
        });

        await click(target, ".o_field_x2many_list_row_add a");
        await testUtils.fields.many2one.searchAndClickItem("product_id", {
            search: "abcd",
            item: 'Create "abcd"',
        });
        assert.containsOnce(document.body, ".modal .o_form_view");
        assert.strictEqual(
            document.body.querySelector(".o_field_widget[name='name']").value,
            "abcd"
        );

        await testUtils.fields.editInput(
            document.body.querySelector(".modal .o_field_widget[name='name']"),
            "xyz"
        );
        await click(document.body, ".modal .modal-footer .btn-primary");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] input").value,
            "xyz"
        );
    });

    QUnit.skipWOWL("slow create on a many2one", async function (assert) {
        assert.expect(11);

        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="name" />
                </form>
            `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="product_id" options="{'quick_create': 0}" />
                    </sheet>
                </form>
            `,
        });

        // cancel the many2one creation with Discard button
        target
            .querySelectorAll(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await nextTick();
        target.querySelectorAll(".o_field_many2one input").trigger("blur");
        await nextTick();
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            1,
            "there should be one opened modal"
        );

        await click(document.body.querySelector(".modal .modal-footer .btn:contains(Discard)"));
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            0,
            "the modal should be closed"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2one input").value,
            "",
            "the many2one should not set a value as its creation has been cancelled (with Cancel button)"
        );

        // cancel the many2one creation with Close button
        target
            .querySelectorAll(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await nextTick();
        target.querySelectorAll(".o_field_many2one input").trigger("blur");
        await nextTick();
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            1,
            "there should be one opened modal"
        );
        await click(document.body.querySelector(".modal .modal-header button"));
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2one input").value,
            "",
            "the many2one should not set a value as its creation has been cancelled (with Close button)"
        );
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            0,
            "the modal should be closed"
        );

        // select a new value then cancel the creation of the new one --> restore the previous
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickItem("product_id", "o");
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2one input").value,
            "xphone",
            "should have selected xphone"
        );

        target
            .querySelectorAll(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await nextTick();
        target.querySelectorAll(".o_field_many2one input").trigger("blur");
        await nextTick();
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            1,
            "there should be one opened modal"
        );

        await click(document.body.querySelector(".modal .modal-footer .btn:contains(Discard)"));
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2one input").value,
            "xphone",
            "should have restored the many2one with its previous selected value (xphone)"
        );

        // confirm the many2one creation
        target
            .querySelectorAll(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await nextTick();
        target.querySelectorAll(".o_field_many2one input").trigger("blur");
        await nextTick();
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            1,
            "there should be one opened modal"
        );

        await click(
            document.body.querySelector(".modal .modal-footer .btn-primary:contains(Create)")
        );
        assert.strictEqual(
            document.body.querySelector(".modal .o_form_view").length,
            1,
            "a new modal should be opened and contain a form view"
        );

        await click(document.body.querySelector(".modal .o_form_button_cancel"));
    });

    QUnit.skipWOWL("select a many2one value by focusing out", async function (assert) {
        assert.expect(3);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="product_id" />
                </form>
            `,
        });

        const input = target.querySelector(".o_field_many2one input");
        input.value = "xph";
        await triggerEvents(input, null, ["input", "change"]);

        assert.containsNone(document.body, ".modal");
        assert.strictEqual(target.querySelector(".o_field_many2one input").value, "xphone");
        assert.containsOnce(form, ".o_external_button");
    });

    QUnit.skipWOWL("no_create option on a many2one", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="product_id" options="{'no_create': 1}" />
                    </sheet>
                </form>
            `,
        });

        await testUtils.fields.editInput(
            target.querySelectorAll(".o_field_many2one input"),
            "new partner"
        );
        target.querySelectorAll(".o_field_many2one input").trigger("keyup").trigger("focusout");
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            0,
            "should not display the create modal"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2one input").value,
            "",
            "many2one value should cleared on focusout if many2one is no_create"
        );
    });

    QUnit.skipWOWL("can_create and can_write option on a many2one", async function (assert) {
        assert.expect(5);

        serverData.models.product.options = {
            can_create: "false",
            can_write: "false",
        };
        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="display_name" />
                </form>
            `,
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="product_id" can_create="false" can_write="false" />
                    </sheet>
                </form>
            `,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });

        await click(target, ".o_field_many2one input");
        assert.strictEqual(
            $(".ui-autocomplete .o_m2o_dropdown_option:contains(Create)").length,
            0,
            "there shouldn't be any option to search and create"
        );

        await click($(".ui-autocomplete li:contains(xpad)").mouseenter());
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2one input").value,
            "xpad",
            "the correct record should be selected"
        );
        assert.containsOnce(
            form,
            ".o_field_many2one .o_external_button",
            "there should be an external button displayed"
        );

        await click(target, ".o_field_many2one .o_external_button");
        assert.strictEqual(
            document.body.querySelector(".modal .o_form_view.o_form_readonly").length,
            1,
            "there should be a readonly form view opened"
        );

        await click(document.body.querySelector(".modal .o_form_button_cancel"));

        await testUtils.fields.editAndTrigger(
            target.querySelectorAll(".o_field_many2one input"),
            "new product",
            ["keyup", "focusout"]
        );
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            0,
            "should not display the create modal"
        );
    });

    QUnit.skipWOWL(
        "many2one with can_create=false shows no result item when searched something that doesn't exist",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="product_id" can_create="false" can_write="false" />
                        </sheet>
                    </form>
                `,
            });

            await click(target, ".o_field_many2one input");
            await testUtils.fields.editAndTrigger(
                target.querySelectorAll('.o_field_many2one[name="product_id"] input'),
                "abc",
                "keydown"
            );
            await nextTick();
            assert.strictEqual(
                $(".ui-autocomplete .o_m2o_dropdown_option:contains(Create)").length,
                0,
                "there shouldn't be any option to search and create"
            );
            assert.strictEqual(
                $(".ui-autocomplete .ui-menu-item a:contains(No records)").length,
                1,
                "there should be option for 'No records'"
            );
        }
    );

    QUnit.skipWOWL("pressing enter in a m2o in an editable list", async function (assert) {
        assert.expect(8);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="product_id" />
                </tree>
            `,
        });

        await click(list.$("td.o_data_cell:first"));
        assert.containsOnce(list, ".o_selected_row", "should have a row in edit mode");

        // we now write 'a' and press enter to check that the selection is
        // working, and prevent the navigation
        await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
        var $input = list.$("td.o_data_cell input:first");
        var $dropdown = $input.autocomplete("widget");
        assert.ok($dropdown.is(":visible"), "autocomplete dropdown should be visible");

        // we now trigger ENTER to select first choice
        await testUtils.fields.triggerKeydown($input, "enter");
        assert.strictEqual($input[0], document.activeElement, "input should still be focused");

        // we now trigger again ENTER to make sure we can move to next line
        await testUtils.fields.triggerKeydown($input, "enter");

        assert.notOk(document.contains($input[0]), "input should no longer be in dom");
        assert.hasClass(
            list.$("tr.o_data_row:eq(1)"),
            "o_selected_row",
            "second row should now be selected"
        );

        // we now write again 'a' in the cell to select xpad. We will now
        // test with the tab key
        await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
        $input = list.$("td.o_data_cell input:first");
        $dropdown = $input.autocomplete("widget");
        assert.ok($dropdown.is(":visible"), "autocomplete dropdown should be visible");
        await testUtils.fields.triggerKeydown($input, "tab");

        assert.notOk(document.contains($input[0]), "input should no longer be in dom");
        assert.hasClass(
            list.$("tr.o_data_row:eq(2)"),
            "o_selected_row",
            "third row should now be selected"
        );
    });

    QUnit.skipWOWL(
        "pressing ENTER on a 'no_quick_create' many2one should open a M2ODialog",
        async function (assert) {
            assert.expect(2);

            serverData.views = {
                "partner,false,form": `
                    <form>
                        <field name="display_name" />
                    </form>
                `,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="trululu" options="{'no_quick_create': 1}" />
                        <field name="foo" />
                    </form>
                `,
            });

            var $input = target.querySelectorAll(".o_field_many2one input");
            await testUtils.fields.editInput($input, "Something that does not exist");
            $(".ui-autocomplete .ui-menu-item a:contains(Create and)").trigger("mouseenter");
            await nextTick();
            await testUtils.fields.triggerKey("down", $input, "enter");
            await testUtils.fields.triggerKey("press", $input, "enter");
            await testUtils.fields.triggerKey("up", $input, "enter");
            $input.blur();
            assert.strictEqual(
                document.body.querySelector(".modal").length,
                1,
                "should have one modal in body"
            );
            // Check that discarding clears $input
            await click(document.body.querySelector(".modal .o_form_button_cancel"));
            assert.strictEqual($input.value, "", "the field should be empty");
        }
    );

    QUnit.skipWOWL(
        "select a value by pressing TAB on a many2one with onchange",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.onchanges.trululu = () => {};

            const def = makeDeferred();

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="trululu" />
                        <field name="display_name" />
                    </form>
                `,
                mockRPC(route, { method }, performRPC) {
                    if (method === "onchange") {
                        return def.then(performRPC(...arguments));
                    }
                },
            });

            await click(target, ".o_form_button_edit");

            var $input = target.querySelectorAll(".o_field_many2one input");
            await testUtils.fields.editAndTrigger($input, "first", ["keydown", "keyup"]);
            await testUtils.fields.triggerKey("down", $input, "tab");
            await testUtils.fields.triggerKey("press", $input, "tab");
            await testUtils.fields.triggerKey("up", $input, "tab");

            // simulate a focusout (e.g. because the user clicks outside)
            // before the onchange returns
            target.querySelectorAll(".o_field_char").focus();

            assert.strictEqual(
                document.body.querySelector(".modal").length,
                0,
                "there shouldn't be any modal in body"
            );

            // unlock the onchange
            def.resolve();
            await nextTick();

            assert.strictEqual(
                $input.value,
                "first record",
                "first record should have been selected"
            );
            assert.strictEqual(
                document.body.querySelector(".modal").length,
                0,
                "there shouldn't be any modal in body"
            );
        }
    );

    QUnit.skipWOWL("leaving a many2one by pressing tab", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu"/>
                    <field name="display_name"/>
                </form>
            `,
        });

        const $input = target.querySelectorAll(".o_field_many2one input");
        await click($input);
        await testUtils.fields.triggerKeydown($input, "tab");
        assert.strictEqual($input.value, "", "no record should have been selected");

        // open autocomplete dropdown and manually select item by UP/DOWN key and press TAB
        await click($input);
        await testUtils.fields.triggerKeydown($input, "down");
        await testUtils.fields.triggerKeydown($input, "tab");
        assert.strictEqual(
            $input.value,
            "second record",
            "second record should have been selected"
        );

        // clear many2one and then open autocomplete, write something and press TAB
        await testUtils.fields.editAndTrigger(
            target.querySelectorAll(".o_field_many2one input"),
            "",
            ["keyup", "blur"]
        );
        await testUtils.dom.triggerEvent($input, "focus");
        await testUtils.fields.editInput($input, "se");
        await testUtils.fields.triggerKeydown($input, "tab");
        assert.strictEqual($input.value, "second record", "first record should have been selected");
    });

    QUnit.skipWOWL(
        "leaving an empty many2one by pressing tab (after backspace or delete)",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="trululu"/>
                        <field name="display_name"/>
                    </form>
                `,
            });

            await click(target, ".o_form_button_edit");

            const $input = target.querySelectorAll(".o_field_many2one input");
            assert.ok($input.value, "many2one should have value");

            // simulate backspace to remove values and press TAB
            await testUtils.fields.editInput($input, "");
            await testUtils.fields.triggerKeyup($input, "backspace");
            await testUtils.fields.triggerKeydown($input, "tab");
            assert.strictEqual($input.value, "", "no record should have been selected");

            // reset a value
            await testUtils.fields.many2one.clickOpenDropdown("trululu");
            await testUtils.fields.many2one.clickItem("trululu", "first record");
            assert.ok($input.value, "many2one should have value");

            // simulate delete to remove values and press TAB
            await testUtils.fields.editInput($input, "");
            await testUtils.fields.triggerKeyup($input, "delete");
            await testUtils.fields.triggerKeydown($input, "tab");
            assert.strictEqual($input.value, "", "no record should have been selected");
        }
    );

    QUnit.skipWOWL(
        "many2one in editable list + onchange, with enter [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.onchanges.product_id = (obj) => {
                obj.int_field = obj.product_id || 0;
            };

            const def = makeDeferred();

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="product_id" />
                        <field name="int_field" />
                    </tree>
                `,
                mockRPC(route, { method }, performRPC) {
                    if (method) {
                        assert.step(method);
                    }
                    if (method === "onchange") {
                        return def.then(performRPC(...arguments));
                    }
                },
            });

            await click(list.$("td.o_data_cell:first"));
            await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
            var $input = list.$("td.o_data_cell input:first");
            await testUtils.fields.triggerKeydown($input, "enter");
            await testUtils.fields.triggerKey("up", $input, "enter");
            def.resolve();
            await nextTick();
            await testUtils.fields.triggerKeydown($input, "enter");
            assert.strictEqual(
                document.body.querySelector(".modal").length,
                0,
                "should not have any modal in DOM"
            );
            assert.verifySteps(["name_search", "onchange", "write", "read"]);
        }
    );

    QUnit.skipWOWL(
        "many2one in editable list + onchange, with enter, part 2 [REQUIRE FOCUS]",
        async function (assert) {
            // this is the same test as the previous one, but the onchange is just
            // resolved slightly later
            assert.expect(6);

            serverData.models.partner.onchanges.product_id = (obj) => {
                obj.int_field = obj.product_id || 0;
            };

            const def = makeDeferred();

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="product_id" />
                        <field name="int_field" />
                    </tree>
                `,
                mockRPC(route, { method }, performRPC) {
                    if (method) {
                        assert.step(method);
                    }
                    if (method === "onchange") {
                        return def.then(performRPC(...arguments));
                    }
                },
            });

            await click(list.$("td.o_data_cell:first"));
            await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
            var $input = list.$("td.o_data_cell input:first");
            await testUtils.fields.triggerKeydown($input, "enter");
            await testUtils.fields.triggerKey("up", $input, "enter");
            await testUtils.fields.triggerKeydown($input, "enter");
            def.resolve();
            await nextTick();
            assert.strictEqual(
                document.body.querySelector(".modal").length,
                0,
                "should not have any modal in DOM"
            );
            assert.verifySteps(["name_search", "onchange", "write", "read"]);
        }
    );

    QUnit.test("many2one: domain updated by an onchange", async function (assert) {
        assert.expect(2);

        serverData.models.partner.onchanges = {
            int_field() {},
        };

        let domain = [];
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="int_field" />
                    <field name="trululu" />
                </form>
            `,
            mockRPC(route, { kwargs, method }) {
                if (method === "onchange") {
                    domain = [["id", "in", [10]]];
                    return Promise.resolve({
                        domain: {
                            trululu: domain,
                            unexisting_field: domain,
                        },
                    });
                }
                if (method === "name_search") {
                    assert.deepEqual(kwargs.args, domain, "sent domain should be correct");
                }
            },
        });

        await click(target, ".o_form_button_edit");

        // trigger a name_search (domain should be [])
        await click(target, ".o_field_widget[name=trululu] input");
        // close the dropdown
        await click(target, ".o_field_widget[name=trululu] input");
        // trigger an onchange that will update the domain
        await triggerEvent(target, ".o_field_widget[name='int_field']", "onchange");

        // trigger a name_search (domain should be [['id', 'in', [10]]])
        await click(target, ".o_field_widget[name='trululu'] input");
    });

    QUnit.skipWOWL("many2one in one2many: domain updated by an onchange", async function (assert) {
        assert.expect(3);

        serverData.models.partner.onchanges = {
            trululu() {},
        };

        let domain = [];
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="foo" />
                            <field name="trululu" />
                        </tree>
                    </field>
                </form>
            `,
            mockRPC(route, { kwargs, method }) {
                if (method === "onchange") {
                    return Promise.resolve({
                        domain: {
                            trululu: domain,
                        },
                    });
                }
                if (method === "name_search") {
                    assert.deepEqual(kwargs.args, domain, "sent domain should be correct");
                }
            },
        });

        await click(target, ".o_form_button_edit");

        // add a first row with a specific domain for the m2o
        domain = [["id", "in", [10]]]; // domain for subrecord 1
        await click(target, ".o_field_x2many_list_row_add a");
        await click(target, ".o_field_widget[name=trululu] input");
        // add some value to foo field to make record dirty
        await testUtils.fields.editInput(
            target.querySelectorAll('tr.o_selected_row input[name="foo"]'),
            "new value"
        );

        // add a second row with another domain for the m2o
        domain = [["id", "in", [5]]]; // domain for subrecord 2
        await click(target, ".o_field_x2many_list_row_add a");
        await click(target, ".o_field_widget[name=trululu] input");

        // check again the first row to ensure that the domain hasn't change
        domain = [["id", "in", [10]]]; // domain for subrecord 1 should have been kept
        await click(target, ".o_data_row:first .o_data_cell:eq(1)");
        await click(target, ".o_field_widget[name=trululu] input");
    });

    QUnit.test("search more in many2one: no text in input", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, and there is no text
        // in the input (i.e. no value to search on), we bypass the name_search that is meant to
        // return a list of preselected ids to filter on in the list view (opened in a dialog)
        assert.expect(6);

        for (let i = 0; i < 8; i++) {
            serverData.models.partner.records.push({ id: 100 + i, display_name: `test_${i}` });
        }
        serverData.views = {
            "partner,false,list": `
                <list>
                    <field name="display_name" />
                </list>
            `,
            "partner,false,search": `<search />`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
            mockRPC(route, { kwargs, method }) {
                assert.step(method || route);
                if (method === "web_search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [],
                        "should not preselect ids as there as nothing in the m2o input"
                    );
                }
            },
        });

        const field = target.querySelector(`.o_field_widget[name="trululu"] input`);
        field.value = "";
        await triggerEvent(field, null, "change");

        await click(target, `.o_field_widget[name="trululu"] input`);
        await click(target, `.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`);

        assert.verifySteps([
            "onchange",
            "name_search", // to display results in the dropdown
            "get_views", // list view in dialog
            "web_search_read", // to display results in the dialog
        ]);
    });

    QUnit.skipWOWL("search more in many2one: text in input", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, and there is some
        // text in the input, we perform a name_search to get a (limited) list of preselected
        // ids and we add a dynamic filter (with those ids) to the search view in the dialog, so
        // that the user can remove this filter to bypass the limit
        assert.expect(12);

        for (let i = 0; i < 8; i++) {
            serverData.models.partner.records.push({ id: 100 + i, display_name: `test_${i}` });
        }
        serverData.views = {
            "partner,false,list": `
                <list>
                    <field name="display_name" />
                </list>
            `,
            "partner,false,search": `<search />`,
        };

        let expectedDomain;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
            mockRPC(route, { kwargs, method }) {
                assert.step(method || route);
                if (method === "web_search_read") {
                    assert.deepEqual(kwargs.domain, expectedDomain);
                }
            },
        });

        expectedDomain = [["id", "in", [100, 101, 102, 103, 104, 105, 106, 107]]];
        const field = target.querySelector(`.o_field_widget[name="trululu"] input`);
        field.value = "test";
        await triggerEvent(field, null, "change");

        await click(target, `.o_field_widget[name="trululu"] input`);
        await click(target, `.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`);

        assert.containsOnce(document.body, ".modal .o_list_view");
        assert.containsOnce(
            document.body,
            ".modal .o_cp_searchview .o_facet_values",
            "should have a special facet for the pre-selected ids"
        );

        // remove the filter on ids
        expectedDomain = [];
        await click(document.body.querySelector(".modal .o_cp_searchview .o_facet_remove"));

        assert.verifySteps([
            "onchange",
            "name_search", // empty search, triggered when the user clicks in the input
            "name_search", // to display results in the dropdown
            "name_search", // to get preselected ids matching the search
            "get_views", // list view in dialog
            "/web/dataset/search_read", // to display results in the dialog
            "/web/dataset/search_read", // after removal of dynamic filter
        ]);
    });

    QUnit.skipWOWL("search more in many2one: dropdown click", async function (assert) {
        assert.expect(8);

        for (let i = 0; i < 8; i++) {
            serverData.models.partner.records.push({ id: 100 + i, display_name: `test_${i}` });
        }
        serverData.views = {
            "partner,false,list": `
                <list>
                    <field name="display_name" />
                </list>
            `,
            "partner,false,search": `<search />`,
        };

        // simulate modal-like element rendered by the field html
        const $fakeDialog = $(`<div>
            <div class="pouet">
                <div class="modal"></div>
            </div>
        </div>`);
        $("body").append($fakeDialog);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
        });
        await testUtils.fields.many2one.searchAndClickItem("trululu", {
            item: "Search More",
            search: "test",
        });

        // dropdown selector
        const filterMenuCss = ".o_search_options > .o_filter_menu";
        const groupByMenuCss = ".o_search_options > .o_group_by_menu";

        await click(document.querySelector(`${filterMenuCss} > .dropdown-toggle`));

        assert.hasClass(document.querySelector(filterMenuCss), "show");
        assert.isVisible(
            document.querySelector(`${filterMenuCss} > .dropdown-menu`),
            "the filter dropdown menu should be visible"
        );
        assert.doesNotHaveClass(document.querySelector(groupByMenuCss), "show");
        assert.isNotVisible(
            document.querySelector(`${groupByMenuCss} > .dropdown-menu`),
            "the Group by dropdown menu should be not visible"
        );

        await click(document.querySelector(`${groupByMenuCss} > .dropdown-toggle`));
        assert.hasClass(document.querySelector(groupByMenuCss), "show");
        assert.isVisible(
            document.querySelector(`${groupByMenuCss} > .dropdown-menu`),
            "the group by dropdown menu should be visible"
        );
        assert.doesNotHaveClass(document.querySelector(filterMenuCss), "show");
        assert.isNotVisible(
            document.querySelector(`${filterMenuCss} > .dropdown-menu`),
            "the filter dropdown menu should be not visible"
        );
    });

    QUnit.skipWOWL("updating a many2one from a many2many", async function (assert) {
        assert.expect(4);

        serverData.models.turtle.records[1].turtle_trululu = 1;
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name" />
                </form>
            `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="display_name" />
                                <field name="turtle_trululu" />
                            </tree>
                        </field>
                    </group>
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "get_formview_id") {
                    assert.deepEqual(args[0], [1], "should call get_formview_id with correct id");
                    return Promise.resolve(false);
                }
            },
        });

        // Opening the modal
        await click(target, ".o_form_button_edit");
        await click(target, ".o_data_row td:contains(first record)");
        await click(target, ".o_external_button");
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            1,
            "should have one modal in body"
        );

        // Changing the 'trululu' value
        await testUtils.fields.editInput($('.modal input[name="display_name"]'), "test");
        await click(document.body.querySelector(".modal button.btn-primary"));

        // Test whether the value has changed
        assert.strictEqual(
            document.body.querySelector(".modal").length,
            0,
            "the modal should be closed"
        );
        assert.equal(
            target.querySelectorAll(".o_data_cell:contains(test)").textContent,
            "test",
            "the partner name should have been updated to 'test'"
        );
    });

    QUnit.skipWOWL("search more in many2one: resequence inside dialog", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, resequencing inside
        // the dialog works
        assert.expect(10);

        serverData.models.partner.fields.sequence = { string: "Sequence", type: "integer" };
        for (let i = 0; i < 8; i++) {
            serverData.models.partner.records.push({ id: 100 + i, display_name: `test_${i}` });
        }
        serverData.views = {
            "partner,false,list": `
                <list>
                    <field name="sequence" widget="handle" />
                    <field name="display_name" />
                </list>
            `,
            "partner,false,search": `<search />`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
            mockRPC(route, { domain, method }) {
                assert.step(method || route);
                if (route === "/web/dataset/search_read") {
                    assert.deepEqual(
                        domain,
                        [],
                        "should not preselect ids as there as nothing in the m2o input"
                    );
                }
            },
        });

        await testUtils.fields.many2one.searchAndClickItem("trululu", {
            item: "Search More",
            search: "",
        });

        var $modal = document.body.querySelector(".modal");
        assert.equal($modal.length, 1, "There should be 1 modal opened");

        var $handles = $modal.find(".ui-sortable-handle");
        assert.equal($handles.length, 11, "There should be 11 sequence handlers");

        await testUtils.dom.dragAndDrop($handles.eq(1), $modal.find("tbody tr").first(), {
            position: "top",
        });

        assert.verifySteps([
            "onchange",
            "name_search", // to display results in the dropdown
            "get_views", // list view in dialog
            "/web/dataset/search_read", // to display results in the dialog
            "/web/dataset/resequence", // resequencing lines
            "read",
        ]);
    });

    QUnit.test("many2one dropdown disappears on scroll", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].display_name =
            "Veeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeery Loooooooooooooooooooooooooooooooooooooooooooong Naaaaaaaaaaaaaaaaaaaaaaaaaaaaaaame";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <div style="height: 2000px;">
                        <field name="trululu" />
                    </div>
                </form>
            `,
        });

        await click(target, ".o_form_button_edit");

        await click(target, ".o_field_many2one input");
        assert.containsOnce(target, ".o_field_many2one .dropdown-menu");

        const dropdown = document.querySelector(".o_field_many2one .dropdown-menu");
        await triggerScroll(dropdown, { left: 50 }, false);
        assert.strictEqual(dropdown.scrollLeft, 50, "a scroll happened");
        assert.containsOnce(target, ".o_field_many2one .dropdown-menu");

        await triggerScroll(target, { top: 50 });
        assert.containsNone(target, ".o_field_many2one .dropdown-menu");
    });

    QUnit.skipWOWL("x2many list sorted by many2one", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.models.partner.fields.trululu.sortable = true;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="id" />
                            <field name="trululu" />
                        </tree>
                    </field>
                </form>
            `,
        });

        assert.strictEqual(
            target.querySelectorAll(".o_data_row .o_list_number").textContent,
            "124",
            "should have correct order initially"
        );

        await click(target, ".o_list_view thead th:nth(1)");

        assert.strictEqual(
            target.querySelectorAll(".o_data_row .o_list_number").textContent,
            "412",
            "should have correct order (ASC)"
        );

        await click(target, ".o_list_view thead th:nth(1)");

        assert.strictEqual(
            target.querySelectorAll(".o_data_row .o_list_number").textContent,
            "214",
            "should have correct order (DESC)"
        );
    });

    QUnit.skipWOWL("one2many with extra field from server not in form", async function (assert) {
        assert.expect(6);

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name" />
                </form>
            `,
            "partner,false,search": `<search />`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="datetime" />
                            <field name="display_name" />
                        </tree>
                    </field>
                </form>
            `,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    args[1].p[0][2].datetime = "2018-04-05 12:00:00";
                }
            },
        });

        await click(target, ".o_form_button_edit");

        var x2mList = target.querySelectorAll(".o_field_x2many_list[name=p]");

        // Add a record in the list
        await click(x2mList.find(".o_field_x2many_list_row_add a"));

        var modal = document.body.querySelector(".modal-lg");

        var nameInput = modal.find("input.o_input[name=display_name]");
        await testUtils.fields.editInput(nameInput, "michelangelo");

        // Save the record in the modal (though it is still virtual)
        await click(modal.find(".btn-primary").first());

        assert.equal(
            x2mList.find(".o_data_row").length,
            1,
            "There should be 1 records in the x2m list"
        );

        var newlyAdded = x2mList.find(".o_data_row").eq(0);

        assert.equal(
            newlyAdded.find(".o_data_cell").first().textContent,
            "",
            "The create_date field should be empty"
        );
        assert.equal(
            newlyAdded.find(".o_data_cell").eq(1).textContent,
            "michelangelo",
            "The display name field should have the right value"
        );

        // Save the whole thing
        await click(target, ".o_form_button_save");

        x2mList = target.querySelectorAll(".o_field_x2many_list[name=p]");

        // Redo asserts in RO mode after saving
        assert.equal(
            x2mList.find(".o_data_row").length,
            1,
            "There should be 1 records in the x2m list"
        );

        newlyAdded = x2mList.find(".o_data_row").eq(0);

        assert.equal(
            newlyAdded.find(".o_data_cell").first().textContent,
            "04/05/2018 12:00:00",
            "The create_date field should have the right value"
        );
        assert.equal(
            newlyAdded.find(".o_data_cell").eq(1).textContent,
            "michelangelo",
            "The display name field should have the right value"
        );
    });

    QUnit.skipWOWL(
        "one2many with extra field from server not in (inline) form",
        async function (assert) {
            assert.expect(1);

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="datetime" />
                                <field name="display_name" />
                            </tree>
                            <form>
                                <field name="display_name" />
                            </form>
                        </field>
                    </form>
                `,
            });

            await click(target, ".o_form_button_edit");

            var x2mList = target.querySelectorAll(".o_field_x2many_list[name=p]");

            // Add a record in the list
            await click(x2mList.find(".o_field_x2many_list_row_add a"));

            var modal = document.body.querySelector(".modal-lg");

            var nameInput = modal.find("input.o_input[name=display_name]");
            await testUtils.fields.editInput(nameInput, "michelangelo");

            // Save the record in the modal (though it is still virtual)
            await click(modal.find(".btn-primary").first());

            assert.equal(
                x2mList.find(".o_data_row").length,
                1,
                "There should be 1 records in the x2m list"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many with extra X2many field from server not in inline form",
        async function (assert) {
            assert.expect(1);

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="turtles" />
                                <field name="display_name" />
                            </tree>
                            <form>
                                <field name="display_name" />
                            </form>
                        </field>
                    </form>
                `,
            });

            await click(target, ".o_form_button_edit");

            var x2mList = target.querySelectorAll(".o_field_x2many_list[name=p]");

            // Add a first record in the list
            await click(x2mList.find(".o_field_x2many_list_row_add a"));

            // Save & New
            await click(document.body.querySelector(".modal-lg").find(".btn-primary").eq(1));

            // Save & Close
            await click(document.body.querySelector(".modal-lg").find(".btn-primary").eq(0));

            assert.equal(
                x2mList.find(".o_data_row").length,
                2,
                "There should be 2 records in the x2m list"
            );
        }
    );

    QUnit.skipWOWL("one2many invisible depends on parent field", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="product_id" />
                        </group>
                        <notebook>
                            <page string="Partner page">
                                <field name="bar" />
                                <field name="p">
                                    <tree>
                                        <field name="foo" attrs="{'column_invisible': [('parent.product_id', '!=', False)]}" />
                                        <field name="bar" attrs="{'column_invisible': [('parent.bar', '=', False)]}" />
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>
            `,
        });
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await click(target, ".o_form_button_edit");
        await click(target, '.o_field_many2one[name="product_id"] input');
        await click($("li.ui-menu-item a:contains(xpad)").trigger("mouseenter"));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column when the product_id is set"
        );
        await testUtils.fields.editAndTrigger(
            target.querySelectorAll('.o_field_many2one[name="product_id"] input'),
            "",
            "keyup"
        );
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many when product_id is not set"
        );
        await click(target, '.o_field_boolean[name="bar"] input');
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column after the value change"
        );
    });

    QUnit.skipWOWL(
        "one2many column visiblity depends on onchange of parent field",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[0].bar = false;

            serverData.models.partner.onchanges.p = (obj) => {
                // set bar to true when line is added
                if (obj.p.length > 1 && obj.p[1][2].foo === "New line") {
                    obj.bar = true;
                }
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="bar" />
                        <field name="p">
                            <tree editable="bottom">
                                <field name="foo" />
                                <field name="int_field" attrs="{'column_invisible': [('parent.bar', '=', False)]}" />
                            </tree>
                        </field>
                    </form>
                `,
            });

            // bar is false so there should be 1 column
            assert.containsOnce(
                form,
                "th:not(.o_list_record_remove_header)",
                "should be only 1 column ('foo') in the one2many"
            );
            assert.containsOnce(form, ".o_list_view .o_data_row", "should contain one row");

            await click(target, ".o_form_button_edit");

            // add a new o2m record
            await click(target, ".o_field_x2many_list_row_add a");
            target.querySelectorAll(".o_field_one2many input:first").focus();
            await testUtils.fields.editInput(
                target.querySelectorAll(".o_field_one2many input:first"),
                "New line"
            );
            await click(form);

            assert.containsN(
                form,
                "th:not(.o_list_record_remove_header)",
                2,
                "should be 2 columns('foo' + 'int_field')"
            );
        }
    );

    QUnit.skipWOWL("one2many column_invisible on view not inline", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];
        serverData.views = {
            "partner,false,list": `
                <list>
                    <field name="foo" attrs="{'column_invisible': [('parent.product_id', '!=', False)]}" />
                    <field name="bar" attrs="{'column_invisible': [('parent.bar', '=', False)]}" />
                </list>
            `,
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="product_id" />
                        </group>
                        <notebook>
                            <page string="Partner page">
                                <field name="bar" />
                                <field name="p" />
                            </page>
                        </notebook>
                    </sheet>
                </form>
            `,
        });
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await click(target, ".o_form_button_edit");
        await click(target, '.o_field_many2one[name="product_id"] input');
        await click($("li.ui-menu-item a:contains(xpad)").trigger("mouseenter"));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column when the product_id is set"
        );
        await testUtils.fields.editAndTrigger(
            target.querySelectorAll('.o_field_many2one[name="product_id"] input'),
            "",
            "keyup"
        );
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many when product_id is not set"
        );
        await click(target, '.o_field_boolean[name="bar"] input');
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column after the value change"
        );
        form.destroy();
    });
});
