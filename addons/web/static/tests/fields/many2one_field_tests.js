/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import {
    click,
    clickDiscard,
    clickDropdown,
    clickEdit,
    clickSave,
    dragAndDrop,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerEvents,
    triggerScroll,
} from "../helpers/utils";
import {
    applyFilter,
    editSearch,
    toggleAddCustomFilter,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenuItem,
    validateSearch,
} from "../search/helpers";
import { makeView, setupViewRegistries } from "../views/helpers";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const serviceRegistry = registry.category("services");

let serverData;
let target;

// WOWL remove after adapting tests
let testUtils, Widget, BasicModel, StandaloneFieldManagerMixin, relationalFields;

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
            target.querySelector(".modal .modal-title").textContent.trim(),
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

        await clickEdit(target);

        // click on the external button (should do an RPC)
        await click(target, ".o_external_button");
        // save and close modal
        await clickSave(target.querySelector(".modal"));
        // save form
        await clickSave(target);
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

            const input = target.querySelector(".modal .o_field_widget[name='foo'] input");
            input.value = "brandon";
            await triggerEvent(input, null, "change");

            // save and close modal
            await clickSave(target.querySelector(".modal"));
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
            mockRPC(route, { method, kwargs }) {
                if (method === "name_get" && kwargs.context.show_address) {
                    return [[4, "aaa\nStreet\nCity ZIP"]];
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
        const namegets = {
            1: "first record\nFirst\nRecord",
            2: "second record\nSecond\nRecord",
            4: "aaa\nAAA\nRecord",
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
            mockRPC(route, { args, kwargs, method }) {
                if (method === "name_get" && kwargs.context.show_address) {
                    return args.map((id) => [id, namegets[id]]);
                }
            },
        });

        await click(target, ".o_form_button_edit");
        const input = target.querySelector(".o_field_widget input");

        assert.strictEqual(input.value, "aaa");
        assert.strictEqual(
            target.querySelector(".o_field_many2one_extra").innerHTML,
            "<span>AAA</span><br><span>Record</span>"
        );

        await editInput(input, null, "first record");
        await click(target.querySelector(".dropdown-menu li"));

        assert.strictEqual(input.value, "first record");
        assert.strictEqual(
            target.querySelector(".o_field_many2one_extra").innerHTML,
            "<span>First</span><br><span>Record</span>"
        );

        await editInput(input, null, "second record");
        await click(target.querySelector(".dropdown-menu li"));

        assert.strictEqual(input.value, "second record");
        assert.strictEqual(
            target.querySelector(".o_field_many2one_extra").innerHTML,
            "<span>Second</span><br><span>Record</span>"
        );
    });

    QUnit.test(
        "show_address works in a view embedded in a view of another type",
        async function (assert) {
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
                mockRPC(route, { kwargs, method, model }) {
                    if (method === "name_get" && kwargs.context.show_address) {
                        return [[2, "second record\nrue morgue\nparis 75013"]];
                    }
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            await click(target, ".o_data_row td.o_data_cell");

            assert.strictEqual(
                target.querySelector('[name="turtle_trululu"]').textContent,
                "second recordrue morgueparis 75013",
                "The partner's address should be displayed"
            );
        }
    );

    QUnit.test(
        "many2one data is reloaded if there is a context to take into account",
        async function (assert) {
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
                mockRPC(route, { kwargs, method, model }) {
                    if (method === "name_get" && kwargs.context.show_address) {
                        return [[2, "second record\nrue morgue\nparis 75013"]];
                    }
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            await click(target.querySelector(".o_data_row td.o_data_cell"));

            assert.strictEqual(
                target.querySelector('.modal [name="turtle_trululu"]').textContent,
                "second recordrue morgueparis 75013",
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

        const modal = target.querySelector(".modal");

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

    QUnit.test(
        "onchanges on many2ones trigger when editing record in form view",
        async function (assert) {
            assert.expect(11);

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
            await editInput(
                target,
                ".modal-body .o_field_widget[name='other_field'] input",
                "wood"
            );

            // save the modal and make sure an onchange is triggered
            await clickSave(target.querySelector(".modal"));
            assert.verifySteps([
                "get_views",
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

            const input = target.querySelector(".o_field_widget[name=trululu] input");

            await editInput(input, null, "");
            await triggerEvent(input, null, "keyup");

            assert.containsNone(
                target,
                ".modal",
                "No save should be triggered when removing value"
            );

            await click(
                target.querySelector(".o_field_widget[name=trululu] .o_m2o_dropdown_option")
            );

            assert.containsOnce(
                target,
                ".modal",
                "Saving should be triggered when selecting a value"
            );
            await click(target, ".modal .btn-primary");
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

        await makeView({
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

        await click(target.querySelector(".o_data_row .o_data_cell"));

        const input = target.querySelector(".o_data_row .o_data_cell input");
        assert.strictEqual(document.activeElement, input, "Input should be focused when activated");

        await editInput(target, ".o_field_widget[name=trululu] input", "ABC");
        await click(target, ".o_field_widget[name=trululu] .o_m2o_dropdown_option_create_edit");

        // At this point, if the focus is correctly registered by the m2o, there
        // should be only one modal (the "Create" one) and none for saving changes.
        assert.containsOnce(target, ".modal", "There should be only one modal");

        await clickDiscard(target.querySelector(".modal"));

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
            target,
            ".dropdown-menu li.o_m2o_dropdown_option",
            "autocomplete should not contains dropdown options"
        );
        assert.containsOnce(
            target,
            ".dropdown-menu li.o_m2o_start_typing",
            "autocomplete should contains start typing option"
        );

        const input = target.querySelector(".o_field_many2one[name='trululu'] input");
        input.value = "abc";
        await triggerEvents(input, null, ["input", "change"]);

        assert.containsN(
            target,
            ".dropdown-menu li.o_m2o_dropdown_option",
            2,
            "autocomplete should contains 2 dropdown options"
        );
        assert.containsNone(
            target,
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

    QUnit.test(
        "empty many2one should not be considered modified on onchange if still empty",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.onchanges = {
                foo: function () {},
            };

            assert.strictEqual(
                serverData.models.partner.records[2].trululu,
                undefined,
                "no value must be provided for trululu to make sure the test works as expected"
            );

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 4, // trululu m2o must be empty
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="trululu" />
                                <field name="foo" /> <!-- onchange will be triggered on this field -->
                            </group>
                        </sheet>
                    </form>
                `,
                mockRPC(route, { method, args }) {
                    if (method === "onchange") {
                        assert.step("onchange");
                        return Promise.resolve({
                            value: {
                                trululu: false,
                            },
                        });
                    } else if (method === "write") {
                        assert.step("write");
                        // non modified trululu should not be sent
                        // as write value
                        assert.deepEqual(args[1], { foo: "3" });
                    }
                },
            });

            await click(target, ".o_form_button_edit");

            // trigger the onchange
            await editInput(target, ".o_field_widget[name='foo'] input", "3");
            assert.verifySteps(["onchange"]);

            // save
            await click(target, ".o_form_button_save");
            assert.verifySteps(["write"]);
        }
    );

    QUnit.test("many2one in edit mode", async function (assert) {
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
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(args[1].trululu, 20, "should write the correct id");
                }
            },
        });

        // the SelectCreateDialog requests the session, so intercept its custom
        // event to specify a fake session to prevent it from crashing
        patchWithCleanup(session.user_context, {});

        await click(target, ".o_form_button_edit");
        await clickDropdown(target, "trululu");

        let dropdown = target.querySelector(".o_field_many2one[name='trululu'] .dropdown-menu");
        assert.isVisible(
            dropdown,
            "clicking on the m2o input should open the dropdown if it is not open yet"
        );
        assert.containsN(
            dropdown,
            "li:not(.o_m2o_dropdown_option)",
            8,
            "autocomplete should contains 8 suggestions"
        );
        assert.containsOnce(
            dropdown,
            "li.o_m2o_dropdown_option",
            'autocomplete should contain "Search More"'
        );
        assert.containsNone(
            dropdown,
            "li.o_m2o_start_typing",
            "autocomplete should not contains start typing option if value is available"
        );

        await click(target.querySelector(".o_field_many2one[name='trululu'] input"));
        assert.containsNone(
            target,
            ".o_field_many2one[name='trululu'] .dropdown-menu",
            "clicking on the m2o input should close the dropdown if it is open"
        );

        // change the value of the m2o with a suggestion of the dropdown
        await selectDropdownItem(target, "trululu", "first record");
        dropdown = target.querySelector(".o_field_many2one[name='trululu'] .dropdown-menu");
        assert.isNotVisible(dropdown, "clicking on a value should close the dropdown");
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "first record",
            "value of the m2o should have been correctly updated"
        );

        // change the value of the m2o with a record in the 'Search More' modal
        await clickDropdown(target, "trululu");
        // click on 'Search More' (mouseenter required by ui-autocomplete)
        dropdown = target.querySelector(".o_field_many2one[name='trululu'] .dropdown-menu");
        await click(dropdown.querySelector(".o_m2o_dropdown_option_search_more"));
        assert.containsOnce(
            target,
            ".modal .o_list_view",
            "should have opened a list view in a modal"
        );
        assert.containsNone(
            target,
            ".modal .o_list_view .o_list_record_selector",
            "there should be no record selector in the list view"
        );
        assert.containsNone(
            target,
            ".modal .modal-footer .o_select_button",
            "there should be no 'Select' button in the footer"
        );
        assert.ok(
            target.querySelectorAll(".modal tbody tr").length > 10,
            "list should contain more than 10 records"
        );
        const modal = target.querySelector(".modal");
        await editInput(modal, ".o_searchview_input", "P");
        await triggerEvent(modal, ".o_searchview_input", "keydown", { key: "Enter" });
        assert.containsN(
            target,
            ".modal tbody tr",
            10,
            "list should be restricted to records containing a P (10 records)"
        );
        // choose a record
        await click(modal.querySelector(".o_data_cell[title='Partner 20']"));
        assert.containsNone(target, ".modal", "should have closed the modal");
        dropdown = target.querySelector(".o_field_many2one[name='trululu'] .dropdown-menu");
        assert.isNotVisible(dropdown, "should have closed the dropdown");
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

    QUnit.test("many2one with co-model whose name field is a many2one", async function (assert) {
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

        await editInput(target, "div[name=product_id] input", "ABC");
        await click(target, "div[name=product_id] .o_m2o_dropdown_option_create_edit");
        assert.containsOnce(target, ".modal .o_form_view");

        // quick create 'new value'
        await editInput(target, "div[name=name] input", "new value");
        await click(target.querySelector("div[name=name] .o_m2o_dropdown_option"));
        assert.strictEqual(
            target.querySelector(".modal .o_field_many2one input").value,
            "new value"
        );

        await clickSave(target.querySelector(".modal"));
        assert.containsNone(target, ".modal .o_form_view");
        assert.strictEqual(target.querySelector(".o_field_many2one input").value, "new value");
    });

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
            target.querySelector("a.o_form_uri").textContent.includes("and some address"),
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
            target.querySelector("a.o_form_uri").textContent.includes("and some address"),
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

    QUnit.test("form: quick create then save directly", async function (assert) {
        assert.expect(5);

        const def = makeDeferred();
        const newRecordId = 5; // with the current records, the created record will be assigned id 5

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
            async mockRPC(route, { args, method }) {
                if (method === "name_create") {
                    assert.step("name_create");
                    await def;
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

        await editInput(target, ".o_field_widget[name=trululu] input", "b");
        await click(target.querySelector(".ui-menu-item"));
        await click(target, ".o_form_button_save");

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );

        def.resolve();
        await nextTick();

        assert.verifySteps(["create"]);
    });

    QUnit.test(
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

            await editInput(target, ".o_field_widget[name=trululu] input", "beam");
            await click(target.querySelector(".ui-menu-item"));
            assert.verifySteps(["name_create"], "attempt to name_create");
            assert.strictEqual(
                target.querySelector(".o_input_dropdown input").value,
                "",
                "the input should contain no text after search and click"
            );
        }
    );

    QUnit.test("list: quick create then save directly", async function (assert) {
        const def = makeDeferred();
        const newRecordId = 5;

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="trululu" />
                </tree>
            `,
            async mockRPC(route, { args, method }) {
                if (method === "name_create") {
                    assert.step("name_create");
                    await def;
                }
                if (method === "create") {
                    assert.step("create");
                    assert.strictEqual(args[0].trululu, newRecordId);
                }
            },
        });

        assert.containsN(target, ".o_data_row", 3);

        await click(target, ".o_list_button_add");

        assert.containsN(target, ".o_data_row", 4);

        await editInput(target, ".o_field_widget[name=trululu] input", "b");
        await click(target.querySelector(".ui-menu-item"));

        await clickSave(target);

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );
        assert.containsN(target, ".o_data_row", 4);

        def.resolve();
        await nextTick();

        assert.verifySteps(["create"]);
        assert.containsN(target, ".o_data_row", 4);
        assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").textContent, "b");
    });

    QUnit.test("list in form: quick create then save directly", async function (assert) {
        assert.expect(6);

        const def = makeDeferred();
        const newRecordId = 5; // with the current records, the created record will be assigned id 5

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
            async mockRPC(route, { args, method }) {
                if (method === "name_create") {
                    assert.step("name_create");
                    await def;
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

        await editInput(target, ".o_field_widget[name=trululu] input", "b");
        await click(target.querySelector(".ui-menu-item"));

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

    QUnit.test("list in form: quick create then add a new line directly", async function (assert) {
        // required many2one inside a one2many list: directly after quick creating
        // a new many2one value (before the name_create returns), click on add an item:
        // at this moment, the many2one has still no value, and as it is required,
        // the row is discarded if a saveLine is requested. However, it should
        // wait for the name_create to return before trying to save the line.
        assert.expect(8);

        serverData.models.partner.onchanges = {
            trululu() {},
        };

        const def = makeDeferred();
        const newRecordId = 5; // with the current records, the created record will be assigned id 5

        await makeView({
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
            async mockRPC(route, { args, method }) {
                if (method === "name_create") {
                    await def;
                }
                if (method === "create") {
                    assert.deepEqual(args[0].p[0][2].trululu, newRecordId);
                }
            },
        });

        await click(target, ".o_field_x2many_list_row_add a");

        await editInput(target, ".o_field_widget[name=trululu] input", "b");
        await click(target.querySelector(".ui-menu-item"));

        await click(target, ".o_field_x2many_list_row_add a");

        assert.containsOnce(target, ".o_data_row", "there should still be only one row");
        assert.hasClass(
            target.querySelector(".o_data_row"),
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
        assert.containsN(target, ".o_data_row", 2, "there should now be 2 rows");
        assert.hasClass(
            target.querySelectorAll(".o_data_row")[1],
            "o_selected_row",
            "the second row should be in edition"
        );

        await clickSave(target);

        assert.containsOnce(
            target,
            ".o_data_row",
            "there should be 1 row saved (the second one was empty and invalid)"
        );
        assert.strictEqual(
            target.querySelector(".o_data_row .o_data_cell").textContent,
            "b",
            "should have the correct m2o value"
        );
    });

    QUnit.test("list in form: create with one2many with many2one", async function (assert) {
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

    QUnit.test(
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

    QUnit.test(
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
                target.querySelector("td.o_data_cell").textContent,
                "new record",
                "should have the correct displayed name"
            );

            assert.containsOnce(
                target,
                "td.o_data_cell .o_required_modifier",
                "should have a required field on this record"
            );
            let requiredElement = target.querySelector("td.o_data_cell .o_required_modifier");
            assert.strictEqual(
                requiredElement.textContent,
                "",
                "should have empty string in the required field on this record"
            );

            click(requiredElement);
            // discard by clicking on body
            click(target);

            assert.containsOnce(target, "tr.o_data_row", "should still have the record in the o2m");
            assert.strictEqual(
                target.querySelector("td.o_data_cell").textContent,
                "new record",
                "should still have the correct displayed name"
            );

            // update selector of required field element
            requiredElement = target.querySelector("td.o_data_cell .o_required_modifier");
            assert.containsOnce(
                target,
                "td.o_data_cell .o_required_modifier",
                "should still have the required field on this record"
            );
            assert.strictEqual(
                requiredElement.textContent,
                "",
                "should still have empty string in the required field on this record"
            );
        }
    );

    QUnit.test("list in form: name_get with unique ids (default_get)", async function (assert) {
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
            [...target.querySelectorAll("td.o_data_cell")].map((cell) => cell.textContent).join(""),
            "MyTrululuMyTrululu",
            "both records should have the correct display_name for trululu field"
        );
    });

    QUnit.test(
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

    QUnit.test(
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

            await makeView({
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
            assert.containsOnce(target, ".o_data_row", "should have a row in the editable list");
            assert.strictEqual(
                target.querySelector("td.o_data_cell").textContent,
                "entry",
                "should have the correct displayed name"
            );
            assert.containsOnce(
                target,
                "td.o_data_cell .o_required_modifier",
                "should have a required field on this record"
            );
            assert.strictEqual(
                target.querySelector("td.o_data_cell .o_required_modifier").textContent,
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            click(target.querySelector("td.o_data_cell .o_required_modifier"));
            // click off so that the required field still stay empty
            click(target);

            // record should not be dropped
            assert.containsOnce(
                target,
                ".o_data_row",
                "should not have dropped record in the editable list"
            );
            assert.strictEqual(
                target.querySelector("td.o_data_cell").textContent,
                "entry",
                "should still have the correct displayed name"
            );
            assert.strictEqual(
                target.querySelector("td.o_data_cell .o_required_modifier").textContent,
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

            await makeView({
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
            assert.containsNone(target, ".o_data_row", "should have no row in the editable list");

            // select product_id to force on_change in editable list
            await click(target, ".o_field_widget[name=product_id] .o_input");
            await click(target.querySelector(".ui-menu-item"));

            // check that there is a record in the editable list with empty string as required field
            assert.containsOnce(target, ".o_data_row", "should have a row in the editable list");
            assert.strictEqual(
                target.querySelector("td.o_data_cell").textContent,
                "entry",
                "should have the correct displayed name"
            );
            assert.containsOnce(
                target,
                "td.o_data_cell .o_required_modifier",
                "should have a required field on this record"
            );
            const requiredField = target.querySelector("td.o_data_cell .o_required_modifier");
            assert.strictEqual(
                requiredField.textContent,
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            await click(requiredField);
            // click off so that the required field still stay empty
            await click(target);

            // record should not be dropped
            assert.containsOnce(
                target,
                ".o_data_row",
                "should not have dropped record in the editable list"
            );
            assert.strictEqual(
                target.querySelector("td.o_data_cell").textContent,
                "entry",
                "should still have the correct displayed name"
            );
            assert.strictEqual(
                target.querySelector("td.o_data_cell .o_required_modifier").textContent,
                "",
                "should still have empty string in the required field"
            );
        }
    );

    QUnit.test(
        'item dropped on discard with empty required field with "Add an item" (invalid on "ADD")',
        async function (assert) {
            // when a record in a list is added with "Add an item", it should
            // always be dropped on discard if some required field are empty
            // at the record creation.
            assert.expect(6);

            await makeView({
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
            target.querySelector(".o_field_widget.o_field_char[name=display_name] input").value =
                "some text";
            assert.containsOnce(
                target,
                ".o_field_widget.o_field_char[name=display_name]",
                "should have a char field 'display_name' on this record"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o_field_widget.o_field_char[name=display_name]"),
                "o_required_modifier",
                "the char field should not be required on this record"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget.o_field_char[name=display_name] input").value,
                "some text",
                "should have entered text in the char field on this record"
            );
            assert.containsOnce(
                target,
                ".o_field_widget.o_required_modifier[name=trululu]",
                "should have a required field 'trululu' on this record"
            );
            const requiredField = target.querySelector(
                ".o_field_widget.o_required_modifier[name=trululu] input"
            );
            assert.strictEqual(
                requiredField.value.trim(),
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            await click(requiredField);
            // click off so that the required field still stay empty
            await click(target);

            // record should be dropped
            assert.containsNone(
                target,
                ".o_data_row",
                "should have dropped record in the editable list"
            );
        }
    );

    QUnit.test(
        'item not dropped on discard with empty required field with "Add an item" (invalid on "UPDATE")',
        async function (assert) {
            // when a record in a list is added with "Add an item", it should
            // be temporarily added to the list when it is valid (e.g. required
            // fields are non-empty). If the record is updated so that the required
            // field is empty, and it is discarded, then the record should not be
            // dropped.
            assert.expect(8);

            await makeView({
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
                target,
                ".o_data_row",
                "should initially not have any record in the list"
            );

            // Click on "Add an item"
            await click(target, ".o_field_x2many_list_row_add a");
            assert.containsOnce(
                target,
                ".o_data_row",
                "should have a temporary record in the list"
            );

            assert.containsOnce(
                target,
                ".o_field_widget.o_required_modifier[name=trululu] input",
                "should have a required field 'trululu' on this record"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget.o_required_modifier[name=trululu] input")
                    .value,
                "",
                "should have empty string in the required field on this record"
            );

            // add something to required field and leave edit mode of the record
            await click(target, ".o_field_widget.o_required_modifier[name=trululu] input");
            await click(target.querySelector("li.ui-menu-item"));
            await click(target);

            assert.containsOnce(
                target,
                ".o_data_row",
                "should not have dropped valid record when leaving edit mode"
            );
            assert.strictEqual(
                target.querySelector(".o_data_cell .o_required_modifier").textContent,
                "first record",
                "should have put some content in the required field on this record"
            );

            // remove the required field and leave edit mode of the record
            await click(target, ".o_data_row");
            assert.containsOnce(
                target,
                ".o_data_row",
                "should not have dropped record in the list on discard (invalid on UPDATE)"
            );
            assert.strictEqual(
                target.querySelector(".o_data_cell .o_required_modifier").textContent,
                "first record",
                "should keep previous valid required field content on this record"
            );
        }
    );

    // WARNING: this does not seem to be a many2one field test
    QUnit.test("list in form: default_get with x2many create", async function (assert) {
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
            target.querySelector("td.o_data_cell").textContent,
            "brandon is the new timmy",
            "should have created the new record in the m2m with the correct name"
        );
        assert.strictEqual(
            target.querySelector(".o_field_integer input").value,
            "1",
            "should have called and executed the onchange properly"
        );

        // edit the subrecord and save
        displayName = "new value";
        await click(target, ".o_data_cell");
        await editInput(target, ".o_data_cell input", displayName);
        await clickSave(target);
    });

    // WARNING: this does not seem to be a many2one field test
    QUnit.test(
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

            await clickSave(target);
        }
    );

    QUnit.test("list in form: call button in sub view", async function (assert) {
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

        const def = makeDeferred();
        const fakeActionService = {
            start() {
                return {
                    doActionButton(params) {
                        const { name, resModel, resId, resIds } = params;
                        assert.step(name);
                        assert.strictEqual(resModel, "product");
                        assert.strictEqual(resId, 37);
                        assert.deepEqual(resIds, [37]);
                        return def.then(() => {
                            params.onClose();
                        });
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="product_id" />
                        </tree>
                    </field>
                </form>
            `,
            async mockRPC(route, args) {
                if (args.method === "get_formview_id") {
                    return false;
                }
            },
        });

        await clickEdit(target);
        await click(target.querySelector("td.o_data_cell"));
        await click(target, ".o_external_button");
        assert.containsOnce(target, ".modal");

        let buttons = target.querySelectorAll(".modal .o_form_statusbar button");

        await click(buttons[0]);
        assert.verifySteps(["action"]);

        await click(buttons[1]);
        assert.verifySteps([]); // the second button is disabled, it can't be clicked

        def.resolve();
        await nextTick();

        await clickDiscard(target.querySelector(".modal"));
        assert.containsNone(target, ".modal");

        await click(target, ".o_external_button");
        assert.containsOnce(target, ".modal");

        buttons = target.querySelectorAll(".modal .o_form_statusbar button");

        await click(buttons[1]);
        assert.verifySteps(["object"]);
    });

    QUnit.test("X2Many sequence list in modal", async function (assert) {
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

        assert.containsOnce(target, ".modal", "There should be 1 modal opened");
        assert.containsN(
            target,
            ".modal .ui-sortable-handle",
            2,
            "There should be 2 sequence handlers"
        );

        await dragAndDrop(
            ".modal .o_data_row:nth-child(2) .ui-sortable-handle",
            ".modal tbody tr",
            "top"
        );

        // Saving the modal and then the original model
        await clickSave(target.querySelector(".modal"));
        await clickSave(target);

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
                if (method === "name_get" && args[0] === 2) {
                    // LPE: any call_kw route can take either [ids] or id as the first
                    // argument as model.browse() in python supports both
                    // With the basic_model, name_get is passed only an id, not an array
                    return Promise.resolve([[2, "hello world\nso much noise"]]);
                }
            },
        });

        assert.strictEqual(count, 3, "should have done 3 rpcs (get_views, onchange and name_get)");
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

    QUnit.test("quick create on a many2one", async function (assert) {
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

        await triggerEvent(target, ".o_field_many2one input", "focus");
        await editInput(target, ".o_field_many2one input", "new partner");
        await triggerEvent(target, ".o_field_many2one input", "blur");

        assert.strictEqual(
            target.querySelector(".modal .modal-body").textContent.trim(),
            "Create new partner as a new Product?"
        );
        await click(target, ".modal .modal-footer .btn-primary");
    });

    QUnit.test("failing quick create on a many2one", async function (assert) {
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

        await editInput(target, ".o_field_widget[name='product_id'] input", "abcd");
        await click(target.querySelector(".o_field_widget[name='product_id'] .dropdown-item"));

        assert.containsOnce(target, ".modal .o_form_view");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name='name'] input").value,
            "abcd"
        );

        await editInput(target, ".modal .o_field_widget[name='name'] input", "xyz");
        await click(target, ".modal .o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] input").value,
            "xyz"
        );
    });

    QUnit.test("failing quick create on a many2one inside a one2many", async function (assert) {
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
            mockRPC(route, { args, method }) {
                if (method === "name_create") {
                    return Promise.reject();
                }
                if (method === "create") {
                    assert.deepEqual(args[0], { name: "xyz" });
                }
            },
        });

        await click(target, ".o_field_x2many_list_row_add a");
        await editInput(target, ".o_field_widget[name='product_id'] input", "abcd");
        await click(target.querySelector(".o_field_widget[name='product_id'] .dropdown-item"));

        assert.containsOnce(target, ".modal .o_form_view");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name='name'] input").value,
            "abcd"
        );

        await editInput(target, ".modal .o_field_widget[name='name'] input", "xyz");
        await click(target, ".modal .o_form_button_save");
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
        await editInput(target, ".o_field_many2one input", "new product");
        await triggerEvent(target, ".o_field_many2one input", "blur");

        assert.containsOnce(target, ".modal", "there should be one opened modal");

        await click(target, ".modal .modal-footer .btn:not(.btn-primary)");
        assert.containsNone(target, ".modal", "the modal should be closed");
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "",
            "the many2one should not set a value as its creation has been cancelled (with Cancel button)"
        );

        // cancel the many2one creation with Close button
        await editInput(target, ".o_field_many2one input", "new product");
        await triggerEvent(target, ".o_field_many2one input", "blur");

        assert.containsOnce(target, ".modal", "there should be one opened modal");
        await click(target, ".modal .modal-header button");
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "",
            "the many2one should not set a value as its creation has been cancelled (with Close button)"
        );
        assert.containsNone(target, ".modal", "the modal should be closed");

        // select a new value then cancel the creation of the new one --> restore the previous
        await click(target, ".o_field_widget[name=product_id] input");
        await click(target.querySelector(".ui-menu-item"));
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "xphone",
            "should have selected xphone"
        );

        await editInput(target, ".o_field_many2one input", "new product");
        await triggerEvent(target, ".o_field_many2one input", "blur");
        assert.containsOnce(target, ".modal", "there should be one opened modal");

        await click(target, ".modal .modal-footer .btn:not(.btn-primary)");
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "xphone",
            "should have restored the many2one with its previous selected value (xphone)"
        );

        // confirm the many2one creation
        await editInput(target, ".o_field_many2one input", "new product");
        await triggerEvent(target, ".o_field_many2one input", "blur");

        assert.containsOnce(target, ".modal", "there should be one opened modal");

        await click(target, ".modal .modal-footer .btn-primary");
        assert.containsOnce(
            target,
            ".modal .o_form_view",
            "a new modal should be opened and contain a form view"
        );

        await click(target, ".modal .o_form_button_cancel");
    });

    QUnit.test("select a many2one value by focusing out", async function (assert) {
        assert.expect(3);

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

        await editInput(target, ".o_field_many2one input", "xph");
        await triggerEvent(target, ".o_field_many2one input", "blur");

        assert.containsNone(target, ".modal");
        assert.strictEqual(target.querySelector(".o_field_many2one input").value, "xphone");
        assert.containsOnce(target, ".o_external_button");
    });

    QUnit.test("no_create option on a many2one", async function (assert) {
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

        await editInput(target, ".o_field_many2one input", "new partner");
        await triggerEvent(target, ".o_field_many2one input", "blur");

        assert.containsNone(target, ".modal", "should not display the create modal");
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
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
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });

        await click(target, ".o_field_many2one input");
        assert.containsNone(
            target,
            ".o_m2o_dropdown_option.o_m2o_dropdown_option_create",
            "there shouldn't be any option to search and create"
        );

        await click(target.querySelectorAll(".ui-menu-item")[1]);
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "xpad",
            "the correct record should be selected"
        );
        assert.containsOnce(
            target,
            ".o_field_many2one .o_external_button",
            "there should be an external button displayed"
        );

        await click(target, ".o_field_many2one .o_external_button");
        assert.containsOnce(
            target,
            ".modal .o_form_view .o_form_readonly",
            "there should be a readonly form view opened"
        );

        await click(target, ".modal .o_form_button_cancel");

        await editInput(target, ".o_field_many2one input", "new product");
        await triggerEvent(target, ".o_field_many2one input", "blur");
        assert.containsNone(target, ".modal", "should not display the create modal");
    });

    QUnit.test(
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
            await editInput(target, ".o_field_many2one[name=product_id] input", "abc");
            assert.containsNone(
                target,
                ".o_field_many2one[name=product_id] .o_m2o_dropdown_option_create",
                "there shouldn't be any option to search and create"
            );
            assert.containsOnce(
                target,
                ".o_field_many2one[name=product_id] .o_m2o_no_result",
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
                target.querySelector(".modal").length,
                1,
                "should have one modal in body"
            );
            // Check that discarding clears $input
            await click(target.querySelector(".modal .o_form_button_cancel"));
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
                async mockRPC(route, { method }) {
                    if (method === "onchange") {
                        await def;
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
                target.querySelector(".modal").length,
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
                target.querySelector(".modal").length,
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
                async mockRPC(route, { method }) {
                    if (method) {
                        assert.step(method);
                    }
                    if (method === "onchange") {
                        await def;
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
                target.querySelector(".modal").length,
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
                async mockRPC(route, { method }) {
                    if (method) {
                        assert.step(method);
                    }
                    if (method === "onchange") {
                        await def;
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
                target.querySelector(".modal").length,
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

    QUnit.test("many2one in one2many: domain updated by an onchange", async function (assert) {
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
        await editInput(target, "tr.o_selected_row .o_field_widget[name='foo'] input", "new value");

        // add a second row with another domain for the m2o
        domain = [["id", "in", [5]]]; // domain for subrecord 2
        await click(target, ".o_field_x2many_list_row_add a");
        await click(target, ".o_field_widget[name=trululu] input");

        // check again the first row to ensure that the domain hasn't change
        domain = [["id", "in", [10]]]; // domain for subrecord 1 should have been kept
        await click(target.querySelectorAll(".o_data_row .o_data_cell")[1]);
        await click(target, ".o_field_widget[name=trululu] input");
    });

    QUnit.test("search more in many2one: no text in input", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, and there is no text
        // in the input (i.e. no value to search on), we bypass the name_search that is meant to
        // return a list of preselected ids to filter on in the list view (opened in a dialog)
        assert.expect(7);

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
                assert.step(method);
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
            "get_views", // main form view
            "onchange",
            "name_search", // to display results in the dropdown
            "get_views", // list view in dialog
            "web_search_read", // to display results in the dialog
        ]);
    });

    QUnit.test("search more in many2one: text in input", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, and there is some
        // text in the input, we perform a name_search to get a (limited) list of preselected
        // ids and we add a dynamic filter (with those ids) to the search view in the dialog, so
        // that the user can remove this filter to bypass the limit
        assert.expect(13);

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
        await click(target, `.o_field_widget[name="trululu"] input`);

        await editInput(target, ".o_field_widget[name='trululu'] input", "test");
        await click(target, `.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`);

        assert.containsOnce(target, ".modal .o_list_view");
        assert.containsOnce(
            target,
            ".modal .o_cp_searchview .o_facet_values",
            "should have a special facet for the pre-selected ids"
        );

        // remove the filter on ids
        expectedDomain = [];
        await click(target.querySelector(".modal .o_cp_searchview .o_facet_remove"));

        assert.verifySteps([
            "get_views", // main form view
            "onchange",
            "name_search", // empty search, triggered when the user clicks in the input
            "name_search", // to display results in the dropdown
            "name_search", // to get preselected ids matching the search
            "get_views", // list view in dialog
            "web_search_read", // to display results in the dialog
            "web_search_read", // after removal of dynamic filter
        ]);
    });

    QUnit.test("search more in many2one: dropdown click", async function (assert) {
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

        await click(target, `.o_field_widget[name="trululu"] input`);

        await editInput(target, ".o_field_widget[name='trululu'] input", "test");
        await click(target, `.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`);

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
        await clickEdit(target);
        await click(target.querySelectorAll(".o_data_row td")[1]);
        await click(target, ".o_external_button");
        assert.containsOnce(target, ".modal", "should have one modal in body");

        // Changing the 'trululu' value
        await editInput(target, ".modal .o_field_widget[name='display_name'] input", "test");
        await clickSave(target.querySelector(".modal"));

        // Test whether the value has changed
        assert.containsNone(target, ".modal", "the modal should be closed");
        assert.strictEqual(
            target.querySelectorAll(".o_data_cell")[1].textContent,
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

        await editInput(target, ".o_field_widget[name='trululu'] input", "");
        await click(target, `.o_field_widget[name="trululu"] .o_m2o_dropdown_option_search_more`);

        assert.containsOnce(target, ".modal", "There should be 1 modal opened");
        assert.containsN(
            target,
            ".modal .ui-sortable-handle",
            11,
            "There should be 11 sequence handlers"
        );

        await dragAndDrop(
            ".modal .o_data_row:nth-child(2) .ui-sortable-handle",
            ".modal tbody tr",
            "top"
        );

        assert.verifySteps([
            "get_views",
            "onchange",
            "name_search", // to display results in the dropdown
            "get_views", // list view in dialog
            "web_search_read", // to display results in the dialog
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

    QUnit.test("search more in many2one: group and use the pager", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records.push(
            {
                id: 5,
                display_name: "Partner 4",
            },
            {
                id: 6,
                display_name: "Partner 5",
            },
            {
                id: 7,
                display_name: "Partner 6",
            },
            {
                id: 8,
                display_name: "Partner 7",
            },
            {
                id: 9,
                display_name: "Partner 8",
            },
            {
                id: 10,
                display_name: "Partner 9",
            }
        );

        serverData.views = {
            "partner,false,list": `
                <tree limit="7">
                    <field name="display_name" />
                </tree>
            `,
            "partner,false,search": `
                <search><group>
                    <filter name="bar" string="Bar" context="{'group_by': 'bar'}" />
                </group></search>
            `,
        };

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

        await clickEdit(target);

        await selectDropdownItem(target, "trululu", "Search More...");
        const modal = target.querySelector(".modal");
        await toggleGroupByMenu(modal);
        await toggleMenuItem(modal, "Bar");

        await click(modal.querySelectorAll(".o_group_header")[1]);

        assert.containsN(modal, ".o_data_row", 7, "should display 7 records in the first page");
        await click(modal.querySelector(".o_group_header .o_pager_next"));
        assert.containsOnce(modal, ".o_data_row", "should display 1 record in the second page");
    });

    QUnit.skipWOWL("focus when closing many2one modal in many2one modal", async function (assert) {
        assert.expect(12);

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="trululu" />
                </form>
            `,
        };

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
            mockRPC(route, { method }) {
                if (method === "get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });

        // Open many2one modal
        await clickEdit(target);
        await click(target, ".o_external_button");

        let $originalModal = target.querySelector(".modal");
        let $focusedModal = target.querySelector(".modal:not(.o_inactive_modal)");

        assert.containsOnce(target, ".modal", "There should be one modal");
        assert.strictEqual($focusedModal, $originalModal, "Modal is focused");
        assert.hasClass(target, "modal-open", "Modal is said opened");

        // Open many2one modal of field in many2one modal
        await click($originalModal, ".o_external_button");

        let nextModal = target.querySelectorAll(".modal")[1];
        $focusedModal = target.querySelector(".modal:not(.o_inactive_modal)");

        assert.containsN(target, ".modal", 2, "There should be two modals");
        assert.strictEqual($focusedModal, nextModal, "Last modal is focused");
        assert.hasClass(target, "modal-open", "Modal is said opened");

        // Close second modal
        await click(nextModal, "button[class='close']");
        $focusedModal = document.activeElement.closest(".modal");

        assert.containsOnce(target, ".modal", "There should be one modal");
        assert.strictEqual(
            $originalModal,
            target.querySelector(".modal"),
            "First modal is still opened"
        );
        assert.strictEqual($focusedModal, $originalModal, "Modal is focused");
        assert.hasClass(target, "modal-open", "Modal is said opened");

        // Close first modal
        await click($originalModal, "button[class='close']");
        assert.containsNone(target, ".modal", "There should be no modal");
        assert.doesNotHaveClass(target, "modal-open", "Modal is not said opened");
    });

    QUnit.test("search more pager is reset when doing a new search", async function (assert) {
        assert.expect(6);

        serverData.models.partner.fields.datetime.searchable = true;
        serverData.models.partner.records.push(
            ...new Array(170).fill().map((_, i) => ({ id: i + 10, name: "Partner " + i }))
        );
        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>
            `,
            "partner,false,search": `
                <search>
                    <field name="datetime"/>
                    <field name="display_name"/>
                </search>
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
                            <field name="trululu"/>
                        </group>
                    </sheet>
                </form>`,
        });

        await clickEdit(target);

        await selectDropdownItem(target, "trululu", "Search More...");

        const modal = target.querySelector(".modal");
        await click(modal, ".o_pager_next");

        assert.strictEqual(
            modal.querySelector(".o_pager_limit").textContent,
            "173",
            "there should be 173 records"
        );
        assert.strictEqual(
            modal.querySelector(".o_pager_value").textContent,
            "81-160",
            "should display the second page"
        );
        assert.containsN(modal, "tr.o_data_row", 80, "should display 80 record");

        await editSearch(modal, "first");
        await validateSearch(modal);

        assert.strictEqual(
            modal.querySelector(".o_pager_limit").textContent,
            "1",
            "there should be 1 record"
        );
        assert.strictEqual(
            modal.querySelector(".o_pager_value").textContent,
            "1-1",
            "should display the first page"
        );
        assert.containsOnce(modal, "tr.o_data_row", "should display 1 record");
    });
});
