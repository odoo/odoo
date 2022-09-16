/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { makeFakeUserService } from "../helpers/mock_services";
import { click, getFixture, patchWithCleanup, triggerEvents } from "../helpers/utils";
import { getMenuItemTexts, toggleActionMenu } from "../search/helpers";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let fixture;

QUnit.module("Mobile Views", ({ beforeEach }) => {
    beforeEach(() => {
        setupViewRegistries();
        fixture = getFixture();
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                    },
                    records: [
                        { id: 1, bar: true, foo: "yop" },
                        { id: 2, bar: true, foo: "blip" },
                        { id: 3, bar: true, foo: "gnap" },
                        { id: 4, bar: false, foo: "blip" },
                    ],
                },
            },
        };

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn() || true,
            clearTimeout: () => {},
        });
    });

    QUnit.module("ListView");

    QUnit.test("selection is properly displayed (single page)", async function (assert) {
        registry.category("services").add(
            "user",
            makeFakeUserService(() => false),
            { force: true }
        );

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>
            `,
            loadActionMenus: true,
        });

        assert.containsN(fixture, ".o_data_row", 4);
        assert.containsNone(fixture, ".o_list_selection_box");
        assert.containsOnce(fixture, ".o_control_panel .o_cp_bottom_right");

        // select a record
        await triggerEvents(fixture, ".o_data_row:nth-child(1)", ["touchstart", "touchend"]);
        assert.containsOnce(fixture, ".o_list_selection_box");
        assert.containsNone(fixture, ".o_list_selection_box .o_list_select_domain");
        assert.containsNone(fixture, ".o_control_panel .o_cp_bottom_right");
        assert.ok(
            fixture.querySelector(".o_list_selection_box").textContent.includes("1 selected")
        );

        // unselect a record
        await triggerEvents(fixture, ".o_data_row:nth-child(1)", ["touchstart", "touchend"]);
        assert.containsNone(fixture, ".o_list_selection_box .o_list_select_domain");

        // select 2 records
        await triggerEvents(fixture, ".o_data_row:nth-child(1)", ["touchstart", "touchend"]);
        await triggerEvents(fixture, ".o_data_row:nth-child(2)", ["touchstart", "touchend"]);
        assert.ok(
            fixture.querySelector(".o_list_selection_box").textContent.includes("2 selected")
        );
        assert.containsOnce(fixture, "div.o_control_panel .o_cp_action_menus");

        await toggleActionMenu(fixture);
        assert.deepEqual(
            getMenuItemTexts(fixture.querySelector(".o_cp_action_menus")),
            ["Delete"],
            "action menu should contain the Delete action"
        );

        // unselect all
        await click(fixture, ".o_discard_selection");
        assert.containsNone(fixture, ".o_list_selection_box");
        assert.containsOnce(fixture, ".o_control_panel .o_cp_bottom_right");
    });

    QUnit.test("selection box is properly displayed (multi pages)", async function (assert) {
        registry.category("services").add(
            "user",
            makeFakeUserService(() => false),
            { force: true }
        );

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree limit="3">
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>
            `,
            loadActionMenus: true,
        });

        assert.containsN(fixture, ".o_data_row", 3);
        assert.containsNone(fixture, ".o_list_selection_box");

        // select a record
        await triggerEvents(fixture, ".o_data_row:nth-child(1)", ["touchstart", "touchend"]);

        assert.containsOnce(fixture, ".o_list_selection_box");
        assert.containsNone(fixture, ".o_list_selection_box .o_list_select_domain");
        assert.ok(
            fixture.querySelector(".o_list_selection_box").textContent.includes("1 selected")
        );
        assert.containsOnce(fixture, ".o_list_selection_box");
        assert.containsOnce(fixture, "div.o_control_panel .o_cp_action_menus");

        await toggleActionMenu(fixture);
        assert.deepEqual(
            getMenuItemTexts(fixture.querySelector(".o_cp_action_menus")),
            ["Delete"],
            "action menu should contain the Delete action"
        );

        // select all records of first page
        await triggerEvents(fixture, ".o_data_row:nth-child(2)", ["touchstart", "touchend"]);
        await triggerEvents(fixture, ".o_data_row:nth-child(3)", ["touchstart", "touchend"]);
        assert.containsOnce(fixture, ".o_list_selection_box");
        assert.containsOnce(fixture, ".o_list_selection_box .o_list_select_domain");
        assert.ok(
            fixture.querySelector(".o_list_selection_box").textContent.includes("3 selected")
        );
        assert.containsOnce(fixture, ".o_list_select_domain");

        // select all domain
        await click(fixture, ".o_list_selection_box .o_list_select_domain");
        assert.containsOnce(fixture, ".o_list_selection_box");
        assert.ok(
            fixture.querySelector(".o_list_selection_box").textContent.includes("All 4 selected")
        );
    });

    QUnit.test("export button is properly hidden", async (assert) => {
        registry.category("services").add(
            "user",
            makeFakeUserService((group) => group === "base.group_allow_export"),
            { force: true }
        );

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>
            `,
        });

        assert.containsN(fixture, ".o_data_row", 4);
        assert.isNotVisible(fixture.querySelector(".o_list_export_xlsx"));
    });

    QUnit.test("editable readonly list view is disabled", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo" />
                </tree>
            `,
        });

        await triggerEvents(fixture, ".o_data_row:nth-child(1)", ["touchstart", "touchend"]);
        await click(fixture, ".o_data_row:nth-child(1) .o_data_cell:nth-child(1)");
        assert.containsNone(
            fixture,
            ".o_selected_row .o_field_widget[name=foo]",
            "The listview should not contains an edit field"
        );
    });

    QUnit.test("add custom field button not shown in mobile (with opt. col.)", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                    <tree>
                        <field name="foo" />
                        <field name="bar" optional="hide" />
                    </tree>
                `,
        });
        assert.containsOnce(fixture, "table .o_optional_columns_dropdown_toggle");
        await click(fixture, "table .o_optional_columns_dropdown_toggle");
        assert.containsOnce(fixture, "div.o_optional_columns_dropdown .dropdown-item");
    });

    QUnit.test(
        "add custom field button not shown to non-system users (wo opt. col.)",
        async (assert) => {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <field name="foo" />
                        <field name="bar" />
                    </tree>
                `,
            });

            assert.containsNone(fixture, "table .o_optional_columns_dropdown_toggle");
        }
    );
});
