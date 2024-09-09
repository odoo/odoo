/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import {
    addRow,
    click,
    clickCreate,
    clickDiscard,
    clickM2OHighlightedItem,
    clickOpenM2ODropdown,
    clickOpenedDropdownItem,
    clickSave,
    dragAndDrop,
    editInput,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    removeRow,
    selectDropdownItem,
    triggerEvent,
    triggerEvents,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeView, makeViewInDialog, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { getNextTabableElement } from "@web/core/utils/ui";
import { session } from "@web/session";
import { Record } from "@web/model/relational_model/record";
import { getPickerCell } from "../../core/datetime/datetime_test_helpers";
import { makeServerError } from "@web/../tests/helpers/mock_server";
import { errorService } from "../../../src/core/errors/error_service";
import { onWillDestroy, onWillStart, reactive, useState } from "@odoo/owl";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

const serviceRegistry = registry.category("services");

let serverData;
let target;

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
                        turtle_qux: {
                            string: "Qux",
                            type: "float",
                            digits: [16, 1],
                            required: true,
                            default: 1.5,
                        },
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
                            turtle_qux: 9.8,
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
    });

    QUnit.module("One2ManyField");

    QUnit.test(
        "New record with a o2m also with 2 new records, ordered, and resequenced",
        async function (assert) {
            // Needed to have two new records in a single stroke
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [
                        [0, 0, { trululu: false }],
                        [0, 0, { trululu: false }],
                    ];
                },
            };

            let startAssert = false;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree editable="bottom" default_order="int_field">
                                <field name="int_field" widget="handle"/>
                                <field name="trululu"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (startAssert) {
                        assert.step(args.method + " " + args.model);
                    }
                },
                resId: 1,
            });

            startAssert = true;

            await clickCreate(target);

            // change the int_field through drag and drop
            // that way, we'll trigger the sorting and the display_name read
            // of the lines of "p"
            await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr", "top");

            assert.verifySteps(["onchange partner"]);
        }
    );

    QUnit.test("one2many in a list x2many editable use the right context", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="int_field" widget="handle"/>
                                <field name="trululu" context="{'my_context': 'list'}" />
                            </tree>
                            <form>
                                <field name="trululu"  context="{'my_context': 'form'}"/>
                            </form>
                        </field>
                    </form>`,
            mockRPC(route, args) {
                if (args.method === "name_create") {
                    assert.step(`name_create ${args.kwargs.context.my_context}`);
                }
            },
            resId: 1,
        });

        await addRow(target, ".o_field_x2many_list");
        await editInput(target, "[name='trululu'] input", "new partner");
        await selectDropdownItem(target, "trululu", 'Create "new partner"');

        assert.verifySteps(["name_create list"]);
    });

    QUnit.test(
        "one2many in a list x2many non-editable use the right context",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="int_field" widget="handle"/>
                                <field name="trululu" context="{'my_context': 'list'}" />
                            </tree>
                            <form>
                                <field name="trululu"  context="{'my_context': 'form'}"/>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "name_create") {
                        assert.step(`name_create ${args.kwargs.context.my_context}`);
                    }
                },
                resId: 1,
            });

            await addRow(target, ".o_field_x2many_list");
            await editInput(target, "[name='trululu'] input", "new partner");
            await selectDropdownItem(target, "trululu", 'Create "new partner"');

            assert.verifySteps(["name_create form"]);
        }
    );

    QUnit.test("O2M field without relation_field", async function (assert) {
        delete serverData.models.partner.fields.p.relation_field;

        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo" invisible="1"/>
                            <field name="display_name" />
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await addRow(target, ".o_field_x2many_list");
        assert.containsOnce(target, ".o_dialog");
    });

    QUnit.test(
        "O2M List with pager, decoration and default_order: add and cancel adding",
        async function (assert) {
            // The decoration on the list implies that its condition will be evaluated
            // against the data of the field (actual records *displayed*)
            // If one data is wrongly formed, it will crash
            // This test adds then cancels a record in a paged, ordered, and decorated list
            // That implies prefetching of records for sorting
            // and evaluation of the decoration against *visible records*

            serverData.models.partner.records[0].p = [2, 4];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom" limit="1" decoration-muted="foo != False" default_order="display_name">
                                <field name="foo" invisible="1"/>
                                <field name="display_name" />
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            await addRow(target, ".o_field_x2many_list");

            assert.containsN(
                target,
                ".o_field_x2many_list .o_data_row",
                2,
                "There should be 2 rows"
            );

            const expectedSelectedRow = target.querySelectorAll(
                ".o_field_x2many_list .o_data_row"
            )[1];
            const actualSelectedRow = target.querySelector(".o_selected_row");
            assert.equal(
                actualSelectedRow[0],
                expectedSelectedRow[0],
                "The selected row should be the new one"
            );

            // Cancel Creation
            triggerEvent(actualSelectedRow, "input", "keydown", { key: "Escape" });
            await nextTick();
            assert.containsOnce(
                target,
                ".o_field_x2many_list .o_data_row",
                "There should be 1 row"
            );
        }
    );

    QUnit.test("O2M with parented m2o and domain on parent.m2o", async function (assert) {
        assert.expect(7);

        // Records in an o2m can have a m2o pointing to themselves.
        // In that case, a domain evaluation on that field followed by name_search
        // shouldn't send virtual_ids to the server.

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        serverData.models.turtle.fields.parent_id = {
            string: "Parent",
            type: "many2one",
            relation: "turtle",
        };
        serverData.views = {
            "turtle,false,form": `
                <form>
                    <field name="parent_id"/>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="parent_id"/>
                        </tree>
                        <form>
                            <field name="parent_id" domain="[('id', 'in', parent.turtles)]"/>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, { kwargs }) {
                if (route === "/web/dataset/call_kw/turtle/name_search") {
                    assert.deepEqual(kwargs.args, [["id", "in", []]]);
                    assert.deepEqual(JSON.stringify(kwargs.args), '[["id","in",[]]]');
                }
            },
        });

        await addRow(target);

        await clickOpenM2ODropdown(target, "parent_id");
        await editInput(target, ".o_field_widget[name=parent_id] input", "ABC");
        await clickOpenedDropdownItem(target, "parent_id", "Create and edit...");

        await click(target, ".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save");
        await click(target, ".o_dialog:not(.o_inactive_modal) .o_form_button_save_new");

        assert.containsOnce(
            target,
            ".o_data_row",
            "The main record should have the new record in its o2m"
        );

        await click(target, ".o_field_many2one input");
    });

    QUnit.test(
        'O2M with buttons with attr "special" in dialog close the dialog',
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="bar"/>
                        </tree>
                        <form>
                            <field name="bar"/>
                            <footer>
                                <button special="cancel" data-hotkey="x" string="Cancel" class="btn-secondary"/>
                            </footer>
                        </form>
                    </field>
                </form>`,
            });

            await addRow(target);
            assert.containsOnce(target, ".o_dialog");

            assert.strictEqual(document.querySelector(".modal .btn").innerText, "Cancel");

            await click(target, ".modal .btn");
            assert.containsNone(target, ".o_dialog");
        }
    );

    QUnit.test("O2M modal buttons are disabled on click", async function (assert) {
        // Records in an o2m can have a m2o pointing to themselves.
        // In that case, a domain evaluation on that field followed by name_search
        // shouldn't send virtual_ids to the server.

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        serverData.models.turtle.fields.parent_id = {
            string: "Parent",
            type: "many2one",
            relation: "turtle",
        };
        serverData.views = {
            "turtle,false,form": `
                <form>
                    <field name="parent_id"/>
                </form>`,
        };
        const def = makeDeferred();
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="parent_id"/>
                        </tree>
                        <form>
                            <field name="parent_id"/>
                        </form>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                if (args.method === "web_save") {
                    await def;
                }
            },
        });

        await addRow(target);

        await clickOpenM2ODropdown(target, "parent_id");
        await editInput(target, ".o_field_widget[name=parent_id] input", "ABC");
        await clickOpenedDropdownItem(target, "parent_id", "Create and edit...");
        await click(
            target.querySelector(
                ".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save"
            )
        );
        assert.strictEqual(
            target
                .querySelector(".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save")
                .getAttribute("disabled"),
            "1"
        );
        def.resolve();
        await nextTick();
        // close all dialogs
        await click(
            target.querySelector(
                ".o_dialog:not(.o_inactive_modal) .modal-footer .o_form_button_save"
            )
        );
        await nextTick();
        assert.containsNone(target, ".o_dialog .o_form_view");
    });

    QUnit.test(
        "clicking twice on a record in a one2many will open it once",
        async function (assert) {
            serverData.views = {
                "turtle,false,form": `
                <form>
                    <field name="turtle_foo"/>
                </form>`,
            };

            const def = makeDeferred();
            let firstRead = true;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
                async mockRPC(route, { method, model }) {
                    if (method === "web_read" && model === "turtle") {
                        assert.step("web_read turtle");
                        if (!firstRead) {
                            await def;
                        }
                        firstRead = false;
                    }
                },
            });
            await click(target, ".o_data_cell");
            await click(target, ".o_data_cell");
            def.resolve();
            await nextTick();
            assert.containsOnce(target, ".modal");

            await click(target, ".modal .btn-close");
            assert.containsNone(target, ".modal");

            await click(target, ".o_data_cell");
            assert.containsOnce(target, ".modal");

            assert.verifySteps(["web_read turtle"]);
        }
    );

    QUnit.test("resequence a x2m in a form view dialog from another x2m", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="partner_ids">
                                <tree editable="top">
                                    <field name="int_field" widget="handle"/>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "write") {
                    assert.deepEqual(Object.keys(args.args[1]), ["turtles"]);
                    assert.strictEqual(args.args[1].turtles.length, 1);
                    assert.deepEqual(args.args[1].turtles[0], [
                        1,
                        2,
                        {
                            partner_ids: [
                                [1, 2, { int_field: 0 }],
                                [1, 4, { int_field: 1 }],
                            ],
                        },
                    ]);
                }
            },
        });
        assert.verifySteps(["get_views", "web_read"]);

        await click(target, ".o_data_cell");
        assert.containsOnce(target, ".modal");
        assert.deepEqual(
            [...target.querySelectorAll(".modal [name='display_name']")].map(
                (el) => el.textContent
            ),
            ["aaa", "second record"]
        );
        assert.verifySteps(["web_read"]);

        await dragAndDrop(".modal tr:nth-child(2) .o_handle_cell", "tbody tr", "top");
        assert.deepEqual(
            [...target.querySelectorAll(".modal [name='display_name']")].map(
                (el) => el.textContent
            ),
            ["second record", "aaa"]
        );
        assert.verifySteps([]);

        await clickSave(target.querySelector(".modal"));
        await clickSave(target);
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("one2many list editable with cell readonly modifier", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].turtles = [1, 2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="turtles" invisible="1"/>
                            <field name="foo" readonly="turtles"/>
                            <field name="qux" readonly="turtles"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.deepEqual(
                        args.args[1].p[0][2],
                        { foo: "ff", qux: 99, turtles: [] },
                        "The right values should be written"
                    );
                }
            },
        });
        await addRow(target);

        const targetInput = target.querySelector(".o_selected_row [name=foo] input");
        assert.equal(
            targetInput,
            document.activeElement,
            "The first input of the line should have the focus"
        );

        // Simulating hitting the 'f' key twice
        targetInput.value = "f";
        await triggerEvent(targetInput, null, "input");
        targetInput.value = "ff";
        await triggerEvent(targetInput, null, "input");

        assert.equal(
            targetInput,
            document.activeElement,
            "The first input of the line should still have the focus"
        );

        // Simulating a TAB key
        triggerHotkey("Tab");
        await triggerEvent(targetInput, null, "change");
        await nextTick();
        const secondTarget = target.querySelector(".o_selected_row [name=qux] input");
        secondTarget.value = 9;
        await triggerEvent(secondTarget, null, "input");
        secondTarget.value = 99;
        await triggerEvent(secondTarget, null, "input");

        await triggerEvent(secondTarget, null, "change");
        await clickSave(target);
    });

    QUnit.test(
        "one2many wait for the onchange of the resequenced finish before save",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.records[0].p = [1, 2];
            serverData.models.partner.onchanges = {
                p: function (obj) {
                    obj.p = [[1, 2, { qux: 99 }]];
                },
            };
            const def = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="int_field" widget="handle"/>
                            <field name="foo"/>
                            <field name="qux"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
                async mockRPC(route, args) {
                    if (args.method === "onchange") {
                        await def;
                        assert.step("onchange");
                    }
                    if (args.method === "web_save") {
                        assert.step("web_save");
                        assert.deepEqual(args.args[1].p, [
                            [1, 1, { int_field: 9 }],
                            [1, 2, { int_field: 10, qux: 99 }],
                        ]);
                    }
                },
            });
            // Drag and drop the second line in first position
            await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr", "top");
            await clickSave(target);

            // resolve the onchange promise
            def.resolve();
            await nextTick();
            assert.verifySteps(["onchange", "web_save"]);
        }
    );

    QUnit.test("one2many basic properties", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="Partner page">
                                <field name="p">
                                    <tree>
                                        <field name="foo"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.verifySteps(["get_views", "web_read"]);
        assert.containsOnce(target, ".o_field_x2many_list_row_add");
        assert.hasAttrValue(target.querySelector(".o_field_x2many_list_row_add"), "colspan", "2");
        assert.containsOnce(target, "td.o_list_record_remove");
    });

    QUnit.test("transferring class attributes in one2many sub fields", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_foo" class="hey"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.containsOnce(target, "td.hey");

        await click(target.querySelector("td.o_data_cell"));
        assert.containsOnce(target, 'td.hey div[name="turtle_foo"] input'); // WOWL to check! hey on input?
    });

    QUnit.test("one2many with date and datetime", async function (assert) {
        const originalZone = luxon.Settings.defaultZone;
        luxon.Settings.defaultZone = luxon.FixedOffsetZone.instance(120);
        registerCleanup(() => {
            luxon.Settings.defaultZone = originalZone;
        });
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="Partner page">
                                <field name="p">
                                    <tree>
                                        <field name="date"/>
                                        <field name="datetime"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.strictEqual(target.querySelector("td").textContent, "01/25/2017");
        assert.strictEqual(target.querySelectorAll("td")[1].textContent, "12/12/2016 12:55:05");
    });

    QUnit.test("rendering with embedded one2many", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="P page">
                                <field name="p">
                                    <tree>
                                        <field name="foo"/>
                                        <field name="bar"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        const firstHeader = target.querySelector("thead th");
        assert.strictEqual(firstHeader.textContent, "Foo");
        const firstValue = target.querySelector("tbody td");
        assert.strictEqual(firstValue.textContent, "blip");
    });

    QUnit.test(
        "use the limit attribute in arch (in field o2m inline tree view)",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.model === "turtle") {
                        assert.deepEqual(args.args[0], [1, 2]);
                    }
                },
            });
            assert.containsN(target, ".o_data_row", 2);
        }
    );

    QUnit.test("nested x2manys with inline form, but not list", async function (assert) {
        serverData.views = {
            "turtle,false,list": `<tree><field name="turtle_foo"/></tree>`,
            "partner,false,list": `<tree><field name="foo"/></tree>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <form>
                            <field name="turtle_foo"/>
                            <field name="partner_ids">
                                <form>
                                    <field name="foo"/>
                                </form>
                            </field>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_data_row");

        await click(target, ".o_data_row .o_data_cell");
        assert.containsOnce(target, ".o_dialog");
        assert.containsN(target.querySelector(".o_dialog"), ".o_data_row", 2);
    });

    QUnit.test(
        "use the limit attribute in arch (in field o2m non inline tree view)",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            serverData.views = {
                "turtle,false,list": `<tree limit="2"><field name="turtle_foo"/></tree>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="turtles" widget="one2many"/></form>`,
                resId: 1,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "web_read") {
                        assert.deepEqual(args.kwargs.specification, {
                            display_name: {},
                            turtles: {
                                fields: {
                                    turtle_foo: {},
                                },
                                limit: 2,
                                order: "",
                            },
                        });
                    }
                },
            });
            assert.containsN(target, ".o_data_row", 2);
            assert.verifySteps(["get_views", "get_views", "web_read"]);
        }
    );

    QUnit.test("one2many with default_order on view not inline", async function (assert) {
        serverData.models.partner.records[0].turtles = [1, 2, 3];
        serverData.views = {
            "turtle,false,list": `
                <tree default_order="turtle_foo">
                    <field name="turtle_int"/>
                    <field name="turtle_foo"/>
                </tree>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="Turtles">
                                <field name="turtles" widget="one2many"/>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_one2many .o_data_cell")].map(
                (el) => el.textContent
            ),
            ["9", "blip", "21", "kawa", "0", "yop"]
        );
    });

    QUnit.test("embedded one2many with widget", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="P page">
                                <field name="p">
                                    <tree>
                                        <field name="int_field" widget="handle"/>
                                        <field name="foo"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, "span.o_row_handle");
    });

    QUnit.test("embedded one2many with handle widget", async function (assert) {
        serverData.models.partner.records[0].turtles = [1, 2, 3];
        serverData.models.partner.onchanges = {
            turtles: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree default_order="turtle_int">
                            <field name="turtle_int" widget="handle"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange");
                }
            },
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell.o_list_char")].map((el) => el.innerText),
            ["yop", "blip", "kawa"]
        );

        // Drag and drop the second line in first position
        await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr", "top");

        assert.verifySteps(["onchange"]);

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell.o_list_char")].map((el) => el.innerText),
            ["blip", "yop", "kawa"]
        );

        await clickSave(target);

        assert.deepEqual(
            serverData.models.turtle.records.map((r) => {
                return {
                    id: r.id,
                    turtle_foo: r.turtle_foo,
                    turtle_int: r.turtle_int,
                };
            }),
            [
                { id: 1, turtle_foo: "yop", turtle_int: 1 },
                { id: 2, turtle_foo: "blip", turtle_int: 0 },
                { id: 3, turtle_foo: "kawa", turtle_int: 21 },
            ]
        );

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell.o_list_char")].map((el) => el.innerText),
            ["blip", "yop", "kawa"]
        );
    });

    QUnit.test("onchange for embedded one2many in a one2many", async function (assert) {
        assert.expect(3);

        serverData.models.turtle.fields.partner_ids.type = "one2many";
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.partner.records[0].turtles = [1];

        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [
                    [
                        1,
                        1,
                        {
                            partner_ids: [[4, 2]],
                        },
                    ],
                ];
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    const expectedResultTurtles = [
                        [1, 1, { turtle_foo: "hop", partner_ids: [[4, 2]] }],
                    ];
                    assert.deepEqual(args.args[1].turtles, expectedResultTurtles);
                }
            },
        });

        assert.deepEqual(target.querySelector(".o_field_many2many_tags").innerText.split("\n"), [
            "first record",
        ]);

        await click(target.querySelectorAll(".o_data_cell")[1]);
        await editInput(target, ".o_selected_row .o_field_widget[name=turtle_foo] input", "hop");

        assert.deepEqual(target.querySelector(".o_field_many2many_tags").innerText.split("\n"), [
            "first record",
            "second record",
        ]);

        await clickSave(target);
    });

    QUnit.test(
        "onchange for embedded one2many in a one2many with a second page",
        async function (assert) {
            serverData.models.turtle.fields.partner_ids.type = "one2many";
            serverData.models.turtle.records[0].partner_ids = [1];
            // we need a second page, so we set two records and only display one per page
            serverData.models.partner.records[0].turtles = [1, 2];

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [
                            1,
                            1,
                            {
                                partner_ids: [[4, 2]],
                            },
                        ],
                        [
                            1,
                            2,
                            {
                                turtle_foo: "blip",
                                partner_ids: [[4, 1]],
                            },
                        ],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom" limit="1">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        const expectedResultTurtles = [
                            [1, 1, { turtle_foo: "hop", partner_ids: [[4, 2]] }],
                            [
                                1,
                                2,
                                {
                                    partner_ids: [[4, 1]],
                                    turtle_foo: "blip",
                                },
                            ],
                        ];
                        assert.deepEqual(args.args[1].turtles, expectedResultTurtles);
                    }
                },
            });

            await click(target.querySelectorAll(".o_data_cell")[1]);
            await editInput(
                target,
                ".o_selected_row .o_field_widget[name=turtle_foo] input",
                "hop"
            );
            await clickSave(target);
        }
    );

    QUnit.test(
        "onchange for embedded one2many in a one2many updated by server",
        async function (assert) {
            // here we test that after an onchange, the embedded one2many field has
            // been updated by a new list of ids by the server response, to this new
            // list should be correctly sent back at save time
            assert.expect(3);

            serverData.models.turtle.fields.partner_ids.type = "one2many";
            serverData.models.partner.records[0].turtles = [2];
            serverData.models.turtle.records[1].partner_ids = [2];

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [
                            1,
                            2,
                            {
                                partner_ids: [[4, 4]],
                            },
                        ],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/partner/web_save") {
                        var expectedResultTurtles = [
                            [
                                1,
                                2,
                                {
                                    partner_ids: [[4, 4]],
                                    turtle_foo: "hop",
                                },
                            ],
                        ];
                        assert.deepEqual(
                            args.args[1].turtles,
                            expectedResultTurtles,
                            "The right values should be written"
                        );
                    }
                },
            });
            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        ".o_data_cell.o_many2many_tags_cell .o_tag_badge_text"
                    ),
                ].map((el) => el.textContent),
                ["second record"]
            );

            await click(target.querySelectorAll(".o_data_cell")[1]);
            await editInput(target, ".o_selected_row [name=turtle_foo] input", "hop");
            await clickSave(target);
            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        ".o_data_cell.o_many2many_tags_cell .o_tag_badge_text"
                    ),
                ].map((el) => el.textContent),
                ["second record", "aaa"]
            );
        }
    );

    QUnit.test("onchange for embedded one2many with handle widget", async function (assert) {
        serverData.models.partner.records[0].turtles = [1, 2, 3];
        let partnerOnchange = 0;
        serverData.models.partner.onchanges = {
            turtles: function () {
                partnerOnchange++;
            },
        };
        let turtleOnchange = 0;
        serverData.models.turtle.onchanges = {
            turtle_int: function () {
                turtleOnchange++;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree default_order="turtle_int">
                            <field name="turtle_int" widget="handle"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "yop",
            "blip",
            "kawa",
        ]);
        // Drag and drop the second line in first position
        await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr", "top");

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "blip",
            "yop",
            "kawa",
        ]);
        assert.strictEqual(turtleOnchange, 2, "should trigger one onchange per line updated");
        assert.strictEqual(partnerOnchange, 1, "should trigger only one onchange on the parent");
    });

    QUnit.test(
        "onchange for embedded one2many with handle widget using same sequence",
        async function (assert) {
            serverData.models.turtle.records[0].turtle_int = 1;
            serverData.models.turtle.records[1].turtle_int = 1;
            serverData.models.turtle.records[2].turtle_int = 1;
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            var turtleOnchange = 0;
            serverData.models.turtle.onchanges = {
                turtle_int: function () {
                    turtleOnchange++;
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree default_order="turtle_int">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(
                            args.args[1].turtles,
                            [
                                [1, 2, { turtle_int: 1 }],
                                [1, 1, { turtle_int: 2 }],
                                [1, 3, { turtle_int: 3 }],
                            ],
                            "should change all lines that have changed (the first one doesn't change because it has the same sequence)"
                        );
                    }
                },
            });

            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")),
                ["yop", "blip", "kawa"]
            );

            // Drag and drop the second line in first position
            await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr", "top");

            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")),
                ["blip", "yop", "kawa"]
            );
            assert.strictEqual(turtleOnchange, 3, "should update all lines");

            await clickSave(target);
        }
    );

    QUnit.test("onchange for embedded one2many with handle widget", async function (assert) {
        const ids = [];
        for (let i = 10; i < 50; i++) {
            const id = 10 + i;
            ids.push(id);
            serverData.models.turtle.records.push({
                id: id,
                turtle_int: 0,
                turtle_foo: "#" + id,
            });
        }
        ids.push(1, 2, 3);
        serverData.models.partner.records[0].turtles = ids;
        serverData.models.partner.onchanges = {
            turtles: function (obj) {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom" default_order="turtle_int">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 1,
        });

        await click(target, "div[name=turtles] .o_pager_next");

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "yop",
            "blip",
            "kawa",
        ]);

        await click(target.querySelector(".o_data_cell.o_list_char"));
        await editInput(target, '.o_list_renderer div[name="turtle_foo"] input', "blurp");

        // Drag and drop the third line in second position
        await dragAndDrop("tbody tr:nth-child(3) .o_handle_cell", "tbody tr:nth-child(2)");

        // need to unselect row...
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "blurp",
            "kawa",
            "blip",
        ]);

        await clickSave(target);
        await click(target, 'div[name="turtles"] .o_pager_next');

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "blurp",
            "kawa",
            "blip",
        ]);
    });

    QUnit.test(
        "onchange with modifiers for embedded one2many on the second page",
        async function (assert) {
            const ids = [];
            for (let i = 10; i < 60; i++) {
                const id = 10 + i;
                ids.push(id);
                serverData.models.turtle.records.push({
                    id: id,
                    turtle_int: 0,
                    turtle_foo: "#" + id,
                });
            }
            ids.push(1, 2, 3);
            serverData.models.partner.records[0].turtles = ids;
            serverData.models.partner.onchanges = {
                turtles: function (obj) {},
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom" default_order="turtle_int" limit="10">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                                <field name="turtle_qux" readonly="not turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            const getTurtleFooValues = () => {
                return getNodesTextContent(
                    target.querySelectorAll(".o_data_cell.o_list_char")
                ).join("");
            };

            assert.strictEqual(getTurtleFooValues(), "#20#21#22#23#24#25#26#27#28#29");

            await click(target.querySelector(".o_data_cell.o_list_char"));
            await editInput(target, "div[name=turtle_foo] input", "blurp");
            // click outside of the one2many to unselect the row
            await click(target, ".o_form_view");
            assert.strictEqual(getTurtleFooValues(), "blurp#21#22#23#24#25#26#27#28#29");

            // the domain fail if the widget does not use the already loaded data.
            await clickDiscard(target);
            assert.containsNone(target, ".modal");
            assert.strictEqual(getTurtleFooValues(), "#20#21#22#23#24#25#26#27#28#29");

            // Drag and drop the third line in second position
            await dragAndDrop("tbody tr:nth-child(3) .o_handle_cell", "tbody tr:nth-child(2)");
            assert.strictEqual(getTurtleFooValues(), "#20#30#31#32#33#34#35#36#37#38");

            // Drag and drop the third line in second position
            await dragAndDrop("tbody tr:nth-child(3) .o_handle_cell", "tbody tr:nth-child(2)");
            assert.strictEqual(getTurtleFooValues(), "#20#39#40#41#42#43#44#45#46#47");

            await click(target, ".o_form_view");
            assert.strictEqual(getTurtleFooValues(), "#20#39#40#41#42#43#44#45#46#47");

            await clickDiscard(target);
            assert.containsNone(target, ".modal");
            assert.strictEqual(getTurtleFooValues(), "#20#21#22#23#24#25#26#27#28#29");
        }
    );

    QUnit.test("onchange followed by edition on the second page", async function (assert) {
        const ids = [];
        for (let i = 1; i < 85; i++) {
            const id = 10 + i;
            ids.push(id);
            serverData.models.turtle.records.push({
                id: id,
                turtle_int: (id / 3) | 0,
                turtle_foo: "#" + i,
            });
        }
        ids.splice(41, 0, 1, 2, 3);
        serverData.models.partner.records[0].turtles = ids;
        serverData.models.partner.onchanges = {
            turtles: function (obj) {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="turtles">
                                <tree editable="top" default_order="turtle_int">
                                    <field name="turtle_int" widget="handle"/>
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));

        await click(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell"
            )[1]
        );
        await editInput(
            target,
            '.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input',
            "value 1"
        );
        await click(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell"
            )[2]
        );
        await editInput(
            target,
            '.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input',
            "value 2"
        );

        assert.containsN(target, ".o_data_row", 40, "should display 40 records");
        assert.strictEqual(
            target.querySelector(".o_field_one2many .o_list_renderer .o_data_cell.o_list_char")
                .innerText,
            "#39",
            "should display '#39' at the first line"
        );

        await addRow(target);

        assert.containsN(
            target,
            ".o_data_row",
            40,
            "should display 39 records and the create line"
        );

        assert.hasClass(
            target.querySelector(".o_data_row"),
            "o_selected_row",
            "should display the create line in first position"
        );
        assert.strictEqual(
            target.querySelector('.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"]')
                .innerText,
            "",
            "should be an empty input"
        );
        assert.strictEqual(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer .o_data_cell.o_list_char"
            )[1].innerText,
            "#39",
            "should display '#39' at the second line"
        );

        await editInput(target, ".o_data_row input", "value 3");

        assert.hasClass(
            target.querySelector(".o_data_row"),
            "o_selected_row",
            "should display the create line in first position"
        );
        assert.strictEqual(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer .o_data_cell.o_list_char"
            )[1].innerText,
            "#39",
            "should display '#39' at the second line after onchange"
        );

        await addRow(target);

        assert.containsN(
            target,
            ".o_data_row",
            40,
            "should display 39 records and the create line"
        );
        assert.deepEqual(
            [
                ...target.querySelectorAll(
                    ".o_field_one2many .o_list_renderer .o_data_cell.o_list_char"
                ),
            ]
                .slice(0, 3)
                .map((el) => el.innerText),
            ["", "value 3", "#39"]
        );
    });

    QUnit.test("onchange followed by edition on the second page (part 2)", async function (assert) {
        const ids = [];
        for (let i = 1; i < 85; i++) {
            const id = 10 + i;
            ids.push(id);
            serverData.models.turtle.records.push({
                id: id,
                turtle_int: (id / 3) | 0,
                turtle_foo: "#" + i,
            });
        }
        ids.splice(41, 0, 1, 2, 3);
        serverData.models.partner.records[0].turtles = ids;
        serverData.models.partner.onchanges = {
            turtles: function (obj) {},
        };

        // bottom order

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="turtles">
                                    <tree editable="bottom" default_order="turtle_int">
                                        <field name="turtle_int" widget="handle"/>
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));

        await click(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell"
            )[1]
        );
        await editInput(
            target,
            '.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input',
            "value 1"
        );
        await click(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer tbody tr td.o_handle_cell"
            )[2]
        );
        await editInput(
            target,
            '.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input',
            "value 2"
        );

        assert.containsN(target, ".o_data_row", 40, "should display 40 records");
        assert.strictEqual(
            target.querySelector(
                ".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char"
            ).innerText,
            "#39",
            "should display '#39' at the first line"
        );
        assert.strictEqual(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char"
            )[39].innerText,
            "#77",
            "should display '#77' at the last line"
        );

        await addRow(target);

        assert.containsN(
            target,
            ".o_data_row",
            41,
            "should display 41 records and the create line"
        );
        assert.strictEqual(
            target.querySelectorAll(
                ".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char"
            )[39].innerText,
            "#77",
            "should display '#77' at the penultimate line"
        );
        assert.hasClass(
            target.querySelectorAll(".o_data_row")[40],
            "o_selected_row",
            "should display the create line in first position"
        );

        await editInput(
            target,
            '.o_field_one2many .o_list_renderer tbody div[name="turtle_foo"] input',
            "value 3"
        );
        await addRow(target);

        assert.containsN(
            target,
            ".o_data_row",
            42,
            "should display 42 records and the create line"
        );
        assert.deepEqual(
            [
                ...target.querySelectorAll(
                    ".o_field_one2many .o_list_renderer tbody .o_data_cell.o_list_char"
                ),
            ]
                .slice(39)
                .map((el) => el.innerText),
            ["#77", "value 3", ""]
        );
        assert.hasClass(
            target.querySelectorAll(".o_data_row")[41],
            "o_selected_row",
            "should display the create line in first position"
        );
    });

    QUnit.test("onchange returning a commands 4 for an x2many", async function (assert) {
        serverData.models.partner.onchanges = {
            foo(obj) {
                obj.turtles = [
                    [4, 1],
                    [4, 3],
                ];
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_data_row");

        // change the value of foo to trigger the onchange
        await editInput(target, ".o_field_widget[name=foo] input", "some value");
        assert.containsN(target, ".o_data_row", 3);
    });

    QUnit.test(
        "x2many fields inside x2manys are fetched after an onchange",
        async function (assert) {
            assert.expect(5);

            serverData.models.turtle.records[0].partner_ids = [1];
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [
                        [3, 2],
                        [4, 1],
                        [4, 2],
                        [4, 3],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="foo"/>
                                <field name="turtles">
                                    <tree>
                                        <field name="turtle_foo"/>
                                        <field name="partner_ids" widget="many2many_tags"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.deepEqual(args.args[3], {
                            // spec
                            display_name: {},
                            foo: {},
                            turtles: {
                                fields: {
                                    partner_ids: {
                                        fields: {
                                            display_name: {},
                                        },
                                    },
                                    turtle_foo: {},
                                },
                                limit: 40,
                                order: "",
                            },
                        });
                    }
                },
                resId: 1,
            });

            assert.containsOnce(
                target,
                ".o_data_row",
                "there should be one record in the relation"
            );
            assert.strictEqual(
                target
                    .querySelector(".o_data_row .o_field_widget[name=partner_ids]")
                    .textContent.replace(/\s/g, ""),
                "secondrecordaaa",
                "many2many_tags should be correctly displayed"
            );

            // change the value of foo to trigger the onchange
            await editInput(target, ".o_field_widget[name=foo] input", "some value");

            assert.containsN(
                target,
                ".o_data_row",
                3,
                "there should be three records in the relation"
            );
            assert.strictEqual(
                target
                    .querySelector(".o_data_row .o_field_widget[name=partner_ids]")
                    .textContent.trim(),
                "first record",
                "many2many_tags should be correctly displayed"
            );
        }
    );

    QUnit.test(
        "reference fields inside x2manys are fetched after an onchange",
        async function (assert) {
            assert.expect(4);

            serverData.models.turtle.records[1].turtle_ref = "product,41";
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [
                        [4, 1],
                        [4, 3],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="foo"/>
                                <field name="turtles">
                                    <tree>
                                        <field name="turtle_foo"/>
                                        <field name="turtle_ref" class="ref_field"/>
                                        </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_data_row");
            assert.deepEqual(
                [...target.querySelectorAll(".ref_field")].map((el) => el.textContent),
                ["xpad"]
            );

            // change the value of foo to trigger the onchange
            await editInput(target, ".o_field_widget[name=foo] input", "some value");

            assert.containsN(target, ".o_data_row", 3);
            assert.deepEqual(
                [...target.querySelectorAll(".ref_field")].map((el) => el.textContent),
                ["xpad", "", "xphone"]
            );
        }
    );

    QUnit.test("onchange on one2many containing x2many in form view", async function (assert) {
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.turtles = [[0, false, { turtle_foo: "new record" }]];
            },
        };
        serverData.views = {
            "partner,false,list": '<tree><field name="foo"/></tree>',
            "partner,false,search": "<search></search>",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree>
                            <field name="turtle_foo"/>
                        </tree>
                        <form>
                            <field name="partner_ids">
                                <tree editable="top">
                                    <field name="foo"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".o_data_row",
            "the onchange should have created one record in the relation"
        );

        // open the created o2m record in a form view, and add a m2m subrecord
        // in its relation
        await click(target.querySelector(".o_data_row .o_data_cell"));

        assert.containsOnce(target, ".modal");
        assert.containsNone(target, ".modal .o_data_row");

        // add a many2many subrecord
        await addRow(target.querySelector(".modal"));

        assert.containsN(target, ".modal", 2, "should have opened a second dialog");

        // select a many2many subrecord
        let secondDialog = target.querySelectorAll(".modal")[1];
        await click(secondDialog.querySelector(".o_list_view .o_data_cell"));

        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal .o_data_row");
        assert.containsNone(
            target,
            ".modal .o_x2m_control_panel .o_pager",
            "m2m pager should be hidden"
        );

        // click on 'Save & Close'
        await click(target.querySelector(".modal-footer .btn-primary"));

        assert.containsNone(target, ".modal", "dialog should be closed");

        // reopen o2m record, and another m2m subrecord in its relation, but
        // discard the changes
        await click(target.querySelector(".o_data_row .o_data_cell"));

        assert.containsOnce(target, ".modal", "should have opened a dialog");
        assert.containsOnce(
            target,
            ".modal .o_data_row",
            "there should be one record in the one2many in the dialog"
        );

        // add another m2m subrecord
        await addRow(target, ".modal");

        assert.containsN(target, ".modal", 2, "should have opened a second dialog");

        secondDialog = target.querySelectorAll(".modal")[1];
        await click(secondDialog.querySelector(".o_list_view .o_data_cell"));

        assert.containsOnce(target, ".modal", "second dialog should be closed");
        assert.containsN(
            target,
            ".modal .o_data_row",
            2,
            "there should be two records in the one2many in the dialog"
        );

        // click on 'Discard'
        await click(target.querySelector(".modal-footer .btn-secondary"));

        assert.containsNone(target, ".modal", "dialog should be closed");

        // reopen o2m record to check that second changes have properly been discarded
        await click(target.querySelector(".o_data_row .o_data_cell"));

        assert.containsOnce(target, ".modal", "should have opened a dialog");
        assert.containsOnce(
            target,
            ".modal .o_data_row",
            "there should be one record in the one2many in the dialog"
        );
    });

    QUnit.test(
        "onchange on one2many with x2many in list (no widget) and form view (list)",
        async function (assert) {
            assert.expect(7);
            serverData.models.turtle.fields.turtle_foo.default = "a default value";
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [[0, false, { turtles: [[0, false, { turtle_foo: "hello" }]] }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree>
                                <field name="turtles"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="top">
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange" && args.model === "partner") {
                        assert.deepEqual(args.args[3], {
                            display_name: {},
                            foo: {},
                            p: {
                                fields: {
                                    turtles: {
                                        fields: {
                                            turtle_foo: {},
                                        },
                                    },
                                },
                                limit: 40,
                                order: "",
                            },
                        });
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_data_row",
                "the onchange should have created one record in the relation"
            );

            // open the created o2m record in a form view
            await click(target.querySelector(".o_data_row .o_data_cell"));

            assert.containsOnce(document.body, ".modal", "should have opened a dialog");
            assert.containsOnce(document.body, ".modal .o_data_row");
            assert.strictEqual(
                document.querySelector(".modal .o_data_row").textContent.trim(),
                "hello"
            );

            // add a one2many subrecord and check if the default value is correctly applied
            await addRow(target, ".modal");

            assert.containsN(document.body, ".modal .o_data_row", 2);
            assert.strictEqual(
                document.querySelector(".modal .o_data_row .o_field_widget[name=turtle_foo] input")
                    .value,
                "a default value"
            );
        }
    );

    QUnit.test("save an o2m dialog form view and discard main form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="display_name"/>
                            </form>
                        </field>
                    </form>`,
        });

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(
            target.querySelector(".o_data_row [name='display_name']").textContent,
            "donatello"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal [name='display_name'] input").value,
            "donatello"
        );

        await editInput(target, ".modal [name='display_name'] input", "leonardo");
        await click(target.querySelector(".modal .o_form_button_save"));
        assert.containsNone(target, ".modal");
        assert.strictEqual(
            target.querySelector(".o_data_row [name='display_name']").textContent,
            "leonardo"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        await click(target.querySelector(".modal .o_form_button_cancel"));
        assert.strictEqual(
            target.querySelector(".o_data_row [name='display_name']").textContent,
            "leonardo"
        );

        await clickDiscard(target);
        assert.strictEqual(
            target.querySelector(".o_data_row [name='display_name']").textContent,
            "donatello"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal [name='display_name'] input").value,
            "donatello"
        );
    });

    QUnit.test("discard with nested o2m form view dialog", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].p = [4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="display_name"/>
                                <field name="p">
                                    <tree>
                                        <field name="display_name"/>
                                    </tree>
                                    <form>
                                        <field name="display_name"/>
                                    </form>
                                </field>
                            </form>
                        </field>
                    </form>`,
        });

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(
            target.querySelector(".o_data_row [name='display_name']").textContent,
            "second record"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector("#dialog_0 [name='display_name'] input").value,
            "second record"
        );

        await click(target.querySelector("#dialog_0 .o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector("#dialog_1 [name='display_name'] input").value,
            "aaa"
        );

        await editInput(target, "#dialog_1 [name='display_name'] input", "leonardo");
        await click(target.querySelector("#dialog_1 .o_form_button_save"));
        assert.containsNone(target, "#dialog_1");
        assert.strictEqual(
            target.querySelector("#dialog_0 .o_data_row [name='display_name']").textContent,
            "leonardo"
        );

        await click(target.querySelector("#dialog_0 .o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector("#dialog_2 [name='display_name'] input").value,
            "leonardo"
        );
        await click(target.querySelector("#dialog_2 .o_form_button_cancel"));
        await click(target.querySelector("#dialog_0 .o_form_button_cancel"));
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal .o_data_row [name='display_name']").textContent,
            "aaa"
        );
    });

    QUnit.test(
        "discard a form dialog view and then reopen it with a domain based on a text field",
        async function (assert) {
            serverData.models.turtle.records[1].turtle_foo = "yop";
            serverData.views = {
                "turtle,false,form": `
                <form>
                <field name="display_name" invisible="turtle_foo == 'yop'"/>
                <field name="turtle_foo"/>
            </form>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="turtles">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </form>`,
            });

            assert.containsOnce(target, ".o_data_row");
            assert.strictEqual(
                target.querySelector(".o_data_row [name='display_name']").textContent,
                "donatello"
            );

            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.containsNone(target, ".modal [name='display_name']");
            assert.strictEqual(
                target.querySelector(".modal [name='turtle_foo'] input").value,
                "yop"
            );

            await editInput(target, ".modal [name='turtle_foo'] input", "display");
            assert.strictEqual(
                target.querySelector(".modal [name='display_name'] input").value,
                "donatello"
            );
            assert.strictEqual(
                target.querySelector(".modal [name='turtle_foo'] input").value,
                "display"
            );

            await click(target.querySelector(".modal .o_form_button_save"));
            await clickDiscard(target);
            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.containsNone(target, ".modal [name='display_name']");
            assert.strictEqual(
                target.querySelector(".modal [name='turtle_foo'] input").value,
                "yop"
            );
        }
    );

    QUnit.test(
        "onchange on one2many with x2many in list (many2many_tags) and form view (list)",
        async function (assert) {
            assert.expect(7);
            serverData.models.turtle.fields.turtle_foo.default = "a default value";
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [[0, false, { turtles: [[0, false, { turtle_foo: "hello" }]] }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree>
                                <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="top">
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange" && args.model === "partner") {
                        assert.deepEqual(args.args[3], {
                            display_name: {},
                            foo: {},
                            p: {
                                fields: {
                                    turtles: {
                                        fields: {
                                            display_name: {},
                                            turtle_foo: {},
                                        },
                                    },
                                },
                                limit: 40,
                                order: "",
                            },
                        });
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_data_row",
                "the onchange should have created one record in the relation"
            );

            // open the created o2m record in a form view
            await click(target.querySelector(".o_data_row .o_data_cell"));

            assert.containsOnce(document.body, ".modal", "should have opened a dialog");
            assert.containsOnce(document.body, ".modal .o_data_row");
            assert.strictEqual(
                document.querySelector(".modal .o_data_row").textContent.trim(),
                "hello"
            );

            // add a one2many subrecord and check if the default value is correctly applied
            await addRow(target, ".modal");

            assert.containsN(document.body, ".modal .o_data_row", 2);
            assert.strictEqual(
                document.querySelector(".modal .o_data_row .o_field_widget[name=turtle_foo] input")
                    .value,
                "a default value"
            );
        }
    );

    QUnit.test(
        "embedded one2many with handle widget with minimum setValue calls",
        async function (assert) {
            serverData.models.turtle.records[0].turtle_int = 6;
            serverData.models.turtle.records.push(
                {
                    id: 4,
                    turtle_int: 20,
                    turtle_foo: "a1",
                },
                {
                    id: 5,
                    turtle_int: 9,
                    turtle_foo: "a2",
                },
                {
                    id: 6,
                    turtle_int: 2,
                    turtle_foo: "a3",
                },
                {
                    id: 7,
                    turtle_int: 11,
                    turtle_foo: "a4",
                }
            );
            serverData.models.partner.records[0].turtles = [1, 2, 3, 4, 5, 6, 7];

            patchWithCleanup(Record.prototype, {
                _update() {
                    if (this.resModel === "turtle") {
                        assert.step(`${this.resId}`);
                    }
                    return super._update(...arguments);
                },
            });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree default_order="turtle_int">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row [name='turtle_foo']")].map(
                    (el) => el.textContent
                ),
                ["a3", "yop", "blip", "a2", "a4", "a1", "kawa"]
            );

            const positions = [
                [7, 1, ["3", "6", "1", "2", "5", "7", "4"]], // move the last to the first line
                [6, 2, ["7", "6", "1", "2", "5"]], // move the penultimate to the second line
                [3, 6, ["1", "2", "5", "6"]], // move the third to the penultimate line
            ];
            for (const [sourceIndex, targetIndex, steps] of positions) {
                await dragAndDrop(
                    `tbody tr:nth-child(${sourceIndex}) .o_handle_cell`,
                    `tbody tr:nth-child(${targetIndex})`
                );
                assert.verifySteps(steps);
            }

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row [name='turtle_foo']")].map(
                    (el) => el.textContent
                ),
                ["kawa", "a4", "yop", "blip", "a2", "a3", "a1"]
            );
        }
    );

    QUnit.test("embedded one2many (editable list) with handle widget", async function (assert) {
        serverData.models.partner.records[0].p = [1, 2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="int_field" widget="handle"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step(args.method);
                    assert.deepEqual(args.args[1].p, [
                        [1, 2, { int_field: 0 }],
                        [1, 4, { int_field: 1 }],
                    ]);
                }
            },
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "My little Foo Value",
            "blip",
            "yop",
        ]);

        assert.verifySteps([]);

        // Drag and drop the second line in first position
        await dragAndDrop(
            "tbody tr:nth-child(2) .o_handle_cell",
            ".o_field_one2many tbody tr:nth-child(1)"
        );

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "blip",
            "My little Foo Value",
            "yop",
        ]);

        await click(target.querySelector(".o_data_cell.o_list_char"));

        assert.strictEqual(target.querySelector(".o_field_widget[name=foo] input").value, "blip");

        assert.verifySteps([]);

        await clickSave(target);

        assert.verifySteps(["web_save"]);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "blip",
            "My little Foo Value",
            "yop",
        ]);
    });

    QUnit.test("one2many list order with handle widget", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="int_field" widget="handle"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_read") {
                    assert.step(`web_read`);
                    assert.strictEqual(args.kwargs.specification.p.order, "int_field ASC, id ASC");
                }
            },
        });
        assert.verifySteps(["web_read"]);
    });

    QUnit.test("one2many field when using the pager", async function (assert) {
        const ids = [];
        for (let i = 0; i < 45; i++) {
            const id = 10 + i;
            ids.push(id);
            serverData.models.partner.records.push({
                id,
                display_name: `relational record ${id}`,
            });
        }
        serverData.models.partner.records[0].p = ids.slice(0, 42);
        serverData.models.partner.records[1].p = ids.slice(42);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div><t t-esc="record.display_name"/></div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_read") {
                    assert.step(`unity read ${args.args[0]}`);
                }
            },
            resId: 1,
            resIds: [1, 2],
        });

        assert.verifySteps(["unity read 1"]);
        assert.containsN(target, '.o_kanban_record:not(".o_kanban_ghost")', 40);

        // move to record 2, which has 3 related records (and shouldn't contain the
        // related records of record 1 anymore)
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_next"));
        assert.verifySteps(["unity read 2"]);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            3,
            "one2many kanban should contain 3 cards for record 2"
        );

        // move back to record 1, which should contain again its first 40 related
        // records
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_previous"));
        assert.verifySteps(["unity read 1"]);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            40,
            "one2many kanban should contain 40 cards for record 1"
        );

        // move to the second page of the o2m: 1 RPC should have been done to fetch
        // the 2 subrecords of page 2, and those records should now be displayed
        await click(target.querySelector(".o_x2m_control_panel .o_pager_next"));
        assert.verifySteps(["unity read 50,51"]);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            2,
            "one2many kanban should contain 2 cards for record 1 at page 2"
        );

        // move to record 2 again and check that everything is correctly updated
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_next"));
        assert.verifySteps(["unity read 2"]);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            3,
            "one2many kanban should contain 3 cards for record 2"
        );

        // move back to record 1 and move to page 2 again: all data should have
        // been correctly reloaded
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_previous"));
        assert.verifySteps(["unity read 1"]);
        await click(target.querySelector(".o_x2m_control_panel .o_pager_next"));
        assert.verifySteps(["unity read 50,51"]);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            2,
            "one2many kanban should contain 2 cards for record 1 at page 2"
        );
    });

    QUnit.test("edition of one2many field with pager", async function (assert) {
        const ids = [];
        for (let i = 0; i < 45; i++) {
            const id = 10 + i;
            ids.push(id);
            serverData.models.partner.records.push({
                id: id,
                display_name: "relational record " + id,
            });
        }
        serverData.models.partner.records[0].p = ids;
        serverData.views = {
            "partner,false,form": '<form><field name="display_name"/></form>',
        };

        let saveCount = 0;
        let checkRead = false;
        let readIDs;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_read" && checkRead) {
                    readIDs = args.args[0];
                    checkRead = false;
                }
                if (args.method === "web_save") {
                    assert.step("web_save");
                    saveCount++;
                    const commands = args.args[1].p;
                    switch (saveCount) {
                        case 1:
                            assert.deepEqual(commands, [
                                [0, commands[0][1], { display_name: "new record" }],
                            ]);
                            break;
                        case 2:
                            assert.deepEqual(commands, [[2, 10]]);
                            break;
                        case 3:
                            assert.deepEqual(commands, [
                                [0, commands[0][1], { display_name: "new record page 1" }],
                                [2, 11],
                                [2, 52],
                                [0, commands[3][1], { display_name: "new record page 2" }],
                            ]);
                            break;
                    }
                }
            },
            resId: 1,
        });

        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            40,
            "there should be 40 records on page 1"
        );
        assert.strictEqual(
            target.querySelector(".o_x2m_control_panel .o_pager_counter").innerText,
            "1-40 / 45",
            "pager range should be correct"
        );

        // add a record on page one
        checkRead = true;
        await click(target.querySelector(".o-kanban-button-new"));
        await editInput(target, ".modal input", "new record");

        await click(target.querySelector(".modal .modal-footer .btn-primary"));

        // checks
        assert.strictEqual(readIDs, undefined, "should not have read any record");
        assert.notOk(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].some(
                (el) => el.innerText === "new record"
            )
        );

        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            40,
            "there should be 40 records on page 1"
        );
        assert.strictEqual(
            target.querySelector(".o_x2m_control_panel .o_pager_counter").innerText,
            "1-40 / 46",
            "pager range should be correct"
        );

        // save
        await clickSave(target);

        // delete a record on page one
        checkRead = true;
        assert.strictEqual(
            target.querySelector(".o_kanban_record:not(.o_kanban_ghost)").innerText,
            "relational record 10"
        );

        await click(target.querySelector(".delete_icon")); // should remove record!!!

        // checks
        assert.deepEqual(
            readIDs,
            [50],
            "should have read a record (to display 40 records on page 1)"
        );
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            40,
            "there should be 40 records on page 1"
        );
        assert.strictEqual(
            target.querySelector(".o_x2m_control_panel .o_pager_counter").innerText,
            "1-40 / 45",
            "pager range should be correct"
        );
        // save
        await clickSave(target);

        // add and delete records in both pages
        checkRead = true;
        readIDs = undefined;
        // add and delete a record in page 1
        await click(target.querySelector(".o-kanban-button-new"));
        await editInput(target, ".modal input", "new record page 1");
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        assert.strictEqual(
            target.querySelector(".o_kanban_record:not(.o_kanban_ghost)").innerText,
            "relational record 11",
            "first record should be the one with id 11 (next checks rely on that)"
        );

        await click(target.querySelector(".delete_icon")); // should remove record!!!
        assert.deepEqual(
            readIDs,
            [51],
            "should have read a record (to display 40 records on page 1)"
        );
        // add and delete a record in page 2
        await click(target.querySelector(".o_x2m_control_panel .o_pager_next"));

        assert.strictEqual(
            target.querySelector(".o_kanban_record:not(.o_kanban_ghost)").innerText,
            "relational record 52",
            "first record should be the one with id 52 (next checks rely on that)"
        );

        checkRead = true;
        readIDs = undefined;
        await click(target.querySelector(".delete_icon")); // should remove record!!!
        await click(target.querySelector(".o-kanban-button-new"));

        await editInput(target, ".modal input", "new record page 2");
        await click(target.querySelector(".modal .modal-footer .btn-primary"));

        assert.strictEqual(readIDs, undefined, "should not have read any record");
        // checks
        assert.containsN(
            target,
            ".o_kanban_record:not(.o_kanban_ghost)",
            5,
            "there should be 5 records on page 2"
        );
        assert.strictEqual(
            target.querySelector(".o_x2m_control_panel .o_pager_counter").innerText,
            "41-45 / 45",
            "pager range should be correct"
        );
        assert.ok(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].some(
                (el) => el.innerText === "new record page 1"
            ),
            "new records should be on page 2"
        );
        assert.ok(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].some(
                (el) => el.innerText === "new record page 2"
            ),
            "new records should be on page 2"
        );
        // save
        await clickSave(target);

        assert.verifySteps(["web_save", "web_save", "web_save"]);
    });

    QUnit.test(
        "When viewing one2many records in an embedded kanban, the delete button should say 'Delete' and not 'Remove'",
        async function (assert) {
            assert.expect(1);
            serverData.views = {
                "turtle,false,form": `
                <form>
                    <h3>Data</h3>
                </form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="turtles">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div t-att-class="'oe_kanban_global_click'">
                                        <h3>Record 1</h3>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
                resId: 1,
            });

            // Opening the record to see the footer buttons
            await click(target.querySelector(".o_kanban_record"));

            assert.strictEqual(target.querySelector(".o_btn_remove").textContent, "Delete");
        }
    );

    QUnit.test("open a record in a one2many kanban (mode 'readonly')", async function (assert) {
        serverData.views = {
            "turtle,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form edit="0">
                    <field name="turtles">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div t-att-class="'oe_kanban_global_click'">
                                        <t t-esc="record.display_name.value"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "donatello");

        await click(target.querySelector(".o_kanban_record"));

        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal div[name=display_name] span").innerText,
            "donatello"
        );
    });

    QUnit.test("open a record in a one2many kanban (mode 'edit')", async function (assert) {
        serverData.views = {
            "turtle,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <t t-esc="record.display_name.value"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(target.querySelector(".o_kanban_record ").innerText, "donatello");

        await click(target.querySelector(".o_kanban_record"));

        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal div[name=display_name] input").value,
            "donatello"
        );
    });

    QUnit.test("open a record in an one2many readonly", async function (assert) {
        serverData.views = {
            "turtle,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles" readonly='1'>
                        <tree>
                            <field name="display_name" />
                        </tree>
                        <form>
                            <field name="display_name" />
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal div[name=display_name] span").textContent,
            "donatello"
        );

        await click(target, ".modal .o_form_button_cancel");
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal div[name=display_name] span").textContent,
            "donatello"
        );
    });

    QUnit.test(
        "open a record in a one2many kanban with an x2m in the form",
        async function (assert) {
            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[1].p = [4];

            serverData.views = {
                "partner,false,form": `
                <form>
                    <field name="display_name"/>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            };

            const def = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <t t-esc="record.display_name.value"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
                resId: 1,
                async mockRPC(route, args) {
                    if (args.method === "web_read" && args.args[0][0] === 2) {
                        assert.step("web_read: 2");
                        await def;
                    }
                },
            });

            await click(target.querySelector(".o_kanban_record"));
            def.resolve();
            await nextTick();
            assert.containsOnce(target, ".modal");
            assert.strictEqual(
                target.querySelector(".modal [name=display_name] input").value,
                "second record"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".modal .o_data_row")].map((el) => el.textContent),
                ["aaa"]
            );

            assert.verifySteps(["web_read: 2"]);
        }
    );

    QUnit.test(
        "one2many in kanban: add a line custom control create editable",
        async function (assert) {
            serverData.views = {
                "turtle,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="turtles">
                        <kanban>
                            <control>
                                <create string="Add food" context="" />
                                <create string="Add pizza" context="{'default_display_name': 'pizza'}"/>
                            </control>
                            <control>
                                <create string="Add pasta" context="{'default_display_name': 'pasta'}"/>
                            </control>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <t t-esc="record.display_name.value"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
                resId: 1,
            });

            const createButtons = target.querySelectorAll(
                ".o_x2m_control_panel .o_cp_buttons button"
            );
            assert.deepEqual(
                [...createButtons].map((el) => el.textContent),
                ["Add food", "Add pizza", "Add pasta"]
            );

            await click(createButtons[0]);
            assert.containsOnce(target, ".modal");
            assert.strictEqual(
                target.querySelector(".modal div[name=display_name] input").value,
                ""
            );

            await click(target, ".modal .o_form_button_cancel");
            await click(createButtons[1]);
            assert.containsOnce(target, ".modal");
            assert.strictEqual(
                target.querySelector(".modal div[name=display_name] input").value,
                "pizza"
            );

            await click(target, ".modal .o_form_button_cancel");
            await click(createButtons[2]);
            assert.containsOnce(target, ".modal");
            assert.strictEqual(
                target.querySelector(".modal div[name=display_name] input").value,
                "pasta"
            );
        }
    );

    QUnit.test(
        "one2many in kanban: add a line custom control create editable",
        async function (assert) {
            serverData.views = {
                "turtle,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="turtles">
                        <kanban>
                            <control>
                                <create string="Create" context="{}" />
                                <button string="Action Button" name="do_something" type="object" context="{'parent_id': parent.id}"/>
                            </control>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <t t-esc="record.display_name.value"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
                resId: 2,
                mockRPC(route, args) {
                    if (args.method === "do_something") {
                        assert.step("do_something");
                        assert.strictEqual(args.kwargs.context.parent_id, 2);
                        return true;
                    }
                },
            });

            const createButtons = target.querySelectorAll(
                ".o_x2m_control_panel .o_cp_buttons button"
            );
            assert.deepEqual(
                [...createButtons].map((el) => el.textContent),
                ["Create", "Action Button"]
            );

            await click(createButtons[1]);
            assert.verifySteps(["do_something"]);
        }
    );

    QUnit.test("add record in a one2many non editable list with context", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="turtles" context="{'abc': int_field}">
                        <tree><field name="display_name"/></tree>
                        <form><field name="display_name"/></form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange" && args.model === "turtle") {
                    // done by the X2ManyFieldDialog
                    assert.deepEqual(args.kwargs.context, {
                        abc: 2,
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                }
            },
        });

        await editInput(target, ".o_field_widget[name=int_field] input", "2");
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
    });

    QUnit.test(
        "edition of one2many field, with onchange and not inline sub view",
        async function (assert) {
            serverData.models.turtle.onchanges.turtle_int = function (obj) {
                obj.turtle_foo = String(obj.turtle_int);
            };
            serverData.models.partner.onchanges.turtles = function () {};
            serverData.views = {
                "turtle,false,list": `
                    <tree>
                        <field name="turtle_foo"/>
                    </tree>`,
                "turtle,false,form": `
                    <form>
                        <group>
                            <field name="turtle_foo"/>
                            <field name="turtle_int"/>
                        </group>
                    </form>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles" widget="one2many"/>
                    </form>`,
                resId: 1,
            });
            await addRow(target);
            await editInput(target, 'div[name="turtle_int"] input', "5");
            await click(target.querySelector(".modal-footer button.btn-primary"));
            let firstCellOfSecondRow = target.querySelectorAll(".o_data_cell.o_list_char")[1];
            assert.strictEqual(firstCellOfSecondRow.innerText, "5");
            await click(firstCellOfSecondRow);

            await editInput(target, 'div[name="turtle_int"] input', "3");
            await click(target.querySelector(".modal-footer button.btn-primary"));
            firstCellOfSecondRow = target.querySelectorAll(".o_data_cell.o_list_char")[1];
            assert.strictEqual(firstCellOfSecondRow.innerText, "3");
        }
    );

    QUnit.test(
        "onchange specification complete after open sub form view not inline",
        async function (assert) {
            serverData.models.partner.onchanges.display_name = () => {};
            serverData.views = {
                "turtle,false,form": `
                    <form>
                        <field name="display_name"/>
                        <field name="partner_ids">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </form>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="turtles">
                            <tree>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                async mockRPC(route, args) {
                    if (args.method === "onchange" && args.model === "partner") {
                        if (args.args[1].display_name === "test") {
                            assert.deepEqual(args.args[3], {
                                display_name: {},
                                turtles: {
                                    fields: {
                                        turtle_foo: {},
                                    },
                                    limit: 40,
                                    order: "",
                                },
                            });
                        } else if (args.args[1].display_name === "test2") {
                            assert.deepEqual(args.args[3], {
                                display_name: {},
                                turtles: {
                                    fields: {
                                        display_name: {},
                                        partner_ids: {
                                            fields: {
                                                display_name: {},
                                            },
                                            limit: 40,
                                            order: "",
                                        },
                                        turtle_foo: {},
                                    },
                                    limit: 40,
                                    order: "",
                                },
                            });
                            return {
                                value: {
                                    turtles: [
                                        [
                                            1,
                                            2,
                                            {
                                                display_name: "yop",
                                                partner_ids: [[1, 2, { display_name: "plop" }]],
                                            },
                                        ],
                                    ],
                                },
                            };
                        }
                    }
                },
            });
            await editInput(target, "div[name='display_name'] input", "test");
            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.strictEqual(
                target.querySelector(".modal [name='display_name'] input").value,
                "donatello"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".modal .o_data_row")].map((el) => el.textContent),
                ["second record", "aaa"]
            );

            await click(target.querySelector(".modal .o_form_button_save"));
            await editInput(target, "div[name='display_name'] input", "test2");
            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.strictEqual(
                target.querySelector(".modal [name='display_name'] input").value,
                "yop"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".modal .o_data_row")].map((el) => el.textContent),
                ["plop", "aaa"]
            );
        }
    );

    QUnit.test("sorting one2many fields", async function (assert) {
        serverData.models.partner.fields.foo.sortable = true;
        serverData.models.partner.records.push({ id: 23, foo: "abc", int_field: 1 });
        serverData.models.partner.records.push({ id: 24, foo: "xyz", int_field: 1 });
        serverData.models.partner.records.push({ id: 25, foo: "def", int_field: 2 });
        serverData.models.partner.records[0].p = [23, 24, 25];

        let rpcCount = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC() {
                rpcCount++;
            },
        });

        rpcCount = 0;
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell[name='foo']")].map((c) => c.textContent),
            ["abc", "xyz", "def"]
        );

        await click(target.querySelector("table thead [data-name='foo'].o_column_sortable"));
        assert.strictEqual(rpcCount, 0, "in memory sort, no RPC should have been done");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell[name='foo']")].map((c) => c.textContent),
            ["abc", "def", "xyz"]
        );

        await click(target.querySelector("table thead [data-name='foo'].o_column_sortable"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell[name='foo']")].map((c) => c.textContent),
            ["xyz", "def", "abc"]
        );

        await click(target.querySelector("table thead [data-name='int_field'].o_column_sortable"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell[name='foo']")].map((c) => c.textContent),
            ["xyz", "abc", "def"]
        );

        await click(target.querySelector("table thead [data-name='int_field'].o_column_sortable"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell[name='foo']")].map((c) => c.textContent),
            ["def", "xyz", "abc"]
        );
    });

    QUnit.test("sorting one2many fields with multi page", async function (assert) {
        serverData.models.partner.fields.foo.sortable = true;
        serverData.models.partner.records.push({ id: 23, foo: "abc", int_field: 1 });
        serverData.models.partner.records.push({ id: 24, foo: "xyz", int_field: 1 });
        serverData.models.partner.records.push({ id: 25, foo: "def", int_field: 2 });
        serverData.models.partner.records.push({ id: 26, foo: "otc", int_field: 2 });
        serverData.models.partner.records[0].p = [23, 24, 25, 26];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree limit="2">
                            <field name="foo"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((c) => c.textContent),
            ["abc1", "xyz1"]
        );

        await click(target.querySelector("table thead [data-name='int_field'].o_column_sortable"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((c) => c.textContent),
            ["abc1", "xyz1"]
        );

        await click(target.querySelector("table thead [data-name='foo'].o_column_sortable"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((c) => c.textContent),
            ["abc1", "def2"]
        );

        await click(target.querySelector(".o_field_widget[name='p'] .o_pager_next"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((c) => c.textContent),
            ["otc2", "xyz1"]
        );
    });

    QUnit.test("one2many list field edition", async function (assert) {
        serverData.models.partner.records.push({
            id: 3,
            display_name: "relational record 1",
        });
        serverData.models.partner.records[1].p = [3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
        });

        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td").textContent,
            "relational record 1"
        );

        await click(target.querySelector(".o_field_one2many tbody td"));
        assert.hasClass(
            target.querySelector(".o_field_one2many tbody .o_data_row"),
            "o_selected_row"
        );

        await editInput(target, ".o_field_one2many tbody td input", "new value");
        assert.hasClass(
            target.querySelector(".o_field_one2many tbody .o_data_row"),
            "o_selected_row"
        );
        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td input").value,
            "new value"
        );

        // leave o2m edition
        await click(target.querySelector(".o_form_view"));
        assert.doesNotHaveClass(
            target.querySelector(".o_field_one2many tbody .o_data_row"),
            "o_selected_row"
        );

        // discard changes
        await clickDiscard(target);
        assert.containsNone(target, ".modal");
        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td").textContent,
            "relational record 1"
        );

        // edit again and save
        await click(target.querySelector(".o_field_one2many tbody td"));
        await editInput(target, ".o_field_one2many tbody td input", "new value");
        await click(target.querySelector(".o_form_view"));
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td").textContent,
            "new value",
            "display name of first record in o2m list should be 'new value'"
        );
    });

    QUnit.test("one2many list: create action disabled", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree create="0">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.containsNone(target, ".o_field_x2many_list_row_add");
    });

    QUnit.test(
        "one2many list: cannot open record in editable list and form in readonly mode",
        async function (assert) {
            serverData.models.partner.records[0].p = [2];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form edit="0">
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_data_cell[name='display_name']");
            await click(target, ".o_data_cell[name='display_name']");
            assert.containsNone(target, ".modal-dialog");
        }
    );

    QUnit.test(
        "one2many list: cannot open record in editable=bottom and edit=false list",
        async function (assert) {
            serverData.models.partner.records[0].p = [2];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom" edit="false">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_data_cell[name='display_name']");
            await click(target, ".o_data_cell[name='display_name']");
            assert.containsNone(target, ".modal-dialog");
        }
    );

    QUnit.test("one2many list: conditional create/delete actions", async function (assert) {
        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="p" options="{'create': [('bar', '=', True)], 'delete': [('bar', '=', True)]}">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // bar is true -> create and delete action are available
        assert.containsOnce(target, ".o_field_x2many_list_row_add");
        assert.containsN(target, "td.o_list_record_remove button", 2);

        // set bar to false -> create and delete action are no longer available
        await click(target, '.o_field_widget[name="bar"] input');

        assert.containsNone(target, ".o_field_x2many_list_row_add");
        assert.containsNone(target, "td.o_list_record_remove button");
    });

    QUnit.test("boolean field in a one2many must be directly editable", async function (assert) {
        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="bar"/>
                            <field name="name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell[name='bar'] input")].map((el) => el.checked),
            [true, false]
        );

        await click(target.querySelector('[name="bar"] .o-checkbox'));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell[name='bar'] input")].map((el) => el.checked),
            [false, false]
        );
    });

    QUnit.test("many2many list: unlink two records", async function (assert) {
        assert.expect(4);
        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" widget="many2many">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, [[3, 1]], "should send a command 3 (unlink)");
                }
            },
        });
        assert.containsN(target, "td.o_list_record_remove button", 3);

        await click(target.querySelector("td.o_list_record_remove button"));
        assert.containsN(target, "td.o_list_record_remove button", 2);

        await click(target.querySelector("tr.o_data_row td"));
        assert.containsNone(target, ".modal .modal-footer .o_btn_remove");

        await click(target.querySelector(".modal .btn-secondary"));
        await clickSave(target);
    });

    QUnit.test("one2many list: deleting one records", async function (assert) {
        assert.expect(3);
        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, [[2, 1]]);
                }
            },
        });
        assert.containsN(target, "td.o_list_record_remove button", 3);

        await click(target.querySelector("td.o_list_record_remove button"));
        assert.containsN(target, "td.o_list_record_remove button", 2);

        // save and check that the correct command has been generated
        await clickSave(target);

        // FIXME: it would be nice to test that the view is re-rendered correctly,
        // but as the relational data isn't re-fetched, the rendering is ok even
        // if the changes haven't been saved
    });

    QUnit.test("one2many kanban: edition", async function (assert) {
        assert.expect(17);

        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            // color will be in the kanban but not in the form
            // foo will be in the form but not in the kanban
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="color"/>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                        <span><t t-esc="record.display_name.value"/></span>
                                        <span><t t-esc="record.color.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="display_name"/>
                            <field name="foo"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, [
                        [
                            0,
                            commands[0][1],
                            {
                                color: "red",
                                display_name: "new subrecord 3",
                                foo: "My little Foo Value",
                            },
                        ],
                        [2, 2],
                    ]);
                }
            },
        });

        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.strictEqual(
            target.querySelector(".o_kanban_record span").textContent,
            "second record"
        );
        assert.strictEqual(target.querySelectorAll(".o_kanban_record span")[1].textContent, "Red");
        assert.containsOnce(target, ".delete_icon");
        assert.containsOnce(target, ".o_field_one2many .o-kanban-button-new");
        assert.hasClass(
            target.querySelector(".o_field_one2many .o-kanban-button-new"),
            "btn-secondary"
        );
        assert.strictEqual(
            target.querySelector(".o_field_one2many .o-kanban-button-new").textContent,
            "Add"
        );

        // edit existing subrecord
        await click($(target).find(".oe_kanban_global_click")[0]);

        await editInput(
            target,
            ".modal .o_form_view .o_field_widget:nth-child(1) input",
            "new name"
        );
        await click($(".modal .modal-footer .btn-primary")[0]);
        assert.strictEqual(
            $(target).find(".o_kanban_record span:first").text(),
            "new name",
            "value of subrecord should have been updated"
        );

        // create a new subrecord
        await click($(target).find(".o-kanban-button-new")[0]);
        await editInput(
            target,
            ".modal .o_form_view .o_field_widget:nth-child(1) input",
            "new subrecord 1"
        );
        await click($(target).find(".modal .modal-footer .btn-primary")[0]);
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            2,
            "should contain 2 records"
        );
        assert.strictEqual(
            $(target).find(".o_kanban_record:nth(1) span").text(),
            "new subrecord 1Red",
            'value of newly created subrecord should be "new subrecord 1"'
        );

        // create two new subrecords
        await click($(target).find(".o-kanban-button-new")[0]);
        await editInput(
            target,
            ".modal .o_form_view .o_field_widget:nth-child(1) input",
            "new subrecord 2"
        );
        await click($(".modal .modal-footer .btn-primary:nth(1)")[0]);
        await editInput(
            target,
            ".modal .o_form_view .o_field_widget:nth-child(1) input",
            "new subrecord 3"
        );
        await click($(target).find(".modal .modal-footer .btn-primary")[0]);
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            4,
            "should contain 4 records"
        );

        // delete subrecords
        await click($(target).find(".oe_kanban_global_click").first()[0]);
        assert.strictEqual(
            $(".modal .modal-footer .o_btn_remove").length,
            1,
            "There should be a modal having Remove Button"
        );
        await click($(".modal .modal-footer .o_btn_remove")[0]);
        assert.containsNone($(".o_modal"), "modal should have been closed");
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            3,
            "should contain 3 records"
        );
        await click($(target).find(".o_kanban_renderer .delete_icon:first()")[0]);
        await click($(target).find(".o_kanban_renderer .delete_icon:first()")[0]);
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            1,
            "should contain 1 records"
        );
        assert.strictEqual(
            $(target).find(".o_kanban_record span:first").text(),
            "new subrecord 3",
            'the remaining subrecord should be "new subrecord 3"'
        );

        // save and check that the correct command has been generated
        await clickSave(target);
    });

    QUnit.test(
        "one2many kanban (editable): properly handle add-label node attribute",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles" add-label="Add turtle" mode="kanban">
                            <kanban>
                                <templates>
                                    <t t-name="kanban-box">
                                        <div class="oe_kanban_details">
                                            <field name="display_name"/>
                                        </div>
                                    </t>
                                </templates>
                            </kanban>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        '.o_field_one2many[name="turtles"] .o-kanban-button-new'
                    ),
                ].map((el) => el.textContent),
                ["Add turtle"],
                "In O2M Kanban, Add button should have 'Add turtle' label"
            );
        }
    );

    QUnit.test("one2many kanban: create action disabled", async function (assert) {
        serverData.models.partner.records[0].p = [4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban create="0">
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsNone(target, ".o-kanban-button-new");
        assert.containsOnce(target, ".o_field_x2many_kanban .delete_icon");
    });

    QUnit.test("one2many kanban: conditional create/delete actions", async function (assert) {
        serverData.models.partner.records[0].p = [2, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="p" options="{'create': [('bar', '=', True)], 'delete': [('bar', '=', True)]}">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="display_name"/>
                            <field name="foo"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        // bar is initially true -> create and delete actions are available
        assert.containsOnce(target, ".o-kanban-button-new", '"Add" button should be available');

        await click(target.querySelector(".oe_kanban_global_click"));
        assert.containsOnce(
            target,
            ".modal .modal-footer .o_btn_remove",
            "There should be a Remove Button inside modal"
        );

        await clickDiscard(target.querySelector(".modal"));
        // set bar false -> create and delete actions are no longer available
        await click(target.querySelector('.o_field_widget[name="bar"] input'));
        assert.containsNone(
            target,
            ".o-kanban-button-new",
            '"Add" button should not be available as bar is False'
        );

        await click(target.querySelector(".oe_kanban_global_click"));
        assert.containsNone(
            target,
            ".modal .modal-footer .o_btn_remove",
            "There should not be a Remove Button as bar field is False"
        );
    });

    QUnit.test("editable one2many list, pager is updated", async function (assert) {
        serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
        serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add a record, add value to turtle_foo then click in form view to confirm it
        await addRow(target);

        await editInput(target, 'div[name="turtle_foo"] input', "nora");

        await click(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=turtles] .o_pager").textContent.trim(),
            "1-4 / 5"
        );
    });

    QUnit.test("one2many list (non editable): edition", async function (assert) {
        assert.expect(11);

        let nbWrite = 0;
        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                            <field name="qux"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC: function (route, args) {
                if (args.method === "web_save") {
                    nbWrite++;
                    assert.deepEqual(args.args[1], {
                        p: [
                            [1, 2, { display_name: "new name" }],
                            [2, 4],
                        ],
                    });
                }
            },
        });

        assert.containsN(target, "td.o_list_number", 2);
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").textContent,
            "second record"
        );
        assert.containsN(target, ".o_list_record_remove", 2);
        assert.containsOnce(target, ".o_field_x2many_list_row_add");

        // edit first record
        await click(target.querySelector(".o_list_renderer .o_data_cell"));
        assert.hasClass(
            target.querySelector(".o_list_renderer .o_data_cell"),
            "o_readonly_modifier"
        );

        await editInput(target, ".modal .o_form_editable input", "new name");

        await click(target, ".modal .modal-footer .btn-primary");
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").textContent,
            "new name"
        );
        assert.strictEqual(nbWrite, 0, "should not have write anything in DB");

        // remove second record
        await click(target.querySelectorAll(".o_list_record_remove")[1]);
        assert.containsOnce(target, "td.o_list_number");
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").textContent,
            "new name"
        );

        await clickSave(target); // save the record
        assert.strictEqual(nbWrite, 1, "should have write the changes in DB");
    });

    QUnit.test("one2many list (editable): edition, part 2", async function (assert) {
        assert.expect(11);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    // Would be nice to assert this way, but we don't control the virtual ids index
                    // assert.deepEqual(args.args[1].p, [
                    //     [0, "virtual_2", { foo: "gemuse" }],
                    //     [0, "virtual_1", { foo: "kartoffel" }],
                    // ]);
                    assert.strictEqual(args.args[1].p[0][0], 0);
                    assert.strictEqual(args.args[1].p[1][0], 0);
                    assert.deepEqual(args.args[1].p[0][2], { foo: "gemuse" });
                    assert.deepEqual(args.args[1].p[1][2], { foo: "kartoffel" });
                }
            },
        });

        // edit mode, then click on Add an item and enter a value
        await addRow(target);
        await editInput(target, ".o_selected_row > td input", "kartoffel");
        assert.strictEqual(target.querySelector("td .o_field_char input").value, "kartoffel");

        // click again on Add an item
        await addRow(target);
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        assert.strictEqual(target.querySelectorAll(".o_data_cell")[1].textContent, "kartoffel");
        assert.containsOnce(target, ".o_selected_row > td input");
        assert.containsN(target, "tr.o_data_row", 2);

        // enter another value and save
        await editInput(target, ".o_selected_row > td input", "gemuse");
        await clickSave(target);
        assert.containsN(target, "tr.o_data_row", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "gemuse",
            "kartoffel",
        ]);
    });

    QUnit.test("one2many list (editable): edition, part 3", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        // edit mode, then click on Add an item, enter value in turtle_foo and Add an item again
        assert.containsOnce(target, "tr.o_data_row");
        await addRow(target);
        await editInput(target, 'div[name="turtle_foo"] input', "nora");
        await addRow(target);
        assert.containsN(target, "tr.o_data_row", 3);

        // cancel the edition
        await clickDiscard(target);

        assert.containsNone(target, ".modal");
        assert.containsOnce(target, "tr.o_data_row");
    });

    QUnit.test("one2many list (editable): edition, part 4", async function (assert) {
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        let i = 0;
        serverData.models.turtle.onchanges = {
            turtle_trululu: function (obj) {
                if (i) {
                    obj.turtle_description = "Some Description";
                }
                i++;
            },
        };
        serverData["partner,false,"];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_trululu"/>
                                <field name="turtle_description"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
        });

        // edit mode, then click on Add an item
        assert.containsNone(target, "tr.o_data_row");
        await addRow(target);
        assert.strictEqual(target.querySelector(".o_data_row textarea").value, "");

        // add a value in the turtle_trululu field to trigger an onchange
        await clickOpenM2ODropdown(target, "turtle_trululu");
        await clickM2OHighlightedItem(target, "turtle_trululu");
        assert.strictEqual(target.querySelector(".o_data_row textarea").value, "Some Description");
    });

    QUnit.test("one2many list (editable): edition, part 5", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        // edit mode, then click on Add an item, enter value in turtle_foo and Add an item again
        assert.containsOnce(target, "tr.o_data_row");
        assert.strictEqual(target.querySelector(".o_data_cell").innerText, "blip");
        await addRow(target);
        await editInput(target, ".o_field_widget[name=turtle_foo] input", "aaa");
        assert.containsN(target, "tr.o_data_row", 2);
        await removeRow(target, 1);
        assert.containsOnce(target, "tr.o_data_row");

        // cancel the edition
        await clickDiscard(target);
        assert.containsOnce(target, "tr.o_data_row");
        assert.strictEqual(target.querySelector(".o_data_cell").innerText, "blip");
    });

    QUnit.test("one2many list (editable): discarding required empty data", async function (assert) {
        serverData.models.turtle.fields.turtle_foo.required = true;
        delete serverData.models.turtle.fields.turtle_foo.default;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        // edit mode, then click on Add an item, then click elsewhere
        assert.containsNone(target, "tr.o_data_row");
        await addRow(target);
        await click(target);
        assert.containsNone(target, "tr.o_data_row");

        // click on Add an item again, then click on save
        await addRow(target);
        await clickSave(target);
        assert.containsNone(target, "tr.o_data_row");

        assert.verifySteps(["get_views", "web_read", "onchange", "onchange"]);
    });

    QUnit.test("discard O2M field with close button", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name" />
                        </tree>
                        <form>
                            <field name="display_name" />
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.strictEqual(target.querySelector(".o_data_row").textContent, "second record");

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_dialog");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=display_name] input").value,
            "second record"
        );

        await editInput(target, ".modal .o_field_widget[name=display_name] input", "plop");
        await click(target.querySelector(".modal .btn-close"));
        assert.strictEqual(target.querySelector(".o_data_row").textContent, "second record");

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_dialog");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=display_name] input").value,
            "second record"
        );
    });

    QUnit.test("editable one2many list, adding line when only one page", async function (assert) {
        serverData.models.partner.records[0].turtles = [1, 2, 3];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add a record, to reach the page size limit
        await addRow(target);
        // the record currently being added should not count in the pager
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");

        // enter value in turtle_foo field and click outside to unselect the row
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await click(target);
        assert.containsNone(target, ".o_selected_row");
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");

        await clickSave(target);
        assert.containsOnce(target, ".o_field_widget[name=turtles] .o_pager");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=turtles] .o_pager").textContent,
            "1-3 / 4"
        );
    });

    QUnit.test("editable one2many list, adding line, then discarding", async function (assert) {
        serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
        serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add a record, then discard
        await addRow(target);

        await clickDiscard(target);
        assert.containsNone(target, ".modal");

        assert.isVisible(target.querySelector(".o_field_widget[name=turtles] .o_pager"));
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=turtles] .o_pager").textContent.trim(),
            "1-3 / 4"
        );
    });

    QUnit.test("editable one2many list, required field and pager", async function (assert) {
        serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
        serverData.models.turtle.fields.turtle_foo.required = true;
        serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add a (empty) record
        await addRow(target);

        // go on next page. The new record is not valid and should be discarded
        await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));
        assert.containsOnce(target, "tr.o_data_row");
    });

    QUnit.test(
        "editable one2many list, required field, pager and confirm discard",
        async function (assert) {
            serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
            serverData.models.turtle.fields.turtle_foo.required = true;
            serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom" limit="3">
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            // add a record with a dirty state, but not valid
            await addRow(target);
            await editInput(target, '.o_field_widget[name="turtle_int"] input', 4321);

            // try to go to next page. The new record is not valid, but dirty so we should
            // stay on the current page, and the record should be marked as invalid
            await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=turtles] .o_pager").textContent,
                "1-4 / 5"
            );

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=turtles] .o_pager").textContent,
                "1-4 / 5"
            );
            assert.containsOnce(target, ".o_field_widget[name=turtle_foo].o_field_invalid");
        }
    );

    QUnit.test("save a record with not new, dirty and invalid subrecord", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].display_name = ""; // invalid record

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name" required="1"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "write") {
                    throw new Error("Should not call write as record is invalid");
                }
            },
            mode: "edit",
        });

        assert.containsOnce(target, ".o_form_editable");
        await click(target.querySelector(".o_data_cell")); // edit the first row
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        await editInput(target, ".o_field_widget[name=int_field] input", 44);
        await click(target.querySelector(".o_form_button_save"));
        assert.containsOnce(target, ".o_form_editable");
        assert.containsOnce(target, ".o_invalid_cell");
    });

    QUnit.test("editable one2many list, adding, discarding, and pager", async function (assert) {
        serverData.models.partner.records[0].turtles = [1];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add 4 records (to have more records than the limit)
        await addRow(target);
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await addRow(target);
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await addRow(target);
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await addRow(target);

        assert.containsN(target, "tr.o_data_row", 5);
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");

        // discard
        await clickDiscard(target);
        assert.containsNone(target, ".modal");

        assert.containsOnce(target, "tr.o_data_row");
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");
    });

    QUnit.test("unselecting a line with missing required data", async function (assert) {
        serverData.models.turtle.fields.turtle_foo.required = true;
        delete serverData.models.turtle.fields.turtle_foo.default;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_foo"/>
                            <field name="turtle_int"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
        });

        // edit mode, then click on Add an item, then click elsewhere
        assert.containsNone(target, "tr.o_data_row");
        await addRow(target);
        assert.containsOnce(target, "tr.o_data_row");

        // adding a value in the non required field, so it is dirty, but with
        // a missing required field
        await editInput(target, '.o_field_widget[name="turtle_int"] input', "12345");

        // click elsewhere
        await click(target);
        assert.containsNone(target, ".modal");

        // the line should still be selected
        assert.containsOnce(target, "tr.o_data_row.o_selected_row");

        // click discard
        await clickDiscard(target);
        assert.containsNone(target, ".modal");
        assert.containsNone(target, "tr.o_data_row");
    });

    QUnit.test("pressing enter in a o2m with a required empty field", async function (assert) {
        serverData.models.turtle.fields.turtle_foo.required = true;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        // edit mode, then click on Add an item, then press enter
        await addRow(target);
        triggerHotkey("Enter");
        await nextTick();
        assert.hasClass(target.querySelector('div[name="turtle_foo"]'), "o_field_invalid");
        assert.verifySteps(["get_views", "web_read", "onchange"]);
    });

    QUnit.test("pressing enter several times in a one2many", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
        });

        await addRow(target);
        assert.containsOnce(target, ".o_data_row");
        assert.hasClass(target.querySelectorAll(".o_data_row")[0], "o_selected_row");

        await editInput(target, "[name='turtle_foo'] input", "a");
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 2);
        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");

        await editInput(target, "[name='turtle_foo'] input", "a");
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 3);
        assert.hasClass(target.querySelectorAll(".o_data_row")[2], "o_selected_row");

        // this is a weird case, but there's no required fields, so the record is already valid, we can press Enter directly.
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 4);
        assert.hasClass(target.querySelectorAll(".o_data_row")[3], "o_selected_row");
    });

    QUnit.test(
        "creating a new line in an o2m with an handle field does not focus the handler",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_int" widget="handle"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
                resId: 2,
            });

            await addRow(target);
            assert.strictEqual(
                document.activeElement,
                target.querySelector("[name='turtle_foo'] input")
            );

            triggerHotkey("Enter");
            await nextTick();
            assert.strictEqual(
                document.activeElement,
                target.querySelector("[name='turtle_foo'] input")
            );
        }
    );

    QUnit.test("editing a o2m, with required field and onchange", async function (assert) {
        serverData.models.turtle.fields.turtle_foo.required = true;
        delete serverData.models.turtle.fields.turtle_foo.default;
        serverData.models.turtle.onchanges = {
            turtle_foo: function (obj) {
                obj.turtle_int = obj.turtle_foo.length;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
            },
        });

        // edit mode, then click on Add an item
        assert.containsNone(target, "tr.o_data_row");
        await addRow(target);

        // input some text in required turtle_foo field
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "aubergine");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="turtle_int"] input').value,
            "9"
        );

        // save and check everything is fine
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_data_row .o_data_cell.o_list_char").textContent,
            "aubergine"
        );
        assert.strictEqual(
            target.querySelector(".o_data_row .o_data_cell.o_list_number").textContent,
            "9"
        );

        assert.verifySteps(["get_views", "web_read", "onchange", "onchange", "web_save"]);
    });

    QUnit.test("editable o2m, pressing ESC discard current changes", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        await addRow(target);
        assert.containsOnce(target, "tr.o_data_row");

        await triggerEvent(target, '[name="turtle_foo"] input', "keydown", { key: "Escape" });
        assert.containsNone(target, "tr.o_data_row");
        assert.verifySteps(["get_views", "web_read", "onchange"]);
    });

    QUnit.test(
        "editable o2m with required field, pressing ESC discard current changes",
        async function (assert) {
            serverData.models.turtle.fields.turtle_foo.required = true;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 2,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            await addRow(target);
            assert.containsOnce(target, "tr.o_data_row");

            await triggerEvent(target, '[name="turtle_foo"] input', "keydown", { key: "Escape" });

            assert.containsNone(target, "tr.o_data_row");
            assert.verifySteps(["get_views", "web_read", "onchange"]);
        }
    );

    QUnit.test("pressing escape in editable o2m list in dialog", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await addRow(target);
        await addRow(target, ".modal");

        assert.containsOnce(target, ".modal .o_data_row.o_selected_row");

        await triggerEvent(target, '[name="display_name"] input', "keydown", { key: "Escape" });

        assert.containsOnce(target, ".modal");
        assert.containsNone(target, ".modal .o_data_row");
    });

    QUnit.test(
        "editable o2m with onchange and required field: delete an invalid line",
        async function (assert) {
            serverData.models.partner.onchanges = {
                turtles: function () {},
            };
            serverData.models.partner.records[0].turtles = [1];
            serverData.models.turtle.records[0].product_id = 37;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="product_id"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            assert.verifySteps(["get_views", "web_read"]);
            await click(target.querySelector(".o_data_cell"));
            await editInput(target, ".o_field_widget[name=product_id] input", "");
            assert.verifySteps([], "no onchange should be done as line is invalid");
            await click(target.querySelector(".o_list_record_remove"));
            assert.verifySteps(["onchange"], "onchange should have been done");
        }
    );

    QUnit.test("onchange in a one2many", async function (assert) {
        serverData.models.partner.records.push({
            id: 3,
            foo: "relational record 1",
        });
        serverData.models.partner.records[1].p = [3];
        serverData.models.partner.onchanges = { p: () => {} };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        value: {
                            p: [
                                [2, 3], // delete 3
                                [0, 0, { foo: "from onchange" }], // create new
                            ],
                        },
                    });
                }
            },
        });

        await click(target.querySelector(".o_field_one2many tbody td"));
        await editInput(
            target.querySelector(".o_field_one2many tbody td input"),
            null,
            "new value"
        );
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td").textContent,
            "from onchange"
        );
    });

    QUnit.test("one2many, default_get and onchange (basic)", async function (assert) {
        serverData.models.partner.fields.p.default = [];
        serverData.models.partner.onchanges = { p: () => {} };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return {
                        value: {
                            p: [
                                [0, 0, { foo: "from onchange" }], // create new
                            ],
                        },
                    };
                }
            },
        });

        assert.strictEqual(target.querySelector("td").textContent, "from onchange");
    });

    QUnit.test("one2many and default_get (with date)", async function (assert) {
        serverData.models.partner.fields.p.default = [[0, false, { date: "2017-10-08", p: [] }]];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="date"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_data_cell").textContent,
            "10/08/2017",
            "should correctly display the date"
        );
    });

    QUnit.test("one2many and onchange (with integer)", async function (assert) {
        serverData.models.turtle.onchanges = {
            turtle_int: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_int"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        const td = target.querySelector("td");
        assert.strictEqual(td.textContent, "9");
        await click(td);
        await editInput(target, 'td [name="turtle_int"] input', "3");
        assert.verifySteps(["get_views", "web_read", "onchange"]);
    });

    QUnit.test("one2many and onchange (with date)", async function (assert) {
        serverData.models.partner.onchanges = {
            date: function () {},
        };
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="date"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        const td = target.querySelector("td");
        assert.strictEqual(td.textContent, "01/25/2017");

        await click(td);
        await click(td, ".o_field_date input");
        await click(getPickerCell("1").at(0));
        await clickSave(target);

        assert.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
    });

    QUnit.test("one2many and onchange only write modified field", async function (assert) {
        assert.expect(2);

        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [
                    [
                        1,
                        3,
                        {
                            display_name: "coucou",
                            turtle_foo: "has changed",
                            turtle_int: 42,
                        },
                    ],
                ];
            },
        };

        serverData.models.partner.records[0].turtles = [3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="display_name"/>
                            <field name="product_id"/>
                            <field name="turtle_bar"/>
                            <field name="turtle_foo"/>
                            <field name="turtle_int"/>
                            <field name="turtle_qux"/>
                            <field name="turtle_ref"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC: function (method, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.args[1].turtles,
                        [
                            [
                                1,
                                3,
                                {
                                    display_name: "coucou",
                                    turtle_foo: "has changed",
                                    turtle_int: 42,
                                },
                            ],
                        ],
                        "correct commands should be sent (only send changed values)"
                    );
                }
            },
            resId: 1,
        });
        assert.containsOnce(target, ".o_data_row");
        await click(target.querySelector(".o_field_one2many td"));
        await editInput(target, ".o_field_widget[name=display_name] input", "blurp");

        await clickSave(target);
    });

    QUnit.test("one2many with CREATE onchanges correctly refreshed", async function (assert) {
        let delta = 0;
        const fieldRegistry = registry.category("fields");
        for (const [name, field] of fieldRegistry.getEntries()) {
            class DeltaField extends field.component {
                setup() {
                    super.setup();
                    onWillStart(() => {
                        delta++;
                    });
                    onWillDestroy(() => {
                        delta--;
                    });
                }
            }
            fieldRegistry.add(name, { ...field, component: DeltaField }, { force: true });
        }
        let onchangeStep = 0;

        serverData.models.partner.records[0].turtles = [];
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                // the onchange will either:
                //  - create a second line if there is only one line
                //  - edit the second line if there are two lines
                if (onchangeStep === 1) {
                    obj.turtles = [
                        [
                            1,
                            obj.turtles[0][1],
                            {
                                display_name: "first",
                            },
                        ],
                        [
                            0,
                            0,
                            {
                                display_name: "second",
                                turtle_int: -obj.turtles[0][2].turtle_int,
                            },
                        ],
                    ];
                } else if (onchangeStep === 2) {
                    obj.turtles = [
                        [
                            1,
                            obj.turtles[1][1],
                            {
                                turtle_int: -obj.turtles[0][2].turtle_int,
                            },
                        ],
                    ];
                }
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="display_name" widget="char"/>
                            <field name="turtle_int"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.containsNone(target, ".o_data_row");

        await addRow(target);
        // trigger the first onchange
        onchangeStep = 1;
        await editInput(target, '[name="turtle_int"] input', "10");
        // put the list back in non edit mode
        await click(target, '[name="foo"] input');
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            ["first10", "second-10"]
        );

        // trigger the second onchange
        onchangeStep = 2;
        await click(target.querySelector(".o_field_x2many_list tbody tr td"));
        await editInput(target, '[name="turtle_int"] input', "20");
        await click(target, '[name="foo"] input');
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            ["first20", "second-20"]
        );
        assert.containsN(
            target,
            ".o_field_widget",
            delta,
            "all (non visible) field widgets should have been destroyed"
        );

        await clickSave(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            ["first20", "second-20"]
        );
    });

    QUnit.test(
        "editable one2many with sub widgets are rendered in readonly",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo" widget="char" readonly="turtle_int == 11111"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_form_view .o_field_x2many_list_row_add ");
            assert.containsNone(target, ".o_form_view input");

            await addRow(target);
            assert.containsOnce(target, ".o_form_view .o_field_x2many_list_row_add ");
            assert.containsN(target, ".o_form_view input", 2);
        }
    );

    QUnit.test("one2many editable list with onchange keeps the order", async function (assert) {
        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.models.partner.onchanges = {
            p: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["first record", "second record", "aaa"]
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".o_selected_row .o_field_widget[name=display_name] input", "new");
        await click(target, ".o_form_view");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["new", "second record", "aaa"]
        );
    });

    QUnit.test("one2many list (editable): readonly domain is evaluated", async function (assert) {
        serverData.models.partner.records[0].p = [2, 4];
        serverData.models.partner.records[1].product_id = false;
        serverData.models.partner.records[2].product_id = 37;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="p">
                            <tree editable="top">
                                <field name="display_name" readonly="not product_id"/>
                                <field name="product_id"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 1,
        });

        // switch the first row in edition
        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(
            target.querySelector(".o_selected_row .o_field_widget"),
            "o_readonly_modifier",
            "first record should have display_name in readonly mode"
        );
        // switch the second row in edition
        await click(target.querySelector(".o_data_row:not(.o_selected_row) .o_data_cell"));
        assert.doesNotHaveClass(
            target.querySelector(".o_selected_row .o_field_widget"),
            "o_readonly_modifier",
            "second record should not have display_name in readonly mode"
        );
    });

    QUnit.test("pager of one2many field in new record", async function (assert) {
        serverData.models.partner.records[0].p = [];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
        });
        assert.containsNone(target, ".o_x2m_control_panel .o_pager", "o2m pager should be hidden");

        // click to create a subrecord
        await addRow(target);
        assert.containsOnce(target, "tr.o_data_row");
        assert.containsNone(target, ".o_x2m_control_panel .o_pager", "o2m pager should be hidden");
    });

    QUnit.test("one2many list with a many2one", async function (assert) {
        assert.expect(5);

        let checkOnchange = false;
        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].product_id = 37;
        serverData.models.partner.onchanges.p = () => {};
        serverData.views = {};
        serverData.views["partner,false,form"] = '<form><field name="product_id"/></form>';

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="product_id"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange" && checkOnchange) {
                    assert.deepEqual(
                        args.args[1].p,
                        [[0, args.args[1].p[0][1], { product_id: 41 }]],
                        "should trigger onchange with correct parameters"
                    );
                }
            },
        });
        assert.containsOnce(target, ".o_data_cell[data-tooltip='xphone']");
        assert.containsNone(target, ".o_data_cell[data-tooltip='xpad']");

        await addRow(target);

        checkOnchange = true;
        await clickOpenM2ODropdown(target, "product_id");
        await click(target.querySelectorAll('div[name="product_id"] .o_input_dropdown li')[1]);

        await click(target.querySelector(".modal .modal-footer button"));
        assert.containsOnce(target, ".o_data_cell[data-tooltip='xphone']");
        assert.containsOnce(target, ".o_data_cell[data-tooltip='xpad']");
    });

    QUnit.test("one2many list with inline form view", async function (assert) {
        assert.expect(5);

        serverData.models.partner.records[0].p = [];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            // don't remove foo field in sub tree view, it is useful to make sure
            // the foo fieldwidget does not crash because the foo field is not in the form view
            arch: `
                <form>
                    <field name="p">
                        <form>
                            <field name="product_id"/>
                            <field name="int_field"/>
                        </form>
                        <tree>
                            <field name="product_id"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1].p, [
                        [
                            0,
                            args.args[1].p[0][1],
                            {
                                foo: "My little Foo Value",
                                int_field: 123,
                                product_id: 41,
                            },
                        ],
                    ]);
                }
            },
        });
        await addRow(target);

        // write in the many2one field, value = 37 (xphone)
        await clickOpenM2ODropdown(target, "product_id");
        await clickM2OHighlightedItem(target, "product_id");

        // write in the integer field
        await editInput(target, '.modal .modal-body div[name="int_field"] input', "123");

        // save and close
        await clickSave(target.querySelector(".modal"));

        assert.containsOnce(target, ".o_data_cell[data-tooltip='xphone']");

        // reopen the record in form view
        await click(target, ".o_data_cell[data-tooltip='xphone']");
        assert.strictEqual(target.querySelector(".modal .modal-body input").value, "xphone");

        await editInput(target, '.modal .modal-body div[name="int_field"] input', "456");

        // discard
        await clickDiscard(target.querySelector(".modal"));

        // reopen the record in form view
        await click(target, ".o_data_cell[data-tooltip='xphone']");

        assert.strictEqual(
            target.querySelector('.modal .modal-body div[name="int_field"] input').value,
            "123",
            "should display 123 (previous change has been discarded)"
        );

        // write in the many2one field, value = 41 (xpad)
        await clickOpenM2ODropdown(target, "product_id");
        await click(target.querySelectorAll('div[name="product_id"] .o_input_dropdown li')[1]);

        // save and close
        await clickSave(target.querySelector(".modal"));

        assert.containsOnce(target, ".o_data_cell[data-tooltip='xpad']");

        // save the record
        await clickSave(target);
    });

    QUnit.test("one2many, edit record in dialog, save, re-edit, discard", async function (assert) {
        assert.expect(6);
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <form>
                            <field name="int_field"/>
                        </form>
                        <tree>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(target.querySelector(".o_data_cell[name=int_field]").innerText, "9");

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=int_field] input").value,
            "9"
        );

        await editInput(target, ".modal .o_field_widget[name=int_field] input", "123");
        await clickSave(target.querySelector(".modal"));
        assert.strictEqual(target.querySelector(".o_data_cell[name=int_field]").innerText, "123");

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=int_field] input").value,
            "123"
        );

        await clickDiscard(target.querySelector(".modal"));
        assert.strictEqual(target.querySelector(".o_data_cell[name=int_field]").innerText, "123");

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=int_field] input").value,
            "123"
        );
    });

    QUnit.test(
        "one2many list with inline form view with context with parent key",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[0].product_id = 41;
            serverData.models.partner.records[1].product_id = 37;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="product_id"/>
                        <field name="p">
                            <form>
                                <field name="product_id" context="{'partner_foo':parent.foo, 'lalala': parent.product_id}"/>
                            </form>
                            <tree>
                                <field name="product_id"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.strictEqual(
                            args.kwargs.context.partner_foo,
                            "yop",
                            "should have correctly evaluated parent foo field"
                        );
                        assert.strictEqual(
                            args.kwargs.context.lalala,
                            41,
                            "should have correctly evaluated parent product_id field"
                        );
                    }
                },
            });

            // open a modal
            await click(target.querySelector("tr.o_data_row td[data-tooltip='xphone']"));

            // write in the many2one field
            await click(target, ".modal .o_field_many2one input");
        }
    );

    QUnit.test(
        "value of invisible x2many fields is correctly evaluated in context",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].timmy = [12];
            serverData.models.partner.records[0].p = [2, 3];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="product_id" context="{'p': p, 'timmy': timmy}"/>
                        <field name="p" invisible="1"/>
                        <field name="timmy" invisible="1"/>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        const { p, timmy } = args.kwargs.context;
                        assert.deepEqual(p, [2, 3]);
                        assert.deepEqual(timmy, [12]);
                    }
                },
            });

            await click(target, ".o_field_widget[name=product_id] input");
        }
    );

    QUnit.test(
        "one2many list, editable, with many2one and with context with parent key",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[1].product_id = 37;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="product_id" context="{'partner_foo':parent.foo}"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.strictEqual(
                            args.kwargs.context.partner_foo,
                            "yop",
                            "should have correctly evaluated parent foo field"
                        );
                    }
                },
            });

            await click(target.querySelector("tr.o_data_row td[data-tooltip='xphone']"));

            // trigger a name search
            await click(target, "table td input");
        }
    );

    QUnit.test(
        "one2many list, multi page, with many2one and with context with parent key",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [1, 2, 3];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="product_id" context="{'partner_foo': parent.foo}"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, { method, model, kwargs }) {
                    if (method === "web_read" && model === "turtle") {
                        assert.step("web_read turtle");
                        assert.deepEqual(
                            kwargs.specification.product_id.context,
                            { partner_foo: "yop" },
                            "should have correctly evaluated parent foo field"
                        );
                    }
                },
            });

            await click(target, ".o_x2m_control_panel .o_pager_next");
            assert.verifySteps(["web_read turtle"]);
        }
    );

    QUnit.test("one2many list, editable, with a date in the context", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].product_id = 37;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="date"/>
                        <field name="p" context="{'date':date}">
                            <tree editable="top">
                                <field name="date"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.strictEqual(
                        args.kwargs.context.date,
                        "2017-01-25",
                        "should have properly evaluated date key in context"
                    );
                }
            },
        });

        await addRow(target);
    });

    QUnit.test("one2many field with context", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles" context="{'turtles':turtles}">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(
                        args.kwargs.context.turtles,
                        [2],
                        "should have properly evaluated turtles key in context"
                    );
                }
            },
        });

        await addRow(target);
        await editInput(target, '[name="turtle_foo"] input', "hammer");
        await addRow(target);
    });

    QUnit.test("one2many list edition, some basic functionality", async function (assert) {
        serverData.models.partner.fields.foo.default = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        await addRow(target);
        assert.containsOnce(
            target,
            "td .o_field_widget input",
            "should have created a row in edit mode"
        );

        await editInput(target, "td .o_field_widget input", "a");
        assert.containsOnce(
            target,
            "td .o_field_widget input",
            "should not have unselected the row after edition"
        );

        await editInput(target, "td .o_field_widget input", "abc");
        await clickSave(target);
        assert.strictEqual(
            [...target.querySelectorAll("td")].filter((el) => el.textContent === "abc").length,
            1,
            "should have a row with the correct value"
        );
    });

    QUnit.test(
        "one2many list, the context is properly evaluated and sent",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="p" context="{'hello': 'world', 'abc': int_field}">
                            <tree editable="top">
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        var context = args.kwargs.context;
                        assert.strictEqual(context.hello, "world");
                        assert.strictEqual(context.abc, 10);
                    }
                },
            });

            await addRow(target);
        }
    );

    QUnit.test(
        "one2many list not editable, the context is properly evaluated and sent",
        async function (assert) {
            assert.expect(4);
            serverData.views = {
                "turtle,false,form":
                    '<form><field name="turtle_foo"/><field name="turtle_int" readonly="context.get(\'abc\') == 10"/></form>',
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="turtles" context="{'hello': 'world', 'abc': int_field, 'default_turtle_int': 5}">
                            <tree>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "get_views" && args.model === "turtle") {
                        const context = args.kwargs.context;
                        assert.deepEqual(context, {
                            lang: "en",
                            tz: "taht",
                            uid: 7,
                        });
                    }
                },
            });

            await addRow(target);
            assert.containsOnce(target, ".modal");
            assert.containsOnce(target, ".o_readonly_modifier");
            assert.equal(target.querySelector(".o_readonly_modifier").textContent, 5);
        }
    );

    QUnit.test("one2many with many2many widget: create", async function (assert) {
        assert.expect(10);

        serverData.views = {
            "turtle,false,list": `
                <tree>
                    <field name="display_name"/>
                    <field name="turtle_foo"/>
                    <field name="turtle_bar"/>
                    <field name="product_id"/>
                </tree>`,
            "turtle,false,search": `
                <search>
                    <field name="turtle_foo"/>
                    <field name="turtle_bar"/>
                    <field name="product_id"/>
                </search>`,
        };

        let expectedCommand;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles" widget="many2many">
                        <tree>
                            <field name="turtle_foo"/>
                            <field name="turtle_qux"/>
                            <field name="turtle_int"/>
                            <field name="product_id"/>
                        </tree>
                        <form>
                            <group>
                                <field name="turtle_foo"/>
                                <field name="turtle_bar"/>
                                <field name="turtle_int"/>
                                <field name="product_id"/>
                            </group>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/turtle/web_save") {
                    assert.ok(args.args, "should write on the turtle record");
                }
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.strictEqual(args.args[0][0], 1, "should write on the partner record 1");
                    assert.deepEqual(
                        args.args[1].turtles,
                        expectedCommand,
                        "should send only a 'LINK TO' command"
                    );
                }
            },
        });

        await addRow(target);

        assert.containsN(
            target,
            ".modal .o_data_row",
            2,
            "should have 2 records in the select view (the last one is not displayed because it is already selected)"
        );

        await click(target.querySelector(".modal .o_data_row .o_list_record_selector input"));
        await nextTick(); // additional render due to the change of selection (done in owl, not pure js)
        await click(target.querySelector(".modal .o_select_button"));
        expectedCommand = [[4, 1]];
        await clickSave(target);

        await addRow(target);
        assert.containsOnce(
            target,
            ".modal .o_data_row",
            "should have 1 record in the select view"
        );

        await click(target.querySelectorAll(".modal-footer button")[1]);
        await editInput(target, '.modal .o_field_widget[name="turtle_foo"] input', "tototo");
        await editInput(target, '.modal .o_field_widget[name="turtle_int"] input', 50);
        await clickOpenM2ODropdown(target, "product_id");
        await clickM2OHighlightedItem(target, "product_id");

        await click(target.querySelector(".modal-footer button"));

        assert.containsNone(target, ".modal", "should close the modals");
        assert.containsN(target, ".o_data_row", 3, "should have 3 records in one2many list");
        assert.strictEqual(
            $(target.querySelectorAll(".o_data_row")).text(),
            "blip1.59yop1.50tototo1.550xphone",
            "should display the record values in one2many list"
        );

        expectedCommand = [[4, 4]];
        await clickSave(target);
    });

    QUnit.test("one2many with many2many widget: edition", async function (assert) {
        assert.expect(7);

        serverData.views = {
            "turtle,false,list": `
                <tree>
                    <field name="display_name"/>
                    <field name="turtle_foo"/>
                    <field name="turtle_bar"/>
                    <field name="product_id"/>
                </tree>`,
            "turtle,false,search": `
                <search>
                    <field name="turtle_foo"/>
                    <field name="turtle_bar"/>
                    <field name="product_id"/>
                </search>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles" widget="many2many">
                        <tree>
                            <field name="turtle_foo"/>
                            <field name="turtle_qux"/>
                            <field name="turtle_int"/>
                            <field name="product_id"/>
                        </tree>
                        <form>
                            <group>
                                <field name="turtle_foo"/>
                                <field name="turtle_bar"/>
                                <field name="turtle_int"/>
                                <field name="turtle_trululu"/>
                                <field name="product_id"/>
                            </group>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/turtle/web_save") {
                    assert.strictEqual(args.args[0].length, 1, "should write on the turtle record");
                    assert.deepEqual(
                        args.args[1],
                        { product_id: 37 },
                        "should write only the product_id on the turtle record"
                    );
                }
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.strictEqual(args.args[0][0], 1, "should write on the partner record 1");
                    assert.strictEqual(
                        args.args[1].turtles[0][0],
                        4,
                        "should send only a 'link to' command"
                    );
                }
            },
        });

        await click(target.querySelector(".o_data_cell"));
        assert.strictEqual(
            $(".modal .modal-title").first().text().trim(),
            "Open: one2many turtle field",
            "modal should use the python field string as title"
        );
        await clickDiscard(target.querySelector(".modal"));

        // edit the first one2many record
        await click($(target).find(".o_data_cell:first")[0]);
        await clickOpenM2ODropdown(target, "product_id");
        await clickM2OHighlightedItem(target, "product_id");
        await click($(".modal-footer button:first")[0]);

        await clickSave(target);

        // add a one2many record
        await addRow(target);
        await click($(".modal .o_data_row:first .o_list_record_selector input")[0]);
        await nextTick(); // wait for re-rendering because of the change of selection
        await click($(".modal .o_select_button")[0]);

        // edit the second one2many record
        await click($(target).find(".o_data_row:eq(1) .o_data_cell")[0]);
        await clickOpenM2ODropdown(target, "product_id");
        await clickM2OHighlightedItem(target, "product_id");
        await click($(".modal .modal-footer button:first")[0]);

        await clickSave(target);
    });

    QUnit.test("new record, the context is properly evaluated and sent", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.int_field.default = 17;
        let n = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="p" context="{'hello': 'world', 'abc': int_field}">
                            <tree editable="top">
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    n++;
                    if (n === 2) {
                        var context = args.kwargs.context;
                        assert.strictEqual(context.hello, "world");
                        assert.strictEqual(context.abc, 17);
                    }
                }
            },
        });

        await addRow(target);
    });

    QUnit.test("parent data is properly sent on an onchange rpc", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="display_name"/>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="bar"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    const fieldValues = args.args[1];
                    assert.deepEqual(
                        fieldValues.trululu,
                        { foo: "hello", id: 1 },
                        "should have properly sent the parent changes"
                    );
                }
            },
        });

        await editInput(target, "[name=foo] input", "hello");
        await addRow(target);
    });

    QUnit.test(
        "parent data is properly sent on an onchange rpc (existing x2many record)",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.onchanges = {
                display_name: function () {},
                foo: function () {},
            };
            serverData.models.partner.records[0].p = [1];
            serverData.models.partner.records[0].turtles = [2];

            let count = 0;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="display_name"/>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="foo"/>
                            <field name="turtles" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        const fieldValues = args.args[1];
                        if (count === 1) {
                            assert.deepEqual(fieldValues.trululu, {
                                foo: "hello",
                                id: 1,
                            });
                        } else if (count === 2) {
                            assert.deepEqual(fieldValues.trululu, {
                                foo: "hello",
                                id: 1,
                                p: [[1, 1, { display_name: "new val" }]],
                            });
                        }
                        count++;
                    }
                },
            });
            assert.containsOnce(target, ".o_data_row");

            await editInput(target, "[name=foo] input", "hello");
            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.containsOnce(target, ".o_data_row.o_selected_row");

            await editInput(
                target,
                ".o_selected_row .o_field_widget[name=display_name] input",
                "new val"
            );
            await editInput(target, ".o_selected_row .o_field_widget[name=foo] input", "new foo");
        }
    );

    QUnit.test(
        "parent data is properly sent on an onchange rpc, new record",
        async function (assert) {
            assert.expect(5);

            serverData.models.turtle.onchanges = { turtle_bar: function () {} };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_bar"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "onchange" && args.model === "turtle") {
                        var fieldValues = args.args[1];
                        assert.strictEqual(
                            fieldValues.turtle_trululu.foo,
                            "My little Foo Value",
                            "should have properly sent the parent foo value"
                        );
                    }
                },
            });
            await addRow(target);
            assert.verifySteps(["get_views", "onchange", "onchange"]);
        }
    );

    QUnit.test("id in one2many obtained in onchange is properly set", async function (assert) {
        serverData.models.partner.onchanges.turtles = function (obj) {
            obj.turtles = [
                [4, 3],
                [1, 3, { turtle_foo: "kawa" }],
            ];
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="id"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.deepEqual(
            [...target.querySelectorAll("tr.o_data_row .o_data_cell")].map((el) => el.textContent),
            ["3", "kawa"],
            "should have properly displayed id and foo field"
        );
    });

    QUnit.test("id field in one2many in a new record", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="id" invisible="1"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    const virtualID = args.args[1].turtles[0][1];
                    assert.deepEqual(
                        args.args[1].turtles,
                        [[0, virtualID, { turtle_foo: "cat" }]],
                        "should send proper commands"
                    );
                }
            },
        });
        await addRow(target);
        await editInput(target, 'td [name="turtle_foo"] input', "cat");
        await clickSave(target);
    });

    QUnit.test("sub form view with a required field", async function (assert) {
        serverData.models.partner.fields.foo.required = true;
        serverData.models.partner.fields.foo.default = null;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <form>
                            <group><field name="foo"/></group>
                        </form>
                        <tree>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await addRow(target);
        await click(target.querySelector(".modal-footer button.btn-primary"));

        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal label.o_field_invalid");
    });

    QUnit.test("one2many list with action button", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <button name="method_name" type="object" icon="fa-plus"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        patchWithCleanup(form.env.services.action, {
            doActionButton: (params) => {
                assert.deepEqual(params.resId, 2);
                assert.strictEqual(params.resModel, "partner");
                assert.strictEqual(params.name, "method_name");
                assert.strictEqual(params.type, "object");
            },
        });

        await click(target, ".o_list_button button");
    });

    QUnit.test("one2many kanban with action button", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="foo"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div>
                                        <span><t t-esc="record.foo.value"/></span>
                                        <button name="method_name" type="object" class="fa fa-plus"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });
        patchWithCleanup(form.env.services.action, {
            doActionButton: (params) => {
                assert.deepEqual(params.resId, 2);
                assert.strictEqual(params.resModel, "partner");
                assert.strictEqual(params.name, "method_name");
                assert.strictEqual(params.type, "object");
            },
        });

        await click(target, ".oe_kanban_action_button");
    });

    QUnit.test("one2many without inline tree arch", async function (assert) {
        serverData.models.partner.records[0].turtles = [2, 3];
        serverData.views = {
            "turtle,false,list": `
                <tree>
                    <field name="turtle_bar"/>
                    <field name="display_name"/>
                    <field name="partner_ids"/>
                </tree>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            // should not call loadViews for the field with many2many_tags widget,
            // nor for the invisible field
            arch: `
                <form>
                    <group>
                        <field name="p" widget="many2many_tags"/>
                        <field name="turtles"/>
                        <field name="timmy" invisible="1"/>
                    </group>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            '.o_field_widget[name="turtles"] .o_list_renderer',
            "should display one2many list view in the modal"
        );

        assert.containsN(target, ".o_data_row", 2, "should display the 2 turtles");
    });

    QUnit.test("many2one and many2many in one2many", async function (assert) {
        assert.expect(8);

        serverData.models.turtle.records[1].product_id = 37;
        serverData.models.partner.records[0].turtles = [2, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="display_name"/>
                                <field name="product_id"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.args[1].turtles,
                        [
                            [
                                1,
                                2,
                                {
                                    partner_ids: [
                                        [3, 4],
                                        [4, 1],
                                    ],
                                    product_id: 41,
                                },
                            ],
                        ],
                        "generated commands should be correct"
                    );
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(
            target.querySelector(".o_data_row .o_list_many2one").innerText,
            "xphone",
            "should correctly display the m2o"
        );
        assert.containsN(
            target,
            '.o_data_row td div[name="partner_ids"] .badge',
            2,
            "m2m should contain two tags"
        );

        // edit the m2m of first row
        await click(target.querySelector(".o_list_renderer tbody td"));

        assert.deepEqual(
            [...target.querySelectorAll(".o_selected_row .o_field_many2many_tags .badge")].map(
                (el) => el.innerText
            ),
            ["second record", "aaa"]
        );

        // remove a tag
        await click(
            target.querySelectorAll(".o_selected_row .o_field_many2many_tags .badge .o_delete")[1]
        );

        assert.deepEqual(
            [...target.querySelectorAll(".o_selected_row .o_field_many2many_tags .badge")].map(
                (el) => el.innerText
            ),
            ["second record"]
        );
        // add a tag
        await click(target.querySelector('div[name="partner_ids"] input'));
        await click(target.querySelector('div[name="partner_ids"] .o_input_dropdown li')); // xpad

        assert.deepEqual(
            [...target.querySelectorAll(".o_selected_row .o_field_many2many_tags .badge")].map(
                (el) => el.innerText
            ),
            ["second record", "first record"]
        );

        // edit the m2o of first row
        await clickOpenM2ODropdown(target, "product_id");
        await click(target.querySelectorAll('div[name="product_id"] .o_input_dropdown li')[1]); // xpad

        assert.strictEqual(
            target.querySelector(".o_selected_row .o_field_many2one input").value,
            "xpad",
            "m2o value should have been updated"
        );

        // save (should correctly generate the commands)
        await clickSave(target);
    });

    QUnit.test(
        "many2manytag in one2many, onchange, some modifiers, and more than one page",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            serverData.models.partner.onchanges.turtles = function () {};

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top" limit="2">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags" readonly="turtle_foo == 'a'"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });
            assert.containsN(target, ".o_data_row", 2);

            await click(target.querySelector(".o_list_record_remove"));
            assert.containsN(target, ".o_data_row", 2);

            await click(target.querySelector(".o_list_record_remove"));
            assert.containsOnce(target, ".o_data_row");

            assert.verifySteps([
                "get_views", // main form view
                "web_read", // initial read on partner
                "web_read", // after first delete, read on turtle (to fetch 3rd record)
                "onchange", // after first delete, onchange on field turtles
                "onchange", // onchange after second delete
            ]);
        }
    );

    QUnit.test("onchange many2many in one2many list editable", async function (assert) {
        serverData.models.product.records.push({
            id: 1,
            display_name: "xenomorphe",
        });

        serverData.models.turtle.onchanges = {
            product_id: function (rec) {
                if (rec.product_id === 41) {
                    rec.partner_ids = [[4, 1]];
                } else if (rec.product_id === 37) {
                    rec.partner_ids = [[4, 2]];
                }
            },
        };
        let enableOnchange = false;
        const partnerOnchange = function (rec) {
            if (!enableOnchange) {
                return;
            }
            rec.turtles = [
                [
                    0,
                    0,
                    {
                        display_name: "new line",
                        product_id: [37, "xphone"],
                        partner_ids: [[4, 1]],
                    },
                ],
                [
                    1,
                    rec.turtles[0][1],
                    {
                        product_id: [1, "xenomorphe"],
                        partner_ids: rec.turtles[0][2].partner_ids.length
                            ? [
                                  [3, 1],
                                  [4, 2],
                              ]
                            : [[4, 2]],
                    },
                ],
            ];
        };

        serverData.models.partner.onchanges = {
            int_field: partnerOnchange,
            turtles: partnerOnchange,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="display_name"/>
                                <field name="product_id"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
        });

        // add new line (first, xpad)
        await addRow(target);
        await editInput(target, 'div[name="display_name"] input', "first");
        await clickOpenM2ODropdown(target, "product_id");
        await click(target.querySelectorAll('div[name="product_id"] .o_input_dropdown li')[1]); // xpad

        assert.containsOnce(
            target,
            ".o_field_many2many_tags .o_tags_input",
            "should display the line in editable mode"
        );
        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "xpad",
            "should display the product xpad"
        );
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .o_tag_badge_text").innerText,
            "first record",
            "should display the tag from the onchange"
        );
        assert.strictEqual(
            target.querySelector(".o_data_cell .o_required_modifier input").value,
            "xpad",
            "should display the product xpad"
        );

        await click(target, 'div[name="int_field"] input');

        assert.containsNone(
            target,
            ".o_field_many2many_tags input.o_input",
            "should display the tag in readonly"
        );

        // enable the many2many onchange and generate it
        enableOnchange = true;
        await editInput(target, 'div[name="int_field"] input', "10");

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["first", "xenomorphe", "second record", "new line", "xphone", "first record"]
        );

        // disable the many2many onchange
        enableOnchange = false;

        // remove and start over
        await click(target.querySelector(".o_list_record_remove button"));
        await click(target.querySelector(".o_list_record_remove button"));

        // enable the many2many onchange
        enableOnchange = true;
        // add new line (first, xenomorphe)
        await addRow(target);
        await editInput(target, 'div[name="display_name"] input', "first");
        await clickOpenM2ODropdown(target, "product_id");
        await click(target.querySelectorAll('div[name="product_id"] .o_input_dropdown li')[2]); // xenomorphe

        assert.containsOnce(
            target,
            ".o_field_many2many_tags .o_tags_input",
            "should display the line in editable mode"
        );
        assert.strictEqual(
            target.querySelector('div[name="product_id"] input').value,
            "xenomorphe",
            "should display the product xenomorphe"
        );
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .o_tag_badge_text").innerText,
            "second record",
            "should display the tag from the onchange"
        );

        // put list in readonly mode
        await click(target, 'div[name="int_field"] input');

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["first", "xenomorphe", "second record", "new line", "xphone", "first record"]
        );

        assert.containsNone(
            target,
            ".o_field_many2many_tags input.o_input",
            "should display the tag in readonly"
        );

        await editInput(target, 'div[name="int_field"] input', "10");

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["first", "xenomorphe", "second record", "new line", "xphone", "first record"]
        );

        await clickSave(target);

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["first", "xenomorphe", "second record", "new line", "xphone", "first record"]
        );
    });

    QUnit.test("load view for x2many in one2many", async function (assert) {
        serverData.models.turtle.records[1].product_id = 37;
        serverData.models.partner.records[0].turtles = [2, 3];
        serverData.models.partner.records[2].turtles = [1, 3];
        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="turtles">
                            <form>
                                <group>
                                    <field name="product_id"/>
                                    <field name="partner_ids"/>
                                </group>
                            </form>
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        assert.containsN(target, ".o_data_row", 2);

        await click(target.querySelector(".o_data_row td"));

        assert.containsOnce(target, '.modal div[name="partner_ids"] .o_list_renderer');
    });

    QUnit.test(
        "one2many (who contains a one2many) with tree view and without form view",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form edit="0">
                        <group>
                            <field name="turtles">
                                <tree>
                                    <field name="partner_ids"/>
                                </tree>
                                <form>
                                    <field name="turtle_foo"/>
                                </form>
                            </field>
                        </group>
                    </form>`,
                resId: 1,
            });

            await click(target.querySelector(".o_data_row td"));

            assert.strictEqual(
                target.querySelector('.modal div[name="turtle_foo"]').innerText,
                "blip"
            );
        }
    );

    QUnit.test("one2many with x2many in form view (but not in list view)", async function (assert) {
        assert.expect(1);

        // avoid error when saving the edited related record (because the
        // related x2m field is unknown in the inline list view)
        // also ensure that the changes are correctly saved

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree>
                                <field name="turtle_foo"/>
                            </tree>
                            <form>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </form>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1].turtles, [
                        [
                            1,
                            2,
                            {
                                partner_ids: [[4, 1]],
                            },
                        ],
                    ]);
                }
            },
        });

        await click(target.querySelector(".o_data_row td")); // edit first record

        await click(target.querySelector('div[name="partner_ids"] input'));
        await click(target.querySelector('div[name="partner_ids"] .o_input_dropdown li'));

        // add a many2many tag and save
        await editInput(target, ".modal .o_field_many2many_tags input", "test");

        await click(target, ".modal .modal-footer .btn-primary"); // save

        await clickSave(target);
    });

    QUnit.test("many2many list in a one2many opened by a many2one", async function (assert) {
        assert.expect(1);

        serverData.models.turtle.records[1].turtle_trululu = 2;
        serverData.views = {
            "partner,false,form": '<form><field name="timmy"/></form>',
            "partner_type,false,list":
                '<tree editable="bottom"><field name="display_name"/></tree>',
            "partner_type,false,search": "<search></search>",
        };
        await makeViewInDialog({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_trululu"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/get_formview_id") {
                    return Promise.resolve(false);
                }
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1].timmy, [[4, 12]], "should properly add id");
                }
            },
        });

        // edit the first partner in the one2many partner form view
        await click(target.querySelector(".o_data_row td.o_data_cell"));
        // open form view for many2one
        await click(target.querySelector(".o_external_button"));

        // click on add, to add a new partner in the m2m
        await addRow(target.querySelectorAll(".modal")[1]);

        // select the partner_type 'gold' (this closes the 3rd modal)
        await click(target.querySelector(".o_dialog:not(.o_inactive_modal) td.o_data_cell")); // select gold

        // confirm the changes in the modal
        await clickSave(target.querySelectorAll(".modal")[1]);

        await clickSave(target);
    });

    QUnit.test("nested x2many default values", async function (assert) {
        serverData.models.partner.fields.turtles.default = [
            [0, 0, { partner_ids: [[4, 4]] }],
            [0, 0, { partner_ids: [[4, 1]] }],
        ];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="partner_ids" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.containsN(target, ".o_field_x2many_list .o_data_row", 2);
        assert.containsN(
            target,
            '.o_field_x2many_list .o_field_many2many_tags[name="partner_ids"] .badge',
            2
        );
        assert.deepEqual(
            [
                ...target.querySelectorAll(
                    '.o_field_x2many_list .o_field_many2many_tags[name="partner_ids"] .o_tag_badge_text'
                ),
            ].map((el) => el.textContent),
            ["aaa", "first record"]
        );
    });

    QUnit.test("nested x2many (inline form view) and onchanges", async function (assert) {
        assert.expect(8);
        serverData.models.partner.onchanges.bar = function (obj) {
            if (!obj.bar) {
                obj.p = [
                    [
                        0,
                        0,
                        {
                            turtles: [
                                [
                                    0,
                                    0,
                                    {
                                        turtle_foo: "new turtle",
                                    },
                                ],
                            ],
                        },
                    ],
                ];
            }
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="p">
                        <tree>
                            <field name="turtles"/>
                        </tree>
                        <form>
                            <field name="turtles">
                                <tree>
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(args.args[3], {
                        bar: {},
                        display_name: {},
                        p: {
                            fields: {
                                turtles: {
                                    fields: {
                                        turtle_foo: {},
                                    },
                                },
                            },
                            limit: 40,
                            order: "",
                        },
                    });
                }
            },
        });
        assert.containsNone(target, ".o_data_row");

        await click(target, ".o_field_widget[name=bar] input");
        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector(".o_data_row").textContent, "1 record");

        await click(target.querySelector(".o_data_row td"));
        assert.containsOnce(target, ".modal .o_form_view");
        assert.containsOnce(target, ".modal .o_form_view .o_data_row");
        assert.strictEqual(
            target.querySelector(".modal .o_form_view .o_data_row").textContent,
            "new turtle"
        );
    });

    QUnit.test(
        "nested x2many (non inline views and no widget on inner x2many in list)",
        async function (assert) {
            serverData.models.partner.records[0].p = [1];
            serverData.views = {
                "partner,false,list": `
                    <tree>
                        <field name="turtles"/>
                    </tree>`,
                "partner,false,form": `
                    <form>
                        <field name="turtles" widget="many2many_tags"/>
                    </form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="p"/></form>',
                resId: 1,
            });

            assert.containsOnce(target, ".o_data_row");
            assert.strictEqual(target.querySelector(".o_data_row").innerText.trim(), "1 record");

            await click(target.querySelector(".o_data_row td"));

            assert.containsOnce(target, ".modal .o_form_view");
            assert.containsOnce(target, ".modal .o_form_view .o_field_many2many_tags .badge");
            assert.strictEqual(
                target.querySelector(".modal .o_field_many2many_tags").innerText.trim(),
                "donatello"
            );
        }
    );

    QUnit.test(
        "one2many (who contains display_name) with tree view and without form view",
        async function (assert) {
            serverData.views = {
                "turtle,false,form": '<form><field name="turtle_foo"/></form>',
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form edit="0">
                        <group>
                            <field name="turtles">
                                <tree>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </group>
                    </form>`,
                resId: 1,
            });

            await click(target.querySelector(".o_data_row td"));

            assert.strictEqual(
                target.querySelector('.modal div[name="turtle_foo"]').innerText,
                "blip",
                "should open the modal and display the form field"
            );
        }
    );

    QUnit.test(
        "open a record in a one2many list (mode 'readonly') with a notebook",
        async function (assert) {
            serverData.views = {
                "turtle,false,form": `
                    <form>
                        <notebook>
                            <page string="Yop">
                                <field name="display_name">
                                </field>
                            </page>
                    </notebook>
                    </form>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            await click(target, ".o_data_cell");
            assert.containsOnce(target, ".modal .o_form_view");
            assert.containsOnce(target, ".modal .o_form_view .o_notebook_headers");
            assert.strictEqual(
                target.querySelector(".modal .o_form_view .o_notebook_headers").textContent,
                "Yop"
            );
        }
    );

    QUnit.test("one2many field with virtual ids", async function (assert) {
        serverData.views = {
            "partner,false,form": '<form><field name="foo"/></form>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <notebook>
                                <page>
                                    <field name="p" mode="kanban">
                                        <kanban>
                                            <templates>
                                                <t t-name="kanban-box">
                                                    <div class="oe_kanban_details">
                                                        <div class="o_test_id">
                                                            <field name="id"/>
                                                        </div>
                                                        <div class="o_test_foo">
                                                            <field name="foo"/>
                                                        </div>
                                                    </div>
                                                </t>
                                            </templates>
                                        </kanban>
                                    </field>
                                </page>
                            </notebook>
                        </group>
                    </sheet>
                </form>`,
            resId: 4,
        });

        assert.containsOnce(
            target,
            ".o_field_widget .o_kanban_renderer",
            "should have one inner kanban view for the one2many field"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
            "should not have kanban records yet"
        );

        // create a new kanban record
        await click(target, ".o_field_widget .o-kanban-button-new");

        // save & close the modal
        assert.strictEqual(
            target.querySelector(".modal-content .o_field_widget input").value,
            "My little Foo Value",
            "should already have the default value for field foo"
        );
        await clickSave(target.querySelector(".modal"));

        assert.containsOnce(
            target,
            ".o_field_widget .o_kanban_renderer",
            "should have one inner kanban view for the one2many field"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
            "should now have one kanban record"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_id"
            ).innerText,
            "",
            "should not have a value for the id field"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_foo"
            ).innerText,
            "My little Foo Value",
            "should have a value for the foo field"
        );

        // save the view to force a create of the new record in the one2many
        await clickSave(target);
        assert.containsOnce(
            target,
            ".o_field_widget .o_kanban_renderer",
            "should have one inner kanban view for the one2many field"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
            "should now have one kanban record"
        );
        assert.notEqual(
            target.querySelector(
                ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_id"
            ).innerText,
            "",
            "should now have a value for the id field"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_field_widget .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost) .o_test_foo"
            ).innerText,
            "My little Foo Value",
            "should still have a value for the foo field"
        );
    });

    QUnit.test("one2many field with virtual ids with kanban button", async function (assert) {
        assert.expect(36);

        // this is a way to avoid the debounce of triggerAction
        patchWithCleanup(browser, {
            setTimeout(fn) {
                Promise.resolve().then(fn);
            },
        });

        serverData.models.partner.records[0].p = [4];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" mode="kanban">
                        <kanban>
                            <templates>
                                <field name="foo"/>
                                <t t-name="kanban-box">
                                    <div>
                                        <span><t t-esc="record.foo.value"/></span>
                                        <button type="object" class="btn btn-link fa fa-shopping-cart" name="button_warn" string="button_warn" warn="warn" />
                                        <button type="object" class="btn btn-link fa fa-shopping-cart" name="button_disabled" string="button_disabled" />
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="foo"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step(args.method);
                    assert.strictEqual(args.args[1].p.length, 1);
                    const command = args.args[1].p[0];
                    assert.strictEqual(command[0], 0);
                    assert.deepEqual(command[2], {
                        foo: "My little Foo Value",
                    });
                }
            },
        });

        patchWithCleanup(form.env.services.action, {
            doActionButton: (params) => {
                const { name, resModel, resId } = params;
                assert.step(`${name}_${resModel}_${resId}`);
                params.onClose();
            },
        });

        // 1. Define all css selector
        const oKanbanView = ".o_field_widget .o_kanban_renderer";
        const oKanbanRecordActive = oKanbanView + " .o_kanban_record:not(.o_kanban_ghost)";
        const oAllKanbanButton = oKanbanRecordActive + " button";
        const btn1 = oKanbanRecordActive + ":nth-child(1) button";
        const btn2 = oKanbanRecordActive + ":nth-child(2) button";
        const btn1Warn = btn1 + '[name="button_warn"]';
        const btn1Disabled = btn1 + '[name="button_disabled"]';
        const btn2Warn = btn2 + '[name="button_warn"]';
        const btn2Disabled = btn2 + '[name="button_disabled"]';

        // check if we already have one kanban card
        assert.containsOnce(
            target,
            oKanbanView,
            "should have one inner kanban view for the one2many field"
        );
        assert.containsOnce(target, oKanbanRecordActive, "should have one kanban records yet");

        // we have 2 buttons
        assert.containsN(target, oAllKanbanButton, 2, "should have 2 buttons type object");

        // disabled ?
        assert.containsNone(
            target,
            oAllKanbanButton + "[disabled]",
            "should not have button type object disabled"
        );

        // click on the button
        await click(target, btn1Disabled);
        assert.verifySteps(["button_disabled_partner_4"]);

        await click(target, btn1Warn);
        assert.verifySteps(["button_warn_partner_4"]);

        // click on existing buttons
        await click(target, btn1Disabled);
        assert.verifySteps(["button_disabled_partner_4"]);

        await click(target, btn1Warn);
        assert.verifySteps(["button_warn_partner_4"]);

        // create new kanban record
        await click(target, ".o_field_widget .o-kanban-button-new");

        // save & close the modal
        assert.strictEqual(
            target.querySelector(".modal-content .o_field_widget input").value,
            "My little Foo Value",
            "should already have the default value for field foo"
        );
        await clickSave(target.querySelector(".modal"));

        // check new item
        assert.containsN(target, oAllKanbanButton, 4, "should have 4 buttons type object");
        assert.containsN(target, btn1, 2, "should have 2 buttons type object in area 1");
        assert.containsN(target, btn2, 2, "should have 2 buttons type object in area 2");
        assert.containsNone(
            target,
            oAllKanbanButton + "[disabled]",
            "should have 1 button type object disabled"
        );

        assert.notOk(target.querySelector(btn2Disabled).disabled);
        assert.notOk(target.querySelector(btn2Warn).disabled);
        assert.strictEqual(
            target.querySelector(btn2Warn).getAttribute("warn"),
            "warn",
            "Should have a button type object with warn attr in area 2"
        );

        // click all buttons
        await click(target, btn1Disabled);
        assert.verifySteps(["web_save", "button_disabled_partner_4"]);
        await click(target, btn1Warn);
        await click(target, btn2Disabled);
        await click(target, btn2Warn);
        assert.verifySteps([
            "button_warn_partner_4",
            "button_disabled_partner_5",
            "button_warn_partner_5",
        ]);

        // save the form
        assert.containsOnce(target, ".o_form_saved");

        // click all buttons
        await click(target, btn1Disabled);
        await click(target, btn1Warn);
        await click(target, btn2Disabled);
        await click(target, btn2Warn);

        assert.verifySteps(
            [
                "button_disabled_partner_4",
                "button_warn_partner_4",
                "button_disabled_partner_5",
                "button_warn_partner_5",
            ],
            "should have clicked once on every button"
        );
    });

    QUnit.test("focusing fields in one2many list", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </group>
                    <field name="foo"/>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_data_row td"));
        const turtleFooInput = target.querySelector('[name="turtle_foo"] input');
        assert.strictEqual(turtleFooInput, document.activeElement);

        triggerHotkey("Tab");
        await nextTick();
        const turtleIntInput = target.querySelector('[name="turtle_int"] input');
        assert.strictEqual(turtleIntInput, document.activeElement);
    });

    QUnit.test("one2many list editable = top", async function (assert) {
        assert.expect(5);

        serverData.models.turtle.fields.turtle_foo.default = "default foo turtle";
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    const commands = args.args[1].turtles;
                    assert.deepEqual(commands, [
                        [0, commands[0][1], { turtle_foo: "default foo turtle" }],
                    ]);
                }
            },
        });
        assert.containsOnce(target, ".o_data_row", "should start with one data row");

        await addRow(target);

        assert.containsN(target, ".o_data_row", 2, "should have 2 data rows");
        assert.strictEqual(
            target.querySelector("tr.o_data_row input").value,
            "default foo turtle",
            "first row should be the new value"
        );
        assert.hasClass(
            target.querySelector("tr.o_data_row"),
            "o_selected_row",
            "first row should be selected"
        );

        await clickSave(target);
    });

    QUnit.test("one2many list editable = bottom", async function (assert) {
        assert.expect(5);
        serverData.models.turtle.fields.turtle_foo.default = "default foo turtle";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    const commands = args.args[1].turtles;
                    assert.deepEqual(commands, [
                        [0, commands[0][1], { turtle_foo: "default foo turtle" }],
                    ]);
                }
            },
        });

        assert.containsOnce(target, ".o_data_row", "should start with one data row");

        await addRow(target);

        assert.containsN(target, ".o_data_row", 2, "should have 2 data rows");
        assert.strictEqual(
            target.querySelector("tr.o_data_row input").value,
            "default foo turtle",
            "second row should be the new value"
        );
        assert.hasClass(
            target.querySelectorAll("tr.o_data_row")[1],
            "o_selected_row",
            "second row should be selected"
        );

        await clickSave(target);
    });

    QUnit.test(
        "one2many list editable - should properly unselect the list field after shift+tab",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: /* xml */ `
                <form>
                    <group>
                        <field name="display_name"/>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="turtle_bar" optional="hide"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
                resId: 1,
            });

            await click(target, ".o_data_row td:first-child");
            assert.containsOnce(target, ".o_selected_row", "should have selected row");
            const { keydownEvent } = await triggerHotkey("Shift+Tab");
            await nextTick();
            assert.containsNone(target, ".o_selected_row", "list should not be in edition");
            // We also check the event is not default prevented, to make sure that the
            // event flows and selection goes to the previous field.
            assert.ok(!keydownEvent.defaultPrevented);
        }
    );

    QUnit.test(
        "one2many list editable - should not allow tab navigation focus on the optional field toggler",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: /* xml */ `
                <form>
                    <group>
                        <field name="display_name"/>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="turtle_bar" optional="hide"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
                resId: 1,
            });

            assert.strictEqual(
                target.querySelector(".o_optional_columns_dropdown .dropdown-toggle").tabIndex,
                -1
            );
        }
    );

    QUnit.test('one2many list edition, no "Remove" button in modal', async function (assert) {
        serverData.models.partner.fields.foo.default = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        await addRow(target);
        assert.containsOnce(target, ".modal");
        assert.containsNone(target, ".modal .modal-footer .o_btn_remove");

        // Discard a modal
        await click(target.querySelector(".modal-footer .btn-secondary"));
    });

    QUnit.test('x2many fields use their "mode" attribute', async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field mode="kanban" name="turtles">
                            <tree>
                                <field name="turtle_foo"/>
                            </tree>
                            <kanban>
                                <templates>
                                    <t t-name="kanban-box">
                                        <div>
                                            <field name="turtle_int"/>
                                        </div>
                                    </t>
                                </templates>
                            </kanban>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_field_one2many .o_field_x2many_kanban",
            "should have rendered a kanban view"
        );
    });

    QUnit.test("one2many list editable, onchange and required field", async function (assert) {
        serverData.models.turtle.fields.turtle_foo.required = true;
        let intFieldVal = 0;
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.int_field = intFieldVal;
            },
        };
        serverData.models.partner.records[0].int_field = 0;
        serverData.models.partner.records[0].turtles = [];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_int"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
            resId: 1,
        });
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="int_field"] input').value,
            "0"
        );

        intFieldVal = 1;
        await addRow(target);
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="int_field"] input').value,
            "0"
        );
        assert.verifySteps(["get_views", "web_read", "onchange"]);

        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "some text");
        assert.verifySteps(["onchange"]);
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="int_field"] input').value,
            "1"
        );
    });

    QUnit.test(
        "one2many list editable: trigger onchange when row is valid",
        async function (assert) {
            // should omit require fields that aren't in the view as they (obviously)
            // have no value, when checking the validity of required fields
            // shouldn't consider numerical fields with value 0 as unset
            serverData.models.turtle.fields.turtle_foo.required = true;
            serverData.models.turtle.fields.turtle_qux.required = true; // required field not in the view
            serverData.models.turtle.fields.turtle_bar.required = true; // required boolean field with no default
            delete serverData.models.turtle.fields.turtle_bar.default;
            serverData.models.turtle.fields.turtle_int.required = true; // required int field (default 0)
            serverData.models.turtle.fields.turtle_int.default = 0;
            serverData.models.turtle.fields.partner_ids.required = true; // required many2many
            let intFieldVal = 0;
            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = intFieldVal;
                },
            };
            serverData.models.partner.records[0].int_field = 0;
            serverData.models.partner.records[0].turtles = [];

            serverData.views = {
                "turtle,false,list": `
                    <tree editable="top">
                        <field name="turtle_qux"/>
                        <field name="turtle_bar"/>
                        <field name="turtle_int"/>
                        <field name="turtle_foo"/>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </tree>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="turtles"/>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
                resId: 1,
            });

            assert.strictEqual(
                $(target).find('.o_field_widget[name="int_field"] input').val(),
                "0",
                "int_field should start with value 0"
            );

            intFieldVal = 1;
            // add a new row (which is invalid at first)
            await addRow(target);
            assert.strictEqual(
                $(target).find('.o_field_widget[name="int_field"] input').val(),
                "0",
                "int_field should still be 0 (no onchange should have been done yet)"
            );
            assert.verifySteps(["get_views", "web_read", "onchange"]);

            // fill turtle_foo field
            await editInput(target, '.o_field_widget[name="turtle_foo"] input', "some text");
            assert.strictEqual(
                $(target).find('.o_field_widget[name="int_field"] input').val(),
                "0",
                "int_field should still be 0 (no onchange should have been done yet)"
            );
            assert.verifySteps([], "no onchange should have been applied");

            // fill partner_ids field with a tag (all required fields will then be set)
            await selectDropdownItem(target, "partner_ids", "first record");

            assert.strictEqual(
                $(target).find('.o_field_widget[name="int_field"] input').val(),
                "1",
                "int_field should now be 1 (the onchange should have been done"
            );
            assert.verifySteps(["name_search", "web_read", "onchange"]);
        }
    );

    QUnit.test(
        "one2many list editable: 'required' modifiers is properly working",
        async function (assert) {
            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = 44;
                },
            };

            serverData.models.partner.records[0].turtles = [];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            assert.strictEqual(
                target.querySelector('.o_field_widget[name="int_field"] input').value,
                "10"
            );

            await addRow(target);
            assert.strictEqual(
                target.querySelector('.o_field_widget[name="int_field"] input').value,
                "10"
            );

            // fill turtle_foo field
            await editInput(target, '.o_field_widget[name="turtle_foo"] input', "some text");

            assert.strictEqual(
                target.querySelector('.o_field_widget[name="int_field"] input').value,
                "44"
            );
        }
    );

    QUnit.test(
        "one2many list editable: 'required' modifiers is properly working, part 2",
        async function (assert) {
            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = 44;
                },
            };

            serverData.models.partner.records[0].turtles = [];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_int"/>
                                <field name="turtle_foo" required='turtle_int == 0'/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            assert.strictEqual(
                target.querySelector('.o_field_widget[name="int_field"] input').value,
                "10"
            );

            await addRow(target);
            assert.strictEqual(
                target.querySelector('.o_field_widget[name="int_field"] input').value,
                "10"
            );

            // fill turtle_int field
            await editInput(target, '.o_field_widget[name="turtle_int"] input', "1");
            assert.strictEqual(
                target.querySelector('.o_field_widget[name="int_field"] input').value,
                "44"
            );
        }
    );

    QUnit.test(
        "one2many list editable: add new line before onchange returns",
        async function (assert) {
            // If the user adds a new row (with a required field with onchange), selects
            // a value for that field, then adds another row before the onchange returns,
            // the editable list must wait for the onchange to return before trying to
            // unselect the first row, otherwise it will be detected as invalid.
            serverData.models.turtle.onchanges = {
                turtle_trululu: function () {},
            };

            let def;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_trululu" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                async mockRPC(route, args) {
                    if (args.method === "onchange") {
                        await Promise.resolve(def);
                    }
                },
            });

            // add a first line but hold the onchange back
            await addRow(target);
            def = makeDeferred();
            assert.containsOnce(target, ".o_data_row");
            await clickOpenM2ODropdown(target, "turtle_trululu");
            await clickM2OHighlightedItem(target, "turtle_trululu");

            // try to add a second line and check that it is correctly waiting
            // for the onchange to return
            await addRow(target);
            assert.containsNone(target, ".modal");
            assert.containsNone(target, ".o_field_invalid");
            assert.containsOnce(target, ".o_data_row");
            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

            // resolve the onchange promise
            def.resolve();
            await nextTick();
            assert.containsN(target, ".o_data_row", 2);
            assert.doesNotHaveClass(target.querySelector(".o_data_row"), "o_selected_row");
        }
    );

    QUnit.test(
        "editable list: multiple clicks on Add an item do not create invalid rows",
        async function (assert) {
            serverData.models.turtle.onchanges = {
                turtle_trululu: function () {},
            };

            let def;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_trululu" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                async mockRPC(route, args) {
                    if (args.method === "onchange") {
                        await Promise.resolve(def);
                    }
                },
            });
            def = makeDeferred();
            // click twice to add a new line
            await addRow(target);
            await addRow(target);
            assert.containsNone(target, ".o_data_row");

            // resolve the onchange promise
            def.resolve();
            await nextTick();
            assert.containsOnce(target, ".o_data_row");
            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        }
    );

    QUnit.test("editable list: value reset by an onchange", async function (assert) {
        // this test reproduces a subtle behavior that may occur in a form view:
        // the user adds a record in a one2many field, and directly clicks on a
        // datetime field of the form view which has an onchange, which totally
        // erases the value from the one2many (command 2 + command 0). The handler
        // that switches the edited row to readonly is then called after the
        // new value of the one2many field is applied (the one returned by the
        // onchange), so the row that must go to readonly doesn't exist anymore.
        serverData.models.partner.onchanges = {
            datetime: function (obj) {
                if (obj.turtles.length) {
                    obj.turtles = [
                        [2, obj.turtles[0][1]],
                        [0, 0, { display_name: "new" }],
                    ];
                }
            },
        };

        let def;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="datetime"/>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    await Promise.resolve(def);
                }
            },
        });

        // trigger the two onchanges
        await addRow(target);
        await editInput(target, ".o_data_row .o_field_widget input", "a name");
        def = makeDeferred();
        await editInput(target, ".o_field_datetime .o_input", "04/27/2022 14:08:52");

        // resolve the onchange promise
        def.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").innerText, "new");
    });

    QUnit.test("editable list: onchange that returns a warning", async function (assert) {
        serverData.models.turtle.onchanges = {
            display_name: function () {},
        };

        const warning = {
            title: "Warning",
            message: "You must first select a partner",
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step(args.method);
                    return {
                        value: {},
                        warning,
                    };
                }
            },
        });
        patchWithCleanup(form.env.services.notification, {
            add: (message, params) => {
                assert.step(params.type);
                assert.strictEqual(message, warning.message);
                assert.strictEqual(params.title, warning.title);
            },
        });

        // add a line (this should trigger an onchange and a warning)
        await addRow(target);

        // check if 'Add an item' still works (this should trigger an onchange
        // and a warning again)
        await addRow(target);

        assert.verifySteps(["onchange", "warning", "onchange", "warning"]);
    });

    QUnit.test("editable list: contexts are correctly sent", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].timmy = [12];

        patchWithCleanup(session, { user_context: { someKey: "some value" } });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="timmy" context="{'key': foo, 'key2': 'hello'}">
                        <tree editable="top">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_read" && args.model === "partner") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            active_field: 2,
                            bin_size: true,
                            someKey: "some value",
                            uid: 7,
                        },
                        "read partner context"
                    );
                    assert.deepEqual(args.kwargs.specification.timmy.context, { key2: "hello" });
                }
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            active_field: 2,
                            someKey: "some value",
                            uid: 7,
                        },
                        "read partner context"
                    );
                    assert.deepEqual(args.kwargs.specification.timmy.context, { key2: "hello" });
                }
            },
            resId: 1,
            context: { active_field: 2 },
        });
        await click(target.querySelector(".o_data_cell"));
        await editInput(target, ".o_field_widget[name=display_name] input", "abc");
        await clickSave(target);
    });

    QUnit.test("contexts of nested x2manys are correctly sent (add line)", async function (assert) {
        assert.expect(4);

        serverData.models.partner.fields.timmy.default = [[4, 12]];

        patchWithCleanup(session, { user_context: { someKey: "some value" } });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="timmy" context="{'key': parent.foo, 'key2': 'hello'}" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            active_field: 2,
                            someKey: "some value",
                            uid: 7,
                        },
                        "onchange context"
                    );
                    assert.deepEqual(args.args[3].timmy.context, {
                        key: "yop",
                        key2: "hello",
                    });
                }
                if (args.method === "web_read" && args.model === "partner") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            active_field: 2,
                            bin_size: true,
                            someKey: "some value",
                            uid: 7,
                        },
                        "read timmy context"
                    );
                    assert.deepEqual(args.kwargs.specification.p.fields.timmy.context, {
                        key2: "hello",
                    });
                }
            },
            resId: 1,
            context: { active_field: 2 },
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
    });

    QUnit.test("nested x2manys with context referencing parent record", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records[0].p = [2];

        let onchangeNb = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="p" context="{'parent_foo': parent.foo}">
                                <tree>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    onchangeNb++;
                    if (onchangeNb === 1) {
                        assert.deepEqual(args.args[3].p.context, { parent_foo: "yop" });
                    } else {
                        assert.strictEqual(args.kwargs.context.parent_foo, "yop");
                    }
                }
            },
            resId: 1,
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.containsOnce(target, ".o_dialog");
        await click(target.querySelector(".o_dialog .o_field_x2many_list_row_add a"));
    });

    QUnit.test("resetting invisible one2manys", async function (assert) {
        serverData.models.partner.records[0].turtles = [];
        serverData.models.partner.onchanges.foo = function (obj) {
            obj.turtles = [[5], [4, 1]];
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles" invisible="1"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        await editInput(target, '[name="foo"] input', "abcd");
        assert.verifySteps(["get_views", "web_read", "onchange"]);
    });

    QUnit.test(
        "one2many: onchange that returns unknown field in list, but not in form",
        async function (assert) {
            assert.expect(6);
            serverData.models.partner.onchanges = {
                name: function (obj) {
                    obj.p = [[0, 0, { display_name: "new", timmy: [[4, 12]] }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="name"/>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="display_name"/>
                                <field name="timmy" widget="many2many_tags"/>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.deepEqual(args.args[3], {
                            display_name: {},
                            name: {},
                            p: {
                                fields: {
                                    display_name: {},
                                    timmy: {
                                        fields: {
                                            display_name: {},
                                        },
                                    },
                                },
                                limit: 40,
                                order: "",
                            },
                        });
                    }
                },
            });

            assert.containsOnce(target, ".o_data_row");
            assert.containsNone(target, '.o_field_widget[name="timmy"]');

            await click(target.querySelector(".o_data_row td"));
            assert.containsOnce(target, '.modal .o_field_many2many_tags[name="timmy"]');
            assert.containsOnce(target, '.modal .o_field_many2many_tags[name="timmy"] .badge');
            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        '.modal .o_field_many2many_tags[name="timmy"] .o_tag_badge_text'
                    ),
                ].map((el) => el.textContent),
                ["gold"]
            );
        }
    );

    QUnit.test("multi level of nested x2manys, onchange", async function (assert) {
        assert.expect(7);
        serverData.models.partner.records[0].p = [1];
        serverData.models.partner.onchanges = {
            name: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="name"/>
                        <field name="p" readonly="name == 'readonly'">
                            <tree><field name="display_name"/></tree>
                            <form>
                                <field name="display_name"/>
                                <field name="p">
                                    <tree><field name="display_name"/></tree>
                                    <form><field name="display_name"/></form>
                                </field>
                            </form>
                        </field>
                    </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1].p[0][2], {
                        p: [[1, 1, { display_name: "new name" }]],
                    });
                }
            },
            resId: 1,
        });

        assert.containsOnce(target, ".o_data_row");

        // open the dialog
        await click(target.querySelector(".o_data_row td"));
        assert.containsOnce(target, ".modal .o_form_editable");
        assert.containsOnce(target, ".modal .o_data_row");

        // open the o2m again, in the dialog
        await click(target.querySelector(".modal .o_data_row td"));

        assert.containsN(target, ".modal .o_form_editable", 2);

        // edit the name and click save modal that is on top
        const dialogs = target.querySelectorAll(".modal");
        await editInput(dialogs[1], ".o_field_widget[name=display_name] input", "new name");
        await click(dialogs[1], ".modal-footer .btn-primary");

        assert.containsOnce(target, ".modal .o_form_editable");

        // click save on the other modal
        await click(target, ".modal .modal-footer .btn-primary");

        assert.containsNone(target, ".modal");

        // save the main record
        await clickSave(target);
    });

    QUnit.test("onchange and required fields with override in arch", async function (assert) {
        serverData.models.partner.onchanges = {
            turtles: function () {},
        };
        serverData.models.turtle.fields.turtle_foo.required = true;
        serverData.models.partner.records[0].turtles = [];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_int"/>
                            <field name="turtle_foo" required="0"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        // triggers an onchange on partner, because the new record is valid
        await addRow(target);

        assert.verifySteps(["get_views", "web_read", "onchange", "onchange"]);
    });

    QUnit.test("onchange on a one2many containing a one2many", async function (assert) {
        // the purpose of this test is to ensure that the onchange specs are
        // correctly and recursively computed
        assert.expect(1);

        serverData.models.partner.onchanges = {
            p: function () {},
        };
        var checkOnchange = false;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                            <field name="p">
                                <tree editable="bottom">
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange" && checkOnchange) {
                    assert.deepEqual(args.args[3], {
                        display_name: {},
                        p: {
                            fields: {
                                display_name: {},
                                p: {
                                    fields: {
                                        display_name: {},
                                    },
                                    limit: 40,
                                    order: "",
                                },
                            },
                            limit: 40,
                            order: "",
                        },
                    });
                }
            },
        });

        await addRow(target);
        await addRow(target, ".modal");
        await editInput(target, ".modal .o_data_cell input", "new record");
        checkOnchange = true;
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
    });

    QUnit.test("editing tabbed one2many (editable=bottom)", async function (assert) {
        assert.expect(10);

        serverData.models.partner.records[0].turtles = [];
        for (let i = 0; i < 42; i++) {
            const id = 100 + i;
            serverData.models.turtle.records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
            serverData.models.partner.records[0].turtles.push(id);
        }

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_save") {
                    assert.strictEqual(
                        args.args[1].turtles[0][0],
                        0,
                        "should send a create command"
                    );
                    assert.deepEqual(args.args[1].turtles[0][2], { turtle_foo: "rainbow dash" });
                }
            },
        });
        await addRow(target);
        assert.containsN(target, "tr.o_data_row", 41);
        assert.hasClass([...target.querySelectorAll("tr.o_data_row")].pop(), "o_selected_row");

        await editInput(target, '.o_data_row [name="turtle_foo"] input', "rainbow dash");
        await clickSave(target);
        assert.containsN(target, "tr.o_data_row", 40);

        assert.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
    });

    QUnit.test("editing tabbed one2many (editable=bottom), again...", async function (assert) {
        serverData.models.partner.records[0].turtles = [];
        for (let i = 0; i < 9; i++) {
            const id = 100 + i;
            serverData.models.turtle.records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
            serverData.models.partner.records[0].turtles.push(id);
        }

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        // add a new record page 1 (this increases the limit to 4)
        await addRow(target);
        await editInput(target, '.o_data_row [name="turtle_foo"] input', "rainbow dash");
        await click(target, ".o_x2m_control_panel .o_pager_next"); // page 2: 4 records
        await click(target, ".o_x2m_control_panel .o_pager_next"); // page 3: 2 records
        assert.containsN(target, "tr.o_data_row", 2);
    });

    QUnit.test("editing tabbed one2many (editable=top)", async function (assert) {
        assert.expect(13);

        serverData.models.partner.records[0].turtles = [];
        serverData.models.turtle.fields.turtle_foo.default = "default foo";
        for (let i = 0; i < 42; i++) {
            const id = 100 + i;
            serverData.models.turtle.records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
            serverData.models.partner.records[0].turtles.push(id);
        }

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_save") {
                    assert.strictEqual(args.args[1].turtles[0][0], 0);
                    assert.deepEqual(args.args[1].turtles[0][2], { turtle_foo: "rainbow dash" });
                }
            },
        });
        await click(target, ".o_field_widget[name=turtles] .o_pager_next");
        assert.containsN(target, "tr.o_data_row", 2);

        await addRow(target);
        assert.containsN(target, "tr.o_data_row", 3);
        assert.hasClass(target.querySelector("tr.o_data_row"), "o_selected_row");
        assert.strictEqual(target.querySelector("tr.o_data_row input").value, "default foo");

        await editInput(target, '.o_data_row [name="turtle_foo"] input', "rainbow dash");
        await clickSave(target);
        assert.containsN(target, "tr.o_data_row", 40);

        assert.verifySteps(["get_views", "web_read", "web_read", "onchange", "web_save"]);
    });

    QUnit.test(
        "one2many field: change value before pending onchange returns",
        async function (assert) {
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            serverData.models.partner.onchanges = {
                int_field: function () {},
            };
            let def;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="int_field"/>
                                <field name="trululu"/>
                            </tree>
                        </field>
                    </form>`,
                async mockRPC(route, args) {
                    if (args.method === "onchange") {
                        // delay the onchange RPC
                        await Promise.resolve(def);
                    }
                },
            });

            await addRow(target);
            def = makeDeferred();
            await editInput(target, ".o_field_widget[name=int_field] input", "44");

            // set trululu before onchange
            await editInput(target, ".o_field_widget[name=trululu] input", "first");

            // complete the onchange
            def.resolve();
            assert.strictEqual(target.querySelector(".o_field_many2one input").value, "first");
            await nextTick();
            // check name_search result
            assert.strictEqual(target.querySelector(".o_field_many2one input").value, "first");
            assert.containsOnce(
                target,
                ".o_field_many2one .dropdown-menu li:not(.o_m2o_dropdown_option)"
            );
        }
    );

    QUnit.test("focus is correctly reset after an onchange in an x2many", async function (assert) {
        serverData.models.partner.onchanges = {
            int_field: function () {},
        };

        let def;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="int_field"/>
                                <button string="hello"/>
                                <field name="qux"/>
                                <field name="trululu"/>
                            </tree>
                        </field>
                    </form>`,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    // delay the onchange RPC
                    await Promise.resolve(def);
                }
            },
        });

        await addRow(target);

        def = makeDeferred();

        editInput(target, "[name=int_field] input", "44");

        click(target, ".o_field_widget[name=qux]");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_field_widget[name=qux] input")
        );

        def.resolve();
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_field_widget[name=qux] input")
        );

        await clickOpenM2ODropdown(target, "trululu");
        await clickM2OHighlightedItem(target, "trululu");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=trululu] input").value,
            "first record"
        );
    });

    QUnit.test("checkbox in an x2many that triggers an onchange", async function (assert) {
        serverData.models.partner.onchanges = {
            bar: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="bar"/>
                        </tree>
                    </field>
                </form>`,
        });

        await addRow(target);
        assert.ok(target.querySelector(".o_field_widget[name=bar] input").checked);

        await click(target, ".o_field_widget[name=bar] input");
        assert.notOk(target.querySelector(".o_field_widget[name=bar] input").checked);
    });

    QUnit.test(
        "one2many with default value: edit line to make it invalid",
        async function (assert) {
            serverData.models.partner.fields.p.default = [
                [0, false, { foo: "coucou", int_field: 5, p: [] }],
            ];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="foo"/>
                                <field name="int_field"/>
                            </tree>
                        </field>
                    </form>`,
            });

            // edit the line and enter an invalid value for int_field
            await click(target.querySelectorAll(".o_data_row .o_data_cell")[1]);
            await editInput(target, ".o_field_widget[name=int_field] input", "e");
            await click(target, ".o_form_view");

            assert.containsOnce(
                target,
                ".o_data_row.o_selected_row",
                "line should not have been removed and should still be in edition"
            );
            assert.containsNone(target, ".modal", "a confirmation dialog should not be opened");
            assert.hasClass(
                target.querySelector(".o_field_widget[name=int_field]"),
                "o_field_invalid"
            );
        }
    );

    QUnit.test("one2many with invalid value and click on another row", async function (assert) {
        serverData.models.partner.records[0].p = [2, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        let rows = target.querySelectorAll(".o_data_row");
        await click(rows[0].querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_data_row.o_selected_row");
        rows = target.querySelectorAll(".o_data_row");
        assert.hasClass(rows[0], "o_selected_row");
        assert.doesNotHaveClass(rows[1], "o_selected_row");

        await editInput(target, ".o_data_row [name='int_field'] input", "abc");
        rows = target.querySelectorAll(".o_data_row");
        await click(rows[1].querySelector(".o_data_cell"));
        // Stays on the invalid row
        assert.containsOnce(target, ".o_data_row.o_selected_row");
        rows = target.querySelectorAll(".o_data_row");
        assert.hasClass(rows[0], "o_selected_row");
        assert.containsOnce(rows[0], "[name='int_field'] .o_field_invalid");
        assert.doesNotHaveClass(rows[1], "o_selected_row");
    });

    QUnit.test(
        "default value for nested one2manys (coming from onchange)",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.onchanges.p = function (obj) {
                obj.p = [
                    [5],
                    [0, 0, { turtles: [[5], [4, 1, false]] }], // link record 1 by default
                ];
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="p">
                                <tree>
                                    <field name="turtles"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.strictEqual(
                            args.args[1].p[0][0],
                            0,
                            "should send a command 0 (CREATE) for p"
                        );
                        assert.deepEqual(
                            args.args[1].p[0][2],
                            { turtles: [[4, 1]] },
                            "should send the correct values"
                        );
                    }
                },
            });

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
                ["1 record"]
            );

            await clickSave(target);
        }
    );

    QUnit.test("display correct value after validation error", async function (assert) {
        assert.expect(4);

        serviceRegistry.add("error", errorService);
        function validationHandler(env, error, originalError) {
            if (originalError.data.name === "odoo.exceptions.ValidationError") {
                return true;
            }
        }
        const errorHandlerRegistry = registry.category("error_handlers");
        errorHandlerRegistry.add("validationHandler", validationHandler, { sequence: 1 });

        serverData.models.partner.onchanges.turtles = function () {};

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    if (args.args[1].turtles[0][2].turtle_foo === "pinky") {
                        throw makeServerError({ type: "ValidationError" });
                    }
                }
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.args[1].turtles[0],
                        [1, 2, { turtle_foo: "foo" }],
                        'should send the "good" value'
                    );
                }
            },
            resId: 1,
        });
        assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").textContent, "blip");

        // click and edit value to 'foo', which will trigger onchange
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".o_field_widget[name=turtle_foo] input", "foo");
        await click(target, ".o_form_view");
        assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").textContent, "foo");

        // click and edit value to 'pinky', which trigger a failed onchange
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".o_field_widget[name=turtle_foo] input", "pinky");
        await click(target, ".o_form_view");
        assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").textContent, "foo");

        // we make sure here that when we save, the values are the current
        // values displayed in the field.
        await clickSave(target);
    });

    QUnit.test("propagate context to sub views without default_* keys", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.strictEqual(
                        args.kwargs.context.flutter,
                        "shy",
                        "view context key should be used for every rpcs"
                    );
                    if (args.model === "partner") {
                        assert.strictEqual(
                            args.kwargs.context.default_flutter,
                            "why",
                            "should have default_* values in context for form view RPCs"
                        );
                    } else if (args.model === "turtle") {
                        assert.notOk(
                            args.kwargs.context.default_flutter,
                            "should not have default_* values in context for subview RPCs"
                        );
                    }
                }
            },
            context: {
                flutter: "shy",
                default_flutter: "why",
            },
        });
        await addRow(target);
        await editInput(target, '[name="turtle_foo"] input', "pinky pie");
        await clickSave(target);
    });

    QUnit.test(
        "nested one2manys with no widget in list and as invisible list in form",
        async function (assert) {
            serverData.models.partner.records[0].p = [1];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="turtles"/>
                            </tree>
                            <form>
                                <field name="turtles" invisible="1"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });
            assert.containsOnce(target, ".o_data_row");
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row .o_data_cell")].map(
                    (el) => el.textContent
                ),
                ["1 record"]
            );

            await click(target.querySelector(".o_data_row td"));
            assert.containsOnce(target, ".modal .o_form_view");
            assert.containsNone(target, ".modal .o_form_view .o_field_one2many");

            // Test possible caching issues
            await clickDiscard(target.querySelector(".modal"));
            await click(target.querySelector(".o_data_row td"));
            assert.containsOnce(target, ".modal .o_form_view");
            assert.containsNone(target, ".modal .o_form_view .o_field_one2many");
        }
    );

    QUnit.test("onchange on nested one2manys", async function (assert) {
        assert.expect(3);

        serverData.models.partner.onchanges.display_name = function (obj) {
            if (obj.display_name) {
                obj.p = [
                    [
                        0,
                        0,
                        {
                            display_name: "test",
                            turtles: [[0, 0, { display_name: "test nested" }]],
                        },
                    ],
                ];
            }
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="display_name"/>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree>
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, [
                        [
                            0,
                            commands[0][1],
                            {
                                display_name: "test",
                                turtles: [
                                    [
                                        0,
                                        commands[0][2].turtles[0][1],
                                        { display_name: "test nested" },
                                    ],
                                ],
                            },
                        ],
                    ]);
                }
            },
        });

        await editInput(target, ".o_field_widget[name=display_name] input", "trigger onchange");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["test"]
        );

        // open the new subrecord to check the value of the nested o2m, and to
        // ensure that it will be saved
        await click(target.querySelector(".o_data_cell"));
        assert.deepEqual(
            [...target.querySelectorAll(".modal .o_data_cell")].map((el) => el.textContent),
            ["test nested"]
        );

        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        await clickSave(target);
    });

    QUnit.test("one2many with multiple pages and sequence field", async function (assert) {
        serverData.models.partner.records[0].turtles = [3, 2, 1];
        serverData.models.partner.onchanges.turtles = function () {};

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree limit="2">
                            <field name="turtle_int" widget="handle"/>
                            <field name="turtle_foo"/>
                            <field name="partner_ids" invisible="1"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    return {
                        value: {
                            turtles: [
                                [2, 2],
                                [2, 3],
                                [
                                    4,
                                    1,
                                    { id: 1, turtle_int: 0, turtle_foo: "yop", partner_ids: [] },
                                ],
                                [1, 1, { turtle_foo: "from onchange" }],
                            ],
                        },
                    };
                }
            },
        });
        await click(target.querySelector(".o_list_record_remove button"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            ["from onchange"]
        );
    });

    QUnit.test("one2many with multiple pages and sequence field, part2", async function (assert) {
        serverData.models.partner.records[0].turtles = [3, 2, 1];
        serverData.models.partner.onchanges.turtles = function () {};

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                                <field name="partner_ids" invisible="1"/>
                            </tree>
                            <form/>
                        </field>
                    </form>`,
            resId: 1,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    return {
                        value: {
                            turtles: [
                                [2, 2],
                                [
                                    4,
                                    1,
                                    { id: 1, turtle_int: 0, turtle_foo: "yop", partner_ids: [] },
                                ],
                                [1, 1, { turtle_foo: "from onchange id2" }],
                                [1, 3, { turtle_foo: "from onchange id3" }],
                            ],
                        },
                    };
                }
            },
        });
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_row .o_data_cell.o_list_char")),
            ["yop", "blip"]
        );
        await click(target.querySelector(".o_list_record_remove button"));
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_row .o_data_cell.o_list_char")),
            ["from onchange id3", "from onchange id2"]
        );
    });

    QUnit.test(
        "one2many with sequence field, override default_get, bottom when inline",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [3, 2, 1];
            serverData.models.turtle.fields.turtle_int.default = 10;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            // starting condition
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
                ["blip", "yop", "kawa"]
            );

            // click add a new line
            // save the record
            // check line is at the correct place
            const inputText = "ninja";
            await addRow(target);
            await editInput(target, '[name="turtle_foo"] input', inputText);
            await clickSave(target);

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
                ["blip", "yop", "kawa", inputText]
            );
        }
    );

    QUnit.test(
        "one2many with sequence field, override default_get, top when inline",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [3, 2, 1];
            serverData.models.turtle.fields.turtle_int.default = 10;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            // starting condition
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
                ["blip", "yop", "kawa"]
            );

            // click add a new line
            // save the record
            // check line is at the correct place
            const inputText = "ninja";
            await addRow(target);
            await editInput(target, '[name="turtle_foo"] input', inputText);
            await clickSave(target);

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
                [inputText, "blip", "yop", "kawa"]
            );
        }
    );

    QUnit.test(
        "one2many with sequence field, override default_get, bottom when popup",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [3, 2, 1];
            serverData.models.turtle.fields.turtle_int.default = 10;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree>
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                            <form>
                                <field name="turtle_int" invisible="1"/>
                                <field name="turtle_foo"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });

            // starting condition
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
                ["blip", "yop", "kawa"]
            );

            // click add a new line
            // save the record
            // check line is at the correct place
            const inputText = "ninja";
            await addRow(target);
            await editInput(target, '.modal [name="turtle_foo"] input', inputText);
            await clickSave(target.querySelector(".modal"));

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
                ["blip", "yop", "kawa", inputText]
            );

            await clickSave(target);

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
                ["blip", "yop", "kawa", inputText]
            );
        }
    );

    QUnit.test(
        "one2many with sequence field, override default_get, not last page",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [3, 2, 1];

            serverData.models.turtle.fields.turtle_int.default = 5;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_int" widget="handle"/>
                            </tree>
                            <form>
                                <field name="turtle_int"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });
            // click add a new line
            // check turtle_int for new is the current max of the page
            await addRow(target);
            assert.strictEqual(target.querySelector('.modal [name="turtle_int"] input').value, "9");
        }
    );

    QUnit.test(
        "one2many with sequence field, override default_get, last page",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [3, 2, 1];
            serverData.models.turtle.fields.turtle_int.default = 10;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="4">
                                <field name="turtle_int" widget="handle"/>
                            </tree>
                            <form>
                                <field name="turtle_int"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });
            // click add a new line
            // check turtle_int for new is the current max of the page +1
            await addRow(target);
            assert.strictEqual(
                target.querySelector('.modal [name="turtle_int"] input').value,
                "22"
            );
        }
    );

    QUnit.test("one2many with sequence field and text field", async function (assert) {
        serverData.models.turtle.fields.turtle_int.default = 10;
        serverData.models.turtle.fields.product_id.default = 37;
        serverData.models.turtle.fields.not_required_product_id = {
            string: "Product",
            type: "many2one",
            relation: "product",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                                <field name="not_required_product_id"/>
                                <field name="turtle_description" widget="text"/>
                            </tree>
                        </field>
                    </form>`,
        });

        // starting condition
        assert.containsNone(target, ".o_data_cell");

        const inputText1 = "relax";
        const inputText2 = "max";
        await addRow(target);
        await editInput(target, 'div[name="turtle_foo"] input', inputText1);
        await addRow(target);
        await editInput(target, 'div[name="turtle_foo"] input', inputText2);
        await addRow(target);

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            inputText1,
            inputText2,
            "",
        ]);

        assert.containsN(target, ".ui-sortable-handle", 3);

        await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr:nth-child(1)");

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")),
            [inputText2, inputText1] // empty line has been discarded on the drag and drop
        );
    });

    QUnit.test("one2many with several pages, onchange and default order", async function (assert) {
        // This test reproduces a specific scenario where a one2many is displayed
        // over several pages, and has a default order such that a record that
        // would normally be on page 1 is actually on another page. Moreover,
        // there is an onchange on that one2many which converts all commands 4
        // (LINK_TO) into commands 1 (UPDATE), which is standard in the ORM.
        // This test ensures that the record displayed on page 2 is never fully
        // read.

        serverData.models.partner.records[0].turtles = [1, 2, 3];
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                var res = obj.turtles.map((command) => {
                    if (command[0] === 1) {
                        // already an UPDATE command: do nothing
                        return command;
                    }
                    // convert LINK_TO commands to UPDATE commands
                    var id = command[1];
                    var record = serverData.models.turtle.records.find(
                        (record) => record.id === id
                    );
                    return [1, id, pick(record, "turtle_int", "turtle_foo", "partner_ids")];
                });
                obj.turtles = res;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top" limit="2" default_order="turtle_foo">
                            <field name="turtle_int"/>
                            <field name="turtle_foo" class="foo"/>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                var ids = args.method === "web_read" ? " [" + args.args[0] + "]" : "";
                assert.step(args.method + ids);
            },
            resId: 1,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell.foo")].map((el) => el.textContent),
            ["blip", "kawa"]
        );

        // edit turtle_int field of first row
        await click(target.querySelector(".o_data_cell"));
        await editInput(
            target.querySelector(".o_data_row"),
            ".o_field_widget[name=turtle_int] input",
            3
        );
        await click(target, ".o_form_view");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell.foo")].map((el) => el.textContent),
            ["blip", "kawa"]
        );

        assert.verifySteps([
            "get_views",
            "web_read [1]", // main record
            "onchange",
            // this test's purpose is to assert that this rpc isn't
            // done, but yet it is. Actually, it wasn't before because mockOnChange
            // returned [1] as command list, instead of [[6, false, [1]]], so basically
            // this value was ignored. Now that mockOnChange properly works, the value
            // is taken into account but the basicmodel doesn't care it concerns a
            // record of the second page, and does the read. I don't think we
            // introduced a regression here, this test was simply wrong...
        ]);
    });

    QUnit.test(
        "one2many with several pages, onchange return command update on unknown record (readonly field)",
        async function (assert) {
            serverData.models.turtle.fields.turtle_int.readonly = true;
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [[1, 3, { turtle_int: 57, turtle_foo: "yop" }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree editable="top" limit="1">
                            <field name="turtle_int"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
                mockRPC(route, { args, method }) {
                    if (method === "web_save") {
                        assert.deepEqual(args[0], [1]);
                        // for unknownCommand, we should not send readonly fields
                        assert.deepEqual(args[1], {
                            foo: "blip",
                            turtles: [[1, 3, { turtle_foo: "yop" }]],
                        });
                    }
                },
                resId: 1,
            });

            await editInput(target, ".o_field_widget[name=foo] input", "blip");
            await clickSave(target);
        }
    );

    QUnit.test(
        "new record, with one2many with more default values than limit",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                context: { default_turtles: [1, 2, 3] },
            });
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map(
                    (el) => el.querySelector(".o_data_cell").textContent
                ),
                ["yop", "blip"]
            );

            await clickSave(target);
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map(
                    (el) => el.querySelector(".o_data_cell").textContent
                ),
                ["yop", "blip"]
            );
        }
    );

    QUnit.test(
        "add a new line after limit is reached should behave nicely",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            serverData.models.partner.onchanges = {
                turtles: function () {},
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="3" editable="bottom">
                                <field name="turtle_foo" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            await addRow(target);
            assert.containsN(target, ".o_data_row", 4);

            await editInput(target, 'div[name="turtle_foo"] .o_input', "a");
            assert.containsN(
                target,
                ".o_data_row",
                4,
                "should still have 4 data rows (the limit is increased to 4)"
            );
        }
    );

    QUnit.test(
        "onchange in a one2many with non inline view on an existing record",
        async function (assert) {
            serverData.models.partner.fields.sequence = { string: "Sequence", type: "integer" };
            serverData.models.partner.records[0].sequence = 1;
            serverData.models.partner.records[1].sequence = 2;
            serverData.models.partner.onchanges = { sequence: function () {} };

            serverData.models.partner_type.fields.partner_ids = {
                string: "Partner",
                type: "one2many",
                relation: "partner",
            };
            serverData.models.partner_type.records[0].partner_ids = [1, 2];
            serverData.views = {
                "partner,false,list": `
                    <tree>
                        <field name="sequence" widget="handle"/>
                        <field name="display_name"/>
                    </tree>`,
            };

            await makeView({
                type: "form",
                resModel: "partner_type",
                serverData,
                arch: `
                    <form>
                        <field name="partner_ids" widget="one2many"/>
                    </form>`,
                resId: 12,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });
            // swap 2 lines in the one2many
            await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr", "top");

            assert.verifySteps(["get_views", "get_views", "web_read", "onchange", "onchange"]);
        }
    );

    QUnit.test(
        "onchange in a one2many with non inline view on a new record",
        async function (assert) {
            serverData.models.turtle.onchanges = {
                display_name: function (obj) {
                    if (obj.display_name) {
                        obj.turtle_int = 44;
                    }
                },
            };
            serverData.views = {
                "turtle,false,list": `
                    <tree editable="bottom">
                        <field name="display_name"/>
                        <field name="turtle_int"/>
                    </tree>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles" widget="one2many"/>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method || route);
                },
            });

            // add a row and trigger the onchange
            await addRow(target);
            await editInput(target, '.o_data_row div[name="display_name"] input', "a name");

            assert.strictEqual(
                target.querySelector(".o_data_row div[name=turtle_int] input").value,
                "44"
            );

            assert.verifySteps([
                "get_views", // load main form
                "get_views", // load sub list
                "onchange", // main record
                "onchange", // sub record
                "onchange", // edition of display_name of sub record
            ]);
        }
    );

    QUnit.test('add a line, edit it and "Save & New"', async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name" widget="char" class="do_not_remove_widget_char"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
        });

        assert.containsNone(target, ".o_data_row");
        // add a new record
        await addRow(target);
        await editInput(target, ".modal .o_field_widget input", "new record");

        await clickSave(target.querySelector(".modal"));

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row .o_data_cell")].map((el) => el.textContent),
            ["new record"]
        );

        // reopen freshly added record and edit it
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".modal .o_field_widget input", "new record edited");

        // save it, and choose to directly create another record
        await click(target.querySelectorAll(".modal .modal-footer .btn-primary")[1]);

        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal .o_field_widget").textContent, "");

        await editInput(target, ".modal .o_field_widget input", "another new record");
        await clickSave(target.querySelector(".modal"));

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row .o_data_cell")].map((el) => el.textContent),
            ["new record edited", "another new record"]
        );
    });

    QUnit.test(
        'add a line with a context depending on the parent record, created a second record with "Save & New"',
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="display_name"/>
                    <field name="p" context="{'default_display_name': display_name}" >
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            });

            assert.containsNone(target, ".o_data_row");
            assert.deepEqual(
                [...target.querySelectorAll("[name='p'] .o_data_row")].map((el) => el.textContent),
                []
            );
            await editInput(target, "[name='display_name'] input", "Jack");

            await addRow(target);
            assert.strictEqual(
                target.querySelector(".modal [name='display_name'] input").value,
                "Jack"
            );

            await click(target, ".modal .o_form_button_save_new");
            assert.strictEqual(
                target.querySelector(".modal [name='display_name'] input").value,
                "Jack"
            );
            assert.deepEqual(
                [...target.querySelectorAll("[name='p'] .o_data_row")].map((el) => el.textContent),
                ["Jack"]
            );

            await clickSave(target.querySelector(".modal"));
            assert.deepEqual(
                [...target.querySelectorAll("[name='p'] .o_data_row")].map((el) => el.textContent),
                ["Jack", "Jack"]
            );
        }
    );

    QUnit.test("o2m add a line custom control create editable", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <control>
                                <create string="Add food" context="" />
                                <create string="Add pizza" context="{'default_display_name': 'pizza'}"/>
                            </control>
                            <control>
                                <create string="Add pasta" context="{'default_display_name': 'pasta'}"/>
                            </control>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
        });

        // new controls correctly added
        const rowAdd = target.querySelectorAll(".o_field_x2many_list_row_add");
        assert.strictEqual(rowAdd.length, 1);
        assert.strictEqual(rowAdd[0].closest("tr").querySelectorAll("td").length, 1);
        assert.deepEqual(
            [...rowAdd[0].querySelectorAll("a")].map((el) => el.textContent),
            ["Add food", "Add pizza", "Add pasta"]
        );

        // click add food
        // check it's empty
        await addRow(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            [""]
        );

        // click add pizza
        // press enter to save the record
        // check it's pizza
        await click(target, ".o_field_x2many_list_row_add a:nth-child(2)");
        const input = target.querySelector(
            '.o_field_widget[name="p"] .o_selected_row .o_field_widget[name="display_name"] input'
        );

        assert.strictEqual(document.activeElement, input);

        triggerHotkey("Enter");
        await nextTick();
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["", "pizza", ""]
        );

        // click add pasta
        await click(target, ".o_field_x2many_list_row_add a:nth-child(3)");
        await clickSave(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["", "pizza", "", "pasta"]
        );
    });

    QUnit.test("o2m add a line custom control create non-editable", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                        <control>
                            <create string="Add food" context="" />
                            <create string="Add pizza" context="{'default_display_name': 'pizza'}" />
                        </control>
                        <control>
                            <create string="Add pasta" context="{'default_display_name': 'pasta'}" />
                        </control>
                        <field name="display_name"/>
                    </tree>
                    <form>
                        <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
        });

        // new controls correctly added
        const rowAdd = target.querySelectorAll(".o_field_x2many_list_row_add");
        assert.strictEqual(rowAdd.length, 1);
        assert.containsN(rowAdd[0].closest("tr"), "td", 1);
        assert.deepEqual(
            [...rowAdd[0].querySelectorAll("a")].map((el) => el.textContent),
            ["Add food", "Add pizza", "Add pasta"]
        );

        // click add food
        // check it's empty
        await addRow(target);
        await clickSave(target.querySelector(".modal"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            [""]
        );

        // click add pizza
        // save the modal
        // check it's pizza
        await click(target, ".o_field_x2many_list_row_add a:nth-child(2)");
        await clickSave(target.querySelector(".modal"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["", "pizza"]
        );

        // click add pasta
        // save the whole record
        // check it's pizzapasta
        await click(target, ".o_field_x2many_list_row_add a:nth-child(3)");
        await clickSave(target.querySelector(".modal"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["", "pizza", "pasta"]
        );
    });

    QUnit.test("o2m add an action button control", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 2,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <control>
                                <create string="Create" context="{}" />
                                <button string="Action Button" name="do_something" class="btn-link" type="object" context="{'parent_id': parent.id}"/>
                            </control>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "do_something") {
                    assert.step("do_something");
                    assert.strictEqual(args.kwargs.context.parent_id, 2);
                    return true;
                }
            },
        });

        assert.deepEqual(
            [...target.querySelector(".o_field_x2many_list_row_add").children].map(
                (el) => el.textContent
            ),
            ["Create", "Action Button"]
        );

        await click(target, ".o_field_x2many_list_row_add button");
        assert.verifySteps(["do_something"]);
    });

    QUnit.test("o2m button with parent in context", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="display_name"/>
                            <button string="Action Button" name="test_button" type="object" context="{'parent_name': parent.display_name}"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "test_button") {
                    assert.step("test_button");
                    assert.strictEqual(args.kwargs.context.parent_name, "first record");
                    return true;
                }
            },
        });
        await click(target, 'button[name="test_button"]');
        assert.verifySteps(["test_button"]);
    });

    QUnit.test("o2m add a line custom control create align with handle", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="int_field" widget="handle"/>
                        </tree>
                    </field>
                </form>`,
        });

        // controls correctly added, at one column offset when handle is present
        const tr = target.querySelector(".o_field_x2many_list_row_add").closest("tr");
        assert.containsN(tr, "td", 2);
        const tds = tr.querySelectorAll("td");
        assert.strictEqual(tds[0].textContent, "");
        assert.strictEqual(tds[1].textContent, "Add a line");
    });

    QUnit.test("one2many form view with action button", async function (assert) {
        // once the action button is clicked, the record is reloaded (via the
        // onClose handler, executed because the python method does not return
        // any action, or an ir.action.act_window_close) ; this test ensures that
        // it reloads the fields of the opened view (i.e. the form in this case).
        // See https://github.com/odoo/odoo/issues/24189

        const actionService = {
            start() {
                return {
                    doActionButton(params) {
                        serverData.models.partner.records[1].display_name = "new name";
                        serverData.models.partner.records[1].timmy = [12];
                        params.onClose();
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        serverData.models.partner.records[0].p = [2];
        serverData.views = {
            "partner_type,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <button type="action" string="Set Timmy"/>
                            <field name="timmy"/>
                        </form>
                    </field>
                </form>`,
        });
        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector(".o_data_cell").textContent, "second record");

        // open one2many record in form view
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".modal .o_form_view");
        assert.containsNone(target, ".modal .o_form_view .o_data_row");

        // click on the action button
        await click(target.querySelector(".modal .o_form_editable button"));
        assert.containsOnce(target, ".modal .o_data_row");
        assert.strictEqual(target.querySelector(".modal .o_data_cell").textContent, "gold");

        // save the dialog
        await click(target.querySelector(".modal .modal-footer .btn-primary"));

        assert.strictEqual(target.querySelector(".o_data_cell").innerText, "new name");
    });

    QUnit.test("onchange affecting inline unopened list view", async function (assert) {
        let numUserOnchange = 0;
        serverData.models.user.onchanges = {
            partner_ids: function (obj) {
                numUserOnchange++;
            },
        };

        await makeView({
            type: "form",
            resModel: "user",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="partner_ids">
                                <form>
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="display_name"/>
                                        </tree>
                                    </field>
                                </form>
                                <tree>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </group>
                    </sheet>
                </form>`,
            resId: 17,
        });

        // add a turtle on second partner
        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        await addRow(target.querySelector(".modal"));
        await editInput(target, ".modal .o_field_widget[name=display_name] input", "michelangelo");
        await click(target.querySelector(".modal .btn-primary"));
        // open first partner so changes from previous action are applied
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await click(target.querySelector(".modal .btn-primary"));
        await clickSave(target);

        assert.strictEqual(
            numUserOnchange,
            1,
            "there should 1 and only 1 onchange from closing the partner modal"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".modal .o_data_row", "only 1 turtle for first partner");
        assert.strictEqual(
            target.querySelector(".modal .o_data_cell").innerText,
            "donatello",
            "first partner turtle is donatello"
        );
        await click(target.querySelector(".modal .modal-footer .btn-primary")); // Close

        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        assert.containsOnce(target, ".modal .o_data_row", "only 1 turtle for second partner");
        assert.strictEqual(
            target.querySelector(".modal .o_data_cell").innerText,
            "michelangelo",
            "second partner turtle is michelangelo"
        );
        await clickDiscard(target.querySelector(".modal"));
    });

    QUnit.test("click on URL should not open the record", async function (assert) {
        serverData.models.partner.records[0].turtles = [1];

        // avoid to open a new tab or the mail app
        const onClick = (ev) => {
            assert.step("link clicked");
            ev.preventDefault();
        };
        browser.addEventListener("click", onClick, { capture: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="display_name" widget="email"/>
                            <field name="turtle_foo" widget="url"/>
                        </tree>
                        <form/>
                    </field>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_email_cell a"));
        assert.containsNone(target, ".modal");
        assert.verifySteps(["link clicked"]);

        await click(target.querySelector(".o_url_cell a"));
        assert.containsNone(target, ".modal");
        assert.verifySteps(["link clicked"]);
    });

    QUnit.test("create and edit on m2o in o2m, and press ESCAPE", async function (assert) {
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_trululu"/>
                        </tree>
                    </field>
                </form>`,
        });

        await addRow(target);

        assert.containsOnce(target, ".o_selected_row");

        await clickOpenM2ODropdown(target, "turtle_trululu");
        await editInput(target, "[name=turtle_trululu] input", "ABC");
        await clickOpenedDropdownItem(target, "turtle_trululu", "Create and edit...");

        assert.containsOnce(target, ".modal .o_form_view");

        triggerHotkey("Escape");
        await nextTick();

        assert.containsNone(target, ".modal .o_form_view");
        assert.containsOnce(target, ".o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_selected_row [name=turtle_trululu] input")
        );
    });

    QUnit.test(
        "one2many add a line should not crash if orderedResIDs is not set",
        async function (assert) {
            // There is no assertion, the code will just crash before the bugfix.
            assert.expect(0);

            const actionService = {
                start() {
                    return {
                        doActionButton(args) {
                            return Promise.reject();
                        },
                    };
                },
            };
            registry.category("services").add("action", actionService, { force: true });

            serverData.models.partner.records[0].turtles = [];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <button name="post" type="object" string="Validate" class="oe_highlight"/>
                        </header>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
            });

            await click(target, 'button[name="post"]');
            await addRow(target);
        }
    );

    QUnit.test(
        "one2many shortcut tab should not crash when there is no input widget",
        async function (assert) {
            // create a one2many view which has no input (only 1 textarea in this case)
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo" widget="text"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            // add a row, fill it, then trigger the tab shortcut
            await addRow(target);
            await editInput(target, "[name=turtle_foo] textarea", "ninja");

            assert.strictEqual(
                target.querySelector("[name=turtle_foo] textarea"),
                document.activeElement
            );

            triggerHotkey("Tab");
            await nextTick();

            assert.deepEqual(
                [...target.querySelectorAll(".o_field_text")].map((el) => el.textContent),
                ["blip", "ninja", ""]
            );
            assert.containsOnce(target, ".o_field_text textarea");
        }
    );

    QUnit.test("o2m add a line custom control create editable with 'tab'", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="bottom">
                                <control>
                                    <create string="Add soft shell turtle" context="{'default_turtle_foo': 'soft'}"/>
                                </control>
                                <field name="turtle_foo"/>
                                </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                const { method, kwargs } = args;
                if (method === "onchange") {
                    assert.step("onchange");
                    assert.strictEqual(kwargs.context.default_turtle_foo, "soft");
                }
            },
        });
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, "[name='turtle_foo'] input", "Test");
        assert.containsOnce(target, ".o_data_row");

        triggerHotkey("Tab");
        await nextTick();
        assert.containsN(target, ".o_data_row", 2);
        assert.verifySteps(["onchange"]);
    });

    QUnit.test("one2many with onchange, required field, shortcut enter", async function (assert) {
        serverData.models.turtle.onchanges = {
            turtle_foo: function () {},
        };

        let def;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo" required="1"/>
                            </tree>
                        </field>
                    </form>`,
            async mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "onchange") {
                    await Promise.resolve(def);
                }
            },
        });

        assert.verifySteps(["get_views", "onchange"]);

        const value = "hello";

        // add a new line
        await addRow(target);

        assert.verifySteps(["onchange"]);

        // we want to add a delay to simulate an onchange
        def = makeDeferred();

        // write something in the field
        const input = target.querySelector("[name=turtle_foo] input");
        input.value = value;
        await triggerEvent(input, null, "input");
        triggerHotkey("Enter");
        await triggerEvent(input, null, "change");

        // check that nothing changed before the onchange finished
        assert.strictEqual(target.querySelector("[name=turtle_foo] input").value, value);
        assert.containsOnce(target, ".o_data_row");

        assert.verifySteps(["onchange"]);

        // unlock onchange
        def.resolve();
        await nextTick();

        // check the current line is added with the correct content and a new line is editable
        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(
            target.querySelector(".o_data_row:nth-child(1) [name=turtle_foo]").innerText,
            value
        );
        assert.strictEqual(
            target.querySelector(".o_data_row:nth-child(2) [name=turtle_foo] input").value,
            ""
        );

        assert.verifySteps(["onchange"]);
    });

    QUnit.test("edit a field with a slow onchange in one2many", async function (assert) {
        serverData.models.turtle.onchanges = {
            turtle_foo: function () {},
        };

        let def;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "onchange") {
                    await Promise.resolve(def);
                }
            },
        });

        assert.verifySteps(["get_views", "onchange"]);

        const value = "hello";

        // add a new line
        await addRow(target);

        assert.verifySteps(["onchange"]);

        // we want to add a delay to simulate an onchange
        def = makeDeferred();

        // write something in the field
        await editInput(target, "[name=turtle_foo] input", value);
        assert.strictEqual(target.querySelector("[name=turtle_foo] input").value, value);

        await click(target, ".o_form_view");

        // check that nothing changed before the onchange finished
        assert.strictEqual(target.querySelector("[name=turtle_foo] input").value, value);

        assert.verifySteps(["onchange"]);

        // unlock onchange
        def.resolve();
        await nextTick();

        // check the current line is added with the correct content
        assert.strictEqual(target.querySelector(".o_data_row [name=turtle_foo]").innerText, value);
    });

    QUnit.test(
        "no deadlock when leaving a one2many line with uncommitted changes",
        async function (assert) {
            // Before unselecting a o2m line, field widgets are asked to commit their changes (new values
            // that they wouldn't have sent to the model yet). This test is added alongside a bug fix
            // ensuring that we don't end up in a deadlock when a widget actually has some changes to
            // commit at that moment.
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            await addRow(target);

            await editInput(target, ".o_field_widget[name=turtles] input", "some foo value");

            // click to add a second row to unselect the current one, then save
            await addRow(target);
            await clickSave(target);

            assert.containsOnce(target, ".o_form_editable");
            assert.strictEqual(
                target.querySelector(".o_data_row").textContent.trim(),
                "some foo value"
            );
            assert.verifySteps([
                "get_views", // main form view
                "onchange", // main record
                "onchange", // line 1
                "onchange", // line 2
                "web_save",
            ]);
        }
    );

    QUnit.test("one2many with extra field from server not in form", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="datetime"/>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    args.args[1].p[0][2].datetime = "2018-04-05 12:00:00";
                }
            },
        });

        // Add a record in the list
        await addRow(target);
        await editInput(target, ".modal div[name=display_name] input", "michelangelo");

        // Save the record in the modal (though it is still virtual)
        await click(target.querySelector(".modal .btn-primary"));

        assert.containsOnce(target, ".o_data_row");
        let cells = target.querySelectorAll(".o_data_cell");
        assert.strictEqual(cells[0].textContent, "");
        assert.strictEqual(cells[1].textContent, "michelangelo");

        // Save the whole thing
        await clickSave(target);

        // Redo asserts in RO mode after saving
        assert.containsOnce(target, ".o_data_row");
        cells = target.querySelectorAll(".o_data_cell");
        assert.strictEqual(cells[0].textContent, "04/05/2018 13:00:00");
        assert.strictEqual(cells[1].textContent, "michelangelo");
    });

    QUnit.test("one2many invisible depends on parent field", async function (assert) {
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="product_id"/>
                        </group>
                        <notebook>
                            <page string="Partner page">
                                <field name="bar"/>
                                <field name="p">
                                    <tree>
                                        <field name="foo" column_invisible="parent.product_id"/>
                                        <field name="bar" column_invisible="not parent.bar"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsN(
            target,
            "th:not(.o_list_actions_header)",
            2,
            "should be 2 columns in the one2many"
        );

        await selectDropdownItem(target, "product_id", "xphone");

        assert.containsOnce(
            target,
            "th:not(.o_list_actions_header)",
            "should be 1 column when the product_id is set"
        );
        await editInput(target, ".o_field_many2one[name=product_id] input", "");
        assert.containsN(
            target,
            "th:not(.o_list_actions_header)",
            2,
            "should be 2 columns in the one2many when product_id is not set"
        );
        await click(target.querySelector(".o_field_boolean[name=bar] input"));
        assert.containsOnce(
            target,
            "th:not(.o_list_actions_header)",
            "should be 1 column after the value change"
        );
    });

    QUnit.test("column_invisible attrs on a button in a one2many list", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="product_id"/>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <button name="abc" string="Do it" class="some_button" column_invisible="not parent.product_id"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=product_id] input").value,
            ""
        );
        assert.containsN(target, ".o_list_table th", 2); // foo + trash bin
        assert.containsNone(target, ".some_button");
        await selectDropdownItem(target, "product_id", "xphone");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=product_id] input").value,
            "xphone"
        );
        assert.containsN(target, ".o_list_table th", 3); // foo + button + trash bin
        assert.containsOnce(target, ".some_button");
    });

    QUnit.test("column_invisible attrs on adjacent buttons", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="product_id"/>
                    <field name="trululu"/>
                    <field name="p">
                        <tree>
                            <button name="abc1" string="Do it 1" class="some_button1"/>
                            <button name="abc2" string="Do it 2" class="some_button2" column_invisible="parent.product_id"/>
                            <field name="foo"/>
                            <button name="abc3" string="Do it 3" class="some_button3" column_invisible="parent.product_id"/>
                            <button name="abc4" string="Do it 4" class="some_button4" column_invisible="parent.trululu"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=product_id] input").value,
            ""
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=trululu] input").value,
            "aaa"
        );
        assert.containsN(target, ".o_list_table th", 4); // button group 1 + foo + button group 2 + trash bin
        assert.containsOnce(target, ".some_button1");
        assert.containsOnce(target, ".some_button2");
        assert.containsOnce(target, ".some_button3");
        assert.containsNone(target, ".some_button4");

        await selectDropdownItem(target, "product_id", "xphone");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=product_id] input").value,
            "xphone"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=trululu] input").value,
            "aaa"
        );
        assert.containsN(target, ".o_list_table th", 3); // button group 1 + foo + trash bin
        assert.containsOnce(target, ".some_button1");
        assert.containsNone(target, ".some_button2");
        assert.containsNone(target, ".some_button3");
        assert.containsNone(target, ".some_button4");
    });

    QUnit.test("field context is correctly passed to x2m subviews", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles" context="{'some_key': 1}">
                        <kanban>
                            <templates>
                                <t t-name="kanban-box">
                                    <div>
                                        <t t-if="context.some_key">
                                            <field name="turtle_foo"/>
                                        </t>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.strictEqual(
            [...target.querySelectorAll(".o_kanban_record span")].filter(
                (el) => el.textContent === "blip"
            ).length,
            1,
            "condition in the kanban template should have been correctly evaluated"
        );
    });

    QUnit.test("one2many kanban with widget handle", async function (assert) {
        serverData.models.partner.records[0].turtles = [1, 2, 3];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <kanban>
                            <field name="turtle_int" widget="handle"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div>
                                        <field name="turtle_foo"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], {
                        turtles: [
                            [1, 2, { turtle_int: 0 }],
                            [1, 3, { turtle_int: 1 }],
                            [1, 1, { turtle_int: 2 }],
                        ],
                    });
                }
            },
            resId: 1,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
                (el) => el.innerText
            ),
            ["yop", "blip", "kawa"]
        );

        // // should not work (form in mode "readonly")
        // await dragAndDrop(".o_kanban_record:nth-child(1)", ".o_kanban_record:nth-child(3)");
        // assert.deepEqual(
        //     [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
        //         (el) => el.innerText
        //     ),
        //     ["yop", "blip", "kawa"]
        // );

        await dragAndDrop(".o_kanban_record:nth-child(1)", ".o_kanban_record:nth-child(3)");

        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
                (el) => el.innerText
            ),
            ["blip", "kawa", "yop"]
        );

        await clickSave(target);
    });

    QUnit.test("one2many editable list: edit and click on add a line", async function (assert) {
        serverData.models.turtle.onchanges = {
            turtle_int: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom"><field name="turtle_int"/></tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange");
                }
            },
        });

        assert.containsOnce(target, ".o_data_row");

        // edit first row
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        target.querySelector(".o_selected_row .o_field_widget[name=turtle_int] input").value = "44";
        await triggerEvent(
            target,
            ".o_selected_row .o_field_widget[name=turtle_int] input",
            "input"
        );
        assert.verifySteps([]);

        // simulate a long click on 'Add a line' (mousedown [delay] mouseup and click events)
        triggerEvent(target, ".o_field_x2many_list_row_add a", "mousedown");
        // mousedown is supposed to trigger the change event on the edited input, but it doesn't
        // in the test environment, for an unknown reason, so we trigger it manually to reproduce
        // what really happens
        await triggerEvent(
            target,
            ".o_selected_row .o_field_widget[name=turtle_int] input",
            "change"
        );

        // release the click
        await triggerEvents(target, ".o_field_x2many_list_row_add a", ["mouseup", "click"]);
        assert.verifySteps(["onchange", "onchange"]);

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_data_cell").innerText, "44");
        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");
    });

    QUnit.test(
        "many2manys inside a one2many are fetched in batch after onchange",
        async function (assert) {
            assert.expect(5);

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [4, 1],
                        [4, 2],
                        [
                            1,
                            1,
                            {
                                turtle_foo: "leonardo",
                                partner_ids: [[4, 2]],
                            },
                        ],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method || route);
                },
            });

            assert.containsN(target, ".o_data_row", 2);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll('.o_field_widget[name="partner_ids"]')),
                ["second record", "second recordaaa"]
            );

            assert.verifySteps(["get_views", "onchange"]);
        }
    );

    QUnit.test("two one2many fields with same relation and onchanges", async function (assert) {
        // this test simulates the presence of two one2many fields with onchanges, such that
        // changes to the first o2m are repercuted on the second one
        serverData.models.partner.fields.turtles2 = {
            string: "Turtles 2",
            type: "one2many",
            relation: "turtle",
            relation_field: "turtle_trululu",
        };
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                // replicate changes on turtles2
                if (obj.turtles.length) {
                    const command = obj.turtles2 && obj.turtles2[0];
                    if (command) {
                        // second onchange (with ABC): there's already a create command
                        obj.turtles2 = [[1, command[1], obj.turtles[0][2]]];
                    } else {
                        // first onchange (when adding the row): replicate the create command
                        obj.turtles2 = [[0, false, obj.turtles[0][2]]];
                    }
                }
            },
            turtles2: () => {}, // simulate an onchange on turtles2 as well
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom"><field name="name" required="1"/></tree>
                    </field>
                    <field name="turtles2">
                        <tree editable="bottom"><field name="name" required="1"/></tree>
                    </field>
                </form>`,
        });

        // trigger first onchange by adding a line in turtles field (should add a line in turtles2)
        await addRow(target, '.o_field_widget[name="turtles"]');
        await editInput(
            target,
            '.o_field_widget[name="turtles"] .o_field_widget[name="name"] input',
            "ABC"
        );

        assert.containsOnce(
            target,
            '.o_field_widget[name="turtles"] .o_data_row',
            "line of first o2m should have been created"
        );
        assert.containsOnce(
            target,
            '.o_field_widget[name="turtles2"] .o_data_row',
            "line of second o2m should have been created"
        );

        // add a line in turtles2
        await addRow(target, '.o_field_widget[name="turtles2"]');
        await editInput(
            target,
            '.o_field_widget[name="turtles2"] .o_field_widget[name="name"] input',
            "DEF"
        );

        assert.containsOnce(
            target,
            '.o_field_widget[name="turtles"] .o_data_row',
            "we should still have 1 line in turtles"
        );
        assert.containsN(
            target,
            '.o_field_widget[name="turtles2"] .o_data_row',
            2,
            "we should have 2 lines in turtles2"
        );
        assert.hasClass(
            target.querySelectorAll('.o_field_widget[name="turtles2"] .o_data_row')[1],
            "o_selected_row",
            "second row should be in edition"
        );

        await clickSave(target);

        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll('.o_field_widget[name="turtles2"] .o_data_row')
            ),
            ["ABC", "DEF"]
        );
    });

    QUnit.test("column widths are kept when adding first record in o2m", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="date"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
        });

        var width = target.querySelector('th[data-name="date"]').offsetWidth;

        await addRow(target);

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector('th[data-name="date"]').offsetWidth, width);
    });

    QUnit.test("column widths are kept when editing a record in o2m", async function (assert) {
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="date"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mode: "edit",
        });

        const width = target.querySelector('th[data-name="date"]').style.width;

        await click(target.querySelector(".o_data_row .o_data_cell"));

        assert.strictEqual(target.querySelector('th[data-name="date"]').style.width, width);

        const longVal =
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, " +
            "justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum " +
            "purus bibendum est.";
        await editInput(target, ".o_field_widget[name=foo] input", longVal);

        assert.strictEqual(target.querySelector('th[data-name="date"]').style.width, width);
    });

    QUnit.test("column widths are kept when remove last record in o2m", async function (assert) {
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="date"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mode: "edit",
        });

        const width = target.querySelector('th[data-name="date"]').offsetWidth;

        await click(target, ".o_data_row .o_list_record_remove");

        assert.strictEqual(target.querySelector('th[data-name="date"]').offsetWidth, width);
    });

    QUnit.test("column widths are correct after toggling optional fields", async function (assert) {
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="date" required="1"/>
                            <field name="foo"/>
                            <field name="int_field" optional="1"/>
                        </tree>
                    </field>
                </form>`,
        });

        // date fields have an hardcoded width, which apply when there is no
        // record, and should be kept afterwards
        const width = target.querySelector('th[data-name="date"]').offsetWidth;

        // create a record to store the current widths, but discard it directly to keep
        // the list empty (otherwise, the browser automatically computes the optimal widths)
        await addRow(target);

        assert.strictEqual(target.querySelector('th[data-name="date"]').offsetWidth, width);

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown .dropdown-item input");

        assert.strictEqual(target.querySelector('th[data-name="date"]').offsetWidth, width);
    });

    QUnit.test(
        "one2many reset by onchange (of another field) while being edited",
        async function (assert) {
            // In this test, we have a many2one and a one2many. The many2one has an onchange that
            // updates the value of the one2many. We set a new value to the many2one (name_create)
            // such that the onchange is delayed. During the name_create, we click to add a new row
            // to the one2many. After a while, we unlock the name_create, which triggers the onchange
            // and resets the one2many. At the end, we want the row to be in edition.

            // patch setTimeout s.t. the autocomplete drodown opens directly
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            const def = makeDeferred();
            serverData.models.partner.onchanges = {
                trululu: () => {},
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="trululu"/>
                        <field name="p">
                            <tree editable="top"><field name="product_id" required="1"/></tree>
                        </field>
                    </form>`,
                async mockRPC(route, args) {
                    if (args.method === "name_create") {
                        await def;
                    }
                },
            });

            // set a new value for trululu (will delay the onchange)
            await editInput(target, ".o_field_widget[name=trululu] input", "new value");
            await clickOpenedDropdownItem(target, "trululu", `Create "new value"`);

            // add a row in p
            await addRow(target);
            assert.containsNone(target, ".o_data_row");

            // resolve the name_create to trigger the onchange, and the reset of p
            def.resolve();
            await nextTick();
            assert.containsOnce(target, ".o_data_row");
            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        }
    );

    QUnit.test(
        "one2many with many2many_tags in list and list in form with a limit",
        async function (assert) {
            // This test encodes a limitation of the current model architecture:
            // we have an nested x2manys, and the inner one is displayed as tags
            // in the list, and as a list in the form. As both the list and the
            // form will use the same Record datapoint, the config of their static
            // list will be the same. We obviously don't want to see the limit
            // applied on the tags (in the background) when opening the form. So
            // the stategy is to keep the initial config, and to ignore the
            // limit set on the list
            serverData.models.partner.records[0].p = [1];
            serverData.models.partner.records[0].turtles = [1, 2, 3];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree>
                                <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree limit="2">
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_field_widget[name=p] .o_data_row");
            assert.containsN(target, ".o_data_row .o_field_many2many_tags .badge", 3);

            await click(target.querySelector(".o_data_cell"));

            assert.containsOnce(document.body, ".modal .o_form_view");
            assert.containsN(document.body, ".modal .o_field_widget[name=turtles] .o_data_row", 3);
            assert.isNotVisible(target.querySelector(".modal .o_field_x2many_list .o_pager"));
        }
    );

    QUnit.test(
        "one2many with many2many_tags in list and list in form, and onchange",
        async function (assert) {
            serverData.models.partner.onchanges = {
                bar: function (obj) {
                    obj.p = [[0, 0, { turtles: [[0, 0, { display_name: "new turtle" }]] }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree>
                                <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="bottom">
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
            });

            assert.containsOnce(target, ".o_field_widget[name=p] .o_data_row");
            assert.containsOnce(target, ".o_data_row .o_field_many2many_tags .badge");

            await click(target.querySelector(".o_data_row .o_data_cell"));

            assert.containsOnce(target, ".modal .o_form_view");
            assert.containsOnce(target, ".modal .o_field_widget[name=turtles] .o_data_row");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".modal .o_data_cell")), [
                "new turtle",
            ]);

            await addRow(target.querySelector(".modal"));
            assert.containsN(target, ".modal .o_field_widget[name=turtles] .o_data_row", 2);
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".modal .o_data_cell")), [
                "new turtle",
                "",
            ]);
            assert.hasClass(
                target.querySelectorAll(".modal .o_field_widget[name=turtles] .o_data_row")[1],
                "o_selected_row"
            );
        }
    );

    QUnit.test(
        "one2many with many2many_tags in list and list in form, and onchange (2)",
        async function (assert) {
            serverData.models.partner.onchanges = {
                bar: function (obj) {
                    obj.p = [
                        [
                            0,
                            0,
                            {
                                turtles: [
                                    [
                                        0,
                                        0,
                                        {
                                            display_name: "new turtle",
                                        },
                                    ],
                                ],
                            },
                        ],
                    ];
                },
            };
            serverData.models.turtle.onchanges = {
                turtle_foo: function (obj) {
                    obj.display_name = obj.turtle_foo;
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree>
                                <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="bottom">
                                        <field name="turtle_foo" required="1"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
            });

            assert.containsOnce(target, ".o_field_widget[name=p] .o_data_row");

            await click(target.querySelector(".o_data_row .o_data_cell"));

            assert.containsOnce(target, ".modal .o_form_view");

            await addRow(target.querySelector(".modal"));
            assert.containsN(target, ".modal .o_field_widget[name=turtles] .o_data_row", 2);

            await editInput(target, ".modal .o_selected_row input", "another one");
            await click(target.querySelector(".modal .modal-footer .btn-primary"));

            assert.containsNone(target, ".modal");

            assert.containsOnce(target, ".o_field_widget[name=p] .o_data_row");
            assert.containsN(target, ".o_data_row .o_field_many2many_tags .badge", 2);
            assert.deepEqual(
                getNodesTextContent(
                    target.querySelectorAll(".o_data_row .o_field_many2many_tags .o_tag_badge_text")
                ),
                ["new turtle", "another one"]
            );
        }
    );

    QUnit.test(
        "reorder one2many with many2many_tags in list and list in form",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].p = [2, 4];
            serverData.models.partner.records[0].p = [1, 4];

            serverData.views = {
                "partner,false,form": `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="int_field" widget="handle"/>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                            <field name="p" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
            });

            await click(target.querySelector(".o_data_cell"));
            assert.containsOnce(target, ".modal");
            assert.deepEqual(
                [...target.querySelectorAll(".modal [name='display_name']")].map(
                    (el) => el.textContent
                ),

                ["aaa", "first record"]
            );

            await dragAndDrop(".modal tr:nth-child(2) .o_handle_cell", "tbody tr", "top");
            assert.deepEqual(
                [...target.querySelectorAll(".modal [name='display_name']")].map(
                    (el) => el.textContent
                ),

                ["first record", "aaa"]
            );
        }
    );

    QUnit.test("nested one2many, onchange, no command value", async function (assert) {
        // This test ensures that we always send all values to onchange rpcs for nested
        // one2manys, even if some field hasn't changed. In this particular test case,
        // a first onchange returns a value for the inner one2many, and a second onchange
        // removes it, thus restoring the field to its initial empty value. From this point,
        // the nested one2many value must still be sent to onchange rpcs (on the main record),
        // as it might be used to compute other fields (so the fact that the nested o2m is empty
        // must be explicit).
        assert.expect(1);

        serverData.models.turtle.fields.o2m = {
            string: "o2m",
            type: "one2many",
            relation: "partner",
            relation_field: "trululu",
        };
        serverData.models.turtle.fields.turtle_bar.default = true;
        serverData.models.partner.onchanges.turtles = function (obj) {};
        serverData.models.turtle.onchanges.turtle_bar = function (obj) {};

        let step = 1;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="o2m"/>
                            <field name="turtle_bar"/>
                        </tree>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                if (step === 3 && args.method === "onchange" && args.model === "partner") {
                    assert.deepEqual(args.args[1].turtles[0][2], {
                        o2m: [],
                        turtle_bar: false,
                    });
                }
                if (args.model === "turtle") {
                    if (step === 2) {
                        return {
                            value: {
                                o2m: [[0, false, { display_name: "default" }]],
                                turtle_bar: true,
                            },
                        };
                    }
                    if (step === 3) {
                        const virtualId = args.args[1].o2m[0][1];
                        return {
                            value: { o2m: [[2, virtualId]] },
                        };
                    }
                }
            },
        });

        step = 2;
        await addRow(target);
        step = 3;
        await click(target.querySelector(".o_data_row .o_field_boolean input"));
    });

    QUnit.test("edition in list containing widget with decoration", async function (assert) {
        // We use here a badge widget and check its decoration is properly managed
        // in this scenario (we need a widget with specific decoration handling)
        serverData.models.partner.records[0].p = [1, 2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="int_field"/>
                            <field name="color" widget="badge" decoration-warning="int_field == 9"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.hasClass(
            target.querySelectorAll(".o_data_row")[1].querySelector(".o_field_badge .badge"),
            "text-bg-warning"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".o_selected_row .o_field_integer input", "44");

        assert.hasClass(
            target.querySelectorAll(".o_data_row")[1].querySelector(".o_field_badge .badge"),
            "text-bg-warning"
        );
    });

    QUnit.test(
        "reordering embedded one2many with handle widget starting with same sequence",
        async function (assert) {
            serverData.models.turtle = {
                fields: { turtle_int: { string: "int", type: "integer", sortable: true } },
                records: [
                    { id: 1, turtle_int: 1 },
                    { id: 2, turtle_int: 1 },
                    { id: 3, turtle_int: 1 },
                    { id: 4, turtle_int: 2 },
                    { id: 5, turtle_int: 3 },
                    { id: 6, turtle_int: 4 },
                ],
            };
            serverData.models.partner.records[0].turtles = [1, 2, 3, 4, 5, 6];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree default_order="turtle_int">
                                <field name="turtle_int" widget="handle"/>
                                <field name="id"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell:not(.o_handle_cell)")].map(
                    (el) => el.innerText
                ),
                ["1", "2", "3", "4", "5", "6"]
            );

            // Drag and drop the fourth line in first position
            await dragAndDrop("tbody tr:nth-child(4) .o_handle_cell", "tbody tr", "top");

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell:not(.o_handle_cell)")].map(
                    (el) => el.innerText
                ),
                ["4", "1", "2", "3", "5", "6"]
            );

            await clickSave(target);

            assert.deepEqual(
                Object.values(serverData.models.turtle.records).map((r) => {
                    return { id: r.id, turtle_int: r.turtle_int };
                }),
                [
                    { id: 1, turtle_int: 2 },
                    { id: 2, turtle_int: 3 },
                    { id: 3, turtle_int: 4 },
                    { id: 4, turtle_int: 1 },
                    { id: 5, turtle_int: 5 },
                    { id: 6, turtle_int: 6 },
                ]
            );
        }
    );

    QUnit.test("combine contexts on o2m field and create tags", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles" context="{'default_turtle_foo': 'hard', 'default_turtle_bar': True}">
                            <tree editable="bottom">
                                <control>
                                    <create name="add_soft_shell_turtle" string="Add soft shell turtle" context="{'default_turtle_foo': 'soft', 'default_turtle_int': 2}"/>
                                </control>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    if (args.model === "turtle") {
                        assert.deepEqual(
                            args.kwargs.context,
                            {
                                default_turtle_foo: "soft",
                                default_turtle_bar: true,
                                default_turtle_int: 2,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            "combined context should have the default_turtle_foo value from the <create>"
                        );
                    }
                }
            },
        });

        await addRow(target);
    });

    QUnit.test("do not call read if display_name already known", async function (assert) {
        serverData.models.partner.fields.product_id.default = 37;
        serverData.models.partner.onchanges = {
            trululu: function (obj) {
                obj.trululu = 1;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu"/>
                    <field name="product_id"/>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method + " on " + args.model);
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=trululu] input").value,
            "first record"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=product_id] input").value,
            "xphone"
        );
        assert.verifySteps(["get_views on partner", "onchange on partner"]);
    });

    QUnit.test("x2many default_order multiple fields", async function (assert) {
        serverData.models.partner.records = [
            { int_field: 10, id: 1, display_name: "record1" },
            { int_field: 12, id: 2, display_name: "record2" },
            { int_field: 11, id: 3, display_name: "record3" },
            { int_field: 12, id: 4, display_name: "record4" },
            { int_field: 10, id: 5, display_name: "record5" },
            { int_field: 10, id: 6, display_name: "record6" },
            { int_field: 11, id: 7, display_name: "record7" },
        ];

        serverData.models.partner.records[0].p = [1, 7, 4, 5, 2, 6, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" >
                        <tree default_order="int_field,id">
                            <field name="id"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        const recordIdList = [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
            (record) => record.querySelector(".o_data_cell").textContent
        );
        const expectedOrderId = ["1", "5", "6", "3", "7", "2", "4"];
        assert.deepEqual(recordIdList, expectedOrderId);
    });

    QUnit.test("x2many default_order multiple fields with limit", async function (assert) {
        serverData.models.partner.records = [
            { int_field: 10, id: 1, display_name: "record1" },
            { int_field: 12, id: 2, display_name: "record2" },
            { int_field: 11, id: 3, display_name: "record3" },
            { int_field: 12, id: 4, display_name: "record4" },
            { int_field: 10, id: 5, display_name: "record5" },
            { int_field: 10, id: 6, display_name: "record6" },
            { int_field: 11, id: 7, display_name: "record7" },
        ];

        serverData.models.partner.records[0].p = [1, 7, 4, 5, 2, 6, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" >
                        <tree default_order="int_field,id" limit="4">
                            <field name="id"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        const recordIdList = [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
            (record) => record.querySelector(".o_data_cell").textContent
        );
        const expectedOrderId = ["1", "5", "6", "3"];
        assert.deepEqual(recordIdList, expectedOrderId);
    });

    QUnit.test("one2many from a model that has been sorted", async function (assert) {
        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        };
        serverData.views = {
            "partner,false,list": `<tree><field name="int_field"/></tree>`,
            "partner,false,search": `<search/>`,
            "partner,false,form": `
                <form>
                    <field name="turtles">
                        <tree><field name="turtle_foo"/></tree>
                    </field>
                </form>`,
        };
        serverData.models.partner.records[0].turtles = [3, 2];

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_list_view");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "10",
            "9",
            "0",
        ]);

        await click(target.querySelector("th.o_column_sortable"));
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "0",
            "9",
            "10",
        ]);

        await click(target, ".o_data_row:nth-child(3) .o_data_cell");
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell")),
            ["kawa", "blip"],
            "The o2m should not have been sorted."
        );
    });

    QUnit.test(
        "prevent the dialog in readonly x2many tree view with option no_open True",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="turtles">
                                <tree editable="bottom" no_open="True">
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                resId: 1,
            });
            assert.containsOnce(
                target,
                '.o_data_row:contains("blip")',
                "There should be one record in x2many list view"
            );
            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.containsNone(
                target,
                ".modal",
                "There is should be no dialog open on click of readonly list row"
            );
        }
    );

    QUnit.test("delete a record while adding another one in a multipage", async function (assert) {
        // in a one2many with at least 2 pages, add a new line. Delete the line above it.
        // it should load the next line to display it on the page.
        serverData.models.partner.records[0].turtles = [2, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="turtles">
                                    <tree editable="bottom" limit="1" decoration-muted="turtle_bar == False">
                                        <field name="turtle_foo"/>
                                        <field name="turtle_bar"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
            resId: 1,
        });

        // add a line (virtual record)
        await addRow(target);
        await editInput(target, ".o_field_widget[name=turtle_foo] input", "pi");
        // delete the line above it
        await click(target.querySelector(".o_list_record_remove"));
        // the next line should be displayed below the newly added one
        assert.containsN(target, ".o_data_row", 2, "should have 2 records");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent.trim()),
            ["pi", "", "kawa", ""],
            "should display the correct records on page 1"
        );
    });

    QUnit.test("one2many, onchange, edition and multipage...", async function (assert) {
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [[5]].concat(obj.turtles);
            },
        };

        serverData.models.partner.records[0].turtles = [1, 2, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="2">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method + " " + args.model);
            },
        });
        await addRow(target);
        await editInput(target, ".o_field_widget[name=turtle_foo] input", "nora");
        await addRow(target);

        assert.verifySteps([
            "get_views partner",
            "web_read partner",
            "onchange turtle",
            "onchange partner",
            "onchange partner",
            "onchange turtle",
            "onchange partner",
        ]);
    });

    QUnit.test(
        "x2many multipage, onchange returning update commands with readonly field",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].turtles = [1, 2];
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [
                        [1, 1, { display_name: "rec 1", turtle_foo: "new val 1" }],
                        [1, 2, { display_name: "rec 2", turtle_foo: "new val 2" }],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="turtles">
                            <tree limit="1">
                                <field name="display_name"/>
                                <field name="turtle_foo" readonly="1"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, { args, method }) {
                    if (method === "web_save") {
                        assert.deepEqual(args[1], {
                            foo: "trigger onchange",
                            turtles: [
                                [1, 1, { display_name: "rec 1" }],
                                [1, 2, { display_name: "rec 2" }],
                            ],
                        });
                    }
                },
            });

            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "leonardo",
                "yop",
            ]);

            await editInput(target, ".o_field_widget[name=foo] input", "trigger onchange");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "rec 1",
                "new val 1",
            ]);

            await clickSave(target);
        }
    );

    QUnit.test(
        "x2many multipage, onchange returning update commands with readonly field (2)",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].turtles = [1, 2];
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [
                        [1, 1, { display_name: "rec 1", turtle_foo: "new val 1" }],
                        [1, 2, { display_name: "rec 2", turtle_foo: "new val 2" }],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="turtles">
                            <tree limit="1">
                                <field name="display_name" readonly="not context.get('some_key')"/>
                                <field name="turtle_foo" readonly="context.get('some_key')"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                context: { some_key: true },
                mockRPC(route, { args, method }) {
                    if (method === "web_save") {
                        assert.deepEqual(args[1], {
                            foo: "trigger onchange",
                            turtles: [
                                [1, 1, { display_name: "rec 1" }],
                                [1, 2, { display_name: "rec 2" }],
                            ],
                        });
                    }
                },
            });

            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "leonardo",
                "yop",
            ]);

            await editInput(target, ".o_field_widget[name=foo] input", "trigger onchange");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "rec 1",
                "new val 1",
            ]);

            await clickSave(target);
        }
    );

    QUnit.test(
        "x2many multipage, onchange returning update commands with readonly field (3)",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].turtles = [1, 2];
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [
                        [1, 1, { display_name: "rec 1", turtle_foo: "new val 1" }],
                        [1, 2, { display_name: "rec 2", turtle_foo: "new val 2" }],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="turtles">
                            <tree limit="1">
                                <field name="display_name" readonly="not turtle_bar"/>
                                <field name="turtle_foo" readonly="turtle_bar"/>
                                <field name="turtle_bar" column_invisible="1"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                context: { some_key: true },
                mockRPC(route, { args, method }) {
                    if (method === "web_save") {
                        assert.deepEqual(args[1], {
                            foo: "trigger onchange",
                            turtles: [
                                [1, 1, { display_name: "rec 1" }],
                                // we can't evaluate the readonly expressions for the record of
                                // second page, so we send both fields
                                [1, 2, { display_name: "rec 2", turtle_foo: "new val 2" }],
                            ],
                        });
                    }
                },
            });

            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "leonardo",
                "yop",
            ]);

            await editInput(target, ".o_field_widget[name=foo] input", "trigger onchange");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "rec 1",
                "new val 1",
            ]);

            await clickSave(target);
        }
    );

    QUnit.test("onchange on unloaded record clearing posterious change", async function (assert) {
        let numUserOnchange = 0;
        serverData.models.user.onchanges = {
            partner_ids: function (obj) {
                numUserOnchange++;
            },
        };

        await makeView({
            type: "form",
            resModel: "user",
            serverData,
            arch: `
                <form>
                    <field name="partner_ids">
                        <form>
                            <field name="trululu"/>
                            <field name="turtles">
                                <tree editable="bottom">
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </form>
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 17,
        });

        // open first partner and change turtle name
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await click(target.querySelector(".modal .o_data_row .o_data_cell"));
        await editInput(target, ".modal .o_field_widget[name=display_name] input", "Donatello");
        await click(target.querySelector(".modal .btn-primary"));

        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        await addRow(target.querySelector(".modal"));
        await editInput(target, ".modal .o_field_widget[name=display_name] input", "Michelangelo");
        await click(target.querySelector(".modal .btn-primary"));

        assert.strictEqual(
            numUserOnchange,
            2,
            "there should 2 and only 2 onchange from closing the partner modal"
        );

        // check first record still has change
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".modal .o_data_row", "only 1 turtle for first partner");
        assert.strictEqual(
            target.querySelector(".modal .o_data_cell").innerText,
            "Donatello",
            "first partner turtle is Donatello"
        );
        await clickDiscard(target.querySelector(".modal"));

        // check second record still has changes
        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        assert.containsOnce(target, ".modal .o_data_row", "only 1 turtle for second partner");
        assert.strictEqual(
            target.querySelector(".modal .o_data_cell").innerText,
            "Michelangelo",
            "second partner turtle is Michelangelo"
        );
        await clickDiscard(target.querySelector(".modal"));

        // re-open, edit michelangelo row, click out -> row still there, in readonly
        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        await click(target.querySelector(".modal .o_data_row .o_data_cell"));
        assert.containsOnce(target, ".modal .o_selected_row");
        await click(target.querySelector(".modal"));
        assert.containsOnce(target, ".modal .o_data_row");
        assert.strictEqual(target.querySelector(".modal .o_data_cell").innerText, "Michelangelo");
    });

    QUnit.test("quickly switch between pages in one2many list", async function (assert) {
        serverData.models.partner.records[0].turtles = [1, 2, 3];

        const readDefs = [Promise.resolve(), makeDeferred(), Promise.resolve()];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree limit="1">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                if (args.method === "web_read") {
                    const recordID = args.args[0][0];
                    await Promise.resolve(readDefs[recordID - 1]);
                }
            },
            resId: 1,
        });

        assert.strictEqual(target.querySelector(".o_data_cell").innerText, "leonardo");

        await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));
        assert.ok(target.querySelector(".o_field_widget[name=turtles] .o_pager_next").disabled);

        readDefs[1].resolve();
        await nextTick();
        assert.strictEqual(target.querySelector(".o_data_cell").innerText, "donatello");

        await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));
        assert.strictEqual(target.querySelector(" .o_data_cell").innerText, "raphael");
    });

    QUnit.test(
        "one2many column visiblity depends on onchange of parent field",
        async function (assert) {
            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[0].bar = false;

            let triggerOnchange = false;
            serverData.models.partner.onchanges.p = function (obj) {
                if (triggerOnchange) {
                    obj.bar = true;
                }
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="foo"/>
                                <field name="int_field" column_invisible="not parent.bar"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            // bar is false so there should be 1 column
            assert.containsOnce(target, ".o_list_renderer th:not(.o_list_actions_header)");
            assert.containsOnce(target, ".o_list_renderer .o_data_row");

            // add a new o2m record
            await addRow(target);
            triggerOnchange = true;
            await editInput(target, ".o_field_one2many input", "New line");
            await click(target, ".o_form_view");

            assert.containsN(target, ".o_list_renderer th:not(.o_list_actions_header)", 2);
        }
    );

    QUnit.test("one2many column_invisible on view not inline", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="foo" column_invisible="parent.product_id"/>
                    <field name="bar" column_invisible="not parent.bar"/>
                </tree>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="product_id"/>
                        </group>
                        <notebook>
                            <page string="Partner page">
                                <field name="bar"/>
                                <field name="p" widget="one2many"/>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsN(
            target,
            "th:not(.o_list_actions_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await selectDropdownItem(target, "product_id", "xphone");
        assert.containsOnce(
            target,
            "th:not(.o_list_actions_header)",
            "should be 1 column when the product_id is set"
        );
        await editInput(target, ".o_field_many2one[name=product_id] input", "");
        assert.containsN(
            target,
            "th:not(.o_list_actions_header)",
            2,
            "should be 2 columns in the one2many when product_id is not set"
        );
        await click(target.querySelector(".o_field_boolean[name=bar] input"));
        assert.containsOnce(
            target,
            "th:not(.o_list_actions_header)",
            "should be 1 column after the value change"
        );
    });

    QUnit.test(
        "one2many field in edit mode with optional fields and trash icon",
        async function (assert) {
            serverData.models.partner.records[0].p = [2];
            serverData.views = {
                "partner,false,list": `
                    <tree editable="top">
                        <field name="foo" optional="show"/>
                        <field name="bar" optional="hide"/>
                    </tree>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="p"/></form>`,
                resId: 1,
            });

            assert.containsOnce(
                target.querySelector(".o_field_one2many table"),
                ".o_optional_columns_dropdown .dropdown-toggle",
                "should have the optional columns dropdown toggle inside the table"
            );

            // should have 2 columns 1 for foo and 1 for trash icon, dropdown is displayed
            // on trash icon cell, no separate cell created for trash icon and advanced field dropdown
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                "th",
                2,
                "should be 2 th in the one2many edit mode"
            );
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                ".o_data_row:first > td",
                2,
                "should be 2 cells in the one2many in edit mode"
            );

            await click(target.querySelector(".o_optional_columns_dropdown .dropdown-toggle"));
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                ".o_optional_columns_dropdown .dropdown-item",
                2,
                "dropdown have 2 advanced field foo with checked and bar with unchecked"
            );
            await click(target.querySelectorAll(".o_optional_columns_dropdown .dropdown-item")[1]);
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                "th",
                3,
                "should be 3 th in the one2many after enabling bar column from advanced dropdown"
            );

            await click(target.querySelector(".o_optional_columns_dropdown .dropdown-item"));
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                "th",
                2,
                "should be 2 th in the one2many after disabling foo column from advanced dropdown"
            );
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                ".o_optional_columns_dropdown .dropdown-item",
                2,
                "dropdown is still open"
            );

            await addRow(target);
            assert.containsNone(
                target.querySelector(".o_field_one2many"),
                ".o_optional_columns_dropdown .dropdown-menu",
                "dropdown is closed"
            );
            assert.containsOnce(
                target.querySelector(".o_field_one2many"),
                "tr.o_selected_row",
                "should have selected row i.e. edition mode"
            );

            await click(target.querySelector(".o_optional_columns_dropdown .dropdown-toggle"));
            await click(target.querySelector(".o_optional_columns_dropdown .dropdown-item"));
            assert.containsOnce(
                target.querySelector(".o_field_one2many"),
                "tr.o_selected_row",
                "current edition mode kept when selecting advanced field"
            );
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                "th",
                3,
                "should be 3 th in the one2many after re-enabling foo column from advanced dropdown"
            );

            // optional columns must be preserved after save
            await clickSave(target);
            assert.containsN(
                target.querySelector(".o_field_one2many"),
                "th",
                3,
                "should have 3 th in the one2many after reloading whole form view"
            );
        }
    );

    QUnit.test("x2many list sorted by many2one", async function (assert) {
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
                            <field name="id"/>
                            <field name="trululu"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_row .o_list_number")),
            ["1", "2", "4"],
            "should have correct order initially"
        );

        await click(target.querySelectorAll(".o_list_renderer thead th")[1]);

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_row .o_list_number")),
            ["4", "1", "2"],
            "should have correct order (ASC)"
        );

        await click(target.querySelectorAll(".o_list_renderer thead th")[1]);

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_row .o_list_number")),
            ["2", "1", "4"],
            "should have correct order (DESC)"
        );
    });

    QUnit.test(
        "one2many with extra field from server not in (inline) form",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="datetime"/>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="display_name"/>
                            </form>
                        </field>
                    </form>`,
            });

            // Add a record in the list
            await addRow(target);
            await editInput(target, ".o_field_widget[name=display_name] input", "michelangelo");

            // Save the record in the modal (though it is still virtual)
            await click(target.querySelector(".modal .modal-footer .btn-primary"));
            assert.containsOnce(target, ".o_data_row");
        }
    );

    QUnit.test(
        "one2many with extra X2many field from server not in inline form",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="turtles"/>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="display_name"/>
                            </form>
                        </field>
                    </form>`,
            });

            // Add a first record in the list
            await addRow(target);
            await editInput(target, ".modal .o_field_widget[name=display_name] input", "first");

            // Save & New
            await click(target.querySelectorAll(".modal .btn-primary")[1]);
            await editInput(target, ".modal .o_field_widget[name=display_name] input", "second");

            // Save & Close
            await click(target.querySelector(".modal .btn-primary"));

            assert.containsN(target, ".o_data_row", 2);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")),
                ["first", "second"]
            );
        }
    );

    QUnit.test(
        "when Navigating to a one2many with tabs, the button add a line receives the focus",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                            <notebook>
                                <page string="Partner page">
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="turtle_foo"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            target.querySelector("[name=qux] input").focus();
            assert.strictEqual(target.querySelector("[name=qux] input"), document.activeElement);
            // next tabable element is notebook tab
            getNextTabableElement(target).focus();
            // go inside one2many
            getNextTabableElement(target).focus();
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_x2many_list_row_add a"),
                document.activeElement
            );
        }
    );

    QUnit.test(
        "Navigate to a one2many with tab then tab again focus the next field",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                            <notebook>
                                <page string="Partner page">
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="turtle_foo"/>
                                            <field name="turtle_description"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                            <group>
                                <field name="foo"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            target.querySelector("[name=qux] input").focus();
            assert.strictEqual(document.activeElement, target.querySelector("[name=qux] input"));

            // next tabable element is notebook tab
            getNextTabableElement(target).focus();
            // go inside one2many
            getNextTabableElement(target).focus();
            await nextTick();

            assert.strictEqual(
                target.querySelector(".o_field_x2many_list_row_add a"),
                document.activeElement
            );
            assert.containsNone(target, "[name=turtles] .o_selected_row");

            const nextInput = target.querySelector("[name=foo] input");
            // trigger Tab event and check that the default behavior can happen.
            const event = triggerEvent(
                document.activeElement,
                null,
                "keydown",
                { key: "Tab" },
                { sync: true }
            );
            assert.strictEqual(getNextTabableElement(target), nextInput);
            assert.ok(!event.defaultPrevented);
            nextInput.focus();
            await nextTick();
            assert.strictEqual(document.activeElement, nextInput);
        }
    );

    QUnit.test(
        "when Navigating to a one2many with tabs, not filling any field and hitting tab, no line is added and the next field is focused",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                            <notebook>
                                <page string="Partner page">
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="turtle_foo"/>
                                            <field name="turtle_description"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                            <group>
                                <field name="foo"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            target.querySelector("[name=qux] input").focus();
            assert.strictEqual(document.activeElement, target.querySelector("[name=qux] input"));

            // next tabable element is notebook tab
            getNextTabableElement(target).focus();
            // go inside one2many
            getNextTabableElement(target).focus();
            await nextTick();

            assert.strictEqual(
                target.querySelector(".o_field_x2many_list_row_add a"),
                document.activeElement
            );
            assert.containsNone(target, "[name=turtles] .o_selected_row");

            await addRow(target);
            assert.strictEqual(
                target.querySelector("[name=turtle_foo] input"),
                document.activeElement
            );

            triggerHotkey("Tab"); // go to turtle_description field
            await nextTick();
            assert.strictEqual(
                target.querySelector("[name=turtle_description] textarea"),
                document.activeElement
            );

            const nextInput = target.querySelector("[name=foo] input");
            // trigger Tab event and check that the default behavior can happen.
            const event = triggerEvent(
                document.activeElement,
                null,
                "keydown",
                { key: "Tab" },
                { sync: true }
            );
            assert.strictEqual(getNextTabableElement(target), nextInput);
            assert.ok(!event.defaultPrevented);
            nextInput.focus();
            await nextTick();
            assert.strictEqual(document.activeElement, nextInput);
        }
    );

    QUnit.test(
        "when Navigating to a one2many with tabs, editing in a popup, the popup should receive the focus then give it back",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                            <notebook>
                                <page string="Partner page">
                                    <field name="turtles">
                                        <tree>
                                            <field name="turtle_foo"/>
                                            <field name="turtle_description"/>
                                        </tree>
                                        <form>
                                            <group>
                                                <field name="turtle_foo"/>
                                                <field name="turtle_int"/>
                                            </group>
                                        </form>
                                    </field>
                                </page>
                            </notebook>
                            <group>
                                <field name="foo"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            target.querySelector("[name=qux] input").focus();
            assert.strictEqual(target.querySelector("[name=qux] input"), document.activeElement);

            // next tabable element is notebook tab
            getNextTabableElement(target).focus();
            // go inside one2many
            getNextTabableElement(target).focus();
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_x2many_list_row_add a"),
                document.activeElement
            );

            await addRow(target);
            assert.strictEqual(
                target.querySelector(".modal [name=turtle_foo] input"),
                document.activeElement
            );

            triggerHotkey("Escape");
            await nextTick();

            assert.containsNone(target, ".modal");
            assert.strictEqual(
                target.querySelector(".o_field_x2many_list_row_add a"),
                document.activeElement
            );
        }
    );

    QUnit.test(
        "when creating a new many2one on a x2many then discarding it immediately with ESCAPE, it should not crash",
        async function (assert) {
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            serverData.models.partner.records[0].turtles = [];
            serverData.views = {
                "partner,false,form": `
                    <form>
                        <field name="foo"/>
                        <field name="bar"/>
                    </form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                                <field name="turtle_trululu"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            // add a new line
            await addRow(target);

            assert.containsOnce(target, ".o_selected_row");

            await clickOpenM2ODropdown(target, "turtle_trululu");
            await editInput(target, ".o_field_widget[name=turtle_trululu] input", "ABC");
            clickOpenedDropdownItem(target, "turtle_trululu", "Create and edit...");

            triggerHotkey("Escape");
            await nextTick();

            assert.containsNone(document.body, ".modal");
            assert.containsNone(target, ".o_selected_row");
        }
    );

    QUnit.test(
        "navigating through an editable list with custom controls [REQUIRE FOCUS]",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="p">
                            <tree editable="bottom">
                                <control>
                                    <create string="Custom 1" context="{'default_foo': '1'}"/>
                                    <create string="Custom 2" context="{'default_foo': '2'}"/>
                                </control>
                                <field name="foo"/>
                            </tree>
                        </field>
                        <field name="int_field"/>
                    </form>`,
            });

            assert.strictEqual(
                document.activeElement,
                target.querySelector("[name=display_name] input")
            );

            assert.containsNone(target, "[name=p] .o_selected_row");

            // press tab to navigate to the list
            const firstCreateActionLink = target.querySelector(".o_field_x2many_list_row_add a");
            let event = triggerEvent(
                document.activeElement,
                null,
                "keydown",
                { key: "Tab" },
                { sync: true }
            );
            assert.strictEqual(getNextTabableElement(target), firstCreateActionLink);
            assert.ok(!event.defaultPrevented);
            firstCreateActionLink.focus(); // goes inside one2many
            await nextTick();

            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_field_x2many_list_row_add a")
            );

            // press right to focus the second control
            triggerHotkey("ArrowRight");
            await nextTick();

            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_field_x2many_list_row_add a:nth-child(2)")
            );

            // press left to come back to first control
            triggerHotkey("ArrowLeft");
            await nextTick();

            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_field_x2many_list_row_add a")
            );

            const secondCreateActionLink = target.querySelector(
                ".o_field_x2many_list_row_add a:nth-child(2)"
            );
            event = triggerEvent(
                document.activeElement,
                null,
                "keydown",
                { key: "Tab" },
                { sync: true }
            );
            assert.strictEqual(getNextTabableElement(target), secondCreateActionLink);
            assert.ok(!event.defaultPrevented);
            secondCreateActionLink.focus();
            await nextTick();
            assert.strictEqual(document.activeElement, secondCreateActionLink);

            const nextInput = target.querySelector("[name=int_field] input");
            event = triggerEvent(
                secondCreateActionLink,
                null,
                "keydown",
                { key: "Tab" },
                { sync: true }
            );
            assert.strictEqual(getNextTabableElement(target), nextInput);
            assert.ok(!event.defaultPrevented);
            nextInput.focus();
            await nextTick();
            assert.strictEqual(document.activeElement, nextInput);
        }
    );

    QUnit.test(
        "be able to press a key on the keyboard when focusing a column header without crashing",
        async function (assert) {
            assert.expect(0);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_int" />
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            await click(target.querySelector(".o_data_row .o_data_cell"));
            target.querySelector(".o_list_renderer .o_column_sortable").focus();
            triggerHotkey("a");
            await nextTick();
        }
    );

    QUnit.test("Navigate from an invalid but not dirty row", async (assert) => {
        serverData.models.partner.records[0].p = [2, 4];
        serverData.models.partner.records[1].display_name = ""; // invalid record

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name" required="1" />
                            <field name="int_field" readonly="1" />
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_data_cell")); // edit the first row

        assert.containsOnce(target, ".o_data_row.o_selected_row");
        assert.hasClass(target.querySelectorAll(".o_data_row")[0], "o_selected_row");

        triggerHotkey("Tab"); // navigate with "Tab" to the second row
        await nextTick();

        assert.containsOnce(target, ".o_data_row.o_selected_row");
        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");
        assert.containsNone(target, ".o_invalid_cell");

        await click(target.querySelector(".o_data_cell")); // come back on first row

        assert.containsOnce(target, ".o_data_row.o_selected_row");
        assert.hasClass(target.querySelectorAll(".o_data_row")[0], "o_selected_row");
        assert.containsNone(target, ".o_invalid_cell");

        triggerHotkey("Enter"); // try to navigate with "Enter" to the second row
        await nextTick();

        assert.containsOnce(target, ".o_data_row.o_selected_row");
        assert.hasClass(target.querySelectorAll(".o_data_row")[0], "o_selected_row");
        assert.containsOnce(target, ".o_invalid_cell");
    });

    QUnit.test("Check onchange with two consecutive one2one", async function (assert) {
        serverData.models.product.fields.product_partner_ids = {
            string: "User",
            type: "one2many",
            relation: "partner",
        };
        serverData.models.product.records[0].product_partner_ids = [1];
        serverData.models.product.records[1].product_partner_ids = [2];
        serverData.models.turtle.fields.product_ids = {
            string: "Product",
            type: "one2many",
            relation: "product",
        };
        serverData.models.turtle.fields.user_ids = {
            string: "Product",
            type: "one2many",
            relation: "user",
        };
        serverData.models.turtle.onchanges = {
            turtle_trululu: function (record) {
                record.product_ids = [[4, 37]];
                record.user_ids = [
                    [4, 17],
                    [4, 19],
                ];
            },
        };

        await makeView({
            type: "form",
            resModel: "turtle",
            serverData,
            arch: `
                <form string="Turtles">
                    <field string="Product" name="turtle_trululu"/>
                    <field readonly="1" string="Related field" name="product_ids">
                        <tree>
                            <field widget="many2many_tags" name="product_partner_ids"/>
                        </tree>
                    </field>
                    <field readonly="1" string="Second related field" name="user_ids">
                        <tree>
                            <field widget="many2many_tags" name="partner_ids"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await clickOpenM2ODropdown(target, "turtle_trululu");
        await clickM2OHighlightedItem(target, "turtle_trululu");

        const getElementTextContent = (name) =>
            [
                ...document.querySelectorAll(
                    `.o_field_many2many_tags[name="${name}"] .badge.o_tag_color_0 > .o_tag_badge_text`
                ),
            ].map((x) => x.textContent);
        assert.deepEqual(
            getElementTextContent("product_partner_ids"),
            ["first record"],
            "should have the correct value in the many2many tag widget"
        );
        assert.deepEqual(
            getElementTextContent("partner_ids"),
            ["first record", "second record"],
            "should have the correct values in the many2many tag widget"
        );
    });

    QUnit.test(
        "does not crash when you parse a tree arch containing another tree arch",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="turtles">
                                <tree>
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_list_renderer");
        }
    );
    QUnit.test("open a one2many record containing a one2many", async (assert) => {
        serverData.views = {
            "partner,1234,form": `<form><field name="turtles" >
                <tree><field name="display_name" /></tree></field>
                </form>`,
        };

        patchWithCleanup(browser.localStorage, {
            setItem(args) {
                assert.step(`localStorage setItem ${args}`);
            },
            getItem(args) {
                assert.step(`localStorage getItem ${args}`);
            },
        });

        const rec = serverData.models.partner.records.find(({ id }) => id === 2);
        rec.p = [1];
        await makeView({
            type: "form",
            arch: `<form>
                <field name="p" context="{ 'form_view_ref': 1234 }">
                    <tree><field name="display_name" /></tree>
                </field>
            </form>`,
            serverData,
            resModel: "partner",
            resId: 2,
        });

        assert.verifySteps([
            "localStorage getItem optional_fields,partner,form,100000001,p,list,display_name",
        ]);

        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".modal .o_data_row");
        assert.verifySteps([
            "localStorage getItem optional_fields,partner,form,100000001,turtles,list,display_name",
        ]);
    });

    QUnit.test(
        "if there are less than 4 lines in a one2many, empty lines must be displayed to cover the difference.",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
            });

            // Should only contain the "Add a line" line and 3 blank lines
            assert.containsNone(target, ".o_list_renderer tbody tr .o_data_row");
            assert.containsOnce(target, ".o_list_renderer tbody tr .o_field_x2many_list_row_add");
            assert.hasClass(
                target.querySelector(".o_list_renderer tbody tr td"),
                "o_field_x2many_list_row_add"
            );
            assert.containsN(target, ".o_list_renderer tbody tr", 4);

            await addRow(target);
            // Should only contain a new row, the "Add a line" line and 2 blank lines
            assert.containsOnce(target, ".o_list_renderer tbody tr.o_data_row");
            assert.hasClass(target.querySelector(".o_list_renderer tbody tr"), "o_data_row");
            assert.containsOnce(target, ".o_list_renderer tbody tr .o_field_x2many_list_row_add");
            assert.hasClass(
                target.querySelectorAll(".o_list_renderer tbody tr")[1].querySelector("td"),
                "o_field_x2many_list_row_add"
            );
            assert.containsN(target, ".o_list_renderer tbody tr", 4);
        }
    );

    QUnit.test("one2many can delete a new record", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="foo"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click_edit"><t t-esc="record.foo.value"/></div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="foo" />
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save"); // should not happen
                }
            },
        });
        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");

        await click(target, ".o-kanban-button-new");
        await clickSave(target.querySelector(".modal"));
        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");

        await click(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.containsOnce(target, ".modal .o_btn_remove");

        await click(target, ".modal .o_btn_remove");
        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");

        await clickSave(target);
        assert.verifySteps([]);
    });

    QUnit.test("toggle boolean in o2m with the formView in edition", async function (assert) {
        serverData.models.partner.onchanges = {
            turtles: () => {},
        };
        serverData.models.turtle.onchanges = {
            turtle_bar: () => {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="turtle_bar" widget="boolean_toggle"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method + " " + args.model);
            },
        });
        assert.verifySteps(["get_views partner", "web_read partner"]);

        await click(target, ".o_boolean_toggle");
        assert.verifySteps(["onchange partner", "web_save turtle"]);
    });

    QUnit.test(
        "Boolean toggle in x2many must not be editable if form is not editable",
        async function (assert) {
            serverData.views = {
                "turtle,false,form": `<form>
                        <field name="turtle_bar" widget="boolean_toggle"/>
                        <field name="partner_ids">
                            <tree>
                                <field name="bar" widget="boolean_toggle"/>
                            </tree>
                        </field>
                    </form>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form edit="0">
                        <field name="turtles">
                            <tree>
                                <field name="turtle_bar" widget="boolean_toggle"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.hasClass(target.querySelector(".o_form_renderer"), "o_form_readonly");
            const booleanToggle = target.querySelector(
                "[name='turtles'] .o_data_row [name='turtle_bar'] .o_boolean_toggle input"
            );
            assert.ok(
                booleanToggle.disabled,
                "The boolean toggle should be disabled when the form is readonly"
            );

            await click(target, ".o_data_cell");
            assert.containsOnce(target, ".modal-dialog");
            assert.hasClass(target.querySelector(".o_form_renderer"), "o_form_readonly");
            const booleanToggleInDialog = target.querySelector(".modal [name='turtle_bar'] input");
            assert.ok(
                booleanToggleInDialog.disabled,
                "The boolean toggle in the form view dialog should be disabled when the main form is readonly"
            );
            assert.ok(
                target.querySelector(
                    ".modal [name='partner_ids'] .o_data_row [name='bar'] .o_boolean_toggle input"
                ).disabled,
                "The boolean toggle in x2m in the form view dialog should be disabled when the main form is readonly"
            );
        }
    );

    QUnit.test("create a new record with an x2m invisible", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="p" invisible="1">
                            <tree>
                                <field name="int_field"/>
                                <field name="trululu"/>
                            </tree>
                        </field>
                    </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "onchange") {
                    assert.deepEqual(args.args[3], {
                        display_name: {},
                        p: {
                            fields: {
                                int_field: {},
                                trululu: {
                                    fields: {
                                        display_name: {},
                                    },
                                },
                            },
                            limit: 40,
                            order: "",
                        },
                    });
                    return {
                        value: {
                            p: [
                                [
                                    0,
                                    false,
                                    {
                                        int_field: 4,
                                        trululu: { id: 1, display_name: "first record" },
                                    },
                                ],
                            ],
                        },
                    };
                }
                if (args.method === "web_save") {
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, [[0, commands[0][1], { int_field: 4, trululu: 1 }]]);
                    assert.deepEqual(args.kwargs.specification, {
                        display_name: {},
                        p: {},
                    });
                }
            },
        });

        assert.containsNone(target, "[name='p']");
        assert.verifySteps(["get_views", "onchange"]);

        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("edit a record with an x2m invisible", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="foo"/>
                        <field name="turtles" invisible="1">
                            <tree>
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </form>`,
            mockRPC(route, args) {
                assert.step(`${args.method} ${args.model}`);
                if (args.method === "web_read") {
                    assert.deepEqual(args.kwargs.specification, {
                        display_name: {},
                        foo: {},
                        turtles: {},
                    });
                }
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1], {
                        foo: "plop",
                    });
                    assert.deepEqual(args.kwargs.specification, {
                        display_name: {},
                        foo: {},
                        turtles: {},
                    });
                }
            },
            resId: 1,
        });

        assert.containsNone(target, "[name='p']");
        assert.verifySteps(["get_views partner", "web_read partner"]);

        await editInput(target, "[name='foo'] input", "plop");
        await clickSave(target);
        assert.verifySteps(["web_save partner"]);
    });

    QUnit.test("can't select a record in a one2many", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 1,
        });

        await triggerEvents(target, ".o_data_row", ["touchstart", "touchend"]);
        assert.containsNone(target, ".o_data_row_selected");
    });

    QUnit.test(
        "save a record after creating and editing a new invalid record in a one2many",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name" required="1"/>
                                <field name="int_field"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            await addRow(target);
            await editInput(target, ".o_field_widget[name=int_field] input", "3");
            await clickSave(target);
            assert.containsOnce(
                target,
                ".o_data_row.o_selected_row",
                "line should not have been removed and should still be in edition"
            );
            assert.hasClass(
                target.querySelector(".o_field_widget[name=display_name]"),
                "o_field_invalid"
            );
        }
    );

    QUnit.test("nested one2manys, multi page, onchange", async function (assert) {
        serverData.models.partner.records[2].int_field = 5;
        serverData.models.partner.records[0].p = [2, 4]; // limit 1 -> record 4 will be on second page
        serverData.models.partner.records[1].turtles = [1];
        serverData.models.partner.records[2].turtles = [2];
        serverData.models.turtle.records[0].turtle_int = 1;
        serverData.models.turtle.records[1].turtle_int = 2;

        serverData.models.partner.onchanges.int_field = function (obj) {
            assert.step("onchange");
            obj.p = [[5]];
            obj.p.push([1, 2, { turtles: [[5], [1, 1, { turtle_int: obj.int_field }]] }]);
            obj.p.push([1, 4, { turtles: [[5], [1, 2, { turtle_int: obj.int_field }]] }]);
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="p">
                        <tree editable="bottom" limit="1" default_order="display_name">
                            <field name="display_name" />
                            <field name="int_field" />
                            <field name="turtles">
                                <tree editable="bottom">
                                    <field name="turtle_int"/>
                                </tree>
                            </field>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mode: "edit",
        });

        await editInput(target, ".o_field_widget[name=int_field] input", "5");
        assert.verifySteps(["onchange"]);

        await clickSave(target);
        assert.strictEqual(serverData.models.partner.records[0].int_field, 5);
        assert.strictEqual(serverData.models.turtle.records[1].turtle_int, 5);
        assert.strictEqual(serverData.models.turtle.records[0].turtle_int, 5);
    });

    QUnit.test("multi page, command forget for record of second page", async function (assert) {
        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.models.partner.onchanges = {
            int_field: function (obj) {
                obj.p = [[3, 4]];
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="p">
                            <tree limit="2">
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(target.querySelector("[name=int_field] input").value, "10");
        assert.containsN(target, ".o_data_row", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "first record",
            "second record",
        ]);
        assert.strictEqual(
            target.querySelector(".o_x2m_control_panel .o_pager_counter").innerText,
            "1-2 / 3"
        );

        // trigger the onchange
        await editInput(target, "[name=int_field] input", "16");
        assert.containsN(target, ".o_data_row", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "first record",
            "second record",
        ]);
        assert.containsNone(target, ".o_x2m_control_panel .o_pager");
    });

    QUnit.test("new record, receive more create commands than limit", async function (assert) {
        serverData.models.partner.fields.sequence = { type: "integer" };
        serverData.models.partner.onchanges = {
            p: function (obj) {
                obj.p = [
                    [0, 0, { sequence: 1, display_name: "Record 1" }],
                    [0, 0, { sequence: 2, display_name: "Record 2" }],
                    [0, 0, { sequence: 3, display_name: "Record 3" }],
                    [0, 0, { sequence: 4, display_name: "Record 4" }],
                ];
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="p">
                            <tree limit="2">
                                <field name="sequence"/>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "Record 1",
            "Record 2",
            "Record 3",
            "Record 4",
        ]);
        assert.containsNone(target, ".o_x2m_control_panel .o_pager");
    });

    QUnit.test("active actions are passed to o2m field", async (assert) => {
        serverData.models.partner.records[0].turtles = [1, 2, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" create="false" delete="false">
                            <field name="display_name" />
                            <field name="turtle_foo" />
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mode: "edit",
        });

        assert.containsN(target, ".o_data_row", 3);
        assert.containsNone(target, ".o_list_record_remove");

        await click(target, ".o_data_row:nth-child(3) .o_data_cell:nth-child(2)");

        assert.hasClass(target.querySelector(".o_data_row:nth-child(3)"), "o_selected_row");

        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, ".o_data_row", 3);
        assert.containsNone(target, ".o_list_record_remove");
        assert.hasClass(target.querySelector(".o_data_row:first-child"), "o_selected_row");
    });

    QUnit.test("kanban one2many in opened view form", async function (assert) {
        serverData.models.partner.records[0].p = [1];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="p">
                                <kanban class="o-custom-class">
                                    <field name="display_name"/>
                                    <templates>
                                        <t t-name="kanban-box">
                                            <div><t t-esc="record.display_name.value"/></div>
                                        </t>
                                    </templates>
                                </kanban>
                            </field>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        await click(target, ".o_data_row td[name=display_name]");
        assert.containsOnce(target, ".modal .o_kanban_record:not(.o_kanban_ghost)");
        assert.hasClass(target.querySelector(".modal .o_field_x2many_kanban"), "o-custom-class");

        const record = target.querySelector(".modal .o_kanban_record:not(.o_kanban_ghost)");
        record.focus(); // shortcut for a true click
        assert.strictEqual(document.activeElement, record);

        await triggerHotkey("ArrowUp");
        await nextTick();

        assert.containsOnce(target, ".modal .o_kanban_record:not('.o_kanban_ghost')");
    });

    QUnit.test("kanban one2many in opened view form (with _view_ref)", async (assert) => {
        serverData.views = {
            "partner,1234,kanban": /* xml */ `
                <kanban class="o-custom-class">
                    <field name="display_name"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><t t-esc="record.display_name.value"/></div>
                        </t>
                    </templates>
                </kanban>
            `,
        };
        serverData.models.partner.records[0].p = [1];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="p" mode="kanban" context="{ 'kanban_view_ref': 1234 }" />
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        await click(target, ".o_data_row td[name=display_name]");
        assert.containsOnce(target, ".modal .o_kanban_record:not(.o_kanban_ghost)");
        assert.hasClass(target.querySelector(".modal .o_field_x2many_kanban"), "o-custom-class");

        const record = target.querySelector(".modal .o_kanban_record:not(.o_kanban_ghost)");
        record.focus(); // shortcut for a true click
        assert.strictEqual(document.activeElement, record);

        await triggerHotkey("ArrowUp");
        await nextTick();

        assert.containsOnce(target, ".modal .o_kanban_record:not('.o_kanban_ghost')");
    });

    QUnit.test("kanban one2many (with widget) in opened view form", async function (assert) {
        serverData.models.partner.records[0].p = [1];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="p">
                        <kanban>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <field name="display_name" widget="char"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "first record");

        await click(target.querySelector(".o_kanban_record"));
        assert.containsOnce(target, ".o_dialog .o_form_view .o_field_widget[name=display_name]");
        assert.strictEqual(
            target.querySelector(".o_dialog .o_form_view .o_field_widget[name=display_name] input")
                .value,
            "first record"
        );
        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "first record");

        await editInput(
            target,
            ".o_dialog .o_form_view .o_field_widget[name=display_name] input",
            "test"
        );
        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "test");
    });

    QUnit.test("list one2many in opened view form", async function (assert) {
        serverData.models.partner.records[0].p = [1];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="p">
                                <tree editable="1" class="o-custom-class">
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        await click(target.querySelector(".o_data_row td[name=display_name]"));
        assert.containsOnce(target, ".modal .o_data_row td[name=display_name]");
        assert.hasClass(target.querySelector(".modal .o_field_x2many_list"), "o-custom-class");

        const header = target.querySelector(".modal thead th[data-name=display_name]");
        header.focus(); // shortcut but possible via the mouse and keynav;
        assert.strictEqual(document.activeElement, header);

        await triggerHotkey("ArrowUp");
        await nextTick();

        assert.containsOnce(target, ".modal .o_data_row td[name=display_name]");
    });

    QUnit.test("list one2many in opened view form (with _view_ref)", async function (assert) {
        serverData.views = {
            "partner,1234,list": /* xml */ `
                <tree editable="1" class="o-custom-class">
                    <field name="display_name"/>
                </tree>
            `,
        };
        serverData.models.partner.records[0].p = [1];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="p" mode="list" context="{ 'list_view_ref': 1234 }" />
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        await click(target.querySelector(".o_data_row td[name=display_name]"));
        assert.containsOnce(target, ".modal .o_data_row td[name=display_name]");
        assert.hasClass(target.querySelector(".modal .o_field_x2many_list"), "o-custom-class");

        const header = target.querySelector(".modal thead th[data-name=display_name]");
        header.focus(); // shortcut but possible via the mouse and keynav;
        assert.strictEqual(document.activeElement, header);

        await triggerHotkey("ArrowUp");
        await nextTick();

        assert.containsOnce(target, ".modal .o_data_row td[name=display_name]");
    });

    QUnit.test("one2many, form view dialog with custom footer", async function (assert) {
        serverData.models.partner.records[0].p = [1];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                            <footer>
                                <span class="my_span">Hello</span>
                            </footer>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_data_row td[name=display_name]"));
        assert.containsOnce(target, ".modal-footer .my_span");

        await click(target.querySelector(".modal-header .btn-close"));
        assert.containsNone(target, ".modal");

        // open it again
        await click(target.querySelector(".o_data_row td[name=display_name]"));
        assert.containsOnce(target, ".modal-footer .my_span");
    });

    QUnit.test('Add a line, click on "Save & New" with an invalid form', async function (assert) {
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name" required="1"/>
                        </form>
                    </field>
                </form>`,
        });
        patchWithCleanup(form.env.services.notification, {
            add: (message, params) => {
                assert.step(params.type);
                assert.strictEqual(params.title, "Invalid fields: ");
                assert.strictEqual(message.toString(), "<ul><li>Displayed name</li></ul>");
            },
        });

        assert.containsNone(target, ".o_data_row");
        // Add a new record
        await addRow(target);
        assert.containsOnce(target, ".o_dialog .o_form_view");

        // Click on "Save & New" with an invalid form
        await click(target, ".o_dialog .o_form_button_save_new");
        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.verifySteps(["danger"]);

        // Check that no buttons are disabled
        assert.hasAttrValue(
            target.querySelector(".o_dialog .o_form_button_save_new"),
            "disabled",
            undefined
        );
        assert.hasAttrValue(
            target.querySelector(".o_dialog .o_form_button_cancel"),
            "disabled",
            undefined
        );
    });

    QUnit.test("field in list but not in fetched form", async function (assert) {
        serverData.models.partner.fields.o2m = {
            type: "one2many",
            relation: "partner_type",
            relation_field: "p_id",
        };
        serverData.models.partner_type.onchanges = {
            display_name: (rec) => {
                if (rec.display_name === "changed") {
                    rec.color = 5;
                }
            },
        };

        serverData.models.partner_type.fields.p_id = { type: "many2one", relation: "partner" };
        serverData.views = {
            "partner_type,false,form": `<form><field name="display_name" /></form>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="o2m">
                        <tree>
                            <field name="display_name"/>
                            <field name="color" />
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(`${args.method}: ${args.model}`);
            },
        });

        assert.verifySteps(["get_views: partner", "onchange: partner"]);
        await click(target, ".o_field_x2many_list_row_add a");
        assert.verifySteps(["get_views: partner_type", "onchange: partner_type"]);
        await editInput(
            target.querySelector(".modal"),
            ".o_field_widget[name='display_name'] input",
            "changed"
        );
        assert.verifySteps(["onchange: partner_type"]);
        await click(target.querySelector(".modal .o_form_button_save"));
        assert.strictEqual(target.querySelector(".o_data_row").textContent, "changed5");
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save: partner"]);
        assert.strictEqual(target.querySelector(".o_data_row").textContent, "changed5");
    });

    QUnit.test("pressing tab before an onchange is resolved", async (assert) => {
        const onchangeGetPromise = makeDeferred();

        serverData.models.partner.onchanges = {
            display_name: (obj) => {
                obj.display_name = "test";
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom" >
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            async mockRPC(route, args, performRPC) {
                if (
                    args.method === "onchange" &&
                    args.model === "product" &&
                    args.args[2] === "display_name"
                ) {
                    await onchangeGetPromise;
                }
            },
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));

        await editInput(target, ".o_field_widget[name='display_name'] input", "gold");
        triggerHotkey("Tab");
        triggerHotkey("Tab");
        onchangeGetPromise.resolve();
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);
    });

    QUnit.test("add a row to an x2many and ask canBeRemoved twice", async function (assert) {
        // This test simulates that the view is asked twice to save its changes because the user
        // is leaving. Before the corresponding fix, the changes in the x2many field weren't
        // removed after the save, and as a consequence they were saved twice (i.e. the row was
        // created twice).

        const def = makeDeferred();
        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_model: "partner",
                res_id: 1,
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
            2: {
                id: 2,
                name: "another action",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            },
        };
        serverData.views = {
            "partner,false,list": `<tree><field name="int_field"/></tree>`,
            "partner,false,search": `<search/>`,
            "partner,false,form": `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
        };

        const mockRPC = async (route, args) => {
            if (args.method === "web_save") {
                assert.step("web_save");
                assert.deepEqual(args.args[1], {
                    p: [[0, args.args[1].p[0][1], { display_name: "a name" }]],
                });
            }
            if (args.method === "web_search_read") {
                return def;
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_form_view");

        // add a row in the x2many
        await click(target, ".o_field_x2many_list_row_add a");
        await editInput(target, ".o_field_widget[name=display_name] input", "a name");
        assert.containsOnce(target, ".o_data_row");

        doAction(webClient, 2);
        await nextTick();
        doAction(webClient, 2);
        await nextTick();
        assert.verifySteps(["web_save"]);

        def.resolve();
        await nextTick();
        assert.containsOnce(target, ".o_list_view");
        assert.verifySteps([]);
    });

    QUnit.test(
        "one2many: save a record before the onchange is complete in a form dialog",
        async function (assert) {
            serverData.models.turtle.onchanges = {
                display_name: function () {},
            };

            serverData.views = {
                "turtle,false,form": `
                    <form>
                        <field name="display_name"/>
                    </form>`,
            };

            const def = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree>
                                <field name="display_name" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                async mockRPC(route, args) {
                    if (
                        args.method === "onchange" &&
                        args.args[2].length === 1 &&
                        args.args[2][0] === "display_name"
                    ) {
                        await def;
                    }
                },
            });
            await addRow(target);
            assert.containsOnce(target, ".modal");

            await editInput(target, ".o_field_widget[name=display_name] input", "new name");
            await click(target, ".modal .o_form_button_save");
            assert.containsOnce(target, ".modal");

            def.resolve();
            await nextTick();
            assert.containsNone(target, ".modal");
            assert.containsN(target, ".o_data_row", 2);
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row [name='display_name']")].map(
                    (el) => el.textContent
                ),
                ["donatello", "new name"]
            );
        }
    );

    QUnit.test("onchange create a record in an invisible x2many", async function (assert) {
        serverData.models.partner.onchanges = {
            foo: function () {},
        };
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <tree>
                            <field name="display_name" required="1"/>
                            <field name="p" invisible="1"/>
                        </tree>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    return {
                        value: {
                            p: [
                                [
                                    1,
                                    2,
                                    {
                                        display_name: "plop",
                                        p: [[0, false, {}]],
                                    },
                                ],
                            ],
                        },
                    };
                }
            },
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            ["second record"]
        );

        await editInput(target, ".o_field_widget[name=foo] input", "new foo value");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            ["plop"]
        );
    });

    QUnit.test("forget command for nested x2manys in form, not in list", async function (assert) {
        assert.expect(8);

        serverData.models.partner.records[0].p = [1, 2];
        serverData.models.partner.records[1].turtles = [2];
        serverData.models.partner.onchanges = {
            int_field: function (obj) {
                obj.p = [
                    [
                        1,
                        1,
                        {
                            foo: "new foo value (1)",
                            turtles: [
                                [
                                    1,
                                    2,
                                    {
                                        turtle_foo: "new turtle foo value (1)",
                                        partner_ids: [[3, 4]],
                                    },
                                ],
                            ],
                        },
                    ],
                    [
                        1,
                        2,
                        {
                            foo: "new foo value (2)",
                            turtles: [
                                [
                                    1,
                                    2,
                                    {
                                        turtle_foo: "new turtle foo value (2)",
                                        partner_ids: [[3, 2]],
                                    },
                                ],
                            ],
                        },
                    ],
                ];
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="p">
                            <tree>
                                <field name="foo"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="bottom">
                                        <field name="turtle_foo"/>
                                        <field name="partner_ids" widget="many2many_tags"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </group>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1], {
                        int_field: 16,
                        p: [
                            [
                                1,
                                1,
                                {
                                    foo: "new foo value (1)",
                                    turtles: [
                                        [
                                            1,
                                            2,
                                            {
                                                turtle_foo: "new turtle foo value (1)",
                                                partner_ids: [[3, 4]],
                                            },
                                        ],
                                    ],
                                },
                            ],
                            [
                                1,
                                2,
                                {
                                    foo: "new foo value (2)",
                                    turtles: [
                                        [
                                            1,
                                            2,
                                            {
                                                turtle_foo: "new turtle foo value (2)",
                                                partner_ids: [[3, 2]],
                                            },
                                        ],
                                    ],
                                },
                            ],
                        ],
                    });
                }
            },
            resId: 1,
        });

        assert.strictEqual(target.querySelector("[name=int_field] input").value, "10");

        // trigger the onchange
        await editInput(target, "[name=int_field] input", "16");
        assert.strictEqual(target.querySelector("[name=foo]").innerText, "new foo value (1)");
        assert.strictEqual(target.querySelectorAll("[name=foo]")[1].innerText, "new foo value (2)");

        // open the second x2many record
        await click(target.querySelectorAll(".o_data_row")[1].querySelector("td"));
        assert.containsOnce(target.querySelector(".o_dialog"), ".o_data_row");
        assert.strictEqual(
            target.querySelector(".o_dialog .o_data_cell[name=turtle_foo]").innerText,
            "new turtle foo value (2)"
        );
        assert.containsOnce(
            target.querySelector(".o_dialog .o_data_cell[name=partner_ids]"),
            ".o_tag"
        );
        assert.strictEqual(
            target.querySelector(".o_dialog .o_data_cell[name=partner_ids] .o_tag").innerText,
            "aaa"
        );

        await clickSave(target.querySelector(".o_dialog"));
        await clickSave(target);
    });

    QUnit.test("modifiers based on x2many", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" >
                        <tree editable="bottom">
                            <field name="foo"/>
                        </tree>
                    </field>
                    <field name="display_name" readonly="p"/>
                    <field name="int_field" required="p"/>
                    <button name="abc" string="Do it" class="my_button" invisible="not p"/>
                </form>`,
            resId: 1,
        });
        assert.containsNone(target, "button.my_button");
        assert.containsNone(target, "[name='display_name'].o_readonly_modifier");
        assert.containsNone(target, "[name='int_field'].o_required_modifier");

        await addRow(target);
        await editInput(target, "[name='foo'] input", "Test");
        assert.containsOnce(target, "button.my_button");
        assert.containsOnce(target, "[name='display_name'].o_readonly_modifier");
        assert.containsOnce(target, "[name='int_field'].o_required_modifier");

        await click(target, "button.fa-trash-o");
        assert.containsNone(target, "button.my_button");
        assert.containsNone(target, "[name='display_name'].o_readonly_modifier");
        assert.containsNone(target, "[name='int_field'].o_required_modifier");
    });

    QUnit.test(
        "add record in nested x2many with context depending on parent",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].p = [1];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="int_field"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="turtles" widget="many2many_tags" context="{'x': parent.int_field, 'y': 2}"/>
                        </tree>
                    </field>
                </form>`,
                mockRPC(route, args) {
                    if (args.method === "web_read" && args.model === "turtle") {
                        assert.deepEqual(args.kwargs.context, {
                            bin_size: true,
                            lang: "en",
                            tz: "taht",
                            uid: 7,
                            x: 10,
                            y: 2,
                        });
                    }
                },
                resId: 1,
            });

            await click(target, ".o_data_cell");
            await click(target.querySelector("div[name=turtles] .o-autocomplete.dropdown input"));
            await click(target.querySelector(".o-autocomplete--dropdown-menu li a"));
        }
    );

    QUnit.test("one2many with default_order on id, but id not in view", async function (assert) {
        serverData.models.partner.records[0].turtles = [1, 2, 3];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top" default_order="turtle_int,id">
                            <field name="turtle_int" widget="handle"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1].turtles, [
                        [1, 3, { turtle_int: 0 }],
                        [1, 1, { turtle_int: 1 }],
                        [1, 2, { turtle_int: 2 }],
                    ]);
                }
            },
            resId: 1,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "yop",
            "blip",
            "kawa",
        ]);

        // drag the third record to top of the list
        await dragAndDrop("tbody tr:nth-child(3) .o_handle_cell", "tbody tr", "top");
        await clickSave(target);

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_char")), [
            "kawa",
            "yop",
            "blip",
        ]);
        assert.verifySteps(["get_views", "web_read", "web_save"]);
    });

    QUnit.test("one2many causes an onchange on the parent which fails", async function (assert) {
        serverData.models.partner.onchanges = {
            turtles: function () {},
        };
        serviceRegistry.add("error", errorService);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange" && args.model === "partner") {
                    throw makeServerError();
                }
            },
            resId: 1,
        });

        await click(target.querySelector(".o_data_cell"));
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='turtle_foo'] input").value,
            "blip"
        );

        // onchange on parent record fails
        await editInput(target, ".o_field_widget[name='turtle_foo'] input", "new value");
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='turtle_foo'] input").value,
            "blip"
        );
        assert.containsOnce(target, ".o_error_dialog");
    });

    QUnit.test(
        "one2many custom which can be edited in dialog or on the line",
        async function (assert) {
            const customState = reactive({ isEditable: false });
            class CustomX2manyField extends X2ManyField {
                setup() {
                    super.setup();
                    this.canOpenRecord = true;
                    this.customState = useState(customState);
                }

                get rendererProps() {
                    const props = super.rendererProps;
                    props.editable = this.customState.isEditable;
                    return props;
                }
            }

            const customX2ManyField = {
                ...x2ManyField,
                component: CustomX2manyField,
            };
            registry.category("fields").add("custom", customX2ManyField);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="turtles" widget="custom">
                        <tree editable="top">
                            <field name="turtle_foo"/>
                        </tree>
                        <form>
                            <field name="display_name" />
                        </form>
                    </field>
                </form>`,
                resId: 1,
            });
            assert.containsOnce(
                target,
                ".o_form_status_indicator_buttons.invisible",
                "form view is not dirty"
            );

            await click(target, ".o_data_cell");
            assert.containsOnce(target, ".modal");

            customState.isEditable = true;
            await click(target, ".modal .btn-close");
            assert.containsOnce(
                target,
                ".o_form_status_indicator_buttons.invisible",
                "form view is not dirty"
            );

            await click(target, ".o_data_cell");
            await editInput(target, "[name='turtle_foo'] input", "new value");
            assert.containsOnce(
                target,
                ".o_form_status_indicator_buttons:not(.invisible)",
                "form view is dirty"
            );
        }
    );

    QUnit.test(
        "x2many kanban with float field in form (non inline) but not in kanban",
        async function (assert) {
            // In this test, the form view contains an extra float field and isn't inline. When we open
            // a record, we add the form fields to the list of activeFields, and we load the
            // corresponding data (for that record only). Afterwards, we force a re-rendering of the
            // x2many kanban to ensure that the other record can still be rendered. Before the fix coming
            // with this test, it wasn't the case, because those records had extra activeFields, but no
            // entry in data for those fields.
            serverData.models.partner.records[0].turtles = [2, 3];
            serverData.views = {
                "turtle,false,form": `
                    <form>
                        <field name="display_name"/>
                        <field name="turtle_qux"/>
                    </form>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="bar"/>
                    <field name="turtles" invisible="not bar">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <t t-esc="record.display_name.raw_value"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_field_widget[name=turtles]");
            assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);

            // open the first record
            await click(target.querySelector(".o_kanban_record"));
            assert.containsOnce(target, ".o_dialog");
            assert.containsOnce(target, ".o_dialog .o_field_widget[name=turtle_qux]");

            // close the dialog
            await click(target.querySelector(".o_dialog .o_form_button_save"));
            assert.containsNone(target, ".o_dialog");

            // toggle bar to make the x2many invisible
            await click(target, ".o_field_widget[name=bar] input");
            assert.containsNone(target, ".o_field_widget[name=turtles]");

            // toggle bar again to make the x2many visible and force kanban cards to re-render
            await click(target, ".o_field_widget[name=bar] input");
            assert.containsOnce(target, ".o_field_widget[name=turtles]");
            assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);
        }
    );

    QUnit.test(
        "onchange on x2many returning an update command with only readonly fields",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [2];
            serverData.models.turtle.fields.display_name.readonly = true;
            serverData.models.partner.onchanges = {
                bar: (obj) => {
                    obj.turtles = [[1, 2, { display_name: "onchange name" }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="turtles">
                            <tree><field name="display_name"/></tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "web_save") {
                        assert.deepEqual(args.args[1], { bar: false }); // should not contain turtles
                    }
                },
                resId: 1,
            });

            assert.containsOnce(target, ".o_field_widget[name=turtles] .o_data_row");
            assert.strictEqual(target.querySelector(".o_data_cell").innerText, "donatello");

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.strictEqual(target.querySelector(".o_data_cell").innerText, "onchange name");

            await clickSave(target);
            assert.strictEqual(target.querySelector(".o_data_cell").innerText, "donatello");
            assert.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
        }
    );

    QUnit.test(
        "onchange on x2many returning a create command with only readonly fields",
        async function (assert) {
            serverData.models.turtle.fields.display_name.readonly = true;
            serverData.models.partner.onchanges = {
                bar: (obj) => {
                    obj.turtles = [[0, false, { display_name: "onchange name" }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="turtles">
                            <tree><field name="display_name"/></tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "web_save") {
                        assert.deepEqual(args.args[1], {
                            bar: false,
                            turtles: [[0, args.args[1].turtles[0][1], {}]],
                        });
                    }
                },
            });

            assert.containsOnce(target, ".o_field_widget[name=turtles] .o_data_row");
            assert.strictEqual(target.querySelector(".o_data_cell").innerText, "donatello");

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsN(target, ".o_field_widget[name=turtles] .o_data_row", 2);
            assert.strictEqual(
                target.querySelectorAll(".o_data_cell")[1].innerText,
                "onchange name"
            );

            await clickSave(target);
            assert.containsN(target, ".o_field_widget[name=turtles] .o_data_row", 2);
            assert.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
        }
    );

    QUnit.test(
        "onchange on x2many add and delete x2m record, returning to initial state",
        async function (assert) {
            serverData.models.turtle.fields.display_name.readonly = true;
            serverData.models.partner.onchanges = {
                turtles: function () {},
            };

            let onchangeCount = 0;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "onchange") {
                        if (onchangeCount === 1) {
                            // partner turtles onchange for the new x2m record
                            assert.strictEqual(args.model, "partner");
                            assert.deepEqual(Object.keys(args.args[1]), ["turtles"]);
                            assert.strictEqual(args.args[1].turtles[0][0], 0);
                            assert.deepEqual(args.args[2], ["turtles"]);
                        } else if (onchangeCount === 2) {
                            // x2m record removed, empty list of commands expected
                            assert.strictEqual(args.model, "partner");
                            assert.deepEqual(Object.keys(args.args[1]), ["turtles"]);
                            assert.deepEqual(args.args[1].turtles, []);
                            assert.deepEqual(args.args[2], ["turtles"]);
                        }
                        onchangeCount++;
                    }
                },
            });

            assert.containsOnce(target, ".o_field_widget[name=turtles] .o_data_row");
            assert.strictEqual(target.querySelector(".o_data_cell").innerText, "donatello");

            await addRow(target);
            assert.containsN(target, ".o_field_widget[name=turtles] .o_data_row", 2);
            await removeRow(target, 1);
            assert.containsN(target, ".o_field_widget[name=turtles] .o_data_row", 1);

            await clickSave(target);
            assert.containsN(target, ".o_field_widget[name=turtles] .o_data_row", 1);
            assert.verifySteps(["get_views", "web_read", "onchange", "onchange", "onchange"]);
        }
    );
});
