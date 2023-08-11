/** @odoo-module **/

import { Component, markup, onRendered, onWillStart, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { currencies } from "@web/core/currency";
import { errorService } from "@web/core/errors/error_service";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { uiService } from "@web/core/ui/ui_service";
import { getNextTabableElement } from "@web/core/utils/ui";
import { session } from "@web/session";
import { FloatField } from "@web/views/fields/float/float_field";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { textField } from "@web/views/fields/text/text_field";
import { ListController } from "@web/views/list/list_controller";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { actionService } from "@web/webclient/actions/action_service";
import { getPickerApplyButton, getPickerCell } from "../core/datetime/datetime_test_helpers";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import {
    addRow,
    click,
    clickDiscard,
    clickOpenM2ODropdown,
    clickOpenedDropdownItem,
    clickSave,
    drag,
    dragAndDrop,
    editInput,
    editSelect,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    mouseEnter,
    nextTick,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerEvents,
    triggerHotkey,
} from "../helpers/utils";
import {
    editFavoriteName,
    editPager,
    getVisibleButtons,
    getFacetTexts,
    getPagerLimit,
    getPagerValue,
    groupByMenu,
    pagerNext,
    pagerPrevious,
    removeFacet,
    saveFavorite,
    toggleActionMenu,
    toggleSearchBarMenu,
    toggleMenuItem,
    toggleSaveFavorite,
    validateSearch,
} from "../search/helpers";
import { createWebClient, doAction, loadState } from "../webclient/helpers";
import { makeView, makeViewInDialog, setupViewRegistries } from "./helpers";
import { makeServerError } from "../helpers/mock_server";

const fieldRegistry = registry.category("fields");
const serviceRegistry = registry.category("services");

let serverData;
let target;

async function reloadListView(target) {
    if (target.querySelector(".o_searchview_input")) {
        await validateSearch(target);
    } else {
        await editPager(target, getPagerValue(target));
    }
}

function getDataRow(position) {
    return target.querySelectorAll(".o_data_row")[position - 1];
}

function getGroup(position) {
    return target.querySelectorAll(".o_group_header")[position - 1];
}

function clickAdd() {
    const listAddButtons = target.querySelectorAll(".o_list_button_add");
    if (listAddButtons.length) {
        return listAddButtons.length >= 2 ? click(listAddButtons[1]) : click(listAddButtons[0]);
    } else {
        throw new Error("No add button found to be clicked.");
    }
}

/**
 * @param {Element} el
 * @param {string} varName
 * @returns {string}
 */
function getCssVar(el, varName) {
    return getComputedStyle(el).getPropertyValue(varName);
}

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        date: { string: "Some Date", type: "date" },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            group_operator: "sum",
                        },
                        text: { string: "text field", type: "text" },
                        qux: { string: "my float", type: "float" },
                        m2o: { string: "M2O field", type: "many2one", relation: "bar" },
                        o2m: { string: "O2M field", type: "one2many", relation: "bar" },
                        m2m: { string: "M2M field", type: "many2many", relation: "bar" },
                        amount: { string: "Monetary field", type: "monetary" },
                        amount_currency: {
                            string: "Monetary field (currency)",
                            type: "monetary",
                            currency_field: "company_currency_id",
                        },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "res_currency",
                            default: 1,
                        },
                        currency_test: {
                            string: "Currency",
                            type: "many2one",
                            relation: "res_currency",
                            default: 1,
                        },
                        company_currency_id: {
                            string: "Company Currency",
                            type: "many2one",
                            relation: "res_currency",
                            default: 2,
                        },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["bar", "Bar"],
                                ["res_currency", "Currency"],
                                ["event", "Event"],
                            ],
                        },
                        properties: {
                            type: "properties",
                            definition_record: "m2o",
                            definition_record_field: "definitions",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.4,
                            m2o: 1,
                            m2m: [1, 2],
                            amount: 1200,
                            amount_currency: 1100,
                            currency_id: 2,
                            company_currency_id: 1,
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                            reference: "bar,1",
                            properties: [],
                        },
                        {
                            id: 2,
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            m2o: 2,
                            m2m: [1, 2, 3],
                            amount: 500,
                            reference: "res_currency,1",
                            properties: [],
                        },
                        {
                            id: 3,
                            bar: true,
                            foo: "gnap",
                            int_field: 17,
                            qux: -3,
                            m2o: 1,
                            m2m: [],
                            amount: 300,
                            reference: "res_currency,2",
                            properties: [],
                        },
                        {
                            id: 4,
                            bar: false,
                            foo: "blip",
                            int_field: -4,
                            qux: 9,
                            m2o: 1,
                            m2m: [1],
                            amount: 0,
                            properties: [],
                        },
                    ],
                },
                bar: {
                    fields: {
                        definitions: { type: "properties_definitions" },
                    },
                    records: [
                        { id: 1, display_name: "Value 1", definitions: [] },
                        { id: 2, display_name: "Value 2", definitions: [] },
                        { id: 3, display_name: "Value 3", definitions: [] },
                    ],
                },
                res_currency: {
                    fields: {
                        symbol: { string: "Symbol", type: "char" },
                        position: {
                            string: "Position",
                            type: "selection",
                            selection: [
                                ["after", "A"],
                                ["before", "B"],
                            ],
                        },
                    },
                    records: [
                        { id: 1, display_name: "USD", symbol: "$", position: "before" },
                        { id: 2, display_name: "EUR", symbol: "€", position: "after" },
                    ],
                },
                event: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "name", type: "char" },
                    },
                    records: [{ id: "2-20170808020000", name: "virtual" }],
                },
            },
        };
        setupViewRegistries();
        serviceRegistry.add("tooltip", tooltipService);
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        target = getFixture();
        serviceRegistry.add("ui", uiService);
    });

    QUnit.module("ListView");

    QUnit.test("simple readonly list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });

        // 3 th (1 for checkbox, 2 for columns)
        assert.containsN(target, "th", 3, "should have 3 columns");

        assert.strictEqual($(target).find("td:contains(gnap)").length, 1, "should contain gnap");
        assert.containsN(target, "tbody tr", 4, "should have 4 rows");
        assert.containsOnce(target, "th.o_column_sortable", "should have 1 sortable column");

        assert.containsOnce(
            target,
            "thead th:nth(2) .o_list_number_th",
            "header cells of integer fields should have o_list_number_th class"
        );
        assert.strictEqual(
            $(target).find("tbody tr:first td:nth(2)").css("text-align"),
            "right",
            "integer cells should be right aligned"
        );
        assert.isNotVisible(target.querySelector(".d-xl-none .o_list_button_add"));
        assert.isVisible(target.querySelector(".d-xl-inline-flex .o_list_button_add"));
        assert.isNotVisible(target.querySelector(".o_list_button_save"));
        assert.isNotVisible(target.querySelector(".o_list_button_discard"));
    });

    QUnit.test("select record range with shift click", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[0]);
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "1 selected"
        );
        assert.strictEqual(
            document.querySelectorAll(".o_data_row .o_list_record_selector input:checked").length,
            1
        );

        // shift click the 4th record to have 0-1-2-3 toggled
        await triggerEvents(
            target.querySelectorAll(".o_data_row .o_list_record_selector input")[3],
            null,
            [["keydown", { key: "Shift", shiftKey: true }], "click"]
        );

        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "4 selected"
        );
        assert.strictEqual(
            document.querySelectorAll(".o_data_row .o_list_record_selector input:checked").length,
            4
        );

        // shift click the 3rd record to untoggle 2-3
        await triggerEvents(
            target.querySelectorAll(".o_data_row .o_list_record_selector input")[2],
            null,
            [["keydown", { key: "Shift", shiftKey: true }], "click"]
        );
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "2 selected"
        );
        assert.strictEqual(
            document.querySelectorAll(".o_data_row .o_list_record_selector input:checked").length,
            2
        );

        // shift click the 1st record to untoggle 0-1
        await triggerEvents(
            target.querySelectorAll(".o_data_row .o_list_record_selector input")[0],
            null,
            [["keydown", { key: "Shift", shiftKey: true }], "click"]
        );
        assert.strictEqual(
            document.querySelectorAll(".o_data_row .o_list_record_selector input:checked").length,
            0
        );
    });

    QUnit.test("select record range with shift+space", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });

        // Go to the first checkbox and check it
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        await nextTick();
        let checkbox = target.querySelector(
            ".o_data_row:nth-child(1) .o_list_record_selector input"
        );
        assert.strictEqual(document.activeElement, checkbox);
        await click(checkbox);
        assert.ok(checkbox.checked);

        // Go to the fourth checkbox and shift+space
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        await nextTick();
        checkbox = target.querySelector(".o_data_row:nth-child(4) .o_list_record_selector input");
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(!checkbox.checked);
        await triggerEvents(document.activeElement, null, [
            ["keydown", { key: "Shift", shiftKey: true }],
            ["keydown", { key: " ", shiftKey: true }],
        ]);
        // focus is on the input and not in the td cell
        assert.strictEqual(document.activeElement.tagName, "INPUT");

        // Check that all checkbox is checked
        for (let i = 1; i < 5; i++) {
            checkbox = target.querySelector(
                `.o_data_row:nth-child(${i}) .o_list_record_selector input`
            );
            assert.ok(checkbox.checked);
        }
    });

    QUnit.test("expand range of checkbox with shift+arrow", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });

        // Go to the first checkbox and check it
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        await nextTick();
        let checkbox = target.querySelector(
            ".o_data_row:nth-child(1) .o_list_record_selector input"
        );
        assert.strictEqual(document.activeElement, checkbox);
        await click(checkbox);
        assert.ok(checkbox.checked);

        // expand the checkbox with arrowdown
        await triggerEvent(document.activeElement, null, "keydown", {
            key: "Shift",
            shiftKey: true,
        });
        triggerHotkey("shift+ArrowDown");
        triggerHotkey("shift+ArrowDown");
        triggerHotkey("shift+ArrowDown");
        triggerHotkey("shift+ArrowUp");
        await nextTick();
        await triggerEvent(document.activeElement, null, "keyup", {
            key: "Shift",
            shiftKey: false,
        });

        checkbox = target.querySelector(".o_data_row:nth-child(3) .o_list_record_selector input");
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(checkbox.checked);

        // Check that the three checkbox are checked
        for (let i = 1; i < 4; i++) {
            checkbox = target.querySelector(
                `.o_data_row:nth-child(${i}) .o_list_record_selector input`
            );
            assert.ok(checkbox.checked);
        }
    });

    QUnit.test(
        "multiple interactions to change the range of checked boxes",
        async function (assert) {
            for (let i = 0; i < 5; i++) {
                serverData.models.foo.records.push({ id: 5 + i, bar: true, foo: "foo" + i });
            }

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
            });

            await triggerHotkey("ArrowDown");
            const firstCheckbox = target.querySelector(
                ".o_data_row:nth-child(1) .o_list_record_selector input"
            );
            assert.notEqual(
                document.activeElement,
                firstCheckbox,
                "first checkbox should not be focused initially"
            );

            await triggerEvent(document.activeElement, null, "keydown", {
                key: "Shift",
                shiftKey: true,
            });
            await triggerHotkey("shift+ArrowDown");
            assert.strictEqual(
                document.activeElement,
                firstCheckbox,
                "first checkbox is now focused"
            );
            triggerHotkey("shift+ArrowDown");
            triggerHotkey("shift+ArrowDown");
            triggerHotkey("shift+ArrowDown");
            triggerHotkey("shift+ArrowUp");
            triggerHotkey("ArrowDown");
            triggerHotkey("ArrowDown");
            triggerHotkey("shift+ArrowDown");

            await click(
                target.querySelector(".o_data_row:nth-child(8) .o_list_record_selector .o-checkbox")
            );
            await triggerEvent(document.activeElement, null, "keydown", {
                key: "Shift",
                shiftKey: true,
            });
            await triggerHotkey("shift+ArrowDown");

            const expectedCheckedRows = [1, 2, 3, 5, 6, 8, 9];

            for (let i = 1; i < 10; i++) {
                if (expectedCheckedRows.includes(i)) {
                    assert.ok(
                        target.querySelector(
                            `.o_data_row:nth-child(${i}) .o_list_record_selector input`
                        ).checked,
                        `row ${i} checked`
                    );
                } else {
                    assert.notOk(
                        target.querySelector(
                            `.o_data_row:nth-child(${i}) .o_list_record_selector input`
                        ).checked,
                        `row ${i} unchecked`
                    );
                }
            }
        }
    );

    QUnit.test("list with class and style attributes", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: /* xml */ `
                <tree class="myClass" style="border: 1px solid red;">
                    <field name="foo"/>
                </tree>
            `,
        });
        assert.containsNone(
            target,
            ".o_view_controller[style*='border: 1px solid red;'], .o_view_controller [style*='border: 1px solid red;']",
            "style attribute should not be copied"
        );
        assert.containsOnce(
            target,
            ".o_view_controller.o_list_view.myClass",
            "class attribute should be passed to the view controller"
        );
        assert.containsOnce(
            target,
            ".myClass",
            "class attribute should ONLY be passed to the view controller"
        );
    });

    QUnit.test('list with create="0"', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree create="0"><field name="foo"/></tree>',
        });

        assert.containsNone(target, ".o_list_button_add", "should not have the 'Create' button");
    });

    QUnit.test(
        "searchbar in listview doesn't take focus after unselected all items",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `<tree><field name="foo"/></tree>`,
            });

            assert.equal(
                document.activeElement,
                target.querySelector(".o_searchview_input"),
                "The search input should be have the focus"
            );
            await click(target, `tbody .o_data_row:first-child input[type="checkbox"]`);
            await click(target, `tbody input[type="checkbox"]:checked`);
            assert.notEqual(
                document.activeElement,
                target.querySelector(".o_searchview_input"),
                "The search input shouldn't have the focus"
            );
        }
    );

    QUnit.test("basic list view and command palette", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
        });

        triggerHotkey("control+k");
        await nextTick();

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_command_hotkey")),
            [
                "NewALT + C",
                "ActionsALT + U",
                "Search...ALT + Q",
                "Toggle search panelALT + SHIFT + Q"
            ]
        );
    });

    QUnit.test('list with delete="0"', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            actionMenus: {},
            arch: '<tree delete="0"><field name="foo"/></tree>',
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, "tbody td.o_list_record_selector", 4, "should have 4 records");

        await click(target.querySelector("tbody td.o_list_record_selector input"));
        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus .dropdown-menu");
    });

    QUnit.test('editable list with edit="0"', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top" edit="0"><field name="foo"/></tree>',
            selectRecord: (resId, options) => {
                assert.step(`switch to form - resId: ${resId} activeIds: ${options.activeIds}`);
            },
        });

        assert.ok(
            target.querySelectorAll("tbody td.o_list_record_selector").length,
            "should have at least one record"
        );

        await click(target.querySelector(".o_data_cell"));
        assert.containsNone(target, "tbody tr.o_selected_row", "should not have editable row");

        assert.verifySteps(["switch to form - resId: 1 activeIds: 1,2,3,4"]);
    });

    QUnit.test("non-editable list with open_form_view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree open_form_view="1"><field name="foo"/></tree>',
        });
        assert.containsNone(
            target,
            "td.o_list_record_open_form_view",
            "button to open form view should not be present on non-editable list"
        );
    });

    QUnit.test("editable list with open_form_view not set", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });
        assert.containsNone(
            target,
            "td.o_list_record_open_form_view",
            "button to open form view should not be present"
        );
    });

    QUnit.test("editable list with open_form_view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top" open_form_view="1"><field name="foo"/></tree>',
            selectRecord: (resId, options) => {
                assert.step(`switch to form - resId: ${resId} activeIds: ${options.activeIds}`);
            },
        });
        assert.containsN(
            target,
            "td.o_list_record_open_form_view",
            4,
            "button to open form view should be present on each rows"
        );
        await click(target.querySelector("td.o_list_record_open_form_view"));
        assert.verifySteps(["switch to form - resId: 1 activeIds: 1,2,3,4"]);
    });

    QUnit.test(
        "export feature in list for users not in base.group_allow_export",
        async function (assert) {
            function hasGroup(group) {
                return group !== "base.group_allow_export";
            }
            serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                actionMenus: {},
                arch: '<tree><field name="foo"/></tree>',
            });

            assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
            assert.ok(
                $(target).find("tbody td.o_list_record_selector").length,
                "should have at least one record"
            );
            assert.containsNone(target, "div.o_control_panel .o_cp_buttons .o_list_export_xlsx");
            await click(target.querySelector("tbody td.o_list_record_selector input"));
            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
            await toggleActionMenu(target);
            assert.deepEqual(
                getNodesTextContent(
                    target.querySelectorAll(".o_control_panel .o_cp_action_menus .o_menu_item")
                ),
                ["Duplicate", "Delete"],
                "action menu should not contain the Export button"
            );
        }
    );

    QUnit.test("list with export button", async function (assert) {
        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            actionMenus: {},
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.ok(
            target.querySelectorAll("tbody td.o_list_record_selector").length,
            "should have at least one record"
        );

        await click(target.querySelector("tbody td.o_list_record_selector input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        await toggleActionMenu(target);
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".o_control_panel .o_cp_action_menus .o_menu_item")
            ),
            ["Export", "Duplicate", "Delete"],
            "action menu should have Export button"
        );
    });

    QUnit.test("Direct export button invisible", async function (assert) {
        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        await makeView({
            serverData,
            type: "list",
            resModel: "foo",
            arch: `<tree export_xlsx="0"><field name="foo"/></tree>`,
        });
        assert.containsNone(target, ".o_list_export_xlsx");
    });

    QUnit.test("list view with adjacent buttons", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
        });

        assert.containsN(
            target,
            "th",
            4,
            "adjacent buttons in the arch must be grouped in a single column"
        );
        assert.containsN(target.querySelector(".o_data_row:first-child"), "td.o_list_button", 2);
    });

    QUnit.test(
        "list view with adjacent buttons and invisible field and button",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" column_invisible="1"/>
                    <!--Here the column_invisible=1 is used to simulate a group on the case that the user
                        don't have the rights to see the button.-->
                    <button name="b" type="object" icon="fa-car" column_invisible="1"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
            });

            assert.containsN(
                target,
                "th",
                3,
                "adjacent buttons in the arch must be grouped in a single column"
            );
            assert.containsN(
                target,
                "tr:first-child button",
                4,
                "Only 4 buttons should be visible"
            );
            assert.containsN(
                target.querySelector(".o_data_row:first-child"),
                "td.o_list_button",
                2
            );
        }
    );

    QUnit.test(
        "list view with adjacent buttons and invisible field (modifier)",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" invisible="foo == 'blip'"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
            });

            assert.containsN(
                target,
                "th",
                4,
                "adjacent buttons in the arch must be grouped in a single column"
            );
            assert.containsN(
                target.querySelector(".o_data_row:first-child"),
                "td.o_list_button",
                2
            );
        }
    );

    QUnit.test("list view with adjacent buttons and optional field", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" optional="hide"/>
                    <button name="x" type="object" icon="fa-star"/>
                    <button name="y" type="object" icon="fa-refresh"/>
                    <button name="z" type="object" icon="fa-exclamation"/>
                </tree>`,
        });

        assert.containsN(
            target,
            "th",
            4,
            "adjacent buttons in the arch must be grouped in a single column"
        );
        assert.containsN(target.querySelector(".o_data_row:first-child"), "td.o_list_button", 2);
    });

    QUnit.test("list view with adjacent buttons with invisible modifier", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <button name="x" type="object" icon="fa-star" invisible="foo == 'blip'"/>
                    <button name="y" type="object" icon="fa-refresh" invisible="foo == 'yop'"/>
                    <button name="z" type="object" icon="fa-exclamation" invisible="foo == 'gnap'"/>
                </tree>`,
        });

        assert.containsN(
            target,
            "th",
            3,
            "adjacent buttons in the arch must be grouped in a single column"
        );
        assert.containsOnce(target.querySelector(".o_data_row"), "td.o_list_button");
        assert.strictEqual($(target).find(".o_field_cell").text(), "yopblipgnapblip");
        assert.containsN(target, "td button i.fa-star", 2);
        assert.containsN(target, "td button i.fa-refresh", 3);
        assert.containsN(target, "td button i.fa-exclamation", 3);
    });

    QUnit.test("list view with icon buttons", async function (assert) {
        serverData.models.foo.records.splice(1);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <button name="x" type="object" icon="fa-asterisk"/>
                    <button name="x" type="object" icon="fa-star" class="o_yeah"/>
                    <button name="x" type="object" icon="fa-refresh" string="Refresh" class="o_yeah"/>
                    <button name="x" type="object" icon="fa-exclamation" string="Danger" class="o_yeah btn-danger"/>
                </tree>`,
        });

        assert.containsOnce(target, "button.btn.btn-link i.fa.fa-asterisk");
        assert.containsOnce(target, "button.btn.btn-link.o_yeah i.fa.fa-star");
        assert.containsOnce(
            target,
            'button.btn.btn-link.o_yeah:contains("Refresh") i.fa.fa-refresh'
        );
        assert.containsOnce(
            target,
            'button.btn.btn-danger.o_yeah:contains("Danger") i.fa.fa-exclamation'
        );
        assert.containsNone(target, "button.btn.btn-link.btn-danger");
    });

    QUnit.test("list view with disabled button", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <button name="a" icon="fa-coffee"/>
                    <button name="b" icon="fa-car" disabled="disabled"/>
                </tree>`,
        });

        assert.ok(
            Array.from(target.querySelectorAll("button[name='a']")).every((btn) => !btn.disabled)
        );
        assert.ok(
            Array.from(target.querySelectorAll("button[name='b']")).every((btn) => btn.disabled)
        );
    });

    QUnit.test("list view: action button in controlPanel basic rendering", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <header>
                         <button name="x" type="object" class="plaf" string="plaf"/>
                         <button name="y" type="object" class="plouf" string="plouf" invisible="not context.get('bim')"/>
                    </header>
                    <field name="foo" />
                </tree>`,
        });
        let cpBreadcrumb = target.querySelector("div.o_control_panel_actions");
        assert.containsNone(cpBreadcrumb, 'button[name="x"]');
        assert.containsNone(cpBreadcrumb, ".o_list_selection_box");
        assert.containsNone(cpBreadcrumb, 'button[name="y"]');

        await click(
            target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        cpBreadcrumb = target.querySelector("div.o_control_panel_actions");
        assert.containsOnce(cpBreadcrumb, 'button[name="x"]');
        assert.hasClass(cpBreadcrumb.querySelector('button[name="x"]'), "btn btn-secondary plaf");
        assert.containsOnce(cpBreadcrumb, ".o_list_selection_box");
        assert.strictEqual(
            cpBreadcrumb.querySelector('button[name="x"]').previousElementSibling,
            cpBreadcrumb.querySelector(".o_list_selection_box")
        );
        assert.containsNone(cpBreadcrumb, 'button[name="y"]');

        await click(
            target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        cpBreadcrumb = target.querySelector("div.o_control_panel_actions");
        assert.containsNone(cpBreadcrumb, 'button[name="x"]');
        assert.containsNone(cpBreadcrumb, ".o_list_selection_box");
        assert.containsNone(cpBreadcrumb, 'button[name="y"]');
    });

    QUnit.test(
        "list view: action button in controlPanel with display='always'",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <header>
                        <button name="display" type="object" class="display" string="display" display="always"/>
                        <button name="default-selection" type="object" class="default-selection" string="default-selection"/>
                    </header>
                    <field name="foo" />
                </tree>`,
            });
            let cpButtons = getVisibleButtons(target);
            assert.deepEqual(
                [...cpButtons].map((button) => button.textContent.trim()),
                [
                    "New",
                    "display",
                    "", // cog dropdown
                    "", // search btn
                ]
            );

            await click(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
            );
            cpButtons = getVisibleButtons(target);
            assert.deepEqual(
                [...cpButtons].map((button) => button.textContent.trim()),
                ["New", "display", "default-selection"]
            );

            await click(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
            );
            cpButtons = getVisibleButtons(target);
            assert.deepEqual(
                [...cpButtons].map((button) => button.textContent.trim()),
                [
                    "New",
                    "display",
                    "", // cog dropdown
                    "", // search btn
                ]
            );
        }
    );

    QUnit.test(
        "list view: give a context dependent on the current context to a header button",
        async function (assert) {
            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <header>
                        <button name="toDo" type="object" string="toDo" display="always" context="{'b': context.get('a')}"/>
                    </header>
                    <field name="foo" />
                </tree>`,
                context: {
                    a: "yop",
                },
            });

            patchWithCleanup(list.env.services.action, {
                doActionButton: (action) => {
                    assert.step("doActionButton");
                    assert.deepEqual(action.buttonContext, {
                        active_domain: [],
                        active_ids: [],
                        active_model: "foo",
                        b: "yop",
                    });
                },
            });

            const cpButtons = getVisibleButtons(target);
            await click(cpButtons[1]);
            assert.verifySteps(["doActionButton"]);
        }
    );

    QUnit.test(
        "list view: action button executes action on click: buttons are disabled and re-enabled",
        async function (assert) {
            const executeActionDef = makeDeferred();
            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <header>
                             <button name="x" type="object" class="plaf" string="plaf"/>
                        </header>
                        <field name="foo" />
                    </tree>`,
            });
            patchWithCleanup(list.env.services.action, {
                doActionButton: async () => {
                    await executeActionDef;
                },
            });
            await click(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
            );
            const cpButtons = getVisibleButtons(target);
            assert.ok([...cpButtons].every((btn) => !btn.disabled));
            await click(cpButtons[1]);
            assert.ok([...cpButtons].every((btn) => btn.disabled));

            executeActionDef.resolve();
            await nextTick();
            assert.ok([...cpButtons].every((btn) => !btn.disabled));
        }
    );

    QUnit.test(
        "list view: buttons handler is called once on double click",
        async function (assert) {
            const executeActionDef = makeDeferred();
            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <field name="foo" />
                        <button name="x" type="object" class="do_something" string="Do Something"/>
                    </tree>`,
            });
            patchWithCleanup(list.env.services.action, {
                doActionButton: async () => {
                    assert.step("execute_action");
                    await executeActionDef;
                },
            });
            const button = target.querySelector("tbody .o_list_button > button");
            await click(button);
            assert.ok(button.matches("[disabled]"));

            executeActionDef.resolve();
            await nextTick();
            assert.verifySteps(["execute_action"]);
        }
    );

    QUnit.test(
        "list view: click on an action button saves the record before executing the action",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo" />
                        <button name="toDo" type="object" class="do_something" string="Do Something"/>
                    </tree>`,
                mockRPC: async (route, args) => {
                    assert.step(args.method);
                    if (route === "/web/dataset/call_button") {
                        return true;
                    }
                },
            });

            await click(target.querySelector(".o_data_cell"));
            await editInput(target, ".o_data_row [name='foo'] input", "plop");
            assert.strictEqual(
                target.querySelector(".o_data_row [name='foo'] input").value,
                "plop"
            );

            await click(target.querySelector(".o_data_row button"));
            assert.strictEqual(
                target.querySelector(".o_data_row [name='foo']").textContent,
                "plop"
            );

            assert.verifySteps([
                "get_views",
                "web_search_read",
                "web_save",
                "toDo",
                "web_search_read",
            ]);
        }
    );

    QUnit.test(
        "list view: action button executes action on click: correct parameters",
        async function (assert) {
            assert.expect(6);

            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <header>
                             <button name="x" type="object" class="plaf" string="plaf" context="{'plouf': 'plif'}"/>
                        </header>
                        <field name="foo" />
                    </tree>`,
                context: {
                    paf: "pif",
                },
            });
            patchWithCleanup(list.env.services.action, {
                doActionButton: async (params) => {
                    const { buttonContext, context, name, resModel, resIds, type } = params;
                    // Action's own properties
                    assert.strictEqual(name, "x");
                    assert.strictEqual(type, "object");

                    // The action's execution context
                    assert.deepEqual(buttonContext, {
                        active_domain: [],
                        // active_id: 1, //FGE TODO
                        active_ids: [1],
                        active_model: "foo",
                        plouf: "plif",
                    });

                    assert.strictEqual(resModel, "foo");
                    assert.deepEqual([...resIds], [1]);
                    assert.deepEqual(context, {
                        lang: "en",
                        paf: "pif",
                        tz: "taht",
                        uid: 7,
                    });
                },
            });
            await click(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
            );
            const cpButtons = getVisibleButtons(target);
            await click(cpButtons[1]);
        }
    );

    QUnit.test(
        "list view: action button executes action on click with domain selected: correct parameters",
        async function (assert) {
            assert.expect(12);

            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree limit="1">
                        <header>
                             <button name="x" type="object" class="plaf" string="plaf"/>
                        </header>
                        <field name="foo" />
                    </tree>`,
                mockRPC(route, args) {
                    if (args.method === "search") {
                        assert.step("search");
                        assert.strictEqual(args.model, "foo");
                        assert.deepEqual(args.args, [[]]); // empty domain since no domain in searchView
                    }
                },
            });
            patchWithCleanup(list.env.services.action, {
                doActionButton: async (params) => {
                    const { buttonContext, context, name, resModel, resIds, type } = params;
                    assert.step("execute_action");
                    // Action's own properties
                    assert.strictEqual(name, "x");
                    assert.strictEqual(type, "object");

                    // The action's execution context
                    assert.deepEqual(buttonContext, {
                        active_domain: [],
                        // active_id: 1, // FGE TODO
                        active_ids: [1, 2, 3, 4],
                        active_model: "foo",
                    });

                    assert.deepEqual(context, {
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                    assert.strictEqual(resModel, "foo");
                    assert.deepEqual([...resIds], [1, 2, 3, 4]);
                },
            });
            await click(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
            );

            await click(target.querySelector(".o_list_select_domain"));
            assert.verifySteps([]);

            await click(target.querySelector('button[name="x"]'));
            assert.verifySteps(["search", "execute_action"]);
        }
    );

    QUnit.test("column names (noLabel, label, string and default)", async function (assert) {
        const fieldRegistry = registry.category("fields");
        const charField = fieldRegistry.get("char");

        class NoLabelCharField extends charField.component {}
        fieldRegistry.add("nolabel_char", {
            ...charField,
            component: NoLabelCharField,
            noLabel: true,
        });

        class LabelCharField extends charField.component {}
        fieldRegistry.add("label_char", {
            ...charField,
            component: LabelCharField,
            label: "Some static label",
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="display_name" widget="nolabel_char" optional="show"/>
                    <field name="foo" widget="label_char" optional="show"/>
                    <field name="int_field" string="My custom label" optional="show"/>
                    <field name="text" optional="show"/>
                </tree>`,
        });

        const columnLabels = [...target.querySelectorAll("thead th")].map((th) => th.textContent);
        assert.deepEqual(columnLabels, [
            "",
            "",
            "Some static label",
            "My custom label",
            "text field",
            "",
        ]);

        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        const optionalColumnLabels = [
            ...target.querySelectorAll(".o_optional_columns_dropdown .dropdown-item"),
        ].map((item) => item.textContent.trim());
        assert.deepEqual(optionalColumnLabels, [
            "Display Name",
            "Some static label",
            "My custom label",
            "text field",
        ]);
    });

    QUnit.test("simple editable rendering", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, "th", 3, "should have 2 th");
        assert.containsN(target, "th", 3, "should have 3 th");
        assert.containsN(target, ".o_list_record_selector input:enabled", 5);
        assert.containsOnce(target, "td:contains(yop)", "should contain yop");

        assert.containsN(
            target,
            ".o_list_button_add",
            2,
            "Should have 2 add button (small and xl screens)"
        );
        assert.containsNone(target, ".o_list_button_save");
        assert.containsNone(target, ".o_list_button_discard");

        await click(target.querySelector(".o_field_cell"));

        assert.containsNone(target, ".o_list_button_add");
        assert.containsN(
            target,
            ".o_list_button_save",
            2,
            "Should have 2 save button (small and xl screens)"
        );
        assert.containsN(
            target,
            ".o_list_button_discard",
            2,
            "Should have 2 discard button (small and xl screens)"
        );
        assert.containsNone(target, ".o_list_record_selector input:enabled");

        await click($(".o_list_button_save:visible").get(0));

        assert.containsN(
            target,
            ".o_list_button_add",
            2,
            "Should have 2 add button (small and xl screens)"
        );
        assert.containsNone(target, ".o_list_button_save");
        assert.containsNone(target, ".o_list_button_discard");
        assert.containsN(target, ".o_list_record_selector input:enabled", 5);
    });

    QUnit.test("editable rendering with handle and no data", async function (assert) {
        serverData.models.foo.records = [];
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="int_field" widget="handle"/>
                    <field name="currency_id"/>
                    <field name="m2o"/>
                </tree>`,
        });
        assert.containsN(target, "thead th", 4, "there should be 4 th");
        assert.hasClass(target.querySelectorAll("thead th")[0], "o_list_record_selector");
        assert.hasClass(target.querySelectorAll("thead th")[1], "o_handle_cell");
        assert.strictEqual(
            target.querySelectorAll("thead th")[1].innerText,
            "",
            "the handle field shouldn't have a header description"
        );
        assert.strictEqual(
            target.querySelectorAll("thead th")[2].getAttribute("style"),
            "width: 50%;"
        );
        assert.strictEqual(
            target.querySelectorAll("thead th")[3].getAttribute("style"),
            "width: 50%;"
        );
    });

    QUnit.test("invisible columns are not displayed", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar" column_invisible="1"/>
                </tree>`,
        });

        // 1 th for checkbox, 1 for 1 visible column
        assert.containsN(target, "th", 2, "should have 2 th");
    });

    QUnit.test(
        "invisible column based on the context are correctly displayed",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <field name="date" column_invisible="True"/>
                    <field name="foo" column_invisible="context.get('notInvisible')"/>
                    <field name="bar" column_invisible="context.get('invisible')"/>
                </tree>`,
                context: {
                    invisible: true,
                    notInvisible: false,
                },
            });

            // 1 th for checkbox, 1 for 1 visible column (foo)
            assert.containsN(target, "th", 2, "should have 2 th");
            assert.strictEqual(target.querySelectorAll("th")[1].dataset.name, "foo");
        }
    );

    QUnit.test(
        "invisible column based on the context are correctly displayed in o2m",
        async function (assert) {
            serverData.models.foo.fields.foo_o2m = {
                string: "Foo O2M",
                type: "one2many",
                relation: "foo",
            };
            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <sheet>
                            <field name="foo_o2m">
                                <tree>
                                    <field name="foo" column_invisible="context.get('notInvisible')"/>
                                    <field name="bar" column_invisible="context.get('invisible')"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                context: {
                    invisible: true,
                    notInvisible: false,
                },
            });

            // 1 for 1 visible column (foo), 1 th for delete button
            assert.containsN(target, "th", 2, "should have 2 th");
            assert.strictEqual(target.querySelectorAll("th")[0].dataset.name, "foo");
        }
    );

    QUnit.test(
        "invisible column based on the parent are correctly displayed in o2m",
        async function (assert) {
            serverData.models.foo.fields.foo_o2m = {
                string: "Foo O2M",
                type: "one2many",
                relation: "foo",
            };
            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <sheet>
                            <field name="int_field"/>
                            <field name="m2m" invisible="True"/>
                            <field name="properties" invisible="True"/>
                            <field name="foo_o2m">
                                <tree>
                                    <field name="date" column_invisible="True"/>
                                    <field name="foo" column_invisible="parent.int_field == 3"/>
                                    <field name="bar" column_invisible="parent.int_field == 10"/>
                                    <field name="qux" column_invisible="parent.m2m"/>
                                    <field name="amount" column_invisible="parent.properties"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
            });

            // 1 for 2 visible column (foo, properties), 1 th for delete button
            assert.containsN(target, "th", 3, "should have 3 th");
            assert.strictEqual(target.querySelectorAll("th")[0].dataset.name, "foo");
            assert.strictEqual(target.querySelectorAll("th")[1].dataset.name, "amount");
        }
    );

    QUnit.test("save a record with an invisible required field", async function (assert) {
        serverData.models.foo.fields.foo.required = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo" column_invisible="1"/>
                    <field name="int_field"/>
                </tree>`,
            mockRPC(_, { args, method }) {
                assert.step(method);
                if (method === "web_save") {
                    assert.deepEqual(args[1], { int_field: 1, foo: false });
                }
            },
        });
        assert.containsN(target, ".o_data_row", 4);
        assert.verifySteps(["get_views", "web_search_read"]);

        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, "[name='int_field'] input", 1);
        await click(target, ".o_list_view");
        assert.containsN(target, ".o_data_row", 5);
        assert.strictEqual(target.querySelector(".o_data_row [name='int_field']").textContent, "1");
        assert.verifySteps(["onchange", "web_save"]);
    });

    QUnit.test("multi_edit: edit a required field with an invalid value", async function (assert) {
        serverData.models.foo.fields.foo.required = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        assert.containsN(target, ".o_data_row", 4);
        assert.verifySteps(["get_views", "web_search_read"]);

        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[0].querySelector(".o_data_cell"));
        await editInput(target, "[name='foo'] input", "");
        await click(target, ".o_list_view");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal .btn").textContent, "Ok");

        await click(target.querySelector(".modal .btn"));
        assert.strictEqual(
            target.querySelector(".o_data_row .o_data_cell[name='foo']").textContent,
            "yop"
        );
        assert.hasClass(target.querySelector(".o_data_row"), "o_data_row_selected");

        assert.verifySteps([]);
    });

    QUnit.test(
        "multi_edit: clicking on a readonly field switches the focus to the next editable field",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree multi_edit="1">
                    <field name="int_field" readonly="1"/>
                    <field name="foo" />
                </tree>`,
            });

            const firstRow = target.querySelector(".o_data_row");
            await click(firstRow, ".o_list_record_selector input");

            let intField = firstRow.querySelector("[name='int_field']");
            intField.focus();
            await click(intField);
            assert.strictEqual(
                document.activeElement.closest(".o_field_widget").getAttribute("name"),
                "foo"
            );

            intField = firstRow.querySelector("[name='int_field']");
            intField.focus();
            await click(intField);
            assert.strictEqual(
                document.activeElement.closest(".o_field_widget").getAttribute("name"),
                "foo"
            );
        }
    );

    QUnit.test("save a record with an required field computed by another", async function (assert) {
        serverData.models.foo.onchanges = {
            foo(record) {
                if (record.foo) {
                    record.text = "plop";
                }
            },
        };
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="text" required="1"/>
                </tree>`,
        });
        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone(target, ".o_selected_row");

        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, "[name='int_field'] input", 1);
        await click(target, ".o_list_view");
        assert.containsN(target, ".o_data_row", 5);
        assert.containsOnce(target, ".o_field_invalid");
        assert.containsOnce(target, ".o_selected_row");

        await editInput(target, "[name='foo'] input", "hello");
        assert.containsNone(target, ".o_field_invalid");
        assert.containsOnce(target, ".o_selected_row");

        await click(target, ".o_list_view");
        assert.containsN(target, ".o_data_row", 5);
        assert.containsNone(target, ".o_selected_row");
    });

    QUnit.test("boolean field has no title (data-tooltip)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="bar"/></tree>',
        });
        assert.strictEqual(target.querySelector(".o_data_cell").getAttribute("data-tooltip"), null);
    });

    QUnit.test("field with nolabel has no title", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo" nolabel="1"/></tree>',
        });
        assert.strictEqual($(target).find("thead tr:first th:eq(1)").text(), "");
    });

    QUnit.test("field titles are not escaped", async function (assert) {
        serverData.models.foo.records[0].foo = "<div>Hello</div>";

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.strictEqual(
            $(target).find("tbody tr:first .o_data_cell").text(),
            "<div>Hello</div>"
        );
        assert.strictEqual(
            $(target).find("tbody tr:first .o_data_cell").attr("data-tooltip"),
            "<div>Hello</div>"
        );
    });

    QUnit.test("record-depending invisible lines are correctly aligned", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar" invisible="id == 1"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsN(target, ".o_data_row td", 16); // 4 cells per row
        assert.strictEqual(target.querySelectorAll(".o_data_row td")[2].innerHTML, "");
    });

    QUnit.test("invisble fields must not have a tooltip", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo" invisible="id == 1"/>
                </tree>`,
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsN(target, ".o_data_row td[data-tooltip]", 3);
    });

    QUnit.test(
        "do not perform extra RPC to read invisible many2one fields",
        async function (assert) {
            serverData.models.foo.fields.m2o.default = 2;

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="foo"/>
                        <field name="m2o" column_invisible="1"/>
                    </tree>`,
                mockRPC(route) {
                    assert.step(route.split("/").pop());
                },
            });

            await click($(".o_list_button_add:visible").get(0));
            assert.verifySteps(
                ["get_views", "web_search_read", "onchange"],
                "no nameget should be done"
            );
        }
    );

    QUnit.test("editable list datepicker destroy widget (edition)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="date"/>
                </tree>`,
        });

        assert.containsN(target, ".o_data_row", 4);

        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");

        await click(target, ".o_field_date input");
        assert.containsOnce(target, ".o_datetime_picker");

        triggerHotkey("Escape");
        await nextTick();

        assert.containsNone(target, ".o_selected_row");
        assert.containsN(target, ".o_data_row", 4);
    });

    QUnit.test("editable list datepicker destroy widget (new line)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="top"><field name="date"/></tree>`,
        });

        assert.containsN(target, ".o_data_row", 4, "There should be 4 rows");

        await click($(".o_list_button_add:visible").get(0));
        assert.containsOnce(target, ".o_selected_row");

        await click(target, ".o_field_date input");
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");
        await triggerEvent(document.activeElement, null, "keydown", { key: "Escape" });

        assert.containsNone(target, ".o_selected_row", "the row is no longer in edition");
        assert.containsN(target, ".o_data_row", 4, "There should still be 4 rows");
    });

    QUnit.test("at least 4 rows are rendered, even if less data", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="bar"/></tree>',
            domain: [["bar", "=", true]],
        });

        assert.containsN(target, "tbody tr", 4, "should have 4 rows");
    });

    QUnit.test(
        'discard a new record in editable="top" list with less than 4 records',
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="bar"/></tree>',
                domain: [["bar", "=", true]],
            });
            assert.containsN(target, ".o_data_row", 3);
            assert.containsN(target, "tbody tr", 4);

            await click($(".o_list_button_add:visible").get(0));
            assert.containsN(target, ".o_data_row", 4);
            assert.hasClass(target.querySelector("tbody tr"), "o_selected_row");

            await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));
            assert.containsN(target, ".o_data_row", 3);
            assert.containsN(target, "tbody tr", 4);
            assert.hasClass(target.querySelector("tbody tr"), "o_data_row");
        }
    );

    QUnit.test("basic grouped list rendering", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
        });

        assert.strictEqual($(target).find("th:contains(Foo)").length, 1, "should contain Foo");
        assert.strictEqual($(target).find("th:contains(Bar)").length, 1, "should contain Bar");
        assert.containsN(target, "tr.o_group_header", 2, "should have 2 .o_group_header");
        assert.containsN(target, "th.o_group_name", 2, "should have 2 .o_group_name");
    });

    QUnit.test('basic grouped list rendering with widget="handle" col', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="int_field" widget="handle"/>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            groupBy: ["bar"],
        });

        assert.containsN(target, "thead th", 3); // record selector + Foo + Bar
        assert.containsOnce(target, "thead th.o_list_record_selector");
        assert.containsOnce(target, "thead th[data-name=foo]");
        assert.containsOnce(target, "thead th[data-name=bar]");
        assert.containsNone(target, "thead th[data-name=int_field]");
        assert.containsN(target, "tr.o_group_header", 2);
        assert.containsN(target, "th.o_group_name", 2);
        assert.containsN(target.querySelector(".o_group_header"), "th", 2); // group name + colspan 2
        assert.containsNone(target.querySelector(".o_group_header"), ".o_list_number");
    });

    QUnit.test(
        "basic grouped list rendering with a date field between two fields with a group_operator",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <field name="int_field"/>
                    <field name="date"/>
                    <field name="int_field"/>
                </tree>`,
                groupBy: ["bar"],
            });

            assert.containsN(target, "thead th", 4); // record selector + Foo + Int + Date + Int
            assert.containsOnce(target, "thead th.o_list_record_selector");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll("thead th")), [
                "",
                "int_field",
                "Some Date",
                "int_field",
            ]);
            assert.containsN(target, "tr.o_group_header", 2);
            assert.containsN(target, "th.o_group_name", 2);
            assert.deepEqual(
                getNodesTextContent(target.querySelector(".o_group_header").querySelectorAll("td")),
                ["-4", "", "-4"]
            );
        }
    );

    QUnit.test("basic grouped list rendering 1 col without selector", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
            groupBy: ["bar"],
            allowSelectors: false,
        });

        assert.containsOnce(target.querySelector(".o_group_header"), "th");
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "1");
    });

    QUnit.test("basic grouped list rendering 1 col with selector", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
            groupBy: ["bar"],
        });

        assert.containsOnce(target.querySelector(".o_group_header"), "th");
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "2");
    });

    QUnit.test("basic grouped list rendering 2 cols without selector", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
            allowSelectors: false,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "1");
    });

    QUnit.test("basic grouped list rendering 3 cols without selector", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree ><field name="foo"/><field name="bar"/><field name="text"/></tree>',
            groupBy: ["bar"],
            allowSelectors: false,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "2");
    });

    QUnit.test("basic grouped list rendering 2 col with selector", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
            allowSelectors: true,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "2");
    });

    QUnit.test("basic grouped list rendering 3 cols with selector", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/><field name="text"/></tree>',
            groupBy: ["bar"],
            allowSelectors: true,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "3");
    });

    QUnit.test(
        "basic grouped list rendering 7 cols with aggregates and selector",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <field name="datetime"/>
                        <field name="foo"/>
                        <field name="int_field" sum="Sum1"/>
                        <field name="bar"/>
                        <field name="qux" sum="Sum2"/>
                        <field name="date"/>
                        <field name="text"/>
                    </tree>`,
                groupBy: ["bar"],
            });

            assert.containsN(target.querySelector(".o_group_header"), "th,td", 5);
            assert.strictEqual(
                target.querySelector(".o_group_header th").getAttribute("colspan"),
                "3"
            );
            assert.containsN(
                target.querySelector(".o_group_header"),
                "td",
                3,
                "there should be 3 tds (aggregates + fields in between)"
            );
            assert.strictEqual(
                target.querySelector(".o_group_header th:last-child").getAttribute("colspan"),
                "2",
                "header last cell should span on the two last fields (to give space for the pager) (colspan 2)"
            );
        }
    );

    QUnit.test(
        "basic grouped list rendering 7 cols with aggregates, selector and optional",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <field name="datetime"/>
                        <field name="foo"/>
                        <field name="int_field" sum="Sum1"/>
                        <field name="bar"/>
                        <field name="qux" sum="Sum2"/>
                        <field name="date"/>
                        <field name="text" optional="show"/>
                    </tree>`,
                groupBy: ["bar"],
            });

            assert.containsN(target.querySelector(".o_group_header"), "th,td", 5);
            assert.strictEqual(
                target.querySelector(".o_group_header th").getAttribute("colspan"),
                "3"
            );
            assert.containsN(
                target.querySelector(".o_group_header"),
                "td",
                3,
                "there should be 3 tds (aggregates + fields in between)"
            );
            assert.strictEqual(
                target.querySelector(".o_group_header th:last-child").getAttribute("colspan"),
                "3",
                "header last cell should span on the two last fields (to give space for the pager) (colspan 2)"
            );
        }
    );

    QUnit.test("group a list view with the aggregable field 'value'", async function (assert) {
        serverData.models.foo.fields.value = {
            string: "Value",
            type: "integer",
            group_operator: "sum",
        };
        for (const record of serverData.models.foo.records) {
            record.value = 1;
        }
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                    <tree>
                        <field name="bar"/>
                        <field name="value" sum="Sum1"/>
                    </tree>`,
            groupBy: ["bar"],
        });
        assert.containsN(target, ".o_group_header", 2);
        assert.deepEqual(
            [...target.querySelectorAll(".o_group_header")].map((el) => el.textContent),
            ["No (1) 1", "Yes (3) 3"]
        );
    });

    QUnit.test("basic grouped list rendering with groupby m2m field", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            groupBy: ["m2m"],
        });

        assert.containsN(target, ".o_group_header", 4, "should contain 4 open groups");
        assert.containsNone(target, ".o_group_open", "no group is open");
        assert.deepEqual(
            [...target.querySelectorAll(".o_group_header .o_group_name")].map((el) => el.innerText),
            ["None (1)", "Value 1 (3)", "Value 2 (2)", "Value 3 (1)"],
            "should have those group headers"
        );

        // Open all groups
        await click(target.querySelectorAll(".o_group_name")[0]);
        await click(target.querySelectorAll(".o_group_name")[1]);
        await click(target.querySelectorAll(".o_group_name")[2]);
        await click(target.querySelectorAll(".o_group_name")[3]);
        assert.containsN(target, ".o_group_open", 4, "all groups are open");

        const rows = target.querySelectorAll(".o_list_view tbody > tr");
        assert.deepEqual(
            [...rows].map((el) => el.innerText.replace(/\s/g, "")),
            [
                "None(1)",
                "gnap",
                "Value1(3)",
                "yopValue1Value2",
                "blipValue1Value2Value3",
                "blipValue1",
                "Value2(2)",
                "yopValue1Value2",
                "blipValue1Value2Value3",
                "Value3(1)",
                "blipValue1Value2Value3",
            ],
            "should have these row contents"
        );
    });

    QUnit.test("grouped list rendering with groupby m2o and m2m field", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="m2o"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            groupBy: ["m2o", "m2m"],
        });

        let rows = target.querySelectorAll("tbody > tr");
        assert.deepEqual(
            [...rows].map((el) => el.innerText.replace(/\s/g, "")),

            ["Value1(3)", "Value2(1)"],
            "should have these row contents"
        );

        await click(target.querySelector("th.o_group_name"));

        rows = target.querySelectorAll("tbody > tr");
        assert.deepEqual(
            [...rows].map((el) => el.innerText.replace(/\s/g, "")),
            ["Value1(3)", "None(1)", "Value1(2)", "Value2(1)", "Value2(1)"],
            "should have these row contents"
        );

        await click(target.querySelectorAll("tbody th.o_group_name")[4]);
        rows = target.querySelectorAll(".o_list_view tbody > tr");

        assert.deepEqual(
            [...rows].map((el) => el.innerText.replace(/\s/g, "")),
            [
                "Value1(3)",
                "None(1)",
                "Value1(2)",
                "Value2(1)",
                "Value2(1)",
                "Value1(1)",
                "Value2(1)",
                "Value3(1)",
            ],
            "should have these row contents"
        );
    });

    QUnit.test("list view with multiple groupbys", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar", "foo"],
            noContentHelp: "<p>should not be displayed</p>",
        });

        assert.containsNone(target, ".o_view_nocontent");
        assert.containsN(target, ".o_group_has_content", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_group_has_content")), [
            "No (1) ",
            "Yes (3) ",
        ]);
    });

    QUnit.test("deletion of record is disabled when groupby m2m field", async function (assert) {
        serviceRegistry.add(
            "user",
            makeFakeUserService(() => false),
            { force: true }
        );

        serverData.models.foo.fields.m2m.store = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            actionMenus: {},
        });
        await groupByMenu(target, "m2m");

        await click(target.querySelector(".o_group_header:first-child")); // open first group
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsNone(
            target,
            "div.o_control_panel .o_cp_action_menus .dropdown",
            "should not have dropdown as delete item is not there"
        );

        // unselect group by m2m (need to unselect record first)
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        await click(target, ".o_searchview .o_facet_remove");

        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus .dropdown");
        await click(target, "div.o_control_panel .o_cp_action_menus .dropdown button");
        assert.deepEqual(
            [...target.querySelectorAll(".o_cp_action_menus .o_menu_item")].map(
                (el) => el.innerText
            ),
            ["Duplicate", "Delete"]
        );
    });

    QUnit.test("add record in list grouped by m2m", async function (assert) {
        assert.expect(7);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            groupBy: ["m2m"],
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(args.kwargs.context.default_m2m, [1]);
                }
            },
        });

        assert.containsN(target, ".o_group_header", 4);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_group_header")), [
            "None (1) ",
            "Value 1 (3) ",
            "Value 2 (2) ",
            "Value 3 (1) ",
        ]);

        await click(target.querySelectorAll(".o_group_header")[1]);
        assert.containsN(target, ".o_data_row", 3);

        await click(target, ".o_group_field_row_add a");
        assert.containsOnce(target, ".o_selected_row");
        assert.containsOnce(target, ".o_selected_row .o_field_tags .o_tag");
        assert.strictEqual(
            target.querySelector(".o_selected_row .o_field_tags .o_tag").innerText,
            "Value 1"
        );
    });

    QUnit.test(
        "editing a record should change same record in other groups when grouped by m2m field",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="m2m" widget="many2many_tags"/>
                    </tree>`,
                groupBy: ["m2m"],
            });
            await click(target.querySelectorAll(".o_group_header")[1]); // open Value 1 group
            await click(target.querySelectorAll(".o_group_header")[2]); // open Value 2 group
            const rows = target.querySelectorAll(".o_data_row");
            assert.strictEqual(rows[0].querySelector(".o_list_char").textContent, "yop");
            assert.strictEqual(rows[3].querySelector(".o_list_char").textContent, "yop");

            await click(target.querySelector(".o_data_row .o_list_record_selector input"));
            await click(target.querySelector(".o_data_row .o_data_cell"));
            await editInput(rows[0], ".o_data_row .o_list_char input", "xyz");
            await click(target, ".o_list_view");
            assert.strictEqual(rows[0].querySelector(".o_list_char").textContent, "xyz");
            assert.strictEqual(rows[3].querySelector(".o_list_char").textContent, "xyz");
        }
    );

    QUnit.test(
        "change a record field in readonly should change same record in other groups when grouped by m2m field",
        async function (assert) {
            assert.expect(6);

            serverData.models.foo.fields.priority = {
                string: "Priority",
                type: "selection",
                selection: [
                    [0, "Not Prioritary"],
                    [1, "Prioritary"],
                ],
                default: 0,
            };

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="priority" widget="priority"/>
                        <field name="m2m" widget="many2many_tags"/>
                    </tree>`,
                groupBy: ["m2m"],
                domain: [["m2o", "=", 1]],
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.deepEqual(args.args[0], [1], "should write on the correct record");
                        assert.deepEqual(
                            args.args[1],
                            {
                                priority: 1,
                            },
                            "should write these changes"
                        );
                    }
                },
            });

            await click(target.querySelectorAll(".o_group_header")[1]); // open Value 1 group
            await click(target.querySelectorAll(".o_group_header")[2]); // open Value 2 group
            const rows = target.querySelectorAll(".o_data_row");
            assert.strictEqual(rows[0].querySelector(".o_list_char").textContent, "yop");
            assert.strictEqual(rows[2].querySelector(".o_list_char").textContent, "yop");
            assert.containsNone(
                target,
                ".o_priority_star.fa-star",
                "should not have any starred records"
            );

            await click(rows[0].querySelector(".o_priority_star"));
            assert.containsN(
                target,
                ".o_priority_star.fa-star",
                2,
                "both 'yop' records should have been starred"
            );
        }
    );

    QUnit.test("ordered target, sort attribute in context", async function (assert) {
        serverData.models.foo.fields.foo.sortable = true;
        serverData.models.foo.fields.date.sortable = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="date"/></tree>',
            mockRPC: (route, args) => {
                if (args.method === "create_or_replace") {
                    const favorite = args.args[0];
                    assert.step(favorite.sort);
                    return 7;
                }
            },
        });

        // Descending order on Foo
        await click(target, "th.o_column_sortable[data-name=foo]");
        await click(target, "th.o_column_sortable[data-name=foo]");

        // Ascending order on Date
        await click(target, "th.o_column_sortable[data-name=date]");

        await toggleSearchBarMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "My favorite");
        await saveFavorite(target);

        assert.verifySteps(['["date","foo desc"]']);
    });

    QUnit.test("Loading a filter with a sort attribute", async function (assert) {
        assert.expect(2);

        serverData.models.foo.fields.foo.sortable = true;
        serverData.models.foo.fields.date.sortable = true;

        let searchReads = 0;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="date"/>
                </tree>`,
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    if (searchReads === 0) {
                        assert.strictEqual(
                            args.kwargs.order,
                            "date ASC, foo DESC",
                            "The sort attribute of the filter should be used by the initial search_read"
                        );
                    } else if (searchReads === 1) {
                        assert.strictEqual(
                            args.kwargs.order,
                            "date DESC, foo ASC",
                            "The sort attribute of the filter should be used by the next search_read"
                        );
                    }
                    searchReads += 1;
                }
            },
            irFilters: [
                {
                    context: "{}",
                    domain: "[]",
                    id: 7,
                    is_default: true,
                    name: "My favorite",
                    sort: '["date asc", "foo desc"]',
                    user_id: [2, "Mitchell Admin"],
                },
                {
                    context: "{}",
                    domain: "[]",
                    id: 8,
                    is_default: false,
                    name: "My second favorite",
                    sort: '["date desc", "foo asc"]',
                    user_id: [2, "Mitchell Admin"],
                },
            ],
        });

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "My second favorite");
    });

    QUnit.test("many2one field rendering", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="m2o"/></tree>',
        });

        assert.ok(
            $(target).find("td:contains(Value 1)").length,
            "should have the display_name of the many2one"
        );
    });

    QUnit.test("many2one field rendering with many2one widget", async function (assert) {
        serverData.models.bar.records[0].display_name = false;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="m2o" widget="many2one"/></tree>',
        });

        assert.ok(
            $(target).find("td:contains(Unnamed)").length,
            "should have a Unnamed as fallback of many2one display_name"
        );
    });

    QUnit.test("many2one field rendering when display_name is falsy", async function (assert) {
        serverData.models.bar.records[0].display_name = false;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="m2o"/></tree>',
            mockRPC(route) {
                assert.step(route);
            },
        });

        assert.ok(
            $(target).find("td:contains(Unnamed)").length,
            "should have a Unnamed as fallback of many2one display_name"
        );
        assert.verifySteps([
            "/web/dataset/call_kw/foo/get_views",
            "/web/dataset/call_kw/foo/web_search_read",
        ]);
    });

    QUnit.test("grouped list view, with 1 open group", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
            groupBy: ["foo"],
        });

        assert.containsN(target, "tr.o_group_header", 3);
        assert.containsNone(target, "tr.o_data_row");

        await click(target.querySelector("th.o_group_name"));
        await nextTick();
        assert.containsN(target, "tr.o_group_header", 3);
        assert.containsN(target, "tr.o_data_row", 2);
        assert.containsOnce(target, "td:contains(9)", "should contain 9");
        assert.containsOnce(target, "td:contains(-4)", "should contain -4");
        assert.containsOnce(target, "td:contains(10)", "should contain 10"); // FIXME: missing aggregates
        assert.containsOnce(
            target,
            "tr.o_group_header td:contains(10)",
            "but 10 should be in a header"
        );
    });

    QUnit.test("opening records when clicking on record", async function (assert) {
        assert.expect(6);

        const listView = registry.category("views").get("list");
        class CustomListController extends listView.Controller {
            openRecord(record) {
                assert.step("openRecord");
                assert.strictEqual(record.resId, 2);
            }
        }
        registry.category("views").add("custom_list", {
            ...listView,
            Controller: CustomListController,
        });

        serverData.models.foo.fields.foo.sortable = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree js_class="custom_list"><field name="foo"/></tree>',
        });

        await click(target.querySelector("tr:nth-child(2) td:not(.o_list_record_selector)"));
        await groupByMenu(target, "foo");

        assert.containsN(target, "tr.o_group_header", 3, "list should be grouped");
        await click(target.querySelector("th.o_group_name"));

        await click(
            target.querySelector("tr:not(.o_group_header) td:not(.o_list_record_selector)")
        );
        assert.verifySteps(["openRecord", "openRecord"]);
    });

    QUnit.test(
        "execute an action before and after each valid save in a list view",
        async function (assert) {
            const listView = registry.category("views").get("list");
            class CustomListController extends listView.Controller {
                async onRecordSaved(record) {
                    assert.step(`onRecordSaved ${record.resId}`);
                }

                async onWillSaveRecord(record) {
                    assert.step(`onWillSaveRecord ${record.resId}`);
                }
            }
            registry.category("views").add(
                "custom_list",
                {
                    ...listView,
                    Controller: CustomListController,
                },
                { force: true }
            );

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree js_class="custom_list" editable="top"><field name="foo" required="1"/></tree>',
                mockRPC: async (route, args) => {
                    if (args.method === "web_save") {
                        assert.step(`web_save ${args.args[0]}`);
                    }
                },
            });

            await click(target.querySelector(".o_data_cell"));
            await editInput(target, "[name='foo'] input", "");
            await click(target, ".o_list_view");
            assert.verifySteps([]);

            await editInput(target, "[name='foo'] input", "YOLO");
            await click(target, ".o_list_view");
            assert.verifySteps(["onWillSaveRecord 1", "web_save 1", "onRecordSaved 1"]);
        }
    );

    QUnit.test(
        "execute an action before and after each valid save in a grouped list view",
        async function (assert) {
            const listView = registry.category("views").get("list");
            class CustomListController extends listView.Controller {
                async onRecordSaved(record) {
                    assert.step(`onRecordSaved ${record.resId}`);
                }

                async onWillSaveRecord(record) {
                    assert.step(`onWillSaveRecord ${record.resId}`);
                }
            }
            registry.category("views").add("custom_list", {
                ...listView,
                Controller: CustomListController,
            });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree js_class="custom_list" editable="top" expand="1"><field name="foo" required="1"/></tree>',
                groupBy: ["bar"],
                mockRPC: async (route, args) => {
                    if (args.method === "web_save") {
                        assert.step(`web_save ${args.args[0]}`);
                    }
                },
            });

            await click(target.querySelector(".o_data_cell[name='foo']"));
            await editInput(target, "[name='foo'] input", "");
            await click(target, ".o_list_view");
            assert.verifySteps([]);

            await editInput(target, "[name='foo'] input", "YOLO");
            await click(target, ".o_list_view");
            assert.verifySteps(["onWillSaveRecord 4", "web_save 4", "onRecordSaved 4"]);
        }
    );

    QUnit.test(
        "don't exec a valid save with onWillSaveRecord in a list view",
        async function (assert) {
            const listView = registry.category("views").get("list");
            class ListViewCustom extends listView.Controller {
                async onRecordSaved(record) {
                    throw new Error("should not execute onRecordSaved");
                }

                async onWillSaveRecord(record) {
                    assert.step(`onWillSaveRecord ${record.resId}`);
                    return false;
                }
            }
            registry.category("views").add(
                "list",
                {
                    ...listView,
                    Controller: ListViewCustom,
                },
                { force: true }
            );

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
                mockRPC: async (route, args) => {
                    if (args.method === "write") {
                        throw new Error("should not save the record");
                    }
                },
            });

            await click(target.querySelector(".o_data_cell"));
            await editInput(target, "[name='foo'] input", "");
            await click(target, ".o_list_view");
            assert.verifySteps([]);

            await click(target.querySelector(".o_data_cell"));
            await editInput(target, "[name='foo'] input", "YOLO");
            await click(target, ".o_list_view");
            assert.verifySteps(["onWillSaveRecord 1"]);
        }
    );

    QUnit.test("action/type attributes on tree arch, type='object'", async (assert) => {
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree action="a1" type="object"><field name="foo"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        patchWithCleanup(list.env.services.action, {
            doActionButton(params) {
                assert.step(`doActionButton type ${params.type} name ${params.name}`);
                params.onClose();
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);
        await click(target.querySelector(".o_data_cell"));
        assert.verifySteps(["doActionButton type object name a1", "web_search_read"]);
    });

    QUnit.test("action/type attributes on tree arch, type='action'", async (assert) => {
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree action="a1" type="action"><field name="foo"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        patchWithCleanup(list.env.services.action, {
            doActionButton(params) {
                assert.step(`doActionButton type ${params.type} name ${params.name}`);
                params.onClose();
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);
        await click(target.querySelector(".o_data_cell"));
        assert.verifySteps(["doActionButton type action name a1", "web_search_read"]);
    });

    QUnit.test("editable list view: readonly fields cannot be edited", async function (assert) {
        serverData.models.foo.fields.foo.readonly = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field" readonly="1"/>
                </tree>`,
        });
        await click(target.querySelector(".o_field_cell"));
        assert.hasClass(
            target.querySelector(".o_data_row"),
            "o_selected_row",
            "row should be in edit mode"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget[name=foo]"),
            "o_readonly_modifier",
            "foo field should be readonly in edit mode"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget[name=bar]"),
            "o_readonly_modifier",
            "bar field should be editable"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget[name=int_field]"),
            "o_readonly_modifier",
            "int_field field should be readonly in edit mode"
        );
        assert.hasClass(target.querySelectorAll(".o_data_cell")[0], "o_readonly_modifier");
    });

    QUnit.test("editable list view: line with no active element", async function (assert) {
        assert.expect(4);

        serverData.models.bar = {
            fields: {
                titi: { string: "Char", type: "char" },
                grosminet: { string: "Bool", type: "boolean" },
            },
            records: [
                { id: 1, titi: "cui", grosminet: true },
                { id: 2, titi: "cuicui", grosminet: false },
            ],
        };
        serverData.models.foo.records[0].o2m = [1, 2];

        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="o2m">
                        <tree editable="top">
                            <field name="titi" readonly="1"/>
                            <field name="grosminet" widget="boolean_toggle"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1], { grosminet: false });
                }
            },
        });

        assert.hasClass(target.querySelectorAll(".o_data_cell")[1], "o_boolean_toggle_cell");

        await click(target.querySelectorAll(".o_data_cell")[0]);
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        assert.containsOnce(target.querySelectorAll(".o_data_cell")[0], ".o_readonly_modifier");
        await click(target.querySelectorAll(".o_data_cell")[1], ".o_boolean_toggle input");
    });

    QUnit.test(
        "editable list view: click on last element after creation empty new line",
        async function (assert) {
            serverData.models.bar = {
                fields: {
                    titi: { string: "Char", type: "char", required: true },
                    int_field: {
                        string: "int_field",
                        type: "integer",
                        sortable: true,
                        required: true,
                    },
                },
                records: [
                    { id: 1, titi: "cui", int_field: 2 },
                    { id: 2, titi: "cuicui", int_field: 4 },
                ],
            };
            serverData.models.foo.records[0].o2m = [1, 2];

            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <field name="o2m">
                            <tree editable="top">
                            <field name="int_field" widget="handle"/>
                            <field name="titi"/>
                            </tree>
                        </field>
                    </form>`,
            });
            await addRow(target);
            await click(
                [...target.querySelectorAll(".o_data_row")].pop().querySelector("td.o_list_char")
            );
            // This test ensure that they aren't traceback when clicking on the last row.
            assert.containsN(target, ".o_data_row", 2, "list should have exactly 2 rows");
        }
    );

    QUnit.test("edit field in editable field without editing the row", async function (assert) {
        // some widgets are editable in readonly (e.g. priority, boolean_toggle...) and they
        // thus don't require the row to be switched in edition to be edited
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="bar" widget="boolean_toggle"/>
                </tree>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save: " + args.args[1].bar);
                }
            },
        });

        // toggle the boolean value of the first row without editing the row
        assert.ok(target.querySelector(".o_data_row .o_boolean_toggle input").checked);
        assert.containsNone(target, ".o_selected_row");
        await click(target.querySelector(".o_data_row .o_boolean_toggle input"));
        assert.notOk(target.querySelector(".o_data_row .o_boolean_toggle input").checked);
        assert.containsNone(target, ".o_selected_row");
        assert.verifySteps(["web_save: false"]);

        // toggle the boolean value after switching the row in edition
        assert.containsNone(target, ".o_selected_row");
        await click(target.querySelector(".o_data_row .o_data_cell .o_field_boolean_toggle div"));
        assert.containsOnce(target, ".o_selected_row");
        await click(target.querySelector(".o_selected_row .o_field_boolean_toggle div"));
        assert.verifySteps(["web_save: true"]);
    });

    QUnit.test("basic operations for editable list renderer", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone(target, ".o_data_row .o_selected_row");
        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
    });

    QUnit.test("editable list: add a line and discard", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
            domain: [["foo", "=", "yop"]],
        });

        assert.containsN(target, "tbody tr", 4, "list should contain 4 rows");
        assert.containsOnce(
            target,
            ".o_data_row",
            "list should contain one record (and thus 3 empty rows)"
        );

        assert.strictEqual(
            target.querySelector(".o_pager_value").innerText,
            "1-1",
            "pager should be correct"
        );

        await click($(".o_list_button_add:visible").get(0));

        assert.containsN(target, "tbody tr", 4, "list should still contain 4 rows");
        assert.containsN(
            target,
            ".o_data_row",
            2,
            "list should contain two record (and thus 2 empty rows)"
        );
        assert.strictEqual(
            target.querySelector(".o_pager_value").innerText,
            "1-2",
            "pager should be correct"
        );

        await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));

        assert.containsN(target, "tbody tr", 4, "list should still contain 4 rows");
        assert.containsOnce(
            target,
            ".o_data_row",
            "list should contain one record (and thus 3 empty rows)"
        );
        assert.strictEqual(
            target.querySelector(".o_pager_value").innerText,
            "1-1",
            "pager should be correct"
        );
    });

    QUnit.test("field changes are triggered correctly", async function (assert) {
        serverData.models.foo.onchanges = {
            foo: function () {
                assert.step("onchange");
            },
        };
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(target.querySelectorAll(".o_data_row")[0], "o_selected_row");
        await editInput(target, ".o_field_widget[name=foo] input", "abc");
        assert.verifySteps(["onchange"]);
        await click(target.querySelectorAll(".o_data_cell")[2]);
        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");
        assert.verifySteps([]);
    });

    QUnit.test("editable list view: basic char field edition", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        await click(target.querySelector(".o_field_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        await editInput(target, ".o_field_char input", "abc");
        assert.strictEqual(
            target.querySelector(".o_field_char input").value,
            "abc",
            "char field has been edited correctly"
        );

        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        assert.strictEqual(
            target.querySelector(".o_field_cell").innerText,
            "abc",
            "changes should be saved correctly"
        );
        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");
        assert.doesNotHaveClass(
            target.querySelector(".o_data_row"),
            "o_selected_row",
            "saved row should be in readonly mode"
        );
        assert.strictEqual(
            serverData.models.foo.records[0].foo,
            "abc",
            "the edition should have been properly saved"
        );
    });

    QUnit.test(
        "editable list view: save data when list sorting in edit mode",
        async function (assert) {
            assert.expect(2);

            serverData.models.foo.fields.foo.sortable = true;

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo"/></tree>',
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.deepEqual(
                            args.args,
                            [[1], { foo: "xyz" }],
                            "should correctly save the edited record"
                        );
                    }
                },
            });

            await click(target.querySelector(".o_data_cell"));
            await editInput(target, '.o_field_widget[name="foo"] input', "xyz");
            await click(target.querySelector(".o_column_sortable"));
            assert.containsNone(target, ".o_selected_row");
        }
    );

    QUnit.test(
        "editable list view: check that controlpanel buttons are updating when groupby applied",
        async function (assert) {
            serverData.models.foo.fields.foo = { string: "Foo", type: "char", required: true };
            serverData.actions = {
                11: {
                    id: 11,
                    name: "Partners Action 11",
                    res_model: "foo",
                    type: "ir.actions.act_window",
                    views: [[3, "list"]],
                    search_view_id: [9, "search"],
                },
            };
            serverData.views = {
                "foo,3,list":
                    '<tree editable="top"><field name="display_name"/><field name="foo"/></tree>',

                "foo,9,search": `
                    <search>
                        <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
                    </search>`,
            };

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, 11);
            await click($(".o_list_button_add:visible").get(0));

            assert.containsNone(target, ".o_list_button_add");
            assert.containsN(
                target,
                ".o_list_button_save",
                2,
                "Should have 2 save button (small and xl screens)"
            );

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "candle");

            assert.containsOnce(
                target,
                ".o_list_button_add:visible",
                "Create available as list is grouped"
            );
            assert.containsNone(
                target,
                ".o_list_button_save",
                "Save not available as no row in edition"
            );
        }
    );

    QUnit.test(
        "editable list view: check that add button is present when groupby applied",
        async function (assert) {
            assert.expect(4);

            serverData.models.foo.fields.foo = { string: "Foo", type: "char", required: true };
            serverData.actions = {
                11: {
                    id: 11,
                    name: "Partners Action 11",
                    res_model: "foo",
                    type: "ir.actions.act_window",
                    views: [
                        [3, "list"],
                        [4, "form"],
                    ],
                    search_view_id: [9, "search"],
                },
            };
            serverData.views = {
                "foo,3,list":
                    '<tree editable="top"><field name="display_name"/><field name="foo"/></tree>',
                "foo,4,form": '<form><field name="display_name"/><field name="foo"/></form>',
                "foo,9,search": `
                    <search>
                        <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
                    </search>`,
            };

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 11);

            assert.containsOnce(target, ".o_list_button_add:visible");
            await click(target.querySelector(".o_searchview_dropdown_toggler"));
            await click($(target).find('.o_menu_item:contains("candle")')[0]);
            assert.containsOnce(target, ".o_list_button_add:visible");

            assert.containsOnce(target, ".o_list_view");
            await click($(".o_list_button_add:visible").get(0));
            assert.containsOnce(target, ".o_form_view");
        }
    );

    QUnit.test("list view not groupable", async function (assert) {
        serverData.views = {
            "foo,false,search": `
                <search>
                    <filter context="{'group_by': 'foo'}" name="foo"/>
                </search>`,
        };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="display_name"/>
                    <field name="foo"/>
                </tree>`,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    throw new Error("Should not do a read_group RPC");
                }
            },
            searchMenuTypes: ["filter", "favorite"],
            context: { search_default_foo: 1 },
        });

        assert.containsNone(
            target,
            ".o_control_panel div.o_search_options div.o_group_by_menu",
            "there should not be groupby menu"
        );
        assert.deepEqual(getFacetTexts(target), []);
    });

    QUnit.test("selection changes are triggered correctly", async function (assert) {
        patchWithCleanup(ListController.prototype, {
            setup() {
                super.setup(...arguments);
                onRendered(() => {
                    assert.step("onRendered ListController");
                });
            },
        });

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });
        var tbody_selector = target.querySelector("tbody .o_list_record_selector input");
        var thead_selector = target.querySelector("thead .o_list_record_selector input");

        assert.strictEqual(list.model.root.selection.length, 0, "no record should be selected");
        assert.notOk(tbody_selector.checked, "selection checkbox should be checked");
        assert.verifySteps(["onRendered ListController"]);

        // tbody checkbox click
        await click(tbody_selector);
        assert.strictEqual(list.model.root.selection.length, 1, "only 1 record should be selected");
        assert.deepEqual(
            list.model.root.selection[0].data,
            {
                bar: true,
                foo: "yop",
            },
            "the correct record should be selected"
        );
        assert.ok(tbody_selector.checked, "selection checkbox should be checked");
        assert.verifySteps(["onRendered ListController"]);

        await click(tbody_selector);
        assert.strictEqual(list.model.root.selection.length, 0, "no record should be selected");
        assert.notOk(tbody_selector.checked, "selection checkbox should be checked");
        assert.verifySteps(["onRendered ListController"]);

        // head checkbox click
        await click(thead_selector);
        assert.strictEqual(list.model.root.selection.length, 4, "all records should be selected");
        assert.containsN(
            target,
            "tbody .o_list_record_selector input:checked",
            target.querySelectorAll("tbody tr").length,
            "all selection checkboxes should be checked"
        );
        assert.verifySteps(["onRendered ListController"]);

        await click(thead_selector);
        assert.strictEqual(list.model.root.selection.length, 0, "no records should be selected");
        assert.containsNone(
            target,
            "tbody .o_list_record_selector input:checked",
            "no selection checkbox should be checked"
        );
        assert.verifySteps(["onRendered ListController"]);
    });

    QUnit.test(
        "Row selection checkbox can be toggled by clicking on the cell",
        async function (assert) {
            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            });

            assert.strictEqual(list.model.root.selection.length, 0, "no record should be selected");

            await click(target.querySelector("tbody .o_list_record_selector"));
            assert.containsOnce(target, "tbody .o_list_record_selector input:checked");
            assert.strictEqual(
                list.model.root.selection.length,
                1,
                "only 1 record should be selected"
            );
            await click(target.querySelector("tbody .o_list_record_selector"));
            assert.containsNone(target, ".o_list_record_selector input:checked");
            assert.strictEqual(list.model.root.selection.length, 0, "no record should be selected");

            await click(target.querySelector("thead .o_list_record_selector"));
            assert.containsN(target, ".o_list_record_selector input:checked", 5);
            assert.strictEqual(
                list.model.root.selection.length,
                4,
                "all records should be selected"
            );
            await click(target.querySelector("thead .o_list_record_selector"));
            assert.containsNone(target, ".o_list_record_selector input:checked");
            assert.strictEqual(list.model.root.selection.length, 0, "no record should be selected");
        }
    );

    QUnit.test("head selector is toggled by the other selectors", async function (assert) {
        await makeView({
            type: "list",
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            serverData,
            groupBy: ["bar"],
            resModel: "foo",
        });

        assert.notOk(
            target.querySelector("thead .o_list_record_selector input").checked,
            "Head selector should be unchecked"
        );

        await click(target.querySelector(".o_group_header:nth-child(2)"));
        await click(target.querySelector("thead .o_list_record_selector input"));
        assert.containsN(
            target,
            "tbody .o_list_record_selector input:checked",
            3,
            "All visible checkboxes should be checked"
        );

        await click(target.querySelector(".o_group_header:first-child"));
        assert.notOk(
            target.querySelector("thead .o_list_record_selector input").checked,
            "Head selector should be unchecked"
        );

        await click(target.querySelector("tbody:nth-child(2) .o_list_record_selector input"));
        assert.ok(
            target.querySelector("thead .o_list_record_selector input").checked,
            "Head selector should be checked"
        );

        await click(target.querySelector("tbody .o_list_record_selector input"));

        assert.notOk(
            target.querySelector("thead .o_list_record_selector input").checked,
            "Head selector should be unchecked"
        );

        await click(target.querySelector(".o_group_header"));

        assert.ok(
            target.querySelector("thead .o_list_record_selector input").checked,
            "Head selector should be checked"
        );
    });

    QUnit.test("selection box is properly displayed (single page)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );

        // select a record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "1 selected"
        );

        // select all records of first page
        await click(target.querySelector("thead .o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "4 selected"
        );

        // unselect a record
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[1]);
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "3 selected"
        );
        await click(target.querySelector(".o_list_unselect_all"));
        assert.containsNone(
            target,
            ".o_list_selection_box",
            "selection options are no longer visible"
        );
        assert.containsNone(
            target,
            ".o_data_row .o_list_record_selector input:checked",
            "no records should be selected"
        );
    });

    QUnit.test("selection box is properly displayed (multi pages)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="3"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 3);
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );

        // select a record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "1 selected"
        );

        // select all records of first page
        await click(target.querySelector("thead .o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsOnce(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.replace(/\s+/g, " ").trim(),
            "3 selected Select all 4"
        );

        // select all domain
        await click(target.querySelector(".o_list_selection_box .o_list_select_domain"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "All 4 selected"
        );
        await click(target.querySelector(".o_list_unselect_all"));
        assert.containsNone(
            target,
            ".o_list_selection_box",
            "selection options are no longer visible"
        );
    });

    QUnit.test("selection box is properly displayed (group list)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["foo"],
        });
        assert.containsN(target, ".o_group_header", 3);
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );

        // open first group
        await click(target.querySelector(".o_group_header"));

        // select a record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "1 selected"
        );

        // select all records of first page
        await click(target.querySelector("thead .o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.containsOnce(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.replace(/\s+/g, " ").trim(),
            "2 selected Select all 4"
        );

        // select all domain
        await click(target.querySelector(".o_list_selection_box .o_list_select_domain"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "All 4 selected"
        );
        await click(target.querySelector(".o_list_unselect_all"));
        assert.containsNone(
            target,
            ".o_list_selection_box",
            "selection options are no longer visible"
        );
    });

    QUnit.test("selection box is displayed as first action button", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <header>
                         <button name="x" type="object" class="plaf" string="plaf"/>
                         <button name="y" type="object" class="plouf" string="plouf"/>
                    </header>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone($(target).find(".o_control_panel_actions"), ".o_list_selection_box");

        // select a record
        await click(target, ".o_data_row:first-child .o_list_record_selector input");
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        const firstElement = target.querySelector(
            ".o_control_panel_actions > div"
        ).firstElementChild;
        assert.strictEqual(
            firstElement,
            target.querySelector(".o_control_panel_actions .o_list_selection_box"),
            "last element should selection box"
        );
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "1 selected"
        );
    });

    QUnit.test("selection box is removed after multi record edition", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree multi_edit="1"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 4, "there should be 4 records");
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box",
            "list selection box should not be displayed"
        );

        // select all records
        await click(target.querySelector(".o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box",
            "list selection box should be displayed"
        );
        assert.containsN(
            target,
            ".o_data_row .o_list_record_selector input:checked",
            4,
            "all 4 records should be selected"
        );

        // edit selected records
        await click(target.querySelector(".o_data_row").querySelector(".o_data_cell"));
        await editInput(target, ".o_data_row [name=foo] input", "legion");
        await click(target, ".modal-dialog button.btn-primary");
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box",
            "list selection box should not be displayed"
        );
        assert.containsNone(
            target,
            ".o_data_row .o_list_record_selector input:checked",
            "no records should be selected"
        );
    });

    QUnit.test("selection is reset on reload", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="int_field" sum="Sum"/>
                </tree>`,
        });

        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.strictEqual(
            $(target).find("tfoot td:nth(2)").text(),
            "32",
            "total should be 32 (no record selected)"
        );

        // select first record
        var firstRowSelector = target.querySelector("tbody .o_list_record_selector input");
        await click(firstRowSelector);
        assert.ok(firstRowSelector.checked, "first row should be selected");
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.strictEqual(
            $(target).find("tfoot td:nth(2)").text(),
            "10",
            "total should be 10 (first record selected)"
        );

        await reloadListView(target);
        firstRowSelector = target.querySelector("tbody .o_list_record_selector input");
        assert.notOk(firstRowSelector.checked, "first row should no longer be selected");
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        assert.strictEqual(
            $(target).find("tfoot td:nth(2)").text(),
            "32",
            "total should be 32 (no more record selected)"
        );
    });

    QUnit.test("selection is kept on render without reload", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["foo"],
            actionMenus: {},
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="int_field" sum="Sum"/>
                </tree>`,
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );

        // open blip grouping and check all lines
        await click($(target).find('.o_group_header:contains("blip (2)")')[0]);
        await click(target.querySelector(".o_data_row input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );

        // open yop grouping and verify blip are still checked
        await click($(target).find('.o_group_header:contains("yop (1)")')[0]);
        assert.containsOnce(
            target,
            ".o_data_row input:checked",
            "opening a grouping does not uncheck others"
        );
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );

        // close and open blip grouping and verify blip are unchecked
        await click($(target).find('.o_group_header:contains("blip (2)")')[0]);
        await click($(target).find('.o_group_header:contains("blip (2)")')[0]);
        assert.containsNone(
            target,
            ".o_data_row input:checked",
            "opening and closing a grouping uncheck its elements"
        );
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
    });

    QUnit.test("select a record in list grouped by date with granularity", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["date:year"],
            // keep the actionMenus, it is relevant as it computes isM2MGrouped which crashes if we
            // don't correctly extract the fieldName/granularity from the groupBy
            actionMenus: {},
        });

        assert.containsN(target, ".o_group_header", 2);
        assert.containsNone(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
        await click(target.querySelector(".o_group_header"));
        assert.containsOnce(target, ".o_data_row");
        await click(target.querySelector(".o_data_row .o_list_record_selector"));
        assert.containsOnce(
            target.querySelector(".o_control_panel_actions"),
            ".o_list_selection_box"
        );
    });

    QUnit.test("aggregates are computed correctly", async function (assert) {
        // map: foo record id -> qux value
        const quxVals = { 1: 1.0, 2: 2.0, 3: 3.0, 4: 0 };

        serverData.models.foo.records = serverData.models.foo.records.map((r) => ({
            ...r,
            qux: quxVals[r.id],
        }));

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: /*xml*/ `
                <tree>
                    <field name="foo"/>
                    <field name="int_field" sum="Sum"/>
                    <field name="qux" avg="Average"/>
                </tree>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('id', '=', 0)]"/>
                </search>`,
        });
        const tbodySelectors = target.querySelectorAll("tbody .o_list_record_selector input");
        const theadSelector = target.querySelector("thead .o_list_record_selector input");

        const getFooterTextArray = () => {
            return [...target.querySelectorAll("tfoot td")].map((td) => td.innerText);
        };

        assert.deepEqual(getFooterTextArray(), ["", "", "32", "1.50"]);

        await click(tbodySelectors[0]);
        await click(tbodySelectors[3]);
        assert.deepEqual(getFooterTextArray(), ["", "", "6", "0.50"]);

        await click(theadSelector);
        assert.deepEqual(getFooterTextArray(), ["", "", "32", "1.50"]);

        // Let's update the view to dislay NO records
        await click(target.querySelector(".o_list_unselect_all"));
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.deepEqual(getFooterTextArray(), ["", "", "", ""]);
    });

    QUnit.test("aggregates are computed correctly in grouped lists", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["m2o"],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
        });
        const groupHeaders = target.querySelectorAll(".o_group_header");
        assert.strictEqual(
            groupHeaders[0].querySelector("td:last-child").textContent,
            "23",
            "first group total should be 23"
        );
        assert.strictEqual(
            groupHeaders[1].querySelector("td:last-child").textContent,
            "9",
            "second group total should be 9"
        );
        assert.strictEqual(
            target.querySelector("tfoot td:last-child").textContent,
            "32",
            "total should be 32"
        );
        await click(groupHeaders[0]);
        await click(target.querySelector("tbody .o_list_record_selector input:first-child"));
        assert.strictEqual(
            target.querySelector("tfoot td:last-child").textContent,
            "10",
            "total should be 10 as first record of first group is selected"
        );
    });

    QUnit.test("aggregates are formatted correctly in grouped lists", async function (assert) {
        // in this scenario, there is a widget on an aggregated field, and this widget has no
        // associated formatter, so we fallback on the formatter corresponding to the field type
        fieldRegistry.add("my_float", FloatField);
        serverData.models.foo.records[0].qux = 5.1654846456;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="qux" widget="my_float" sum="Sum"/>
                </tree>`,
            groupBy: ["int_field"],
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_group_header .o_list_number")),
            ["9.00", "13.00", "5.17", "-3.00"]
        );
    });

    QUnit.test("aggregates in grouped lists with buttons", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["m2o"],
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="int_field" sum="Sum"/>
                    <button name="a" type="object"/>
                    <field name="qux" sum="Sum"/>
                </tree>`,
        });

        const cellVals = ["23", "6.40", "9", "13.00", "32", "19.40"];
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_list_number")), cellVals);
    });

    QUnit.test("date field aggregates in grouped lists", async function (assert) {
        // this test simulates a scenario where a date field has a group_operator
        // and the web_read_group thus return a value for that field for each group
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["m2o"],
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="date"/>
                </tree>`,
            async mockRPC(route, args, performRPC) {
                if (args.method === "web_read_group") {
                    const res = await performRPC(...arguments);
                    res.groups[0].date = "2021-03-15";
                    res.groups[1].date = "2021-02-11";
                    return res;
                }
            },
        });

        assert.containsN(target, ".o_group_header", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_group_header")), [
            `Value 1 (3) `,
            `Value 2 (1) `,
        ]);
    });

    QUnit.test(
        "hide aggregated value in grouped lists when no data provided by RPC call",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["bar"],
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="qux" widget="float_time" sum="Sum"/>
                    </tree>`,
                mockRPC: async function (route, args, performRPC) {
                    if (args.method === "web_read_group") {
                        const result = await performRPC(route, args);
                        result.groups.forEach((group) => {
                            delete group.qux;
                        });
                        return Promise.resolve(result);
                    }
                },
            });

            assert.strictEqual(
                target.querySelectorAll("tfoot td")[2].textContent,
                "",
                "There isn't any aggregated value"
            );
        }
    );

    QUnit.test("aggregates are updated when a line is edited", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="int_field" sum="Sum"/></tree>',
        });

        assert.strictEqual(
            target.querySelector('span[data-tooltip="Sum"]').innerText,
            "32",
            "current total should be 32"
        );

        await click(target.querySelector("tr.o_data_row td.o_data_cell"));
        await editInput(target, "td.o_data_cell input", "15");

        assert.strictEqual(
            target.querySelector('span[data-tooltip="Sum"]').innerText,
            "37",
            "current total should be 37"
        );
    });

    QUnit.test("aggregates are formatted according to field widget", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="qux" widget="float_time" sum="Sum"/>
                </tree>`,
        });

        assert.strictEqual(
            target.querySelectorAll("tfoot td")[2].textContent,
            "19:24",
            "total should be formatted as a float_time"
        );
    });

    QUnit.test("aggregates digits can be set with digits field attribute", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="amount" widget="monetary" sum="Sum" digits="[69,3]"/>
                </tree>`,
        });

        assert.strictEqual(
            target.querySelectorAll(".o_data_row td")[1].textContent,
            "1200.00",
            "field should still be formatted based on currency"
        );
        assert.strictEqual(
            target.querySelectorAll("tfoot td")[1].textContent,
            "—",
            "aggregates monetary should never work if no currency field is present"
        );
    });

    QUnit.test("aggregates monetary (same currency)", async function (assert) {
        serverData.models.foo.records[0].currency_id = 1;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="amount" widget="monetary" sum="Sum"/>
                    <field name="currency_id"/>
                </tree>`,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll("tbody .o_monetary_cell")), [
            "$\u00a01200.00",
            "$\u00a0500.00",
            "$\u00a0300.00",
            "$\u00a00.00",
        ]);

        assert.strictEqual(target.querySelectorAll("tfoot td")[1].textContent, "$\u00a02000.00");
    });

    QUnit.test("aggregates monetary (different currencies)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="amount" widget="monetary" sum="Sum"/>
                    <field name="currency_id"/>
                </tree>`,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll("tbody .o_monetary_cell")), [
            "1200.00\u00a0€",
            "$\u00a0500.00",
            "$\u00a0300.00",
            "$\u00a00.00",
        ]);

        assert.strictEqual(target.querySelectorAll("tfoot td")[1].textContent, "—");
    });

    QUnit.test("aggregates monetary (currency field not in view)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="amount" widget="monetary" sum="Sum" options="{'currency_field': 'currency_test'}"/>
                    <field name="currency_id"/>
                </tree>`,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll("tbody .o_monetary_cell")), [
            "1200.00",
            "500.00",
            "300.00",
            "0.00",
        ]);

        assert.strictEqual(target.querySelectorAll("tfoot td")[1].textContent, "—");
    });

    QUnit.test("aggregates monetary (currency field in view)", async function (assert) {
        serverData.models.foo.fields.amount.currency_field = "currency_test";
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="amount" widget="monetary" sum="Sum"/>
                    <field name="currency_test"/>
                </tree>`,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll("tbody .o_monetary_cell")), [
            "$\u00a01200.00",
            "$\u00a0500.00",
            "$\u00a0300.00",
            "$\u00a00.00",
        ]);

        assert.strictEqual(target.querySelectorAll("tfoot td")[1].textContent, "$\u00a02000.00");
    });

    QUnit.test("aggregates monetary with custom digits (same currency)", async function (assert) {
        serverData.models.foo.records = serverData.models.foo.records.map((record) => ({
            ...record,
            currency_id: 1,
        }));
        patchWithCleanup(currencies, {
            1: { ...currencies[1], digits: [42, 4] },
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="amount" sum="Sum"/>
                    <field name="currency_id"/>
                </tree>`,
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll("tbody [name='amount']")), [
            "$\u00a01200.0000",
            "$\u00a0500.0000",
            "$\u00a0300.0000",
            "$\u00a00.0000",
        ]);

        assert.strictEqual(target.querySelectorAll("tfoot td")[1].textContent, "$\u00a02000.0000");
    });

    QUnit.test(
        "aggregates float with monetary widget and custom digits (same currency)",
        async function (assert) {
            serverData.models.foo.records = serverData.models.foo.records.map((record) => ({
                ...record,
                currency_id: 1,
            }));
            patchWithCleanup(currencies, {
                1: { ...currencies[1], digits: [42, 4] },
            });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <field name="qux" widget="monetary" sum="Sum"/>
                    <field name="currency_id"/>
                </tree>`,
            });

            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll("tbody .o_monetary_cell")),
                ["$\u00a00.4000", "$\u00a013.0000", "$\u00a0-3.0000", "$\u00a09.0000"]
            );

            assert.strictEqual(
                target.querySelectorAll("tfoot td")[1].textContent,
                "$\u00a019.4000"
            );
        }
    );

    QUnit.test(
        "currency_field is taken into account when formatting monetary values",
        async (assert) => {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <field name="company_currency_id" column_invisible="1"/>
                    <field name="currency_id" column_invisible="1"/>
                    <field name="amount"/>
                    <field name="amount_currency"/>
                </tree>`,
            });

            assert.strictEqual(
                target.querySelectorAll('.o_data_row td[name="amount"]')[0].textContent,
                "1200.00\u00a0€",
                "field should be formatted based on currency_id"
            );
            assert.strictEqual(
                target.querySelectorAll('.o_data_row td[name="amount_currency"]')[0].textContent,
                "$\u00a01100.00",
                "field should be formatted based on company_currency_id"
            );
            assert.strictEqual(
                target.querySelectorAll("tfoot td")[1].textContent,
                "—",
                "aggregates monetary should never work if different currencies are used"
            );
        }
    );

    QUnit.test(
        "groups can not be sorted on a different field than the first field of the groupBy - 1",
        async function (assert) {
            assert.expect(1);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree default_order="foo"><field name="foo"/><field name="bar"/></tree>',
                mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        assert.strictEqual(args.kwargs.orderby, "", "should not have an orderBy");
                    }
                },
                groupBy: ["bar"],
            });
        }
    );

    QUnit.test(
        "groups can not be sorted on a different field than the first field of the groupBy - 2",
        async function (assert) {
            assert.expect(1);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree default_order="foo"><field name="foo"/><field name="bar"/></tree>',
                mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        assert.strictEqual(args.kwargs.orderby, "", "should not have an orderBy");
                    }
                },
                groupBy: ["bar", "foo"],
            });
        }
    );

    QUnit.test("groups can be sorted on the first field of the groupBy", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree default_order="bar desc"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    assert.strictEqual(args.kwargs.orderby, "bar DESC", "should have an orderBy");
                }
            },
            groupBy: ["bar"],
        });

        assert.strictEqual(
            document.querySelector(".o_group_header:first-child").textContent.trim(),
            "Yes (3)"
        );
        assert.strictEqual(
            document.querySelector(".o_group_header:last-child").textContent.trim(),
            "No (1)"
        );
    });

    QUnit.test(
        "groups can't be sorted on aggregates if there is no record",
        async function (assert) {
            serverData.models.foo.records = [];

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["foo"],
                arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="int_field" sum="Sum"/>
                </tree>`,
                mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        assert.step(args.kwargs.orderby || "default order");
                    }
                },
            });

            await click(target, ".o_column_sortable");
            assert.verifySteps(["default order"]);
        }
    );

    QUnit.test("groups can be sorted on aggregates", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["foo"],
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="int_field" sum="Sum"/>
                </tree>`,
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    assert.step(args.kwargs.orderby || "default order");
                }
            },
        });

        assert.strictEqual(
            $(target).find("tbody .o_list_number").text(),
            "51710",
            "initial order should be 5, 17, 17"
        );
        assert.strictEqual($(target).find("tfoot td:last()").text(), "32", "total should be 32");

        await click(target, ".o_column_sortable");
        assert.strictEqual(
            $(target).find("tfoot td:last()").text(),
            "32",
            "total should still be 32"
        );
        assert.strictEqual(
            $(target).find("tbody .o_list_number").text(),
            "51017",
            "order should be 5, 10, 17"
        );

        await click(target, ".o_column_sortable");
        assert.strictEqual(
            $(target).find("tbody .o_list_number").text(),
            "17105",
            "initial order should be 17, 10, 5"
        );
        assert.strictEqual(
            $(target).find("tfoot td:last()").text(),
            "32",
            "total should still be 32"
        );

        assert.verifySteps(["default order", "int_field ASC", "int_field DESC"]);
    });

    QUnit.test(
        "groups cannot be sorted on non-aggregable fields if every group is folded",
        async function (assert) {
            serverData.models.foo.fields.sort_field = {
                string: "sortable_field",
                type: "sting",
                sortable: true,
                default: "value",
            };
            serverData.models.foo.records.forEach((elem) => {
                elem.sort_field = "value" + elem.id;
            });
            serverData.models.foo.fields.foo.sortable = true;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["foo"],
                arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="sort_field"/>
                </tree>`,
                mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        assert.step(args.kwargs.orderby || "default order");
                    }
                },
            });
            assert.verifySteps(["default order"]);

            // we cannot sort by sort_field since it doesn't have a group_operator
            await click(target.querySelector(".o_column_sortable[data-name='sort_field']"));
            assert.verifySteps([]);

            // we can sort by int_field since it has a group_operator
            await click(target.querySelector(".o_column_sortable[data-name='int_field']"));
            assert.verifySteps(["int_field ASC"]);

            // we keep previous order
            await click(target.querySelector(".o_column_sortable[data-name='sort_field']"));
            assert.verifySteps([]);

            // we can sort on foo since we are groupped by foo + previous order
            await click(target.querySelector(".o_column_sortable[data-name='foo']"));
            assert.verifySteps(["foo ASC, int_field ASC"]);
        }
    );

    QUnit.test(
        "groups can be sorted on non-aggregable fields if a group isn't folded",
        async function (assert) {
            serverData.models.foo.fields.foo.sortable = true;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["bar"],
                arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                </tree>`,
                mockRPC(route, args) {
                    const { method } = args;
                    if (method === "web_read_group") {
                        assert.step(
                            `web_read_group.orderby: ${args.kwargs.orderby || "default order"}`
                        );
                    }
                    if (method === "web_search_read") {
                        assert.step(
                            `web_search_read.order: ${args.kwargs.order || "default order"}`
                        );
                    }
                },
            });
            await click(target.querySelectorAll(".o_group_header")[1]);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_cell[name='foo']")),
                ["yop", "blip", "gnap"]
            );
            assert.verifySteps([
                "web_read_group.orderby: default order",
                "web_search_read.order: default order",
            ]);

            await click(target.querySelector(".o_column_sortable[data-name='foo']"));
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_cell[name='foo']")),
                ["blip", "gnap", "yop"]
            );
            assert.verifySteps([
                "web_read_group.orderby: default order",
                "web_search_read.order: foo ASC",
            ]);
        }
    );

    QUnit.test(
        "groups can be sorted on non-aggregable fields if a group isn't folded with expand='1'",
        async function (assert) {
            serverData.models.foo.fields.foo.sortable = true;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["bar"],
                arch: `
                <tree editable="bottom" expand="1">
                    <field name="foo"/>
                </tree>`,
                mockRPC(route, args) {
                    const { method } = args;
                    if (method === "web_read_group") {
                        assert.step(
                            `web_read_group.orderby: ${args.kwargs.orderby || "default order"}`
                        );
                    }
                    if (method === "web_search_read") {
                        assert.step(
                            `web_search_read.orderby: ${args.kwargs.order || "default order"}`
                        );
                    }
                },
            });
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_cell[name='foo']")),
                ["blip", "yop", "blip", "gnap"]
            );
            assert.verifySteps([
                "web_read_group.orderby: default order",
                "web_search_read.orderby: default order",
                "web_search_read.orderby: default order",
            ]);

            await click(target.querySelector(".o_column_sortable[data-name='foo']"));
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_cell[name='foo']")),
                ["blip", "blip", "gnap", "yop"]
            );
            assert.verifySteps([
                "web_read_group.orderby: default order",
                "web_search_read.orderby: foo ASC",
                "web_search_read.orderby: foo ASC",
            ]);
        }
    );

    QUnit.test("properly apply onchange in simple case", async function (assert) {
        serverData.models.foo.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        await click(target.querySelector(".o_field_cell"));

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "10",
            "should contain initial value"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "1007",
            "should contain input with onchange applied"
        );
    });

    QUnit.test("column width should not change when switching mode", async function (assert) {
        // Warning: this test is css dependant
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="int_field" readonly="1"/>
                    <field name="m2o"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
        });

        var startWidths = [...target.querySelectorAll("thead th")].map((el) => el.offsetWidth);
        var startWidth = window.getComputedStyle(target.querySelector("table")).width;

        // start edition of first row
        await click(target.querySelector("td:not(.o_list_record_selector)"));

        var editionWidths = [...target.querySelectorAll("thead th")].map((el) => el.offsetWidth);
        var editionWidth = window.getComputedStyle(target.querySelector("table")).width;

        // leave edition
        await click($(".o_list_button_save:visible").get(0));

        var readonlyWidths = [...target.querySelectorAll("thead th")].map((el) => el.offsetWidth);
        var readonlyWidth = window.getComputedStyle(target.querySelector("table")).width;

        assert.strictEqual(
            editionWidth,
            startWidth,
            "table should have kept the same width when switching from readonly to edit mode"
        );
        assert.deepEqual(
            editionWidths,
            startWidths,
            "width of columns should remain unchanged when switching from readonly to edit mode"
        );
        assert.strictEqual(
            readonlyWidth,
            editionWidth,
            "table should have kept the same width when switching from edit to readonly mode"
        );
        assert.deepEqual(
            readonlyWidths,
            editionWidths,
            "width of columns should remain unchanged when switching from edit to readonly mode"
        );
    });

    QUnit.test(
        "column widths should depend on the content when there is data",
        async function (assert) {
            serverData.models.foo.records[0].foo = "Some very very long value for a char field";

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="bar"/>
                        <field name="foo"/>
                        <field name="int_field"/>
                        <field name="qux"/>
                        <field name="date"/>
                        <field name="datetime"/>
                    </tree>`,
                limit: 2,
            });

            assert.strictEqual(
                target.querySelector("thead .o_list_record_selector").offsetWidth,
                41
            );
            const widthPage1 = target.querySelector(`th[data-name=foo]`).offsetWidth;

            await pagerNext(target);

            assert.strictEqual(
                target.querySelector("thead .o_list_record_selector").offsetWidth,
                41
            );
            const widthPage2 = target.querySelector(`th[data-name=foo]`).offsetWidth;
            assert.ok(
                widthPage1 > widthPage2,
                "column widths should be computed dynamically according to the content"
            );
        }
    );

    QUnit.test(
        "width of some of the fields should be hardcoded if no data",
        async function (assert) {
            const assertions = [
                { field: "bar", expected: 70, type: "Boolean" },
                { field: "int_field", expected: 74, type: "Integer" },
                { field: "qux", expected: 92, type: "Float" },
                { field: "date", expected: 92, type: "Date" },
                { field: "datetime", expected: 146, type: "Datetime" },
                { field: "amount", expected: 104, type: "Monetary" },
            ];
            assert.expect(9);

            serverData.models.foo.records = [];
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="bar"/>
                        <field name="foo"/>
                        <field name="int_field"/>
                        <field name="qux"/>
                        <field name="date"/>
                        <field name="datetime"/>
                        <field name="amount"/>
                        <field name="currency_id" width="25px"/>
                    </tree>`,
            });

            assert.containsNone(
                target,
                ".o_resize",
                "There shouldn't be any resize handle if no data"
            );
            assertions.forEach((a) => {
                assert.strictEqual(
                    target.querySelector(`th[data-name="${a.field}"]`).offsetWidth,
                    a.expected,
                    `Field ${a.type} should have a fixed width of ${a.expected} pixels`
                );
            });
            assert.strictEqual(
                target.querySelector('th[data-name="foo"]').style.width,
                "100%",
                "Char field should occupy the remaining space"
            );
            assert.strictEqual(
                target.querySelector('th[data-name="currency_id"]').offsetWidth,
                25,
                "Currency field should have a fixed width of 25px (see arch)"
            );
        }
    );

    QUnit.test("colspan of empty lines is correct in readonly", async function (assert) {
        serverData.models.foo.fields.foo_o2m = {
            string: "Foo O2M",
            type: "one2many",
            relation: "foo",
        };
        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            arch: `
                    <form edit="0">
                        <sheet>
                            <field name="foo_o2m">
                                <tree editable="bottom">
                                    <field name="int_field"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
        });
        // in readonly mode, the delete action is not available
        assert.strictEqual(target.querySelector("tbody td").getAttribute("colspan"), "1");
    });

    QUnit.test("colspan of empty lines is correct in edit", async function (assert) {
        serverData.models.foo.fields.foo_o2m = {
            string: "Foo O2M",
            type: "one2many",
            relation: "foo",
        };
        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            arch: `
                    <form>
                        <sheet>
                            <field name="foo_o2m">
                                <tree editable="bottom">
                                    <field name="int_field"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
        });
        // in edit mode, the delete action is available and the empty lines should cover that col
        assert.strictEqual(target.querySelector("tbody td").getAttribute("colspan"), "2");
    });

    QUnit.test(
        "colspan of empty lines is correct in readonly with optional fields",
        async function (assert) {
            serverData.models.foo.fields.foo_o2m = {
                string: "Foo O2M",
                type: "one2many",
                relation: "foo",
            };
            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                arch: `
                    <form edit="0">
                        <sheet>
                            <field name="foo_o2m">
                                <tree editable="bottom">
                                    <field name="int_field"/>
                                    <field name="foo" optional="hidden"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
            });
            // in readonly mode, the delete action is not available but the optional fields is and the empty lines should cover that col
            assert.strictEqual(target.querySelector("tbody td").getAttribute("colspan"), "2");
        }
    );

    QUnit.test(
        "colspan of empty lines is correct in edit with optional fields",
        async function (assert) {
            serverData.models.foo.fields.foo_o2m = {
                string: "Foo O2M",
                type: "one2many",
                relation: "foo",
            };
            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <sheet>
                            <field name="foo_o2m">
                                <tree editable="bottom">
                                    <field name="int_field"/>
                                    <field name="foo" optional="hidden"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
            });
            // in edit mode, both the delete action and the optional fields are available and the empty lines should cover that col
            assert.strictEqual(target.querySelector("tbody td").getAttribute("colspan"), "2");
        }
    );

    QUnit.test(
        "width of some fields should be hardcoded if no data, and list initially invisible",
        async function (assert) {
            const assertions = [
                { field: "bar", expected: 70, type: "Boolean" },
                { field: "int_field", expected: 74, type: "Integer" },
                { field: "qux", expected: 92, type: "Float" },
                { field: "date", expected: 92, type: "Date" },
                { field: "datetime", expected: 146, type: "Datetime" },
                { field: "amount", expected: 104, type: "Monetary" },
            ];
            assert.expect(12);

            serverData.models.foo.fields.foo_o2m = {
                string: "Foo O2M",
                type: "one2many",
                relation: "foo",
            };
            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                mode: "edit",
                arch: `
                    <form>
                        <sheet>
                            <notebook>
                                <page string="Page1"></page>
                                <page string="Page2">
                                    <field name="foo_o2m">
                                        <tree editable="bottom">
                                            <field name="bar"/>
                                            <field name="foo"/>
                                            <field name="int_field"/>
                                            <field name="qux"/>
                                            <field name="date"/>
                                            <field name="datetime"/>
                                            <field name="amount"/>
                                            <field name="currency_id" width="25px"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
            });

            assert.containsNone(target, ".o_field_one2many");

            await click(target.querySelector(".nav-item:last-child .nav-link"));

            assert.isVisible(target.querySelector(".o_field_one2many"));

            assert.containsNone(
                target,
                ".o_field_one2many .o_resize",
                "There shouldn't be any resize handle if no data"
            );
            assertions.forEach((a) => {
                assert.strictEqual(
                    target.querySelector(`.o_field_one2many th[data-name="${a.field}"]`).style
                        .width,
                    `${a.expected}px`,
                    `Field ${a.type} should have a fixed width of ${a.expected} pixels`
                );
            });
            assert.strictEqual(
                target.querySelector('.o_field_one2many th[data-name="foo"]').style.width,
                "100%",
                "Char field should occupy the remaining space"
            );
            assert.strictEqual(
                target.querySelector('th[data-name="currency_id"]').offsetWidth,
                25,
                "Currency field should have a fixed width of 25px (see arch)"
            );
            assert.strictEqual(target.querySelector(".o_list_actions_header").offsetWidth, 32);
        }
    );

    QUnit.test(
        "empty editable list with the handle widget and no content help",
        async function (assert) {
            // no records for the foo model
            serverData.models.foo.records = [];

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="int_field" widget="handle" />
                        <field name="foo" />
                    </tree>`,
                noContentHelp: '<p class="hello">click to add a foo</p>',
            });

            assert.containsOnce(target, ".o_view_nocontent", "should have no content help");

            // click on create button
            await click($(".o_list_button_add:visible").get(0));
            const handleWidgetWidth = "33px";
            const handleWidgetHeader = target.querySelector("thead > tr > th.o_handle_cell");

            assert.strictEqual(
                window.getComputedStyle(handleWidgetHeader).width,
                handleWidgetWidth,
                "While creating first record, width should be applied to handle widget."
            );

            // creating one record
            await editInput(target, ".o_selected_row [name='foo'] input", "test_foo");
            await clickSave(target);
            assert.strictEqual(
                window.getComputedStyle(handleWidgetHeader).width,
                handleWidgetWidth,
                "After creation of the first record, width of the handle widget should remain as it is"
            );
        }
    );

    QUnit.test("editable list: overflowing table", async function (assert) {
        serverData.models.bar = {
            fields: {
                titi: { string: "Small char", type: "char", sortable: true },
                grosminet: { string: "Beeg char", type: "char", sortable: true },
            },
            records: [
                {
                    id: 1,
                    titi: "Tiny text",
                    grosminet:
                        // Just want to make sure that the table is overflowed
                        `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                        Donec est massa, gravida eget dapibus ac, eleifend eget libero.
                        Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
                        velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
                        ipsum primis in faucibus orci luctus et ultrices posuere cubilia
                        Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
                        Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
                        eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
                        nunc, ut aliquet enim. Suspendisse malesuada felis non metus
                        efficitur aliquet.`,
                },
            ],
        };
        await makeView({
            type: "list",
            resModel: "bar",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="titi"/>
                    <field name="grosminet" widget="char"/>
                </tree>`,
        });

        assert.strictEqual(
            target.querySelector("table").offsetWidth,
            target.querySelector(".o_list_renderer").offsetWidth,
            "Table should not be stretched by its content"
        );
    });

    QUnit.test("editable list: overflowing table (3 columns)", async function (assert) {
        const longText = `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                        Donec est massa, gravida eget dapibus ac, eleifend eget libero.
                        Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
                        velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
                        ipsum primis in faucibus orci luctus et ultrices posuere cubilia
                        Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
                        Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
                        eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
                        nunc, ut aliquet enim. Suspendisse malesuada felis non metus
                        efficitur aliquet.`;

        serverData.models.bar = {
            fields: {
                titi: { string: "Small char", type: "char", sortable: true },
                grosminet1: { string: "Beeg char 1", type: "char", sortable: true },
                grosminet2: { string: "Beeg char 2", type: "char", sortable: true },
                grosminet3: { string: "Beeg char 3", type: "char", sortable: true },
            },
            records: [
                {
                    id: 1,
                    titi: "Tiny text",
                    grosminet1: longText,
                    grosminet2: longText + longText,
                    grosminet3: longText + longText + longText,
                },
            ],
        };
        await makeView({
            arch: `
                <tree editable="top">
                    <field name="titi"/>
                    <field name="grosminet1" class="large"/>
                    <field name="grosminet3" class="large"/>
                    <field name="grosminet2" class="large"/>
                </tree>`,
            serverData,
            resModel: "bar",
            type: "list",
        });

        assert.strictEqual(
            target.querySelector("table").offsetWidth,
            target.querySelector(".o_list_view").offsetWidth
        );
        const largeCells = target.querySelectorAll(".o_data_cell.large");
        assert.ok(Math.abs(largeCells[0].offsetWidth - largeCells[1].offsetWidth) <= 1);
        assert.ok(Math.abs(largeCells[1].offsetWidth - largeCells[2].offsetWidth) <= 1);
        assert.ok(
            target.querySelector(".o_data_cell:not(.large)").offsetWidth < largeCells[0].offsetWidth
        );
    });

    QUnit.test(
        "editable list: list view in an initially unselected notebook page",
        async function (assert) {
            serverData.models.foo.records = [{ id: 1, o2m: [1] }];
            serverData.models.bar = {
                fields: {
                    titi: { string: "Small char", type: "char", sortable: true },
                    grosminet: { string: "Beeg char", type: "char", sortable: true },
                },
                records: [
                    {
                        id: 1,
                        titi: "Tiny text",
                        grosminet:
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
                            "Ut at nisi congue, facilisis neque nec, pulvinar nunc. " +
                            "Vivamus ac lectus velit.",
                    },
                ],
            };
            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <sheet>
                            <notebook>
                                <page string="Page1"></page>
                                <page string="Page2">
                                    <field name="o2m">
                                        <tree editable="bottom">
                                            <field name="titi"/>
                                            <field name="grosminet"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
            });
            assert.containsNone(target, ".o_field_one2many");

            await click(target.querySelector(".nav-item:last-child .nav-link"));
            assert.containsOnce(target, ".o_field_one2many");

            const [titi, grosminet] = target.querySelectorAll(".tab-pane:last-child th");
            assert.ok(
                titi.style.width.split("px")[0] > 80 && grosminet.style.width.split("px")[0] > 500,
                "list has been correctly frozen after being visible"
            );
        }
    );

    QUnit.test("editable list: list view hidden by an invisible modifier", async function (assert) {
        serverData.models.foo.records = [{ id: 1, bar: true, o2m: [1] }];
        serverData.models.bar = {
            fields: {
                titi: { string: "Small char", type: "char", sortable: true },
                grosminet: { string: "Beeg char", type: "char", sortable: true },
            },
            records: [
                {
                    id: 1,
                    titi: "Tiny text",
                    grosminet:
                        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
                        "Ut at nisi congue, facilisis neque nec, pulvinar nunc. " +
                        "Vivamus ac lectus velit.",
                },
            ],
        };
        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <sheet>
                        <field name="bar"/>
                        <field name="o2m" invisible="bar">
                            <tree editable="bottom">
                                <field name="titi"/>
                                <field name="grosminet"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
        });
        assert.containsNone(target, ".o_field_one2many");

        await click(target.querySelector(".o_field_boolean input"));
        assert.containsOnce(target, ".o_field_one2many");

        const [titi, grosminet] = target.querySelectorAll("th");
        assert.ok(
            titi.style.width.split("px")[0] > 80 && grosminet.style.width.split("px")[0] > 700,
            "list has been correctly frozen after being visible"
        );
    });

    QUnit.test("editable list: updating list state while invisible", async function (assert) {
        serverData.models.foo.onchanges = {
            bar: function (obj) {
                obj.o2m = [[5], [0, null, { display_name: "Whatever" }]];
            },
        };
        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <sheet>
                        <field name="bar"/>
                        <notebook>
                            <page string="Page 1"></page>
                            <page string="Page 2">
                                <field name="o2m">
                                    <tree editable="bottom">
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
        });
        assert.containsNone(target, ".o_field_one2many");

        await click(target.querySelector(".o_field_boolean input"));
        assert.containsNone(target, ".o_field_one2many");

        await click(target.querySelector(".nav-item:last-child .nav-link"));
        assert.containsOnce(target, ".o_field_one2many");
        assert.strictEqual(
            target.querySelector(".o_field_one2many .o_data_row").textContent,
            "Whatever"
        );
        assert.notEqual(
            target.querySelector("th").style.width,
            "",
            "Column header should have been frozen"
        );
    });

    QUnit.test("empty list: state with nameless and stringless buttons", async function (assert) {
        serverData.models.foo.records = [];
        await makeView({
            type: "list",
            arch: `
                <tree>
                    <field name="foo"/>
                    <button string="choucroute"/>
                    <button icon="fa-heart"/>
                </tree>`,
            serverData,
            resModel: "foo",
        });

        assert.strictEqual(
            [...target.querySelectorAll("th")].find((el) => el.textContent === "Foo").style.width,
            "50%",
            "Field column should be frozen"
        );
        assert.strictEqual(
            target.querySelector("th:last-child").style.width,
            "50%",
            "Buttons column should be frozen"
        );
    });

    QUnit.test("editable list: unnamed columns cannot be resized", async function (assert) {
        serverData.models.foo.records = [{ id: 1, o2m: [1] }];
        serverData.models.bar.records = [{ id: 1, display_name: "Oui" }];
        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            mode: "edit",
            arch: `
                <form>
                    <sheet>
                        <field name="o2m">
                            <tree editable="top">
                                <field name="display_name"/>
                                <button name="the_button" icon="fa-heart"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
        });

        const [charTh, buttonTh] = target.querySelectorAll(".o_field_one2many th");
        const thRect = charTh.getBoundingClientRect();
        const resizeRect = charTh.querySelector(".o_resize").getBoundingClientRect();

        assert.ok(
            resizeRect.right - thRect.right <= 1,
            "First resize handle should be attached at the end of the first header"
        );
        assert.containsNone(
            buttonTh,
            ".o_resize",
            "Columns without name should not have a resize handle"
        );
    });

    QUnit.test(
        "editable list view, click on m2o dropdown does not close editable row",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="m2o"/></tree>',
            });

            await click($(".o_list_button_add:visible").get(0));
            assert.strictEqual(
                target.querySelector(".o_selected_row .o_field_many2one input").value,
                ""
            );
            await click(target.querySelector(".o_selected_row .o_field_many2one input"));
            assert.containsOnce(target, ".o_field_many2one .o-autocomplete--dropdown-menu");

            await click(
                target.querySelector(
                    ".o_field_many2one .o-autocomplete--dropdown-menu .dropdown-item"
                )
            );
            assert.strictEqual(
                target.querySelector(".o_selected_row .o_field_many2one input").value,
                "Value 1"
            );
            assert.containsOnce(target, ".o_selected_row", "should still have editable row");
        }
    );

    QUnit.test(
        "width of some of the fields should be hardcoded if no data (grouped case)",
        async function (assert) {
            const assertions = [
                { field: "bar", expected: 70, type: "Boolean" },
                { field: "int_field", expected: 74, type: "Integer" },
                { field: "qux", expected: 92, type: "Float" },
                { field: "date", expected: 92, type: "Date" },
                { field: "datetime", expected: 146, type: "Datetime" },
                { field: "amount", expected: 104, type: "Monetary" },
            ];
            assert.expect(9);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="bar"/>
                        <field name="foo"/>
                        <field name="int_field"/>
                        <field name="qux"/>
                        <field name="date"/>
                        <field name="datetime"/>
                        <field name="amount"/>
                        <field name="currency_id" width="25px"/>
                    </tree>`,
                groupBy: ["int_field"],
            });

            assert.containsNone(
                target,
                ".o_resize",
                "There shouldn't be any resize handle if no data"
            );
            assertions.forEach((a) => {
                assert.strictEqual(
                    a.expected,
                    target.querySelectorAll(`th[data-name="${a.field}"]`)[0].offsetWidth,
                    `Field ${a.type} should have a fixed width of ${a.expected} pixels`
                );
            });
            assert.strictEqual(
                target.querySelectorAll('th[data-name="foo"]')[0].style.width,
                "100%",
                "Char field should occupy the remaining space"
            );
            assert.strictEqual(
                target.querySelectorAll('th[data-name="currency_id"]')[0].offsetWidth,
                25,
                "Currency field should have a fixed width of 25px (see arch)"
            );
        }
    );

    QUnit.test("column width should depend on the widget", async function (assert) {
        serverData.models.foo.records = []; // the width heuristic only applies when there are no records
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="datetime" widget="date"/>
                    <field name="text"/>
                </tree>`,
        });
        assert.strictEqual(
            target.querySelector('th[data-name="datetime"]').offsetWidth,
            92,
            "should be the optimal width to display a date, not a datetime"
        );
    });

    QUnit.test("column widths are kept when adding first record", async function (assert) {
        serverData.models.foo.records = []; // in this scenario, we start with no records
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="datetime"/>
                    <field name="text"/>
                </tree>`,
        });

        var width = target.querySelectorAll('th[data-name="datetime"]')[0].offsetWidth;

        await click($(".o_list_button_add:visible").get(0));

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(
            target.querySelectorAll('th[data-name="datetime"]')[0].offsetWidth,
            width
        );
    });

    QUnit.test("column widths are kept when editing a record", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="datetime"/>
                    <field name="text"/>
                </tree>`,
        });

        var width = target.querySelectorAll('th[data-name="datetime"]')[0].offsetWidth;

        await click(target.querySelector(".o_data_row:nth-child(1) > .o_data_cell:nth-child(2)"));
        assert.containsOnce(target, ".o_selected_row");

        var longVal =
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, " +
            "justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum purus " +
            "bibendum est.";
        await editInput(target.querySelector(".o_field_widget[name=text] .o_input"), null, longVal);
        await clickSave(target);

        assert.containsNone(target, ".o_selected_row");
        assert.strictEqual(
            target.querySelectorAll('th[data-name="datetime"]')[0].offsetWidth,
            width
        );
    });

    QUnit.test("column widths are kept when switching records in edition", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="text"/>
                </tree>`,
        });

        const width = target.querySelectorAll('th[data-name="m2o"]')[0].offsetWidth;

        await click(target.querySelector(".o_data_row:nth-child(1) > .o_data_cell:nth-child(2)"));

        assert.hasClass(target.querySelector(".o_data_row:nth-child(1)"), "o_selected_row");
        assert.strictEqual(target.querySelectorAll('th[data-name="m2o"]')[0].offsetWidth, width);

        await click(target.querySelector(".o_data_row:nth-child(2) > .o_data_cell:nth-child(2)"));

        assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
        assert.strictEqual(target.querySelectorAll('th[data-name="m2o"]')[0].offsetWidth, width);
    });

    QUnit.test("column widths are re-computed on window resize", async function (assert) {
        serverData.models.foo.records[0].text =
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
            "Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus " +
            "ipsum purus bibendum est.";

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="datetime"/>
                    <field name="text"/>
                </tree>`,
        });

        const initialTextWidth = target.querySelectorAll('th[data-name="text"]')[0].offsetWidth;
        const selectorWidth = target.querySelectorAll("th.o_list_record_selector")[0].offsetWidth;

        // simulate a window resize
        target.style.width = target.getBoundingClientRect().width / 2 + "px";
        window.dispatchEvent(new Event("resize"));

        const postResizeTextWidth = target.querySelectorAll('th[data-name="text"]')[0].offsetWidth;
        const postResizeSelectorWidth = target.querySelectorAll("th.o_list_record_selector")[0]
            .offsetWidth;
        assert.ok(postResizeTextWidth < initialTextWidth);
        assert.strictEqual(selectorWidth, postResizeSelectorWidth);
    });

    QUnit.test(
        "columns with an absolute width are never narrower than that width",
        async function (assert) {
            serverData.models.foo.records[0].text =
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit, " +
                "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim " +
                "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo " +
                "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum " +
                "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, " +
                "sunt in culpa qui officia deserunt mollit anim id est laborum";
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="datetime"/>
                        <field name="int_field" width="200px"/>
                        <field name="text"/>
                    </tree>`,
            });
            const pixelsWidth = getComputedStyle(
                target.querySelector('th[data-name="int_field"]')
            ).width;
            const width = Math.floor(parseFloat(pixelsWidth));
            assert.strictEqual(width, 200);
        }
    );

    QUnit.test("list view with data: text columns are not crushed", async function (assert) {
        const longText =
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do " +
            "eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim " +
            "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo " +
            "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum " +
            "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, " +
            "sunt in culpa qui officia deserunt mollit anim id est laborum";
        serverData.models.foo.records[0].foo = longText;
        serverData.models.foo.records[0].text = longText;
        serverData.models.foo.records[1].foo = "short text";
        serverData.models.foo.records[1].text = "short text";
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="text"/></tree>',
        });

        const foo = [...target.querySelectorAll("th")].find((el) => el.textContent === "Foo");
        const fooWidth = Math.ceil(foo.getBoundingClientRect().width);

        const text = [...target.querySelectorAll("th")].find(
            (el) => el.textContent === "text field"
        );
        const textWidth = Math.ceil(text.getBoundingClientRect().width);

        assert.ok(
            Math.abs(fooWidth - textWidth) <= 1,
            "both columns should have been given the same width"
        );

        const firstRowHeight = $(target).find(".o_data_row:nth(0)")[0].offsetHeight;
        const secondRowHeight = $(target).find(".o_data_row:nth(1)")[0].offsetHeight;
        assert.ok(
            firstRowHeight > secondRowHeight,
            "in the first row, the (long) text field should be properly displayed on several lines"
        );
    });

    QUnit.test("button in a list view with a default relative width", async function (assert) {
        await makeView({
            type: "list",
            arch: `
                <tree>
                    <field name="foo"/>
                    <button name="the_button" icon="fa-heart" width="0.1"/>
                </tree>`,
            serverData,
            resModel: "foo",
        });

        assert.strictEqual(
            target.querySelector(".o_data_cell button").style.width,
            "",
            "width attribute should not change the CSS style"
        );
    });

    QUnit.test("button columns in a list view don't have a max width", async function (assert) {
        // set a long foo value s.t. the column can be squeezed
        serverData.models.foo.records[0].foo = "Lorem ipsum dolor sit amet";
        await makeView({
            type: "list",
            arch: `
                <tree>
                    <field name="foo"/>
                    <button name="b1" string="Do This"/>
                    <button name="b2" string="Do That"/>
                    <button name="b3" string="Or Rather Do Something Else"/>
                </tree>`,
            serverData,
            resModel: "foo",
        });

        // simulate a window resize (buttons column width should not be squeezed)
        target.style.width = "300px";
        window.dispatchEvent(new Event("resize"));
        await nextTick();

        assert.strictEqual(
            window.getComputedStyle(target.querySelectorAll("th")[1]).maxWidth,
            "92px",
            "max-width should be set on column foo to the minimum column width (92px)"
        );
        assert.strictEqual(
            window.getComputedStyle(target.querySelectorAll("th")[2]).maxWidth,
            "none",
            "no max-width should be harcoded on the buttons column"
        );
    });

    QUnit.test("column widths are kept when editing multiple records", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="datetime"/>
                    <field name="text"/>
                </tree>`,
        });

        var width = target.querySelector('th[data-name="datetime"]').offsetWidth;

        // select two records and edit
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");
        await click(rows[0].querySelectorAll(".o_data_cell")[1]);

        assert.containsOnce(target, ".o_selected_row");
        var longVal =
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, " +
            "justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum purus " +
            "bibendum est.";
        await editInput(target, ".o_field_widget[name=text] textarea", longVal);
        assert.containsOnce(document.body, ".modal");
        await click(target, ".modal .btn-primary");

        assert.containsNone(target, ".o_selected_row");
        assert.strictEqual(target.querySelector('th[data-name="datetime"]').offsetWidth, width);
    });

    QUnit.test(
        "row height and width should not change when switching mode",
        async function (assert) {
            // Warning: this test is css dependant
            serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
                force: true,
            });

            serverData.models.foo.fields.foo.translate = true;
            serverData.models.foo.fields.boolean = { type: "boolean", string: "Bool" };
            const currencies = {};
            serverData.models.res_currency.records.forEach((currency) => {
                currencies[currency.id] = currency;
            });
            patchWithCleanup(session, { currencies });

            // the width is hardcoded to make sure we have the same condition
            // between debug mode and non debug mode
            target.style.width = "1200px";
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="foo" required="1"/>
                        <field name="int_field" readonly="1"/>
                        <field name="boolean"/>
                        <field name="date"/>
                        <field name="text"/>
                        <field name="amount"/>
                        <field name="currency_id" column_invisible="1"/>
                        <field name="m2o"/>
                        <field name="m2m" widget="many2many_tags"/>
                    </tree>`,
            });
            const startHeight = target.querySelector(".o_data_row").offsetHeight;
            const startWidth = target.querySelector(".o_data_row").offsetWidth;

            // start edition of first row
            await click(target.querySelector(".o_data_row > td:not(.o_list_record_selector)"));
            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
            const editionHeight = target.querySelector(".o_data_row").offsetHeight;
            const editionWidth = target.querySelector(".o_data_row").offsetWidth;

            // leave edition
            await click($(".o_list_button_save:visible").get(0));
            const readonlyHeight = target.querySelector(".o_data_row").offsetHeight;
            const readonlyWidth = target.querySelector(".o_data_row").offsetWidth;

            assert.strictEqual(startHeight, editionHeight);
            assert.strictEqual(startHeight, readonlyHeight);
            assert.strictEqual(startWidth, editionWidth);
            assert.strictEqual(startWidth, readonlyWidth);
        }
    );

    QUnit.test("fields are translatable in list view", async function (assert) {
        serverData.models.foo.fields.foo.translate = true;
        serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
            force: true,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([
                        ["en_US", "English"],
                        ["fr_BE", "Frenglish"],
                    ]);
                }
                if (route === "/web/dataset/call_kw/foo/get_field_translations") {
                    return Promise.resolve([
                        [
                            { lang: "en_US", source: "yop", value: "yop" },
                            { lang: "fr_BE", source: "yop", value: "valeur français" },
                        ],
                        { translation_type: "char", translation_show_source: false },
                    ]);
                }
            },
            arch: '<tree editable="top">' + '<field name="foo" required="1"/>' + "</tree>",
        });
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

        await click(target.querySelector("span.o_field_translate"));
        assert.containsOnce(target, ".o_translation_dialog");
        assert.containsN(
            target.querySelector(".o_translation_dialog"),
            ".translation>input.o_field_char",
            2,
            "modal should have 2 languages to translate"
        );
    });

    QUnit.test("long words in text cells should break into smaller lines", async function (assert) {
        serverData.models.foo.records[0].text = "a";
        serverData.models.foo.records[1].text = "pneumonoultramicroscopicsilicovolcanoconiosis"; // longest english word I could find

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="text"/></tree>',
        });

        // Intentionally set the table width to a small size
        $(target).find("table").width("100px");
        $(target).find("th:last").width("100px");
        var shortText = $(target).find(".o_data_row:eq(0) td:last")[0].clientHeight;
        var longText = $(target).find(".o_data_row:eq(1) td:last")[0].clientHeight;
        var emptyText = $(target).find(".o_data_row:eq(2) td:last")[0].clientHeight;

        assert.strictEqual(
            shortText,
            emptyText,
            "Short word should not change the height of the cell"
        );
        assert.ok(longText > emptyText, "Long word should change the height of the cell");
    });

    QUnit.test("deleting one record and verify context key", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            actionMenus: {},
            arch: '<tree><field name="foo"/></tree>',
            mockRPC(route, args) {
                if (args.method === "unlink") {
                    assert.step("unlink");
                    const { context } = args.kwargs;
                    assert.strictEqual(context.ctx_key, "ctx_val");
                }
            },
            context: {
                ctx_key: "ctx_val",
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, "tbody td.o_list_record_selector", 4, "should have 4 records");

        await click(target.querySelector("tbody td.o_list_record_selector:first-child input"));

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");
        assert.hasClass(
            document.querySelector("body"),
            "modal-open",
            "body should have modal-open class"
        );

        await click(document, "body .modal footer button.btn-primary");

        assert.verifySteps(["unlink"]);

        assert.containsN(target, "tbody td.o_list_record_selector", 3, "should have 3 records");
    });

    QUnit.test("custom delete confirmation dialog", async (assert) => {
        const listView = registry.category("views").get("list");
        class CautiousController extends listView.Controller {
            get deleteConfirmationDialogProps() {
                const props = super.deleteConfirmationDialogProps;
                props.body = markup(
                    `<span class="text-danger">These are the consequences</span><br/>${props.body}`
                );
                return props;
            }
        }
        registry.category("views").add("caution", {
            ...listView,
            Controller: CautiousController,
        });

        await makeView({
            resModel: "foo",
            type: "list",
            arch: `
                <tree js_class="caution">
                    <field name="foo"/>
                </tree>
            `,
            serverData,
            actionMenus: {},
        });

        await click(target.querySelector("tbody td.o_list_record_selector:first-child input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");
        assert.containsOnce(
            document.body,
            ".modal:contains('you sure') .text-danger:contains('consequences')",
            "confirmation dialog should have markup and more"
        );

        await click(document, "body .modal footer button.btn-secondary");
        assert.containsN(
            target,
            "tbody td.o_list_record_selector",
            4,
            "nothing deleted, 4 records remain"
        );
    });

    QUnit.test(
        "deleting record which throws UserError should close confirmation dialog",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                actionMenus: {},
                arch: '<tree><field name="foo"/></tree>',
                mockRPC(route, args) {
                    if (args.method === "unlink") {
                        return Promise.reject({ message: "Odoo Server Error" });
                    }
                },
            });

            await click(target.querySelector("tbody td.o_list_record_selector:first-child input"));

            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Delete");
            assert.containsOnce(
                document.body,
                ".modal",
                "should have open the confirmation dialog"
            );

            await click(document, "body .modal footer button.btn-primary");
            assert.containsNone(document.body, ".modal", "confirmation dialog should be closed");
        }
    );

    QUnit.test("delete all records matching the domain", async function (assert) {
        assert.expect(6);

        serverData.models.foo.records.push({ id: 5, bar: true, foo: "xxx" });

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [["bar", "=", true]],
            mockRPC(route, args) {
                if (args.method === "unlink") {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
            },
            actionMenus: {},
        });
        patchWithCleanup(list.env.services.notification, {
            add: () => {
                throw new Error("should not display a notification");
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, "tbody td.o_list_record_selector", 2, "should have 2 records");

        await click(target.querySelector("thead .o_list_record_selector input"));

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target, ".o_list_selection_box .o_list_select_domain");

        await click(target, ".o_list_selection_box .o_list_select_domain");
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");

        assert.strictEqual(
            document.querySelectorAll(".modal").length,
            1,
            "a confirm modal should be displayed"
        );
        await click(document, "body .modal footer button.btn-primary");
    });

    QUnit.test("delete all records matching the domain (limit reached)", async function (assert) {
        assert.expect(8);

        serverData.models.foo.records.push({ id: 5, bar: true, foo: "xxx" });
        serverData.models.foo.records.push({ id: 6, bar: true, foo: "yyy" });

        patchWithCleanup(session, {
            active_ids_limit: 4,
        });
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [["bar", "=", true]],
            mockRPC(route, args) {
                if (args.method === "unlink") {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
            },
            actionMenus: {},
        });
        patchWithCleanup(list.env.services.notification, {
            add: () => {
                assert.step("notify");
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, "tbody td.o_list_record_selector", 2, "should have 2 records");

        await click(target.querySelector("thead .o_list_record_selector input"));

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target, ".o_list_selection_box .o_list_select_domain");

        await click(target.querySelector(".o_list_selection_box .o_list_select_domain"));
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");

        assert.strictEqual(
            document.querySelectorAll(".modal").length,
            1,
            "a confirm modal should be displayed"
        );
        await click(document, "body .modal footer button.btn-primary");

        assert.verifySteps(["notify"]);
    });

    QUnit.test("duplicate one record", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="top"><field name="foo"/></tree>`,
            actionMenus: {},
        });

        // Initial state: there should be 4 records
        assert.containsN(target, "tbody tr", 4, "should have 4 rows");

        // Duplicate one record
        await click(target.querySelector(".o_data_row input"));
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Duplicate");

        // Final state: there should be 5 records
        assert.containsN(target, "tbody tr", 5, "should have 5 rows");
    });

    QUnit.test("duplicate all records", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="top"><field name="foo"/></tree>`,
            actionMenus: {},
        });

        // Initial state: there should be 4 records
        assert.containsN(target, "tbody tr", 4, "should have 4 rows");

        // Duplicate all records
        await click(target.querySelector(".o_list_record_selector input"));
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Duplicate");

        // Final state: there should be 8 records
        assert.containsN(target, "tbody tr", 8, "should have 8 rows");
    });

    QUnit.test("archiving one record", async function (assert) {
        // add active field on foo model and make all records active
        serverData.models.foo.fields.active = { string: "Active", type: "boolean", default: true };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            actionMenus: {},
            arch: '<tree><field name="foo"/></tree>',
            mockRPC(route) {
                assert.step(route);
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, "tbody td.o_list_record_selector", 4, "should have 4 records");

        await click(target.querySelector("tbody td.o_list_record_selector:first-child input"));

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        assert.verifySteps([
            "/web/dataset/call_kw/foo/get_views",
            "/web/dataset/call_kw/foo/web_search_read",
        ]);
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Archive");

        assert.strictEqual(
            document.querySelectorAll(".modal").length,
            1,
            "a confirm modal should be displayed"
        );
        await click(document, ".modal-footer .btn-secondary");
        assert.containsN(
            target,
            "tbody td.o_list_record_selector",
            4,
            "still should have 4 records"
        );

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Archive");
        assert.strictEqual(
            document.querySelectorAll(".modal").length,
            1,
            "a confirm modal should be displayed"
        );
        await click(document, ".modal-footer .btn-primary");
        assert.containsN(target, "tbody td.o_list_record_selector", 3, "should have 3 records");
        assert.verifySteps([
            "/web/dataset/call_kw/foo/action_archive",
            "/web/dataset/call_kw/foo/web_search_read",
        ]);
    });

    QUnit.test("archive all records matching the domain", async function (assert) {
        assert.expect(6);
        // add active field on foo model and make all records active
        serverData.models.foo.fields.active = { string: "Active", type: "boolean", default: true };
        serverData.models.foo.records.push({ id: 5, bar: true, foo: "xxx" });

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [["bar", "=", true]],
            mockRPC(route, args) {
                if (args.method === "action_archive") {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
            },
            actionMenus: {},
        });
        patchWithCleanup(list.env.services.notification, {
            add: () => {
                throw new Error("should not display a notification");
            },
            loadActionMenus: true,
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, "tbody td.o_list_record_selector", 2, "should have 2 records");

        await click(target, "thead .o_list_record_selector input");

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target, ".o_list_selection_box .o_list_select_domain");

        await click(target, ".o_list_selection_box .o_list_select_domain");
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Archive");

        assert.strictEqual(
            document.querySelectorAll(".modal").length,
            1,
            "a confirm modal should be displayed"
        );
        await click(document, ".modal-footer .btn-primary");
    });

    QUnit.test("archive all records matching the domain (limit reached)", async function (assert) {
        assert.expect(8);

        // add active field on foo model and make all records active
        serverData.models.foo.fields.active = { string: "Active", type: "boolean", default: true };
        serverData.models.foo.records.push({ id: 5, bar: true, foo: "xxx" });
        serverData.models.foo.records.push({ id: 6, bar: true, foo: "yyy" });

        patchWithCleanup(session, {
            active_ids_limit: 4,
        });
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [["bar", "=", true]],
            mockRPC(route, args) {
                if (args.method === "action_archive") {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
            },
            actionMenus: {},
        });

        patchWithCleanup(list.env.services.notification, {
            add: () => {
                assert.step("notify");
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, "tbody td.o_list_record_selector", 2, "should have 2 records");

        await click(target, "thead .o_list_record_selector input");

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target, ".o_list_selection_box .o_list_select_domain");

        await click(target, ".o_list_selection_box .o_list_select_domain");
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Archive");

        assert.strictEqual($(".modal").length, 1, "a confirm modal should be displayed");
        await click(document.querySelector(".modal-footer .btn-primary"));

        assert.verifySteps(["notify"]);
    });

    QUnit.test("archive/unarchive handles returned action", async function (assert) {
        // add active field on foo model and make all records active
        serverData.models.foo.fields.active = { string: "Active", type: "boolean", default: true };

        serverData.actions = {
            11: {
                id: 11,
                name: "Action 11",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[3, "list"]],
                search_view_id: [9, "search"],
            },
        };
        serverData.views = {
            "foo,3,list": '<tree><field name="foo"/></tree>',
            "foo,9,search": `
                <search>
                    <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                </search>`,
            "bar,false,form": '<form><field name="display_name"/></form>',
        };

        const mockRPC = (route) => {
            if (route === "/web/dataset/call_kw/foo/action_archive") {
                return {
                    type: "ir.actions.act_window",
                    name: "Archive Action",
                    res_model: "bar",
                    view_mode: "form",
                    target: "new",
                    views: [[false, "form"]],
                };
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 11);

        assert.containsN(target, "tbody td.o_list_record_selector", 4, "should have 4 records");

        await click(target.querySelector("tbody td.o_list_record_selector input"));
        assert.containsOnce(target, ".o_cp_action_menus", "sidebar should be visible");

        await click(target.querySelector(".o_cp_action_menus .dropdown-toggle"));
        const archiveItem = [
            ...target.querySelectorAll(".o_cp_action_menus .dropdown-menu .o_menu_item"),
        ].filter((elem) => elem.textContent === "Archive");
        await click(archiveItem[0]);
        assert.strictEqual(
            document.querySelectorAll(".modal").length,
            1,
            "a confirm modal should be displayed"
        );

        await click(document.querySelector(".modal .modal-footer .btn-primary"));
        assert.strictEqual(
            document.querySelectorAll(".modal").length,
            1,
            "archive action dialog should be displayed"
        );
        assert.strictEqual(
            document.querySelector(".modal .modal-title").textContent.trim(),
            "Archive Action",
            "action wizard should have been opened"
        );
    });

    QUnit.test("apply custom static action menu (archive)", async function (assert) {
        // add active field on foo model and make all records active
        serverData.models.foo.fields.active = { string: "Active", type: "boolean", default: true };

        const listView = registry.category("views").get("list");
        class CustomListController extends listView.Controller {
            getStaticActionMenuItems() {
                const menuItems = super.getStaticActionMenuItems();
                menuItems.archive.callback = () => {
                    assert.step("customArchive");
                };
                return menuItems;
            }
        }
        registry.category("views").add("custom_list", {
            ...listView,
            Controller: CustomListController,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree js_class="custom_list">
                    <field name="foo"/>
                </tree>`,
            actionMenus: {},
        });
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await click(target, "thead .o_list_record_selector input");
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Archive");
        assert.verifySteps(["customArchive"]);
    });

    QUnit.test("add custom static action menu", async function (assert) {
        const listView = registry.category("views").get("list");
        class CustomListController extends listView.Controller {
            getStaticActionMenuItems() {
                const menuItems = super.getStaticActionMenuItems();
                menuItems.customAvailable = {
                    isAvailable: () => true,
                    description: "Custom Available",
                    sequence: 35,
                    callback: () => {
                        assert.step("Custom Available");
                    },
                };
                menuItems.customNotAvailable = {
                    isAvailable: () => false,
                    description: "Custom Not Available",
                    callback: () => {
                        assert.step("Custom Not Available");
                    },
                };
                menuItems.customDefaultAvailable = {
                    description: "Custom Default Available",
                    callback: () => {
                        assert.step("Custom Default Available");
                    },
                };
                return menuItems;
            }
        }
        registry.category("views").add("custom_list", {
            ...listView,
            Controller: CustomListController,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree js_class="custom_list">
                    <field name="foo"/>
                </tree>`,
            actionMenus: {},
        });
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await click(target, "thead .o_list_record_selector input");
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await toggleActionMenu(target);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_cp_action_menus .dropdown-item")),
            ["Custom Default Available", "Export", "Duplicate", "Custom Available", "Delete"]
        );

        await toggleMenuItem(target, "Custom Available");
        assert.verifySteps(["Custom Available"]);

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Custom Default Available");
        assert.verifySteps(["Custom Default Available"]);
    });

    QUnit.test(
        "grouped, update the count of the group (and ancestors) when a record is deleted",
        async function (assert) {
            serverData.models.foo.records = [
                { id: 121, foo: "blip", bar: true },
                { id: 122, foo: "blip", bar: true },
                { id: 123, foo: "blip", bar: true },
                { id: 124, foo: "blip", bar: true },
                { id: 125, foo: "blip", bar: false },
                { id: 126, foo: "blip", bar: false },
            ];
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: /*xml*/ `
                    <tree expand="1">
                        <field name="foo"/>
                    </tree>`,
                groupBy: ["foo", "bar"],
                actionMenus: {},
            });
            assert.strictEqual(
                target.querySelector(".o_group_header:first-child").textContent.trim(),
                "blip (6)"
            );
            assert.strictEqual(
                target.querySelector(".o_group_header:nth-child(2)").textContent.trim(),
                "No (2)"
            );

            const secondNestedGroup = target.querySelector(".o_group_header:nth-child(3)");
            assert.strictEqual(secondNestedGroup.textContent.trim(), "Yes (4)");
            await click(secondNestedGroup);
            assert.containsN(target, ".o_data_row", 4);

            await click(target.querySelector(".o_data_row input"));
            await toggleActionMenu(target);
            await toggleMenuItem(target, "Delete");
            await click(target, ".modal .btn-primary");
            assert.strictEqual(
                target.querySelector(".o_group_header:first-child").textContent.trim(),
                "blip (5)"
            );
            assert.strictEqual(
                target.querySelector(".o_group_header:nth-child(3)").textContent.trim(),
                "Yes (3)"
            );
        }
    );

    QUnit.test("pager (ungrouped and grouped mode), default limit", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            searchViewArch: `
                <search>
                    <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
                </search>`,
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.limit, 80, "default limit should be 80 in List");
                }
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_pager .o_pager");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Bar");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "2");
    });

    QUnit.test("pager, ungrouped, with count limit reached", async function (assert) {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

        let expectedCountLimit = 4;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.count_limit, expectedCountLimit);
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        await click(target.querySelector(".o_pager_limit"));
        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        assert.verifySteps(["search_count"]);

        expectedCountLimit = undefined;
        await click(target.querySelector(".o_pager_next"));
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("pager, ungrouped, with count limit reached, click next", async function (assert) {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

        let expectedCountLimit = 4;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.count_limit, expectedCountLimit);
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        expectedCountLimit = 5;
        await click(target.querySelector(".o_pager_next"));
        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "3-4");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("pager, ungrouped, with count limit reached, click next (2)", async (assert) => {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
        serverData.models.foo.records.push({ id: 5, bar: true, foo: "xxx" });

        let expectedCountLimit = 4;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.count_limit, expectedCountLimit);
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        expectedCountLimit = 5;
        await click(target.querySelector(".o_pager_next"));
        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "3-4");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4+");
        assert.verifySteps(["web_search_read"]);

        expectedCountLimit = 7;
        await click(target.querySelector(".o_pager_next"));
        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "5-5");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5");
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("pager, ungrouped, with count limit reached, click previous", async (assert) => {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
        serverData.models.foo.records.push({ id: 5, bar: true, foo: "xxx" });

        let expectedCountLimit = 4;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.count_limit, expectedCountLimit);
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        expectedCountLimit = undefined;
        await click(target.querySelector(".o_pager_previous"));
        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "5-5");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5");
        assert.verifySteps(["search_count", "web_search_read"]);
    });

    QUnit.test("pager, ungrouped, with count limit reached, edit pager", async (assert) => {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
        serverData.models.foo.records.push({ id: 5, bar: true, foo: "xxx" });

        let expectedCountLimit = 4;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.count_limit, expectedCountLimit);
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        expectedCountLimit = 5;
        await click(target, ".o_pager_value");
        await editInput(target, "input.o_pager_value", "2-4");
        assert.containsN(target, ".o_data_row", 3);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "2-4");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4+");
        assert.verifySteps(["web_search_read"]);

        expectedCountLimit = 15;
        await click(target, ".o_pager_value");
        await editInput(target, "input.o_pager_value", "2-14");
        assert.containsN(target, ".o_data_row", 4);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "2-5");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5");
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("pager, ungrouped, with count equals count limit", async function (assert) {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 4 });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        assert.verifySteps(["get_views", "web_search_read"]);
    });

    QUnit.test("pager, ungrouped, reload while fetching count", async function (assert) {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

        const def = makeDeferred();
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            async mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "search_count") {
                    await def;
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        await click(target.querySelector(".o_pager_limit"));
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["search_count"]);

        await reloadListView(target);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["web_search_read"]);

        def.resolve();
        await nextTick();
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps([]);
    });

    QUnit.test("pager, ungrouped, next and fetch count simultaneously", async function (assert) {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 5 });
        serverData.models.foo.records.push({ id: 11, foo: "r11", bar: true });
        serverData.models.foo.records.push({ id: 12, foo: "r12", bar: true });
        serverData.models.foo.records.push({ id: 13, foo: "r13", bar: true });

        let def;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
            async mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_search_read") {
                    await def;
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5+");
        assert.verifySteps(["get_views", "web_search_read"]);

        def = makeDeferred();
        await click(target.querySelector(".o_pager_next")); // this request will be pending
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5+");
        // can't fetch count simultaneously as it is temporarily disabled while updating
        assert.hasClass(target.querySelector(".o_pager_limit"), "disabled");
        assert.verifySteps(["web_search_read"]);

        def.resolve();
        await nextTick();
        assert.doesNotHaveClass(target.querySelector(".o_pager_limit"), "disabled");
    });

    QUnit.test("pager, grouped, with groups count limit reached", async function (assert) {
        patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
        serverData.models.foo.records.push({ id: 398, foo: "ozfijz" }); // to have 4 groups

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree groups_limit="2"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["foo"],
        });

        assert.containsN(target, ".o_group_header", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
    });

    QUnit.test("pager, grouped, with count limit reached", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="1"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["foo"],
        });

        assert.containsN(target, ".o_group_header", 3, "should have 3 groups");
        assert.containsOnce(
            target,
            ".o_group_header:first-of-type .o_group_name",
            "first group should have a name"
        );
        assert.containsNone(
            target,
            ".o_group_header:first-of-type .o_pager",
            "pager shouldn't be present until unfolded"
        );
        // unfold
        await click(target.querySelector(".o_group_header:first-of-type"));
        assert.containsOnce(
            target,
            ".o_group_header:first-of-type .o_group_name .o_pager",
            "first group should have a pager"
        );
        assert.strictEqual(
            target.querySelector(".o_group_header:first-of-type .o_pager_value").innerText,
            "1"
        );
        assert.strictEqual(
            target.querySelector(".o_group_header:first-of-type .o_pager_limit").innerText,
            "2"
        );
    });

    QUnit.test("count_limit attrs set in arch", async function (assert) {
        let expectedCountLimit = 4;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2" count_limit="3"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.count_limit, expectedCountLimit);
                }
            },
        });

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        await click(target.querySelector(".o_pager_limit"));
        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        assert.verifySteps(["search_count"]);

        expectedCountLimit = undefined;
        await click(target.querySelector(".o_pager_next"));
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test(
        "pager, grouped, pager limit should be based on the group's count",
        async function (assert) {
            patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
            serverData.models.foo.records = [
                { id: 121, foo: "blip" },
                { id: 122, foo: "blip" },
                { id: 123, foo: "blip" },
                { id: 124, foo: "blip" },
                { id: 125, foo: "blip" },
                { id: 126, foo: "blip" },
            ];
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
                groupBy: ["foo"],
            });

            // unfold
            await click(target.querySelector(".o_group_header:first-of-type"));
            assert.strictEqual(
                target.querySelector(".o_group_header:first-of-type .o_pager_limit").innerText,
                "6"
            );
        }
    );

    QUnit.test(
        "pager, grouped, group pager should update after removing a filter",
        async function (assert) {
            patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
            serverData.models.foo.records = [
                { id: 121, foo: "aaa" },
                { id: 122, foo: "blip" },
                { id: 123, foo: "blip" },
                { id: 124, foo: "blip" },
                { id: 125, foo: "blip" },
                { id: 126, foo: "blip" },
            ];
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="2"><field name="foo"/><field name="bar"/></tree>',
                searchViewArch: `
                    <search>
                        <filter name="foo" domain="[('foo','=','aaa')]"/>
                        <filter name="groupby_foo" context="{'group_by': 'bar'}"/>
                    </search>`,
            });

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Foo");
            await toggleMenuItem(target, "Bar");

            // expand group
            await click(target, "th.o_group_name");

            assert.containsNone(target, "th.o_group_name .o_pager_counter");

            // remove filter
            await removeFacet(target);

            assert.strictEqual(
                $(target).find("th.o_group_name:eq(0) .o_pager_counter").text().trim(),
                "1-2 / 6"
            );
        }
    );

    QUnit.test(
        "grouped, show only limited records when the list view is initially expanded",
        async function (assert) {
            const forcedDefaultLimit = 3;
            patchWithCleanup(RelationalModel, { DEFAULT_LIMIT: forcedDefaultLimit });

            serverData.models.foo.records = [
                { id: 121, foo: "blip" },
                { id: 122, foo: "blip" },
                { id: 123, foo: "blip" },
                { id: 124, foo: "blip" },
                { id: 125, foo: "blip" },
                { id: 126, foo: "blip" },
            ];
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: /*xml*/ `
                    <tree expand="1">
                        <field name="foo"/>
                    </tree>`,
                groupBy: ["foo"],
            });

            assert.containsN(target, ".o_data_row", forcedDefaultLimit);
        }
    );

    QUnit.test("list keeps offset on switchView", async (assert) => {
        assert.expect(3);
        serverData.views = {
            "foo,false,search": `<search />`,
            "foo,99,list": `<list limit="1"><field name="display_name" /></list>`,
            "foo,100,form": `<form><field name="display_name" /></form>`,
        };

        const offsets = [0, 1, 1];
        const mockRPC = async (route, args) => {
            if (args.method === "web_search_read") {
                assert.strictEqual(args.kwargs.offset, offsets.shift());
            }
        };
        const wc = await createWebClient({ serverData, mockRPC });
        await doAction(wc, {
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [
                [99, "list"],
                [100, "form"],
            ],
        });
        await click(target, ".o_pager_next");
        await click(target, ".o_data_cell");
        await click(target, ".o_back_button");
    });

    QUnit.test(
        "Navigate between the list and kanban view using the command palette",
        async (assert) => {
            serverData.views = {
                "foo,false,search": `<search />`,
                "foo,false,list": `<list><field name="display_name" /></list>`,
                "foo,false,kanban": `
                <kanban class="o_kanban_test">
                    <templates><t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
            };
            registry.category("command_categories").add("view_switcher", {});

            const wc = await createWebClient({ serverData });
            await doAction(wc, {
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "kanban"],
                ],
            });
            assert.containsN(
                target,
                ".o_cp_switch_buttons",
                2,
                "Should have 2 button (small and xl screens)"
            );
            assert.containsN(target, ".o_switch_view", 2);
            assert.containsOnce(target, ".o_list_view");

            triggerHotkey("control+k");
            await nextTick();
            assert.containsOnce(target.querySelector(".o_command_category"), ".o_command");
            let command = target.querySelector(".o_command_category .o_command");
            assert.strictEqual(command.textContent, "Show Kanban view");

            await click(command);
            assert.containsOnce(target, ".o_kanban_view");

            triggerHotkey("control+k");
            await nextTick();
            assert.containsOnce(target.querySelector(".o_command_category"), ".o_command");
            command = target.querySelector(".o_command_category .o_command");
            assert.strictEqual(command.textContent, "Show List view");
            await click(command);
            assert.containsOnce(target, ".o_list_view");
        }
    );

    QUnit.test("can sort records when clicking on header", async function (assert) {
        serverData.models.foo.fields.foo.sortable = true;

        let nbSearchRead = 0;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    nbSearchRead++;
                }
            },
        });

        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(
            $(target).find("tbody tr:first td:contains(yop)").length,
            "record 1 should be first"
        );
        assert.ok(
            $(target).find("tbody tr:eq(3) td:contains(blip)").length,
            "record 3 should be first"
        );

        nbSearchRead = 0;
        await click($(target).find("thead th:contains(Foo)")[0]);
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(
            $(target).find("tbody tr:first td:contains(blip)").length,
            "record 3 should be first"
        );
        assert.ok(
            $(target).find("tbody tr:eq(3) td:contains(yop)").length,
            "record 1 should be first"
        );

        nbSearchRead = 0;
        await click($(target).find("thead th:contains(Foo)")[0]);
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(
            $(target).find("tbody tr:first td:contains(yop)").length,
            "record 3 should be first"
        );
        assert.ok(
            $(target).find("tbody tr:eq(3) td:contains(blip)").length,
            "record 1 should be first"
        );
    });

    QUnit.test("do not sort records when clicking on header with nolabel", async function (assert) {
        serverData.models.foo.fields.foo.sortable = true;

        let nbSearchRead = 0;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo" nolabel="1"/><field name="int_field"/></tree>',
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    nbSearchRead++;
                }
            },
        });

        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.strictEqual($(target).find(".o_data_cell").text(), "yop10blip9gnap17blip-4");

        await click(target.querySelectorAll("thead th")[2]);
        assert.strictEqual(nbSearchRead, 2, "should have done one other search_read");
        assert.strictEqual($(target).find(".o_data_cell").text(), "blip-4blip9yop10gnap17");

        await click(target.querySelectorAll("thead th")[1]);
        assert.strictEqual(nbSearchRead, 2, "shouldn't have done anymore search_read");
        assert.strictEqual($(target).find(".o_data_cell").text(), "blip-4blip9yop10gnap17");
    });

    QUnit.test("use default_order", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree default_order="foo"><field name="foo"/><field name="bar"/></tree>',
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    assert.strictEqual(
                        args.kwargs.order,
                        "foo ASC",
                        "should correctly set the sort attribute"
                    );
                }
            },
        });

        assert.ok(
            $(target).find("tbody tr:first td:contains(blip)").length,
            "record 3 should be first"
        );
        assert.ok(
            $(target).find("tbody tr:eq(3) td:contains(yop)").length,
            "record 1 should be first"
        );
    });

    QUnit.test("use more complex default_order", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree default_order="foo, bar desc, int_field">' +
                '<field name="foo"/><field name="bar"/>' +
                "</tree>",
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    assert.strictEqual(
                        args.kwargs.order,
                        "foo ASC, bar DESC, int_field ASC",
                        "should correctly set the sort attribute"
                    );
                }
            },
        });

        assert.ok(
            $(target).find("tbody tr:first td:contains(blip)").length,
            "record 3 should be first"
        );
        assert.ok(
            $(target).find("tbody tr:eq(3) td:contains(yop)").length,
            "record 1 should be first"
        );
    });

    QUnit.test("use default_order on editable tree: sort on save", async function (assert) {
        serverData.models.foo.records[0].o2m = [1, 3];

        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="o2m">
                            <tree editable="bottom" default_order="display_name">
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
                (el) => el.textContent
            ),
            ["Value 1", "Value 3"]
        );

        await addRow(target);
        await editInput(target, ".o_field_widget[name=o2m] .o_field_widget input", "Value 2");
        await click(target, ".o_form_view");
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
                (el) => el.textContent
            ),
            ["Value 1", "Value 3", "Value 2"]
        );

        await clickSave(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
                (el) => el.textContent
            ),
            ["Value 1", "Value 2", "Value 3"]
        );
    });

    QUnit.test("use default_order on editable tree: sort on demand", async function (assert) {
        serverData.models.foo.records[0].o2m = [1, 3];
        serverData.models.bar.fields = {
            ...serverData.models.bar.fields,
            name: { string: "Name", type: "char", sortable: true },
        };
        serverData.models.bar.records[0].name = "Value 1";
        serverData.models.bar.records[2].name = "Value 3";

        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="o2m">
                            <tree editable="bottom" default_order="name">
                                <field name="name"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
                (el) => el.textContent
            ),
            ["Value 1", "Value 3"]
        );

        await addRow(target);
        await editInput(target, ".o_field_widget[name=o2m] .o_field_widget input", "Value 2");
        await click(target, ".o_form_view");
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
                (el) => el.textContent
            ),
            ["Value 1", "Value 3", "Value 2"]
        );

        await click(target, ".o_field_widget[name=o2m] .o_column_sortable");
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
                (el) => el.textContent
            ),
            ["Value 1", "Value 2", "Value 3"]
        );

        await click(target, ".o_field_widget[name=o2m] .o_column_sortable");
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
                (el) => el.textContent
            ),
            ["Value 3", "Value 2", "Value 1"]
        );
    });

    QUnit.test(
        "use default_order on editable tree: sort on demand in page",
        async function (assert) {
            serverData.models.bar.fields = {
                ...serverData.models.bar.fields,
                name: { string: "Name", type: "char", sortable: true },
            };

            const ids = [];
            for (let i = 0; i < 45; i++) {
                const id = 4 + i;
                ids.push(id);
                serverData.models.bar.records.push({
                    id: id,
                    name: "Value " + (id < 10 ? "0" : "") + id,
                });
            }
            serverData.models.foo.records[0].o2m = ids;

            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="o2m">
                                <tree editable="bottom" default_order="name">
                                    <field name="name"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            await pagerNext(target.querySelector(".o_field_widget[name=o2m]"));
            assert.strictEqual(
                target.querySelector("tbody tr").textContent,
                "Value 44",
                "record 44 should be first"
            );
            assert.strictEqual(
                target.querySelectorAll("tbody tr")[4].textContent,
                "Value 48",
                "record 48 should be last"
            );

            await click(target.querySelector(".o_column_sortable"));
            assert.strictEqual(
                target.querySelector("tbody tr").textContent,
                "Value 08",
                "record 48 should be first"
            );
            assert.strictEqual(
                target.querySelectorAll("tbody tr")[4].textContent,
                "Value 04",
                "record 44 should be first"
            );
        }
    );

    QUnit.test("can display button in edit mode", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <button name="notafield" type="object" icon="fa-asterisk" class="o_yeah"/>
                </tree>`,
        });
        assert.containsN(target, "tbody button[name=notafield]", 4);
        assert.containsN(
            target,
            "tbody button[name=notafield].o_yeah",
            4,
            "class o_yeah should be set on the four button"
        );

        await click(target.querySelector(".o_field_cell"));
        assert.containsOnce(target, ".o_selected_row button[name=notafield]");
    });

    QUnit.test("can display a list with a many2many field", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree><field name="m2m"/></tree>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        assert.verifySteps(["get_views", "web_search_read"]);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "2 records",
            "3 records",
            "No records",
            "1 record",
        ]);
    });

    QUnit.test("display a tooltip on a field", async function (assert) {
        patchWithCleanup(odoo, {
            debug: false,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar" widget="boolean_favorite"/>
                </tree>`,
        });

        await mouseEnter(target.querySelector("th[data-name=foo]"));
        await nextTick(); // GES: see next nextTick comment
        assert.strictEqual(
            target.querySelectorAll(".o-tooltip .o-tooltip--technical").length,
            0,
            "should not have rendered a tooltip"
        );

        patchWithCleanup(odoo, {
            debug: true,
        });

        // it is necessary to rerender the list so tooltips can be properly created
        await reloadListView(target);
        await mouseEnter(target.querySelector("th[data-name=bar]"));
        await nextTick(); // GES: I had once an indetermist failure because of no tooltip, so for safety I add a nextTick.

        assert.strictEqual(
            target.querySelectorAll(".o-tooltip .o-tooltip--technical").length,
            1,
            "should have rendered a tooltip"
        );

        assert.containsOnce(
            target,
            '.o-tooltip--technical>li[data-item="widget"]',
            "widget should be present for this field"
        );

        assert.deepEqual(
            getNodesTextContent([
                target.querySelector('.o-tooltip--technical>li[data-item="widget"]'),
            ]),
            ["Widget:Favorite (boolean_favorite) "],
            "widget description should be correct"
        );
    });

    QUnit.test("support row decoration", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree decoration-info="int_field > 5">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(
            target,
            "tbody tr.text-info",
            3,
            "should have 3 columns with text-info class"
        );

        assert.containsN(target, "tbody tr", 4, "should have 4 rows");
    });

    QUnit.test("support row decoration (with unset numeric values)", async function (assert) {
        serverData.models.foo.records = [];

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="bottom" decoration-danger="int_field &lt; 0">' +
                '<field name="int_field"/>' +
                "</tree>",
        });

        await click($(".o_list_button_add:visible").get(0));
        assert.containsNone(
            target,
            "tr.o_data_row.text-danger",
            "the data row should not have .text-danger decoration (int_field is unset)"
        );

        await editInput(target, '[name="int_field"] input', "-3");
        assert.containsOnce(
            target,
            "tr.o_data_row.text-danger",
            "the data row should have .text-danger decoration (int_field is negative)"
        );
    });

    QUnit.test("support row decoration with date", async function (assert) {
        serverData.models.foo.records[0].datetime = "2017-02-27 12:51:35";

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree decoration-info="datetime == '2017-02-27 12:51:35'" decoration-danger="datetime &gt; '2017-02-27 12:51:35' and datetime &lt; '2017-02-27 10:51:35'">
                    <field name="datetime"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsOnce(
            target,
            "tbody tr.text-info",
            "should have 1 columns with text-info class with good datetime"
        );

        assert.containsNone(
            target,
            "tbody tr.text-danger",
            "should have 0 columns with text-danger class with wrong timezone datetime"
        );

        assert.containsN(target, "tbody tr", 4, "should have 4 rows");
    });

    QUnit.test("support row decoration (decoration-bf)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree decoration-bf="int_field > 5">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(target, "tbody tr.fw-bold", 3, "should have 3 columns with fw-bold class");

        assert.containsN(target, "tbody tr", 4, "should have 4 rows");
    });

    QUnit.test("support row decoration (decoration-it)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree decoration-it="int_field > 5">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(
            target,
            "tbody tr.fst-italic",
            3,
            "should have 3 columns with fst-italic class"
        );

        assert.containsN(target, "tbody tr", 4, "should have 4 rows");
    });

    QUnit.test("support field decoration", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo" decoration-danger="int_field > 5"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(target, "tbody tr", 4);
        assert.containsN(target, "tbody td.o_list_char", 4);
        assert.containsN(target, "tbody td.text-danger", 3);
        assert.containsN(target, "tbody td.o_list_number", 4);
        assert.containsNone(target, "tbody td.o_list_number.text-danger");
    });

    QUnit.test("support field decoration (decoration-bf)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo" decoration-bf="int_field > 5"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(target, "tbody tr", 4);
        assert.containsN(target, "tbody td.o_list_char", 4);
        assert.containsN(target, "tbody td.fw-bold", 3);
        assert.containsN(target, "tbody td.o_list_number", 4);
        assert.containsNone(target, "tbody td.o_list_number.fw-bold");
    });

    QUnit.test("support field decoration (decoration-it)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo" decoration-it="int_field > 5"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(target, "tbody tr", 4);
        assert.containsN(target, "tbody td.o_list_char", 4);
        assert.containsN(target, "tbody td.fst-italic", 3);
        assert.containsN(target, "tbody td.o_list_number", 4);
        assert.containsNone(target, "tbody td.o_list_number.fst-italic");
    });

    QUnit.test(
        "bounce create button when no data and click on empty area",
        async function (assert) {
            patchWithCleanup(browser, {
                setTimeout: () => {},
            });
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree><field name="foo"/></tree>',
                noContentHelp: "click to add a record",
                searchViewArch: `
                    <search>
                        <filter name="Empty List" domain="[('id', '&lt;', 0)]"/>
                    </search>`,
            });

            assert.containsNone(target, ".o_view_nocontent");
            await click(target, ".o_list_view");
            assert.doesNotHaveClass(
                target.querySelector(".o_list_button_add"),
                "o_catch_attention"
            );

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Empty List");
            assert.containsOnce(target, ".o_view_nocontent");

            await click(target, ".o_nocontent_help");
            assert.hasClass(target.querySelector(".o_list_button_add"), "o_catch_attention");
        }
    );

    QUnit.test("no content helper when no data", async function (assert) {
        const records = serverData.models.foo.records;

        serverData.models.foo.records = [];

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
            noContentHelp: "click to add a partner",
        });
        assert.containsOnce(target, ".o_view_nocontent", "should display the no content helper");
        assert.containsOnce(target, ".o_list_view table", "should have a table in the dom");
        assert.deepEqual(
            [...target.querySelectorAll(".o_view_nocontent")].map((el) => el.textContent),
            ["click to add a partner"]
        );

        serverData.models.foo.records = records;
        await reloadListView(target);

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "should not display the no content helper"
        );
    });

    QUnit.test("no nocontent helper when no data and no help", async function (assert) {
        serverData.models.foo.records = [];

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "should not display the no content helper"
        );
        assert.containsNone(target, "tr.o_data_row", "should not have any data row");
        assert.containsOnce(target, ".o_list_view table", "should have a table in the dom");
    });

    QUnit.test("empty list with sample data", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                    <field name="m2o"/>
                    <field name="m2m" widget="many2many_tags"/>
                    <field name="date"/>
                    <field name="datetime"/>
                </tree>`,
            context: { search_default_empty: true },
            noContentHelp: "click to add a partner",
            searchViewArch: `
                <search>
                    <filter name="empty" domain="[('id', '&lt;', 0)]"/>
                    <filter name="True Domain" domain="[(1,'=',1)]"/>
                    <filter name="False Domain" domain="[(1,'=',0)]"/>
                </search>`,
        });

        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 10);
        assert.containsOnce(target, ".o_nocontent_help");

        // Check list sample data
        const firstRow = target.querySelector(".o_data_row");
        const cells = firstRow.querySelectorAll(":scope > .o_data_cell");
        assert.strictEqual(
            cells[0].innerText.trim(),
            "",
            "Char field should yield an empty element"
        );
        assert.containsOnce(cells[1], ".o-checkbox", "Boolean field has been instantiated");
        assert.notOk(isNaN(cells[2].innerText.trim()), "Intger value is a number");
        assert.ok(cells[3].innerText.trim(), "Many2one field is a string");

        const firstM2MTag = cells[4].querySelector(":scope div.o_tag_badge_text").innerText.trim();
        assert.ok(firstM2MTag.length > 0, "Many2many contains at least one string tag");

        assert.ok(
            /\d{2}\/\d{2}\/\d{4}/.test(cells[5].innerText.trim()),
            "Date field should have the right format"
        );
        assert.ok(
            /\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}/.test(cells[6].innerText.trim()),
            "Datetime field should have the right format"
        );

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "empty");
        await toggleMenuItem(target, "False Domain");
        assert.doesNotHaveClass(
            target.querySelector(".o_list_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsOnce(target, ".o_list_table");
        assert.containsOnce(target, ".o_nocontent_help");

        await toggleMenuItem(target, "False Domain");
        await toggleMenuItem(target, "True Domain");
        assert.doesNotHaveClass(
            target.querySelector(".o_list_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone(target, ".o_nocontent_help");
    });

    QUnit.test("refresh empty list with sample data", async function (assert) {
        serverData.views = {
            "foo,false,search": `
                <search>
                    <filter name="empty" domain="[('id', '&lt;', 0)]"/>
                </search>`,
            "foo,false,list": `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                    <field name="m2o"/>
                    <field name="m2m" widget="many2many_tags"/>
                    <field name="date"/>
                    <field name="datetime"/>
                </tree>`,
            "foo,false,kanban": "<kanban></kanban>",
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "kanban"],
            ],
            context: { search_default_empty: true },
            help: '<p class="hello">click to add a partner</p>',
        });
        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 10);
        assert.containsOnce(target, ".o_nocontent_help");

        const textContent = target.querySelector(".o_list_view").textContent;
        await click(target, ".o_cp_switch_buttons .o_list");
        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 10);
        assert.containsOnce(target, ".o_nocontent_help");
        assert.strictEqual(target.querySelector(".o_list_view").textContent, textContent);
    });

    QUnit.test("empty list with sample data: toggle optional field", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="m2o" optional="hide"/>
                </tree>`,
            domain: Domain.FALSE.toList(),
        });
        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.ok(target.querySelectorAll(".o_data_row").length > 0);
        assert.containsN(
            target,
            "th",
            3,
            "should have 3 th, 1 for selector, 1 for foo and 1 for optional columns"
        );
        assert.containsOnce(target, "table .o_optional_columns_dropdown");

        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");

        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");

        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.ok(target.querySelectorAll(".o_data_row").length > 0);
        assert.containsN(target, "th", 4);
    });

    QUnit.test("empty list with sample data: keyboard navigation", async function (assert) {
        await makeView({
            type: "list",
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            serverData,
            domain: Domain.FALSE.toList(),
            resModel: "foo",
        });

        // Check keynav is disabled
        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");

        // From search bar
        assert.hasClass(document.activeElement, "o_searchview_input");

        triggerHotkey("arrowdown");
        await nextTick();

        assert.hasClass(document.activeElement, "o_searchview_input");

        // From 'Create' button
        $(".o_list_button_add:visible").get(0).focus();

        assert.hasClass(document.activeElement, "o_list_button_add");

        triggerHotkey("arrowdown");
        await nextTick();

        assert.hasClass(document.activeElement, "o_list_button_add");

        triggerHotkey("tab");
        await nextTick();

        assert.containsNone(document.body, ".o-tooltip--string");

        // From column header
        target.querySelector(':scope th[data-name="foo"]').focus();

        assert.ok(document.activeElement.dataset.name === "foo");

        triggerHotkey("arrowdown");
        await nextTick();

        assert.ok(document.activeElement.dataset.name === "foo");
    });

    QUnit.test("empty list with sample data: group by date", async (assert) => {
        await makeView({
            type: "list",
            arch: `
                <tree sample="1">
                    <field name="date"/>
                </tree>`,
            serverData,
            domain: Domain.FALSE.toList(),
            resModel: "foo",
            groupBy: ["date:day"],
        });

        assert.containsOnce(target, ".o_list_view .o_view_sample_data");
        const groupHeaders = [...target.querySelectorAll(".o_group_header")];
        assert.ok(groupHeaders.length);

        await click(target.querySelector(".o_group_has_content.o_group_header"));
        assert.containsN(target, ".o_data_row", 4);
    });

    QUnit.test("non empty list with sample data", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            domain: Domain.TRUE.toList(),
            context: { search_default_true_domain: true },
            searchViewArch: `
                    <search>
                        <filter name="true_domain" domain="[(1,'=',1)]"/>
                        <filter name="false_domain" domain="[(1,'=',0)]"/>
                    </search>`,
        });

        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 4);
        assert.doesNotHaveClass(
            target.querySelector(".o_list_view .o_content"),
            "o_view_sample_data"
        );

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "true_domain");
        await toggleMenuItem(target, "false_domain");
        assert.containsOnce(target, ".o_list_table");
        assert.containsNone(target, ".o_data_row");
        assert.doesNotHaveClass(
            target.querySelector(".o_list_view .o_content"),
            "o_view_sample_data"
        );
    });

    QUnit.test("click on header in empty list with sample data", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
            domain: Domain.FALSE.toList(),
        });

        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 10);

        const content = target.querySelector(".o_list_view").textContent;

        await click(target.querySelector("tr .o_column_sortable"));
        assert.strictEqual(
            target.querySelector(".o_list_view").textContent,
            content,
            "the content should still be the same"
        );
    });

    QUnit.test(
        "non empty editable list with sample data: delete all records",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top" sample="1">
                        <field name="foo"/>
                        <field name="bar"/>
                        <field name="int_field"/>
                    </tree>`,
                domain: Domain.TRUE.toList(),
                noContentHelp: "click to add a partner",
                actionMenus: {},
            });

            // Initial state: all records displayed
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_list_table");
            assert.containsN(target, ".o_data_row", 4);
            assert.containsNone(target, ".o_nocontent_help");

            // Delete all records
            await click(target.querySelector("thead .o_list_record_selector input"));
            await toggleActionMenu(target);
            await toggleMenuItem(target, "Delete");
            await click(target.querySelector(".modal-footer .btn-primary"));

            // Final state: no more sample data, but nocontent helper displayed
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_list_table");
            assert.containsOnce(target, ".o_nocontent_help");
        }
    );

    QUnit.test(
        "empty editable list with sample data: start create record and cancel",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree editable="top" sample="1">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="int_field"/>
                </tree>`,
                domain: Domain.FALSE.toList(),
                noContentHelp: "click to add a partner",
            });

            // Initial state: sample data and nocontent helper displayed
            assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
            assert.containsOnce(target, ".o_list_table");
            assert.containsN(target, ".o_data_row", 10);
            assert.containsOnce(target, ".o_nocontent_help");

            // Start creating a record
            await click($(".o_list_button_add:visible").get(0));
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_data_row");

            // Discard temporary record
            await click($(".o_list_button_discard:visible").get(0));

            // Final state: there should be no table, but the no content helper
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_list_table");
            assert.containsOnce(target, ".o_nocontent_help");
        }
    );

    QUnit.test(
        "empty editable list with sample data: create and delete record",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top" sample="1">
                        <field name="foo"/>
                        <field name="bar"/>
                        <field name="int_field"/>
                    </tree>`,
                domain: Domain.FALSE.toList(),
                noContentHelp: "click to add a partner",
                actionMenus: {},
            });

            // Initial state: sample data and nocontent helper displayed
            assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
            assert.containsOnce(target, ".o_list_table");
            assert.containsN(target, ".o_data_row", 10);
            assert.containsOnce(target, ".o_nocontent_help");

            // Start creating a record
            await click($(".o_list_button_add:visible").get(0));
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_data_row");

            // Save temporary record
            await clickSave(target);
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_list_table");
            assert.containsOnce(target, ".o_data_row");
            assert.containsNone(target, ".o_nocontent_help");

            // Delete newly created record
            await click(target.querySelector(".o_data_row input"));
            await toggleActionMenu(target);
            await toggleMenuItem(target, "Delete");
            await click(target.querySelector(".modal-footer .btn-primary"));

            // Final state: there should be no table, but the no content helper
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_list_table");
            assert.containsOnce(target, ".o_nocontent_help");
        }
    );

    QUnit.test(
        "empty editable list with sample data: create and duplicate record",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top" sample="1">
                        <field name="foo"/>
                        <field name="bar"/>
                        <field name="int_field"/>
                    </tree>`,
                domain: [["int_field", "=", 0]],
                noContentHelp: "click to add a partner",
                actionMenus: {},
            });

            // Initial state: sample data and nocontent helper displayed
            assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
            assert.containsOnce(target, ".o_list_table");
            assert.containsN(target, ".o_data_row", 10);
            assert.containsOnce(target, ".o_nocontent_help");

            // Start creating a record
            await click($(".o_list_button_add:visible").get(0));
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_data_row");

            // Save temporary record
            await clickSave(target);
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_list_table");
            assert.containsOnce(target, ".o_data_row");
            assert.containsNone(target, ".o_nocontent_help");

            // Duplicate newly created record
            await click(target.querySelector(".o_data_row input"));
            await toggleActionMenu(target);
            await toggleMenuItem(target, "Duplicate");

            // Final state: there should be 2 records
            assert.containsN(
                target.querySelector(".o_list_view .o_content"),
                ".o_data_row",
                2,
                "there should be 2 records"
            );
        }
    );

    QUnit.test("groupby node with a button", async function (assert) {
        assert.expect(17);

        serverData.models.foo.fields.currency_id.sortable = true;
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <button string="Button 1" type="object" name="button_method"/>
                    </groupby>
                </tree>`,
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });
        patchWithCleanup(list.env.services.action, {
            doActionButton: (params) => {
                assert.step(params.name);
                assert.deepEqual(params.resId, 1, "should call with correct id");
                assert.strictEqual(
                    params.resModel,
                    "res_currency",
                    "should call with correct model"
                );
                assert.strictEqual(params.name, "button_method", "should call correct method");
                assert.strictEqual(params.type, "object", "should have correct type");
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);
        assert.containsOnce(
            target,
            "thead th:not(.o_list_record_selector)",
            "there should be only one column"
        );

        await groupByMenu(target, "currency_id");

        assert.verifySteps(["web_read_group"]);
        assert.containsN(target, ".o_group_header", 2, "there should be 2 group headers");
        assert.containsNone(
            target,
            ".o_group_header button",
            0,
            "there should be no button in the header"
        );
        await click(target, ".o_group_header:first-child");
        assert.verifySteps(["web_search_read"]);
        assert.containsOnce(target, ".o_group_header button");

        await click(target, ".o_group_header:first-child button");
        assert.verifySteps(["button_method"]);
    });

    QUnit.test("groupby node with a button in inner groupbys", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <button string="Button 1" type="object" name="button_method"/>
                    </groupby>
                </tree>`,
            groupBy: ["bar", "currency_id"],
        });

        assert.containsN(target, ".o_group_header", 2, "there should be 2 group headers");
        assert.containsNone(target, ".o_group_header button");

        await click(target, ".o_group_header:first-child");
        assert.containsN(target, ".o_list_view .o_group_header", 3);
        assert.containsNone(target, ".o_group_header button");
        await click(target, ".o_group_header:nth-child(2)");
        assert.containsOnce(target, ".o_group_header button");
    });

    QUnit.test("groupby node with a button with modifiers", async function (assert) {
        assert.expect(16);
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <field name="position"/>
                        <button string="Button 1" type="object" name="button_method" invisible="position == 'after'"/>
                    </groupby>
                </tree>`,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "web_read" && args.model === "res_currency") {
                    assert.deepEqual(args.args, [[1, 2]]);
                    assert.deepEqual(args.kwargs.specification, { position: {} });
                }
            },
            groupBy: ["currency_id"],
        });

        assert.verifySteps(["get_views", "web_read_group", "web_read"]);
        assert.containsNone(target, ".o_group_header button");
        assert.containsNone(target, ".o_data_row");

        await click(target, ".o_group_header:nth-child(2)");
        assert.verifySteps(["web_search_read"]);
        assert.containsNone(target, ".o_group_header button");
        assert.containsN(target, ".o_data_row", 1);

        await click(target, ".o_group_header:first-child");
        assert.verifySteps(["web_search_read"]);
        assert.containsOnce(target, ".o_group_header button");
        assert.containsN(target, ".o_data_row", 4);
    });

    QUnit.test(
        "groupby node with a button with modifiers using a many2one",
        async function (assert) {
            serverData.models.res_currency.fields.m2o = {
                string: "Currency M2O",
                type: "many2one",
                relation: "bar",
            };
            serverData.models.res_currency.records[0].m2o = 1;

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree expand="1">
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <field name="m2o"/>
                        <button string="Button 1" type="object" name="button_method" invisible="not m2o"/>
                    </groupby>
                </tree>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
                groupBy: ["currency_id"],
            });
            const groupHeaders = target.querySelectorAll(".o_group_header");
            assert.containsOnce(groupHeaders[0], "button");
            assert.containsNone(groupHeaders[1], "button");

            assert.verifySteps([
                "get_views",
                "web_read_group",
                "web_search_read",
                "web_search_read",
                "web_read",
            ]);
        }
    );

    QUnit.test("reload list view with groupby node", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree expand="1">
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <field name="position"/>
                        <button string="Button 1" type="object" name="button_method" invisible="position == 'after'"/>
                    </groupby>
                </tree>`,
            groupBy: ["currency_id"],
        });

        assert.containsOnce(target, ".o_group_header button");

        await reloadListView(target);
        assert.containsOnce(target, ".o_group_header button");
    });

    QUnit.test("editable list view with groupby node and modifiers", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree expand="1" editable="bottom">
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <field name="position"/>
                        <button string="Button 1" type="object" name="button_method" invisible="position == 'after'"/>
                    </groupby>
                </tree>`,
            groupBy: ["currency_id"],
        });

        assert.doesNotHaveClass(
            $(target).find(".o_data_row:first"),
            "o_selected_row",
            "first row should be in readonly mode"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.hasClass(
            $(target).find(".o_data_row:first"),
            "o_selected_row",
            "the row should be in edit mode"
        );

        await triggerEvent(document.activeElement, null, "keydown", { key: "escape" });
        assert.doesNotHaveClass(
            $(target).find(".o_data_row:first"),
            "o_selected_row",
            "the row should be back in readonly mode"
        );
    });

    QUnit.test("groupby node with edit button", async function (assert) {
        assert.expect(1);

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree expand="1">
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <button string="Button 1" type="edit" name="edit"/>
                    </groupby>
                </tree>`,
            groupBy: ["currency_id"],
        });
        patchWithCleanup(list.env.services.action, {
            doAction: (action) => {
                assert.deepEqual(action, {
                    context: { create: false },
                    res_id: 2,
                    res_model: "res_currency",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                    flags: { mode: "edit" },
                });
            },
        });
        await click(target.querySelectorAll(".o_group_header button")[1]);
    });

    QUnit.test("groupby node with subfields, and onchange", async function (assert) {
        assert.expect(1);

        serverData.models.foo.onchanges = {
            foo: function () {},
        };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom" expand="1">
                    <field name="foo"/>
                    <field name="currency_id"/>
                    <groupby name="currency_id">
                        <field name="position" column_invisible="1"/>
                    </groupby>
                </tree>`,
            groupBy: ["currency_id"],
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(
                        args.args[3],
                        {
                            currency_id: {
                                fields: {
                                    display_name: {},
                                },
                            },
                            foo: {},
                        },
                        "onchange spec should not follow relation of many2one fields"
                    );
                }
            },
        });
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
    });

    QUnit.test("list view, editable, without data", async function (assert) {
        serverData.models.foo.records = [];
        serverData.models.foo.fields.date.default = "2017-02-10";

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="date"/>
                    <field name="m2o"/>
                    <field name="foo"/>
                    <button type="object" icon="fa-plus-square" name="method"/>
                </tree>`,
            noContentHelp: "click to add a partner",
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save");
                }
            },
        });

        assert.containsOnce(
            target,
            ".o_view_nocontent",
            "should have a no content helper displayed"
        );
        assert.containsOnce(target, "div.table-responsive", "should have a div.table-responsive");
        assert.containsOnce(target, "table", "should have rendered a table");

        await click($(".o_list_button_add:visible").get(0));
        assert.containsNone(
            target,
            ".o_view_nocontent",
            "should not have a no content helper displayed"
        );
        assert.hasClass(
            target.querySelector("tbody tr"),
            "o_selected_row",
            "the date field td should be in edit mode"
        );
        assert.strictEqual(
            target.querySelector("tbody tr").querySelectorAll("td")[1].textContent,
            "",
            "the date field td should not have any content"
        );
        assert.strictEqual(
            target.querySelector("tr.o_selected_row .o_list_record_selector input").disabled,
            true,
            "record selector checkbox should be disabled while the record is not yet created"
        );
        assert.strictEqual(
            target.querySelector(".o_list_button button").disabled,
            false,
            "buttons should not be disabled while the record is not yet created"
        );

        await clickSave(target);
        assert.strictEqual(
            target.querySelector("tbody tr .o_list_record_selector input").disabled,
            false,
            "record selector checkbox should not be disabled once the record is created"
        );
        assert.strictEqual(
            target.querySelector(".o_list_button button").disabled,
            false,
            "buttons should not be disabled once the record is created"
        );
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("list view, editable, with a button", async function (assert) {
        serverData.models.foo.records = [];
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <button string="abc" icon="fa-phone" type="object" name="schedule_another_phonecall"/>
                </tree>`,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                } else if (route === "/web/dataset/call_button") {
                    assert.step("call_button");
                    return true;
                }
            },
        });

        await click($(".o_list_button_add:visible").get(0));

        assert.containsOnce(
            target,
            "table button i.o_button_icon.fa-phone",
            "should have rendered a button"
        );
        assert.notOk(
            target.querySelector("table button").disabled,
            "button should not be disabled when creating the record"
        );

        await click(target, "table button");
        assert.verifySteps(
            ["web_save", "call_button"],
            "clicking the button should save the record and then execute the action"
        );
    });

    QUnit.test("list view with a button without icon", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <button string="abc" type="object" name="schedule_another_phonecall"/>
                </tree>`,
        });

        assert.strictEqual(
            target.querySelector("table button").innerText,
            "abc",
            "should have rendered a button with string attribute as label"
        );
    });

    QUnit.test("list view, editable, can discard", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        assert.containsNone(
            target,
            "td:not(.o_list_record_selector) input",
            "no input should be in the table"
        );
        assert.containsNone(target, ".o_list_button_discard");

        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(
            target,
            "td:not(.o_list_record_selector) input",
            "first cell should be editable"
        );
        assert.containsN(
            target,
            ".o_list_button_discard",
            2,
            "Should have 2 discard button (small and xl screens)"
        );

        await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));

        assert.containsNone(
            target,
            "td:not(.o_list_record_selector) input",
            "no input should be in the table"
        );
        assert.containsNone(target, ".o_list_button_discard");
    });

    QUnit.test("editable list view, click on the list to save", async function (assert) {
        serverData.models.foo.fields.date.default = "2017-02-10";
        serverData.models.foo.records = [];

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="int_field" sum="Sum"/>
                </tree>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save");
                }
            },
        });

        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        await click(target.querySelector(".o_list_renderer"));
        assert.verifySteps(["web_save"]);

        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        await click(target.querySelector("tfoot"));
        assert.verifySteps(["web_save"]);

        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        await click(target.querySelectorAll("tbody tr")[2].querySelector(".o_data_cell"));
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("editable list view, should refocus date field", async (assert) => {
        patchDate(2017, 1, 10, 0, 0, 0);
        serverData.models.foo.records = [];
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: /* xml */ `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="date"/>
                </tree>`,
        });
        await click($(".o_list_button_add:visible").get(0));
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_field_widget[name=foo] input")
        );

        await click(target, ".o_field_widget[name=date] input");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_field_widget[name=date] input")
        );
        assert.containsOnce(target, ".o_datetime_picker");

        const clickPromise = click(getPickerCell("15"));
        getPickerCell("15").focus();
        await clickPromise;

        assert.containsNone(target, ".o_datetime_picker");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=date] input").value,
            "02/15/2017"
        );
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_field_widget[name=date] input")
        );
    });

    QUnit.test("text field should keep it's selection when clicking on it", async (assert) => {
        serverData.models.foo.records[0].text = "1234";
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom" limit="1">
                    <field name="text"/>
                </tree>`,
        });

        await click(target, "td[name=text]");
        assert.strictEqual(
            window.getSelection().toString(),
            "1234",
            "the entire content should be selected on initial click"
        );

        Object.assign(target.querySelector("[name=text] textarea"), {
            selectionStart: 0,
            selectionEnd: 1,
        });

        await click(target, "[name=text] textarea");

        assert.strictEqual(
            window.getSelection().toString(),
            "1",
            "the selection shouldn't be changed"
        );
    });

    QUnit.test("click on a button cell in a list view", async (assert) => {
        serverData.models.foo.records[0].foo = "bar";
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom" limit="1">
                    <field name="foo"/>
                    <button name="action_do_something" type="object" string="Action"/>
                </tree>`,
        });

        patchWithCleanup(list.env.services.action, {
            doActionButton: (action) => {
                assert.step("doActionButton");
                action.onClose();
            },
        });

        await click(target.querySelector(".o_data_cell.o_list_button"));
        assert.strictEqual(
            window.getSelection().toString(),
            "bar",
            "Focus should have returned to the editable cell without throwing an error"
        );
        assert.containsOnce(target, ".o_selected_row");
        assert.verifySteps([]);
    });

    QUnit.test("click on a button in a list view", async function (assert) {
        assert.expect(10);

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <button string="a button" name="button_action" icon="fa-car" type="object"/>
                </tree>`,
            mockRPC(route) {
                assert.step(route);
            },
        });
        patchWithCleanup(list.env.services.action, {
            doActionButton: (action) => {
                assert.deepEqual(action.resId, 1, "should call with correct id");
                assert.strictEqual(action.resModel, "foo", "should call with correct model");
                assert.strictEqual(action.name, "button_action", "should call correct method");
                assert.strictEqual(action.type, "object", "should have correct type");
                action.onClose();
            },
        });

        assert.containsN(target, "tbody .o_list_button", 4, "there should be one button per row");
        assert.containsN(target, ".o_data_row .o_list_button .o_button_icon.fa.fa-car", 4);

        await click(target.querySelector(".o_data_row .o_list_button > button"));
        assert.verifySteps(
            [
                "/web/dataset/call_kw/foo/get_views",
                "/web/dataset/call_kw/foo/web_search_read",
                "/web/dataset/call_kw/foo/web_search_read",
            ],
            "should have reloaded the view (after the action is complete)"
        );
    });

    QUnit.test("invisible attrs in readonly and editable list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <button string="a button" name="button_action" icon="fa-car" type="object" invisible="id == 1"/>
                    <field name="int_field"/>
                    <field name="qux"/>
                    <field name="foo" invisible="id == 1"/>
                </tree>`,
        });

        assert.strictEqual(target.querySelectorAll(".o_field_cell")[2].innerHTML, "");
        assert.strictEqual(target.querySelector(".o_data_cell.o_list_button").innerHTML, "");

        // edit first row
        await click(target.querySelector(".o_field_cell"));
        assert.strictEqual(target.querySelectorAll(".o_field_cell")[2].innerHTML, "");
        assert.strictEqual(target.querySelector(".o_data_cell.o_list_button").innerHTML, "");

        await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));

        // click on the invisible field's cell to edit first row
        await click(target.querySelectorAll(".o_field_cell")[2]);
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
    });

    QUnit.test("monetary fields are properly rendered", async function (assert) {
        const currencies = {};
        serverData.models.res_currency.records.forEach((currency) => {
            currencies[currency.id] = currency;
        });
        patchWithCleanup(session, { currencies });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="id"/>
                    <field name="amount"/>
                    <field name="currency_id" column_invisible="1"/>
                </tree>`,
        });

        assert.containsN(
            target,
            "tbody tr:first td",
            3,
            "currency_id column should not be in the table"
        );
        assert.strictEqual(
            target
                .querySelector("tbody .o_data_row:first-child .o_data_cell:nth-child(3)")
                .textContent.replace(/\s/g, " "),
            "1200.00 €",
            "currency_id column should not be in the table"
        );
        assert.strictEqual(
            target
                .querySelector("tbody .o_data_row:nth-child(2) .o_data_cell:nth-child(3)")
                .textContent.replace(/\s/g, " "),
            "$ 500.00",
            "currency_id column should not be in the table"
        );
    });

    QUnit.test("simple list with date and datetime", async function (assert) {
        patchTimeZone(120);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="date"/><field name="datetime"/></tree>',
        });
        const cells = target.querySelectorAll(".o_data_row .o_data_cell");
        assert.strictEqual(cells[0].textContent, "01/25/2017", "should have formatted the date");
        assert.strictEqual(
            cells[1].textContent,
            "12/12/2016 12:55:05",
            "should have formatted the datetime"
        );
    });

    QUnit.test("edit a row by clicking on a readonly field", async function (assert) {
        serverData.models.foo.fields.foo.readonly = true;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
        });

        // edit the first row
        await click(target.querySelector(".o_field_cell"));
        assert.hasClass(
            target.querySelector(".o_data_row"),
            "o_selected_row",
            "first row should be selected"
        );
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        assert.hasClass(
            target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
            "o_readonly_modifier"
        );
        assert.strictEqual(
            target.querySelector(".o_selected_row .o_field_widget[name=foo] span").innerText,
            "yop",
            "a widget should have been rendered for readonly fields"
        );
        assert.containsOnce(
            target,
            ".o_selected_row .o_field_widget[name=int_field] input",
            "'int_field' should be editable"
        );

        // click again on readonly cell of first line: nothing should have changed
        await click(target.querySelector(".o_field_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        assert.hasClass(
            target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
            "o_readonly_modifier"
        );
        assert.containsOnce(
            target,
            ".o_selected_row .o_field_widget[name=int_field] input",
            "'int_field' should be editable"
        );
    });

    QUnit.test("list view with nested groups", async function (assert) {
        assert.expect(40);

        serverData.models.foo.records.push({ id: 5, foo: "blip", int_field: -7, m2o: 1 });
        serverData.models.foo.records.push({ id: 6, foo: "blip", int_field: 5, m2o: 2 });

        let nbRPCs = { readGroup: 0, webSearchRead: 0 };
        let envIDs = []; // the ids that should be in the environment during this test

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ["m2o", "foo"],
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    if (args.kwargs.groupby[0] === "foo") {
                        // nested read_group
                        // called twice (once when opening the group, once when sorting)
                        assert.deepEqual(
                            args.kwargs.domain,
                            [["m2o", "=", 1]],
                            "nested read_group should be called with correct domain"
                        );
                    }
                    nbRPCs.readGroup++;
                } else if (args.method === "web_search_read") {
                    // called twice (once when opening the group, once when sorting)
                    assert.deepEqual(
                        args.kwargs.domain,
                        [
                            ["foo", "=", "blip"],
                            ["m2o", "=", 1],
                        ],
                        "nested web_search_read should be called with correct domain"
                    );
                    nbRPCs.webSearchRead++;
                }
            },
            selectRecord: (resId, options) => {
                assert.step(`switch to form - resId: ${resId}`);
            },
        });

        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.webSearchRead, 0, "should have done no web_search_read");
        assert.deepEqual(
            list.model.root.records.map((r) => r.resId),
            envIDs
        );

        // basic rendering tests
        assert.containsN(target, ".o_group_header", 2, "should contain 2 groups at first level");
        const value1Group = getGroup(1);
        assert.strictEqual(
            value1Group.querySelector(".o_group_name").textContent.trim(),
            "Value 1 (4)",
            "group should have correct name and count"
        );
        assert.containsN(
            target,
            ".o_group_name .fa-caret-right",
            2,
            "the carret of closed groups should be right"
        );
        assert.strictEqual(
            getCssVar(value1Group.querySelector("span"), "--o-list-group-level").trim(),
            "0"
        );
        assert.strictEqual(
            [...value1Group.querySelectorAll("td")].pop().textContent,
            "16",
            "group aggregates are correctly displayed"
        );

        // open the first group
        nbRPCs = { readGroup: 0, webSearchRead: 0 };
        await click(value1Group);
        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.webSearchRead, 0, "should have done no web_search_read");
        assert.deepEqual(
            list.model.root.records.map((r) => r.resId),
            envIDs
        );

        assert.strictEqual(
            getGroup(1).querySelector(".o_group_name").textContent.trim(),
            "Value 1 (4)",
            "group should have correct name and count (of records, not inner subgroups)"
        );
        assert.containsOnce(
            target,
            ".o_group_name:first .fa-caret-down",
            "the carret of open groups should be down"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_group_header").length,
            5,
            "open group should contain 5 groups (2 groups and 3 subGroup)"
        );
        const blipGroup = getGroup(2);
        assert.strictEqual(
            blipGroup.querySelector(".o_group_name").textContent.trim(),
            "blip (2)",
            "group should have correct name and count"
        );
        assert.strictEqual(
            getCssVar(blipGroup.querySelector("span"), "--o-list-group-level").trim(),
            "1"
        );
        assert.strictEqual(
            [...blipGroup.querySelectorAll("td")].pop().textContent,
            "-11",
            "inner group aggregates are correctly displayed"
        );

        // open subgroup
        nbRPCs = { readGroup: 0, webSearchRead: 0 };
        envIDs = [4, 5]; // the opened subgroup contains these two records
        await click(blipGroup);
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.webSearchRead, 1, "should have done one web_search_read");
        assert.deepEqual(
            list.model.root.records.map((r) => r.resId),
            envIDs
        );
        assert.strictEqual(
            target.querySelectorAll(".o_group_header").length,
            5,
            "open group should contain 5 groups (2 groups and 3 subGroup)"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_data_row").length,
            2,
            "open subgroup should contain 2 data rows"
        );
        assert.strictEqual(
            [...target.querySelector(".o_data_row").querySelectorAll(".o_data_cell")].pop()
                .textContent,
            "-4",
            "first record in open subgroup should be res_id 4 (with int_field -4)"
        );

        // open a record (should trigger event 'open_record')
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.verifySteps([`switch to form - resId: 4`]);

        // sort by int_field (ASC) and check that open groups are still open
        nbRPCs = { readGroup: 0, webSearchRead: 0 };
        envIDs = [5, 4]; // order of the records changed
        await click(target.querySelector(".o_list_view thead [data-name='int_field']"));
        assert.strictEqual(nbRPCs.readGroup, 2, "should have done two read_groups");
        assert.strictEqual(nbRPCs.webSearchRead, 1, "should have done one web_search_read");
        assert.deepEqual(
            list.model.root.records.map((r) => r.resId),
            envIDs
        );
        assert.strictEqual(
            target.querySelectorAll(".o_group_header").length,
            5,
            "open group should contain 5 groups (2 groups and 3 subGroup)"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_data_row").length,
            2,
            "open subgroup should contain 2 data rows"
        );
        assert.strictEqual(
            [...target.querySelector(".o_data_row").querySelectorAll(".o_data_cell")].pop()
                .textContent,
            "-7",
            "first record in open subgroup should be res_id 5 (with int_field -7)"
        );

        // close first level group
        nbRPCs = { readGroup: 0, webSearchRead: 0 };
        envIDs = []; // the group being closed, there is no more record in the environment
        await click(getGroup(2));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.webSearchRead, 0, "should have done no web_search_read");
        assert.deepEqual(
            list.model.root.records.map((r) => r.resId),
            envIDs
        );

        assert.containsN(target, ".o_group_header", 2, "should contain 2 groups at first level");
        assert.containsN(
            target,
            ".o_group_name .fa-caret-right",
            2,
            "the carret of closed groups should be right"
        );
    });

    QUnit.test("grouped list on selection field at level 2", async function (assert) {
        serverData.models.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [
                [1, "Low"],
                [2, "Medium"],
                [3, "High"],
            ],
            default: 1,
        };
        serverData.models.foo.records.push({
            id: 5,
            foo: "blip",
            int_field: -7,
            m2o: 1,
            priority: 2,
        });
        serverData.models.foo.records.push({
            id: 6,
            foo: "blip",
            int_field: 5,
            m2o: 1,
            priority: 3,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ["m2o", "priority"],
        });

        assert.containsN(target, ".o_group_header", 2, "should contain 2 groups at first level");

        // open the first group
        await click(target.querySelector(".o_group_header"));
        assert.containsN(
            target,
            ".o_group_header",
            5,
            "should contain 2 groups at first level and 3 groups at second level"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_group_header .o_group_name")].map((el) => el.innerText),
            ["Value 1 (5)", "Low (3)", "Medium (1)", "High (1)", "Value 2 (1)"]
        );
    });

    QUnit.test("grouped list with a pager in a group", async function (assert) {
        serverData.models.foo.records[3].bar = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
            limit: 3,
        });
        const headerHeight = target.querySelector(".o_group_header").offsetHeight;
        // basic rendering checks
        await click(target.querySelector(".o_group_header"));
        assert.strictEqual(
            target.querySelector(".o_group_header").offsetHeight,
            headerHeight,
            "height of group header shouldn't have changed"
        );
        assert.hasClass(
            target.querySelector(".o_group_header th nav"),
            "o_pager",
            "last cell of open group header should have classname 'o_pager'"
        );
        assert.deepEqual(getPagerValue(target.querySelector(".o_group_header")), [1, 3]);
        assert.containsN(target, ".o_data_row", 3);

        // go to next page
        await pagerNext(target.querySelector(".o_group_header"));
        assert.deepEqual(getPagerValue(target.querySelector(".o_group_header")), [4, 4]);
        assert.containsOnce(target, ".o_data_row");
    });

    QUnit.test("edition: create new line, then discard", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, "tr.o_data_row", 4, "should have 4 records");
        assert.containsN(
            target,
            ".o_list_button_add",
            2,
            "Should have 2 add button (small and xl screens)"
        );
        assert.containsNone(target, ".o_list_button_discard");
        assert.containsN(target, ".o_list_record_selector input:enabled", 5);
        await click($(".o_list_button_add:visible").get(0));
        assert.containsNone(target, ".o_list_button_add");
        assert.containsN(
            target,
            ".o_list_button_discard",
            2,
            "Should have 2 discard button (small and xl screens)"
        );
        assert.containsNone(target, ".o_list_record_selector input:enabled");
        await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));
        assert.containsN(target, "tr.o_data_row", 4, "should still have 4 records");
        assert.containsN(
            target,
            ".o_list_button_add",
            2,
            "Should have 2 add button (small and xl screens)"
        );
        assert.containsNone(target, ".o_list_button_discard");
        assert.containsN(target, ".o_list_record_selector input:enabled", 5);
    });

    QUnit.test(
        "invisible attrs on fields are re-evaluated on field change",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="foo" invisible="bar"/>
                        <field name="bar"/>
                    </tree>`,
            });

            let fooCells = target.querySelectorAll(".o_data_cell.o_list_char");
            assert.deepEqual(
                [...fooCells].map((c) => c.innerText),
                ["", "", "", "blip"]
            );

            // Make first line editable
            await click(target.querySelector(".o_field_cell"));
            assert.containsNone(target, ".o_selected_row .o_list_char .o_field_widget[name=foo]");

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsOnce(target, ".o_selected_row .o_list_char .o_field_widget[name=foo]");
            assert.strictEqual(target.querySelector(".o_list_char input").value, "yop");
            fooCells = target.querySelectorAll(".o_data_cell.o_list_char");
            assert.deepEqual(
                [...fooCells].map((c) => c.innerText),
                ["", "", "", "blip"]
            );

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsNone(target, ".o_selected_row .o_list_char .o_field_widget[name=foo]");
            fooCells = target.querySelectorAll(".o_data_cell.o_list_char");
            assert.deepEqual(
                [...fooCells].map((c) => c.innerText),
                ["", "", "", "blip"]
            );

            // Reswitch the field to visible and save the row
            await click(target.querySelector(".o_field_widget[name=bar] input"));
            await click($(".o_list_button_save:visible").get(0));

            target.querySelectorAll(".o_data_cell.o_list_char");
            assert.deepEqual(
                [...fooCells].map((c) => c.innerText),
                ["yop", "", "", "blip"]
            );
        }
    );

    QUnit.test(
        "readonly attrs on fields are re-evaluated on field change",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="foo" readonly="bar"/>
                        <field name="bar"/>
                    </tree>`,
            });

            // Make first line editable
            await click(target.querySelector(".o_field_cell"));
            assert.containsOnce(target, ".o_selected_row");
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] span");
            assert.hasClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_readonly_modifier"
            );

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] input");
            assert.doesNotHaveClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_readonly_modifier"
            );

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] span");
            assert.hasClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_readonly_modifier"
            );

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] input");
            assert.doesNotHaveClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_readonly_modifier"
            );

            // Click outside to leave edition mode and make first line editable again
            await click(target);
            assert.containsNone(target, ".o_selected_row");
            await click(target.querySelector(".o_field_cell"));
            assert.containsOnce(target, ".o_selected_row");
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] input");
            assert.doesNotHaveClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_readonly_modifier"
            );
        }
    );

    QUnit.test(
        "required attrs on fields are re-evaluated on field change",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="foo" required="bar"/>
                        <field name="bar"/>
                    </tree>`,
            });

            // Make first line editable
            await click(target.querySelector(".o_field_cell"));
            assert.hasClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_required_modifier"
            );

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.doesNotHaveClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_required_modifier"
            );

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.hasClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_required_modifier"
            );

            // Reswitch the field to required and save the row and make first line editable again
            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.doesNotHaveClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_required_modifier"
            );
            await click($(".o_list_button_save:visible").get(0));
            await click(target.querySelector(".o_field_cell"));
            assert.doesNotHaveClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_required_modifier"
            );
        }
    );

    QUnit.test(
        "modifiers of other x2many rows a re-evaluated when a subrecord is updated",
        async function (assert) {
            // In an x2many, a change on a subrecord might trigger an onchange on the x2many that
            // updates other sub-records than the edited one. For that reason, modifiers must be
            // re-evaluated.
            serverData.models.foo.onchanges = {
                o2m: function (obj) {
                    obj.o2m = [
                        [1, 1, { display_name: "Value 1", stage: "open" }],
                        [1, 2, { display_name: "Value 2", stage: "draft" }],
                    ];
                },
            };

            serverData.models.bar.fields.stage = {
                string: "Stage",
                type: "selection",
                selection: [
                    ["draft", "Draft"],
                    ["open", "Open"],
                ],
            };

            serverData.models.foo.records[0].o2m = [1, 2];
            serverData.models.bar.records[0].stage = "draft";
            serverData.models.bar.records[1].stage = "open";

            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                arch: `
                    <form>
                        <field name="o2m">
                            <tree editable="top">
                                <field name="display_name" invisible="stage == 'open'"/>
                                <field name="stage"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        ".o_field_widget[name=o2m] .o_data_row .o_data_cell:first-child"
                    ),
                ].map((el) => el.innerText),
                ["Value 1", ""]
            );

            // Make a change in the list to trigger the onchange
            await click(
                target.querySelector(
                    ".o_field_widget[name=o2m] .o_data_row .o_data_cell:nth-child(2)"
                )
            );
            await editSelect(
                target,
                '.o_field_widget[name=o2m] .o_data_row [name="stage"] select',
                '"open"'
            );
            assert.deepEqual(
                [
                    ...target.querySelectorAll(
                        ".o_field_widget[name=o2m] .o_data_row .o_data_cell:first-child"
                    ),
                ].map((el) => el.innerText),
                ["", "Value 2"]
            );
            assert.strictEqual(
                target.querySelector(".o_data_row:nth-child(2)").textContent,
                "Value 2Draft",
                "the onchange should have been applied"
            );
        }
    );

    QUnit.test("leaving unvalid rows in edition", async function (assert) {
        let warnings = 0;
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo" required="1"/>
                    <field name="bar"/>
                </tree>`,
        });
        patchWithCleanup(list.env.services.notification, {
            add: (message, { type }) => {
                if (type === "danger") {
                    warnings++;
                }
            },
        });

        // Start first line edition
        await click(target.querySelector(".o_data_cell"));

        // Remove required foo field value
        await editInput(target, ".o_selected_row .o_field_widget[name=foo] input", "");

        // Try starting other line edition
        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        assert.hasClass(
            target.querySelectorAll(".o_data_row")[0],
            "o_selected_row",
            "first line should still be in edition as invalid"
        );
        assert.containsOnce(target, ".o_selected_row", "no other line should be in edition");
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_field_invalid input",
            "the required field should be marked as invalid"
        );
        assert.strictEqual(warnings, 1, "a warning should have been displayed");
    });

    QUnit.test("open a virtual id", async function (assert) {
        await makeView({
            type: "list",
            resModel: "event",
            serverData,
            arch: '<tree><field name="name"/></tree>',
            selectRecord: (resId, options) => {
                assert.step(`switch to form - resId: ${resId}`);
            },
        });
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.verifySteps([`switch to form - resId: 2-20170808020000`]);
    });

    QUnit.test("pressing enter on last line of editable list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="bottom"><field name="foo"/></tree>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);
        assert.containsN(target, "tr.o_data_row", 4);

        // click on 3rd line
        await click(target.querySelector("tr.o_data_row:nth-child(3) .o_field_cell[name=foo]"));
        assert.hasClass(target.querySelector("tr.o_data_row:nth-child(3)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_selected_row [name=foo] input")
        );

        // press enter in input
        triggerHotkey("Enter");
        await nextTick();
        assert.hasClass(target.querySelector("tr.o_data_row:nth-child(4)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_selected_row [name=foo] input")
        );

        // press enter on last row
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, "tr.o_data_row", 5);
        assert.hasClass(target.querySelector("tr.o_data_row:nth-child(5)"), "o_selected_row");

        assert.verifySteps(["onchange"]);
    });

    QUnit.test("pressing tab on last cell of editable list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC(route) {
                assert.step(route);
            },
        });
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[3].querySelector(".o_data_cell"));
        assert.strictEqual(
            document.activeElement.parentNode.getAttribute("name"),
            "foo",
            "focus should be on an input with name = foo"
        );

        //it will not create a new line unless a modification is made
        await editInput(document.activeElement, null, "blip-changed");
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement.parentNode.getAttribute("name"),
            "int_field",
            "focus should be on an input with name = int_field"
        );

        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass(
            $(target).find("tr.o_data_row:eq(4)"),
            "o_selected_row",
            "5th row should be selected"
        );
        assert.strictEqual(
            document.activeElement.parentNode.getAttribute("name"),
            "foo",
            "focus should be on an input with name = foo"
        );

        assert.verifySteps([
            "/web/dataset/call_kw/foo/get_views",
            "/web/dataset/call_kw/foo/web_search_read",
            "/web/dataset/call_kw/foo/web_save",
            "/web/dataset/call_kw/foo/onchange",
        ]);
    });

    QUnit.test("navigation with tab and read completes after default_get", async function (assert) {
        const onchangeGetPromise = makeDeferred();
        const readPromise = makeDeferred();

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC(route, args, performRPC) {
                assert.step(args.method);
                const result = performRPC(route, args);
                if (args.method === "web_save") {
                    return readPromise.then(function () {
                        return result;
                    });
                }
                if (args.method === "onchange") {
                    return onchangeGetPromise.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[3].querySelectorAll(".o_data_cell")[1]);

        await editInput(target, ".o_selected_row [name='int_field'] input", "1234");
        triggerHotkey("Tab");
        await nextTick();

        onchangeGetPromise.resolve();
        assert.containsN(target, "tbody tr.o_data_row", 4, "should have 4 data rows");

        readPromise.resolve();
        await nextTick();
        assert.containsN(target, "tbody tr.o_data_row", 5, "should have 5 data rows");
        assert.strictEqual(
            $(target).find("td:contains(1234)").length,
            1,
            "should have a cell with new value"
        );

        // we trigger a tab to move to the second cell in the current row. this
        // operation requires that this.currentRow is properly set in the
        // list editable renderer.
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass(
            $(target).find("tr.o_data_row:eq(4)"),
            "o_selected_row",
            "5th row should be selected"
        );

        assert.verifySteps(["get_views", "web_search_read", "web_save", "onchange"]);
    });

    QUnit.test("display toolbar", async function (assert) {
        await makeView({
            type: "list",
            resModel: "event",
            serverData,
            arch: '<tree><field name="name"/></tree>',
            info: {
                actionMenus: {
                    action: [
                        {
                            id: 29,
                            name: "Action event",
                        },
                    ],
                },
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await click(target.querySelector(".o_list_record_selector input"));
        await toggleActionMenu(target);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_cp_action_menus .dropdown-item")),
            ["Export", "Duplicate", "Delete", "Action event"]
        );
    });

    QUnit.test("execute ActionMenus actions", async function (assert) {
        patchWithCleanup(actionService, {
            start() {
                return {
                    doAction(id, { additionalContext, onClose }) {
                        assert.step(JSON.stringify({ action_id: id, context: additionalContext }));
                        onClose(); // simulate closing of target new action's dialog
                    },
                };
            },
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
            info: {
                actionMenus: {
                    action: [
                        {
                            id: 44,
                            name: "Custom Action",
                            type: "ir.actions.act_window",
                            target: "new",
                        },
                    ],
                    print: [],
                },
            },
            actionMenus: {},
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsN(target, ".o_data_row", 4);
        // select all records
        await click(target, "thead .o_list_record_selector input");
        assert.containsN(target, ".o_list_record_selector input:checked", 5);
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Custom Action");

        assert.verifySteps([
            "get_views",
            "web_search_read",
            `{"action_id":44,"context":{"lang":"en","uid":7,"tz":"taht","active_id":1,"active_ids":[1,2,3,4],"active_model":"foo","active_domain":[]}}`,
            "web_search_read",
        ]);
    });

    QUnit.test(
        "execute ActionMenus actions with correct params (single page)",
        async function (assert) {
            assert.expect(12);

            patchWithCleanup(actionService, {
                start() {
                    const result = super.start(...arguments);
                    return {
                        ...result,
                        doAction(id, { additionalContext }) {
                            assert.step(
                                JSON.stringify({ action_id: id, context: additionalContext })
                            );
                        },
                    };
                },
            });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree><field name="foo"/></tree>',
                info: {
                    actionMenus: {
                        action: [
                            {
                                id: 44,
                                name: "Custom Action",
                                type: "ir.actions.server",
                            },
                        ],
                        print: [],
                    },
                },
                actionMenus: {},
                searchViewArch: `
                    <search>
                        <filter name="bar" domain="[('bar', '=', true)]"/>
                    </search>`,
            });

            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
            assert.containsN(target, ".o_data_row", 4);

            // select all records
            await click(target.querySelector("thead .o_list_record_selector input"));
            assert.containsN(target, ".o_list_record_selector input:checked", 5);
            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // unselect first record (will unselect the thead checkbox as well)
            await click(target.querySelector(".o_data_row .o_list_record_selector input"));
            assert.containsN(target, ".o_list_record_selector input:checked", 3);

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // add a domain and select first two records (need to unselect records first)
            await click(target.querySelector("thead .o_list_record_selector input")); // select all
            await click(target.querySelector("thead .o_list_record_selector input")); // unselect all
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "bar");
            assert.containsN(target, ".o_data_row", 3);
            assert.containsNone(target, ".o_list_record_selector input:checked");

            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");
            assert.containsN(target, ".o_list_record_selector input:checked", 2);

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            assert.verifySteps([
                '{"action_id":44,"context":{"lang":"en","uid":7,"tz":"taht","active_id":1,"active_ids":[1,2,3,4],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"lang":"en","uid":7,"tz":"taht","active_id":2,"active_ids":[2,3,4],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"lang":"en","uid":7,"tz":"taht","active_id":1,"active_ids":[1,2],"active_model":"foo","active_domain":[["bar","=",true]]}}',
            ]);
        }
    );

    QUnit.test(
        "execute ActionMenus actions with correct params (multi pages)",
        async function (assert) {
            patchWithCleanup(actionService, {
                start() {
                    const result = super.start(...arguments);
                    return {
                        ...result,
                        doAction(id, { additionalContext }) {
                            assert.step(
                                JSON.stringify({ action_id: id, context: additionalContext })
                            );
                        },
                    };
                },
            });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="2"><field name="foo"/></tree>',
                info: {
                    actionMenus: {
                        action: [
                            {
                                id: 44,
                                name: "Custom Action",
                                type: "ir.actions.server",
                            },
                        ],
                        print: [],
                    },
                },
                actionMenus: {},
                searchViewArch: `
                    <search>
                        <filter name="bar" domain="[('bar', '=', true)]"/>
                    </search>`,
            });

            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
            assert.containsN(target, ".o_data_row", 2);

            // select all records
            await click(target, "thead .o_list_record_selector input");
            assert.containsN(target, ".o_list_record_selector input:checked", 3);
            assert.containsOnce(target, ".o_list_selection_box .o_list_select_domain");
            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // select all domain
            await click(target, ".o_list_selection_box .o_list_select_domain");
            assert.containsN(target, ".o_list_record_selector input:checked", 3);

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // add a domain (need to unselect records first)
            await click(target.querySelector("thead .o_list_record_selector input"));
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "bar");
            assert.containsNone(target, ".o_list_selection_box .o_list_select_domain");

            // select all domain
            await click(target, "thead .o_list_record_selector input");
            await click(target, ".o_list_selection_box .o_list_select_domain");
            assert.containsN(target, ".o_list_record_selector input:checked", 3);
            assert.containsNone(target, ".o_list_selection_box .o_list_select_domain");

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            assert.verifySteps([
                '{"action_id":44,"context":{"lang":"en","uid":7,"tz":"taht","active_id":1,"active_ids":[1,2],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"lang":"en","uid":7,"tz":"taht","active_id":1,"active_ids":[1,2,3,4],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"lang":"en","uid":7,"tz":"taht","active_id":1,"active_ids":[1,2,3],"active_model":"foo","active_domain":[["bar","=",true]]}}',
            ]);
        }
    );

    QUnit.test("edit list line after line deletion", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[2].querySelector(".o_data_cell"));
        assert.ok(
            $(target).find(".o_data_row:nth(2)").is(".o_selected_row"),
            "third row should be in edition"
        );

        await clickDiscard(target);
        await click($(".o_list_button_add:visible").get(0));
        assert.ok(
            $(target).find(".o_data_row:nth(0)").is(".o_selected_row"),
            "first row should be in edition (creation)"
        );

        await clickDiscard(target);
        assert.containsNone(target, ".o_selected_row", "no row should be selected");

        await click(rows[2].querySelector(".o_data_cell"));
        assert.ok(
            $(target).find(".o_data_row:nth(2)").is(".o_selected_row"),
            "third row should be in edition"
        );
        assert.containsOnce(target, ".o_selected_row", "no other row should be selected");
    });

    QUnit.test(
        "pressing TAB in editable list with several fields [REQUIRE FOCUS]",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </tree>`,
            });

            await click(target.querySelector(".o_data_cell"));
            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row .o_data_cell input")
            );

            // Press 'Tab' -> should go to next cell (still in first row)
            triggerHotkey("Tab");
            await nextTick();

            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row .o_data_cell:nth-child(3) input")
            );

            // Press 'Tab' -> should go to next line (first cell)
            triggerHotkey("Tab");
            await nextTick();

            assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(2) .o_data_cell input")
            );
        }
    );

    QUnit.test(
        "pressing SHIFT-TAB in editable list with several fields [REQUIRE FOCUS]",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </tree>`,
            });

            await click(target.querySelector(".o_data_row:nth-child(2) .o_data_cell"));
            assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(2) .o_data_cell input")
            );

            triggerHotkey("shift+Tab");
            await nextTick();

            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row .o_data_cell:nth-child(3) input")
            );

            triggerHotkey("shift+Tab");
            await nextTick();

            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row .o_data_cell input")
            );
        }
    );

    QUnit.test("navigation with tab and readonly field (no modification)", async function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we press TAB when the
        // focus is on the first, then the focus skip the readonly cells and
        // directly goes to the next line instead.
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="int_field" readonly="1"/>
                </tree>`,
        });

        // Pass the first row in edition.
        await click(target, ".o_data_row:nth-child(1) [name=foo]");
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(1)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(1) [name=foo] input")
        );

        // Pressing Tab should skip the readonly field and directly go to the next row.
        triggerHotkey("Tab");
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(2) [name=foo] input")
        );

        // We do it again.
        triggerHotkey("Tab");
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(3)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(3) [name=foo] input")
        );
    });

    QUnit.test(
        "navigation with tab and readonly field (with modification)",
        async function (assert) {
            // This test makes sure that if we have 2 cells in a row, the first in
            // edit mode, and the second one readonly, then if we press TAB when the
            // focus is on the first, then the focus skips the readonly cells and
            // directly goes to the next line instead.
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="int_field" readonly="1"/>
                    </tree>`,
            });

            // Pass the first row in edition.
            await click(target, ".o_data_row:nth-child(1) [name=foo]");
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(target.querySelector(".o_data_row:nth-child(1)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(1) [name=foo] input")
            );

            // Modity the cell content
            await editInput(document.activeElement, null, "blip-changed");

            // Pressing Tab should skip the readonly field and directly go to the next row.
            triggerHotkey("Tab");
            await nextTick();
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(2) [name=foo] input")
            );

            // We do it again.
            triggerHotkey("Tab");
            await nextTick();
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(target.querySelector(".o_data_row:nth-child(3)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(3) [name=foo] input")
            );
        }
    );

    QUnit.test('navigation with tab on a list with create="0"', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom" create="0">
                    <field name="display_name"/>
                </tree>`,
        });

        assert.containsN(target, ".o_data_row", 4, "the list should contain 4 rows");

        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[2].querySelector(".o_data_cell"));
        assert.hasClass(
            $(target).find(".o_data_row:nth(2)"),
            "o_selected_row",
            "third row should be in edition"
        );

        // Press 'Tab' -> should go to next line
        // add a value in the cell because the Tab on an empty first cell would activate the next widget in the view
        await editInput(target, ".o_selected_row .o_data_cell input", 11);
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass(
            $(target).find(".o_data_row:nth(3)"),
            "o_selected_row",
            "fourth row should be in edition"
        );

        // Press 'Tab' -> should go back to first line as the create action isn't available
        await editInput(target, ".o_selected_row .o_data_cell input", 11);
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass(
            $(target).find(".o_data_row:first"),
            "o_selected_row",
            "first row should be in edition"
        );
    });

    QUnit.test('navigation with tab on a one2many list with create="0"', async function (assert) {
        serverData.models.foo.records[0].o2m = [1, 2];
        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="o2m">
                        <tree editable="bottom" create="0">
                            <field name="display_name"/>
                        </tree>
                        </field>
                        <field name="foo"/>
                    </sheet>
                </form>`,
            resId: 1,
            mode: "edit",
        });

        assert.containsN(target, ".o_field_widget[name=o2m] .o_data_row", 2);

        await click(
            target,
            ".o_field_widget[name=o2m] .o_data_row:nth-child(1) .o_data_cell[name=display_name]"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget[name=o2m] .o_data_row:nth-child(1)"),
            "o_selected_row"
        );
        assert.containsOnce(target, ".o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_selected_row [name=display_name] input")
        );

        // Press 'Tab' -> should go to next line
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass(
            target.querySelector(".o_field_widget[name=o2m] .o_data_row:nth-child(2)"),
            "o_selected_row"
        );
        assert.containsOnce(target, ".o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_selected_row [name=display_name] input")
        );

        // Pressing 'Tab' -> should use default behavior and thus get out of
        // the one to many and go to the next field of the form
        const nextInput = target.querySelector("[name=foo] input");
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
    });

    QUnit.test(
        "edition, then navigation with tab (with a readonly field)",
        async function (assert) {
            // This test makes sure that if we have 2 cells in a row, the first in
            // edit mode, and the second one readonly, then if we edit and press TAB,
            // (before debounce), the save operation is properly done (before
            // selecting the next row)

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="int_field" readonly="1"/>
                    </tree>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            // click on first dataRow and press TAB
            await click(target.querySelector(".o_data_row .o_data_cell"));
            await editInput(target, ".o_selected_row [name='foo'] input", "new value");
            triggerHotkey("Tab");
            await nextTick();

            assert.strictEqual(
                $(target).find("tbody tr:first td:contains(new value)").length,
                1,
                "should have the new value visible in dom"
            );
            assert.verifySteps(["get_views", "web_search_read", "web_save"]);
        }
    );

    QUnit.test(
        "edition, then navigation with tab (with a readonly field and onchange)",
        async function (assert) {
            // This test makes sure that if we have a read-only cell in a row, in
            // case the keyboard navigation move over it and there a unsaved changes
            // (which will trigger an onchange), the focus of the next activable
            // field will not crash
            serverData.models.bar.onchanges = {
                o2m: function () {},
            };
            serverData.models.bar.fields.o2m = {
                string: "O2M field",
                type: "one2many",
                relation: "foo",
            };
            serverData.models.bar.records[0].o2m = [1, 4];

            await makeView({
                type: "form",
                resModel: "bar",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="display_name"/>
                            <field name="o2m">
                                <tree editable="bottom">
                                    <field name="foo"/>
                                    <field name="date" readonly="1"/>
                                    <field name="int_field"/>
                                </tree>
                            </field>
                        </group>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.step(`onchange:${args.model}`);
                    }
                },
            });

            await click(target.querySelector(".o_data_cell"));
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_cell[name=foo] input")
            );
            await editInput(target, ".o_data_cell[name=foo] input", "new value");

            triggerHotkey("Tab");
            await nextTick();

            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_cell[name=int_field] input")
            );

            assert.verifySteps(["onchange:bar"]);
        }
    );

    QUnit.test(
        "pressing SHIFT-TAB in editable list with a readonly field [REQUIRE FOCUS]",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="int_field" readonly="1"/>
                        <field name="qux"/>
                    </tree>`,
            });

            await click(target.querySelector(".o_data_row:nth-child(2) [name=qux]"));

            assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(2) [name=qux] input")
            );

            await triggerHotkey("shift+Tab");
            await nextTick();

            assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(2) [name=foo] input")
            );
        }
    );

    QUnit.test(
        "pressing SHIFT-TAB in editable list with a readonly field in first column [REQUIRE FOCUS]",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="int_field" readonly="1"/>
                        <field name="foo"/>
                        <field name="qux"/>
                    </tree>`,
            });

            await click(target.querySelector(".o_data_row:nth-child(2) .o_data_cell"));

            assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(2) [name=foo] input")
            );

            triggerHotkey("shift+Tab");
            await nextTick();

            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row [name=qux] input")
            );
        }
    );

    QUnit.test(
        "pressing SHIFT-TAB in editable list with a readonly field in last column [REQUIRE FOCUS]",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="int_field"/>
                        <field name="foo"/>
                        <field name="qux" readonly="1"/>
                    </tree>`,
            });

            await click(target.querySelector(".o_data_row:nth-child(2) .o_data_cell"));

            assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:nth-child(2) [name=int_field] input")
            );

            triggerHotkey("shift+Tab");
            await nextTick();

            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row [name=foo] input")
            );
        }
    );

    QUnit.test("skip invisible fields when navigating list view with TAB", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="bar" column_invisible="1"/>
                        <field name="int_field"/>
                    </tree>`,
            resId: 1,
        });

        await click(target, ".o_data_row:nth-child(1) .o_field_cell[name=foo]");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(1) .o_field_cell[name=foo] input")
        );
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(1) .o_field_cell[name=int_field] input")
        );
    });

    QUnit.test("skip buttons when navigating list view with TAB (end)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <button name="kikou" string="Kikou" type="object"/>
                    </tree>`,
            resId: 1,
        });

        await click(target, ".o_data_row:nth-child(3) [name=foo]");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(3) [name=foo] input")
        );
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(4) [name=foo] input")
        );
    });

    QUnit.test("skip buttons when navigating list view with TAB (middle)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                    <tree editable="bottom">
                        <button name="kikou" string="Kikou" type="object"/>
                        <field name="foo"/>
                        <button name="kikou" string="Kikou" type="object"/>
                        <field name="int_field"/>
                    </tree>`,
            resId: 1,
        });

        await click(target, ".o_data_row:nth-child(3) [name=foo]");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(3) [name=foo] input")
        );
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(3) [name=int_field] input")
        );
    });

    QUnit.test("navigation: not moving down with keydown", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
        });

        await click(target.querySelector(".o_field_cell[name=foo]"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        triggerHotkey("arrowdown");
        await nextTick();
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
    });

    QUnit.test(
        "navigation: moving right with keydown from text field does not move the focus",
        async function (assert) {
            serverData.models.foo.fields.foo.type = "text";
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="bar"/>
                    </tree>`,
            });

            await click(target.querySelector(".o_field_cell[name=foo]"));

            const textarea = target.querySelector(".o_field_widget[name=foo] textarea");
            assert.strictEqual(document.activeElement, textarea);
            assert.strictEqual(textarea.selectionStart, 0);
            assert.strictEqual(textarea.selectionEnd, 3);
            textarea.selectionStart = 3; // Simulate browser keyboard right behavior (unselect)

            assert.strictEqual(document.activeElement, textarea);
            assert.ok(textarea.selectionStart === 3 && textarea.selectionEnd === 3);

            triggerHotkey("arrowright");
            await nextTick();

            assert.strictEqual(document.activeElement, textarea);
        }
    );

    QUnit.test(
        "discarding changes in a row properly updates the rendering",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo"/></tree>',
            });

            assert.strictEqual(
                target.querySelector(".o_field_cell").innerText,
                "yop",
                "first cell should contain 'yop'"
            );

            await click(target.querySelector(".o_field_cell"));
            await editInput(target, ".o_field_widget[name=foo] input", "hello");
            await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));
            assert.containsNone(document.body, ".modal", "should be no modal to ask for discard");

            assert.strictEqual(
                target.querySelector(".o_field_cell").innerText,
                "yop",
                "first cell should still contain 'yop'"
            );
        }
    );

    QUnit.test("numbers in list are right-aligned", async function (assert) {
        const currencies = {};
        serverData.models.res_currency.records.forEach((currency) => {
            currencies[currency.id] = currency;
        });
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="qux"/>
                    <field name="amount" widget="monetary"/>
                    <field name="currency_id" column_invisible="1"/>
                </tree>`,
        });
        patchWithCleanup(session, { currencies });
        const nbCellRight = [
            ...target.querySelectorAll(".o_data_row:first-child > .o_data_cell"),
        ].filter((el) => window.getComputedStyle(el).textAlign === "right").length;
        assert.strictEqual(nbCellRight, 2, "there should be two right-aligned cells");

        await click(target.querySelector(".o_data_cell"));
        const nbInputRight = [
            ...target.querySelectorAll(".o_data_row:first-child > .o_data_cell input"),
        ].filter((el) => window.getComputedStyle(el).textAlign === "right").length;
        assert.strictEqual(nbInputRight, 2, "there should be two right-aligned input");
    });

    QUnit.test(
        "grouped list with another grouped list parent, click unfold",
        async function (assert) {
            serverData.models.bar.fields = {
                ...serverData.models.bar.fields,
                cornichon: { string: "cornichon", type: "char" },
            };

            const rec = serverData.models.bar.records[0];
            // create records to have the search more button
            const newRecs = [];
            for (let i = 0; i < 8; i++) {
                const newRec = Object.assign({}, rec);
                newRec.id = 1 + i;
                newRec.cornichon = "extra fin";
                newRecs.push(newRec);
            }
            serverData.models.bar.records = newRecs;
            serverData.views = {
                "bar,false,list": '<tree><field name="cornichon"/></tree>',
                "bar,false,search":
                    "<search><filter context=\"{'group_by': 'cornichon'}\" string=\"cornichon\"/></search>",
            };
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo"/><field name="m2o"/></tree>',
                searchViewArch: `
                    <search>
                        <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
                    </search>`,
            });
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "bar");
            await toggleMenuItem(target, "bar");

            await click(target.querySelector(".o_data_cell"));
            await clickOpenM2ODropdown(target, "m2o");
            await clickOpenedDropdownItem(target, "m2o", "Search More...");
            assert.containsOnce(target, ".modal-content");
            assert.containsNone(
                target,
                ".modal-content .o_group_name",
                "list in modal not grouped"
            );

            const modal = target.querySelector(".modal");
            await toggleSearchBarMenu(modal);
            await toggleMenuItem(modal, "cornichon");
            await click(target.querySelector(".o_group_header"));
            assert.containsOnce(target, ".modal-content .o_group_open");
        }
    );

    QUnit.test("field values are escaped", async function (assert) {
        const value = "<script>throw Error();</script>";

        serverData.models.foo.records[0].foo = value;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        assert.strictEqual(
            target.querySelector(".o_data_cell").textContent,
            value,
            "value should have been escaped"
        );
    });

    QUnit.test("pressing ESC discard the current line changes", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        await click($(".o_list_button_add:visible").get(0));
        assert.containsN(target, "tr.o_data_row", 5, "should currently adding a 5th data row");

        await triggerEvent(target, '[name="foo"] input', "keydown", { key: "escape" });
        assert.containsN(target, "tr.o_data_row", 4, "should have only 4 data row after escape");
        assert.containsNone(target, "tr.o_data_row.o_selected_row", "no rows should be selected");
        assert.containsNone(target, ".o_list_button_save", "should not have a save button");
    });

    QUnit.test(
        "pressing ESC discard the current line changes (with required)",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            });

            await click($(".o_list_button_add:visible").get(0));
            assert.containsN(target, "tr.o_data_row", 5, "should currently adding a 5th data row");

            await triggerEvent(target, '[name="foo"] input', "keydown", { key: "escape" });
            assert.containsN(
                target,
                "tr.o_data_row",
                4,
                "should have only 4 data row after escape"
            );
            assert.containsNone(
                target,
                "tr.o_data_row.o_selected_row",
                "no rows should be selected"
            );
            assert.containsNone(target, ".o_list_button_save", "should not have a save button");
        }
    );

    QUnit.test("field with password attribute", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo" password="True"/></tree>',
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row .o_data_cell")].map((el) => el.textContent),
            ["***", "****", "****", "****"]
        );
    });

    QUnit.test("list with handle widget", async function (assert) {
        assert.expect(11);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="int_field" widget="handle"/>
                    <field name="amount" widget="float" digits="[5,0]"/>
                </tree>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    assert.strictEqual(
                        args.offset,
                        9,
                        "should write the sequence starting from the lowest current one"
                    );
                    assert.strictEqual(
                        args.field,
                        "int_field",
                        "should write the right field as sequence"
                    );
                    assert.deepEqual(
                        args.ids,
                        [3, 2, 1],
                        "should write the sequence in correct order"
                    );
                    return Promise.resolve();
                }
            },
        });

        let rows = target.querySelectorAll(".o_data_row");
        assert.strictEqual(
            rows[0].querySelector("[name='amount']").textContent,
            "0",
            "default fourth record should have amount 0"
        );
        assert.strictEqual(
            rows[1].querySelector("[name='amount']").textContent,
            "500",
            "default second record should have amount 500"
        );
        assert.strictEqual(
            rows[2].querySelector("[name='amount']").textContent,
            "1200",
            "default first record should have amount 1200"
        );
        assert.strictEqual(
            rows[3].querySelector("[name='amount']").textContent,
            "300",
            "default third record should have amount 300"
        );

        // Drag and drop the fourth line in second position
        await dragAndDrop("tbody tr:nth-child(4) .o_handle_cell", "tbody tr:nth-child(2)");
        // await nextTick()
        rows = target.querySelectorAll(".o_data_row");
        assert.strictEqual(
            rows[0].querySelector("[name='amount']").textContent,
            "0",
            "new second record should have amount 0"
        );
        assert.strictEqual(
            rows[1].querySelector("[name='amount']").textContent,
            "300",
            "new fourth record should have amount 300"
        );
        assert.strictEqual(
            rows[2].querySelector("[name='amount']").textContent,
            "500",
            "new third record should have amount 500"
        );
        assert.strictEqual(
            rows[3].querySelector("[name='amount']").textContent,
            "1200",
            "new first record should have amount 1200"
        );
    });

    QUnit.test("result of consecutive resequences is correctly sorted", async function (assert) {
        assert.expect(9);
        serverData.models = {
            // we want the data to be minimal to have a minimal test
            foo: {
                fields: { int_field: { string: "int_field", type: "integer", sortable: true } },
                records: [
                    { id: 1, int_field: 11 },
                    { id: 2, int_field: 12 },
                    { id: 3, int_field: 13 },
                    { id: 4, int_field: 14 },
                ],
            },
        };
        let moves = 0;
        const context = {
            lang: "en",
            tz: "taht",
            uid: 7,
        };
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="int_field" widget="handle"/>
                    <field name="id"/>
                </tree>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    if (moves === 0) {
                        assert.deepEqual(args, {
                            context,
                            model: "foo",
                            ids: [4, 3],
                            offset: 13,
                            field: "int_field",
                        });
                    }
                    if (moves === 1) {
                        assert.deepEqual(args, {
                            context,
                            model: "foo",
                            ids: [4, 2],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    if (moves === 2) {
                        assert.deepEqual(args, {
                            context,
                            model: "foo",
                            ids: [2, 4],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    if (moves === 3) {
                        assert.deepEqual(args, {
                            context,
                            model: "foo",
                            ids: [4, 2],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    moves += 1;
                }
            },
        });
        assert.strictEqual(
            $(target).find("tbody tr td.o_list_number").text(),
            "1234",
            "default should be sorted by id"
        );

        await dragAndDrop(
            ".o_list_view tbody tr:nth-child(4) .o_handle_cell",
            ".o_list_view tbody tr:nth-child(3)"
        );
        assert.strictEqual(
            $(target).find("tbody tr td.o_list_number").text(),
            "1243",
            "the int_field (sequence) should have been correctly updated"
        );

        await dragAndDrop(
            ".o_list_view tbody tr:nth-child(3) .o_handle_cell",
            ".o_list_view tbody tr:nth-child(2)"
        );
        assert.deepEqual(
            $(target).find("tbody tr td.o_list_number").text(),
            "1423",
            "the int_field (sequence) should have been correctly updated"
        );

        await dragAndDrop(
            ".o_list_view tbody tr:nth-child(2) .o_handle_cell",
            ".o_list_view tbody tr:nth-child(3)",
            "top"
        );
        assert.deepEqual(
            $(target).find("tbody tr td.o_list_number").text(),
            "1243",
            "the int_field (sequence) should have been correctly updated"
        );

        await dragAndDrop(
            ".o_list_view tbody tr:nth-child(3) .o_handle_cell",
            ".o_list_view tbody tr:nth-child(2)",
            "top"
        );
        assert.deepEqual(
            $(target).find("tbody tr td.o_list_number").text(),
            "1423",
            "the int_field (sequence) should have been correctly updated"
        );
    });

    QUnit.test("editable list with handle widget", async function (assert) {
        assert.expect(12);

        // resequence makes sense on a sequence field, not on arbitrary fields
        serverData.models.foo.records[0].int_field = 0;
        serverData.models.foo.records[1].int_field = 1;
        serverData.models.foo.records[2].int_field = 2;
        serverData.models.foo.records[3].int_field = 3;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top" default_order="int_field">
                    <field name="int_field" widget="handle"/>
                    <field name="amount" widget="float" digits="[5,0]"/>
                </tree>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    assert.strictEqual(
                        args.offset,
                        1,
                        "should write the sequence starting from the lowest current one"
                    );
                    assert.strictEqual(
                        args.field,
                        "int_field",
                        "should write the right field as sequence"
                    );
                    assert.deepEqual(
                        args.ids,
                        [4, 2, 3],
                        "should write the sequence in correct order"
                    );
                }
            },
        });

        assert.strictEqual(
            $(target).find("tbody tr:eq(0) td:last").text(),
            "1200",
            "default first record should have amount 1200"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(1) td:last").text(),
            "500",
            "default second record should have amount 500"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(2) td:last").text(),
            "300",
            "default third record should have amount 300"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(3) td:last").text(),
            "0",
            "default fourth record should have amount 0"
        );

        // Drag and drop the fourth line in second position
        await dragAndDrop("tbody tr:nth-child(4) .o_handle_cell", "tbody tr:nth-child(2)");

        assert.strictEqual(
            $(target).find("tbody tr:eq(0) td:last").text(),
            "1200",
            "new first record should have amount 1200"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(1) td:last").text(),
            "0",
            "new second record should have amount 0"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(2) td:last").text(),
            "500",
            "new third record should have amount 500"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(3) td:last").text(),
            "300",
            "new fourth record should have amount 300"
        );

        await click(target, "tbody tr:nth-child(2) div[name='amount']");

        assert.strictEqual(
            $(target).find("tbody tr:eq(1) td:last input").val(),
            "0",
            "the edited record should be the good one"
        );
    });

    QUnit.test("editable target, handle widget locks and unlocks on sort", async function (assert) {
        // we need another sortable field to lock/unlock the handle
        serverData.models.foo.fields.amount.sortable = true;
        // resequence makes sense on a sequence field, not on arbitrary fields
        serverData.models.foo.records[0].int_field = 0;
        serverData.models.foo.records[1].int_field = 1;
        serverData.models.foo.records[2].int_field = 2;
        serverData.models.foo.records[3].int_field = 3;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top" default_order="int_field">
                    <field name="int_field" widget="handle"/>
                    <field name="amount" widget="float"/>
                </tree>`,
        });

        assert.strictEqual(
            $(target).find('tbody div[name="amount"]').text(),
            "1200.00500.00300.000.00",
            "default should be sorted by int_field"
        );

        // Drag and drop the fourth line in second position
        await dragAndDrop("tbody tr:nth-child(4) .o_row_handle", "tbody tr:nth-child(2)");

        // Handle should be unlocked at this point
        assert.strictEqual(
            $(target).find('tbody div[name="amount"]').text(),
            "1200.000.00500.00300.00",
            "drag and drop should have succeeded, as the handle is unlocked"
        );

        // Sorting by a field different for int_field should lock the handle
        await click(target.querySelectorAll(".o_column_sortable")[1]);
        assert.strictEqual(
            $(target).find('tbody div[name="amount"]').text(),
            "0.00300.00500.001200.00",
            "should have been sorted by amount"
        );

        // Drag and drop the fourth line in second position (not)
        await dragAndDrop("tbody tr:nth-child(4) .o_row_handle", "tbody tr:nth-child(2)");
        assert.strictEqual(
            $(target).find('tbody div[name="amount"]').text(),
            "0.00300.00500.001200.00",
            "drag and drop should have failed as the handle is locked"
        );

        // Sorting by int_field should unlock the handle
        await click(target.querySelectorAll(".o_column_sortable")[0]);
        assert.strictEqual(
            $(target).find('tbody div[name="amount"]').text(),
            "1200.000.00500.00300.00",
            "records should be ordered as per the previous resequence"
        );

        // Drag and drop the fourth line in second position
        await dragAndDrop("tbody tr:nth-child(4) .o_row_handle", "tbody tr:nth-child(2)");
        assert.strictEqual(
            $(target).find('tbody div[name="amount"]').text(),
            "1200.00300.000.00500.00",
            "drag and drop should have worked as the handle is unlocked"
        );
    });

    QUnit.test("editable list with handle widget with slow network", async function (assert) {
        assert.expect(15);

        // resequence makes sense on a sequence field, not on arbitrary fields
        serverData.models.foo.records[0].int_field = 0;
        serverData.models.foo.records[1].int_field = 1;
        serverData.models.foo.records[2].int_field = 2;
        serverData.models.foo.records[3].int_field = 3;

        const prom = makeDeferred();

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="int_field" widget="handle" />
                    <field name="amount" widget="float" digits="[5,0]" />
                </tree>`,
            mockRPC: async function (route, { field, ids, offset }) {
                if (route === "/web/dataset/resequence") {
                    assert.strictEqual(
                        offset,
                        1,
                        "should write the sequence starting from the lowest current one"
                    );
                    assert.strictEqual(
                        field,
                        "int_field",
                        "should write the right field as sequence"
                    );
                    assert.deepEqual(ids, [4, 2, 3], "should write the sequence in correct order");
                    await prom;
                }
            },
        });
        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(1) td:nth-child(3)").textContent,
            "1200",
            "default first record should have amount 1200"
        );
        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(2) td:nth-child(3)").textContent,
            "500",
            "default second record should have amount 500"
        );
        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(3) td:nth-child(3)").textContent,
            "300",
            "default third record should have amount 300"
        );
        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(4) td:nth-child(3)").textContent,
            "0",
            "default fourth record should have amount 0"
        );
        // drag and drop the fourth line in second position
        await dragAndDrop("tbody tr:nth-child(4) .o_handle_cell", "tbody tr:nth-child(2)");

        // edit moved row before the end of resequence
        await click(target, "tbody tr:nth-child(4) .o_field_widget[name='amount']");
        await nextTick();

        assert.containsNone(
            target,
            "tbody tr:nth-child(4) td:nth-child(3) input",
            "shouldn't edit the line before resequence"
        );

        prom.resolve();
        await nextTick();

        assert.containsOnce(
            target,
            "tbody tr:nth-child(4) td:nth-child(3) input",
            "should edit the line after resequence"
        );

        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(4) td:nth-child(3) input").value,
            "300",
            "fourth record should have amount 300"
        );

        await editInput(target, ".o_data_row [name='amount'] input", 301);
        await click(target, "tbody tr:nth-child(1) .o_field_widget[name='amount']");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(1) td:nth-child(3)").textContent,
            "1200",
            "first record should have amount 1200"
        );
        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(2) td:nth-child(3)").textContent,
            "0",
            "second record should have amount 1"
        );
        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(3) td:nth-child(3)").textContent,
            "500",
            "third record should have amount 500"
        );
        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(4) td:nth-child(3)").textContent,
            "301",
            "fourth record should have amount 301"
        );

        await click(target, "tbody tr:nth-child(4) .o_field_widget[name='amount']");

        assert.strictEqual(
            target.querySelector("tbody tr:nth-child(4) td:nth-child(3) input").value,
            "301",
            "fourth record should have amount 301"
        );
    });

    QUnit.test("multiple clicks on Add do not create invalid rows", async function (assert) {
        serverData.models.foo.onchanges = {
            m2o: function () {},
        };

        const prom = makeDeferred();
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="m2o" required="1"/></tree>',
            mockRPC: async function (route, args, performRPC) {
                const result = await performRPC(route, args);
                if (args.method === "onchange") {
                    await prom;
                }
                return result;
            },
        });

        assert.containsN(target, ".o_data_row", 4, "should contain 4 records");

        // click on Add and delay the onchange (check that the button is correctly disabled)
        click($(".o_list_button_add:visible").get(0));
        assert.ok($(".o_list_button_add:visible").get(0).disabled);

        prom.resolve();
        await nextTick();

        assert.containsN(target, ".o_data_row", 5, "only one record should have been created");
    });

    QUnit.test("reference field rendering", async function (assert) {
        serverData.models.foo.records.push({
            id: 5,
            reference: "res_currency,2",
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="reference"/></tree>',
        });

        assert.strictEqual(
            $(target).find("tbody td:not(.o_list_record_selector)").text(),
            "Value 1USDEUREUR",
            "should have the display_name of the reference"
        );
    });

    QUnit.test("reference field batched in grouped list", async function (assert) {
        assert.expect(7);

        serverData.models.foo.records = [
            // group 1
            { id: 1, foo: "1", reference: "bar,1" },
            { id: 2, foo: "1", reference: "bar,2" },
            { id: 3, foo: "1", reference: "res_currency,1" },
            //group 2
            { id: 4, foo: "2", reference: "bar,2" },
            { id: 5, foo: "2", reference: "bar,3" },
        ];
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree expand="1">
                   <field name="foo" column_invisible="1"/>
                   <field name="reference"/>
               </tree>`,
            groupBy: ["foo"],
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });
        assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_search_read"]);
        assert.containsN(target, ".o_group_header", 2);
        const allNames = Array.from(
            target.querySelectorAll(".o_data_cell"),
            (node) => node.textContent
        );
        assert.deepEqual(allNames, ["Value 1", "Value 2", "USD", "Value 2", "Value 3"]);
    });

    QUnit.test("multi edit in view grouped by field not in view", async function (assert) {
        serverData.models.foo.records = [
            // group 1
            { id: 1, foo: "1", m2o: 1 },
            { id: 3, foo: "2", m2o: 1 },
            //group 2
            { id: 2, foo: "1", m2o: 2 },
            { id: 4, foo: "2", m2o: 2 },
            // group 3
            { id: 5, foo: "2", m2o: 3 },
        ];

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree expand="1" multi_edit="1">
                   <field name="foo"/>
               </tree>`,
            groupBy: ["m2o"],
        });
        // Select items from the first group
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");
        await click(target.querySelector(".o_list_char"));
        await editInput(target, ".o_data_row [name=foo] input", "test");
        assert.containsOnce(target, ".modal");

        await click(target, ".modal .modal-footer .btn-primary");
        assert.containsNone(target, ".modal");
        const allNames = [...document.querySelectorAll(".o_data_cell")].map((n) => n.textContent);
        assert.deepEqual(allNames, ["test", "test", "1", "2", "2"]);
    });

    QUnit.test("multi edit reference field batched in grouped list", async function (assert) {
        assert.expect(13);

        serverData.models.foo.records = [
            // group 1
            { id: 1, foo: "1", reference: "bar,1" },
            { id: 2, foo: "1", reference: "bar,2" },
            //group 2
            { id: 3, foo: "2", reference: "res_currency,1" },
            { id: 4, foo: "2", reference: "bar,2" },
            { id: 5, foo: "2", reference: "bar,3" },
        ];
        // Field boolean_toggle just to simplify the test flow
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree expand="1" multi_edit="1">
                    <field name="foo" column_invisible="1"/>
                    <field name="bar" widget="boolean_toggle"/>
                    <field name="reference"/>
                </tree>`,
            groupBy: ["foo"],
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "write") {
                    assert.deepEqual(args.args, [[1, 2, 3], { bar: true }]);
                }
            },
        });

        assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_search_read"]);
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[0]);
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[1]);
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[2]);
        await click(target.querySelector(".o_data_row .o_field_boolean input"));
        assert.containsOnce(target, ".modal");

        await click(target, ".modal .modal-footer .btn-primary");
        assert.containsNone(target, ".modal");
        assert.verifySteps(["write", "web_read"]);
        assert.containsN(target, ".o_group_header", 2);

        const allNames = Array.from(target.querySelectorAll(".o_data_cell"))
            .filter((node) => !node.children.length)
            .map((n) => n.textContent);
        assert.deepEqual(allNames, ["Value 1", "Value 2", "USD", "Value 2", "Value 3"]);
    });

    QUnit.test("multi edit field with daterange widget", async function (assert) {
        assert.expect(5);

        serverData.models.daterange = {
            fields: {
                date_start: { string: "Date Start", type: "date" },
                date_end: { string: "Date End", type: "date" },
            },
            records: [
                {
                    id: 1,
                    date_start: "2017-01-25",
                    date_end: "2017-01-26",
                },
                {
                    id: 2,
                    date_start: "2017-01-02",
                    date_end: "2017-01-03",
                },
            ],
        };
        patchTimeZone(360);

        await makeView({
            type: "list",
            resModel: "daterange",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="date_start" widget="daterange" options="{'end_date_field': 'date_end'}" />
                </tree>`,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args, [
                        [1, 2],
                        { date_start: "2017-01-16", date_end: "2017-02-12" },
                    ]);
                }
            },
        });
        await click(target.querySelector(".o_list_record_selector input"));
        await click(target.querySelector(".o_data_row .o_data_cell")); // edit first row
        await click(target.querySelector(".o_data_row .o_data_cell .o_field_daterange input"));

        // change dates range
        await click(getPickerCell("16").at(0));
        await click(getPickerCell("12").at(1));
        assert.notOk(getPickerApplyButton().disabled);

        // Apply the changes
        await click(getPickerApplyButton());
        assert.containsOnce(
            target,
            ".modal",
            "The confirm dialog should appear to confirm the multi edition."
        );

        const changesTable = document.querySelector(".modal-body .o_modal_changes");
        assert.strictEqual(
            changesTable.innerText.replaceAll("\n", "").replaceAll("\t", ""),
            "Field:Date StartUpdate to:01/16/201702/12/2017Field:Date EndUpdate to:02/12/2017"
        );

        // Valid the confirm dialog
        await click(target, ".modal .btn-primary");
        assert.containsNone(target, ".modal");
    });

    QUnit.test(
        "multi edit field with daterange widget (edition without using the picker)",
        async function (assert) {
            assert.expect(4);

            serverData.models.daterange = {
                fields: {
                    date_start: { string: "Date Start", type: "date" },
                    date_end: { string: "Date End", type: "date" },
                },
                records: [
                    {
                        id: 1,
                        date_start: "2017-01-25",
                        date_end: "2017-01-26",
                    },
                    {
                        id: 2,
                        date_start: "2017-01-02",
                        date_end: "2017-01-03",
                    },
                ],
            };
            patchTimeZone(360);

            await makeView({
                type: "list",
                resModel: "daterange",
                serverData,
                arch: `
                    <tree multi_edit="1">
                        <field name="date_start" widget="daterange" options="{'end_date_field': 'date_end'}" />
                    </tree>`,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(args.args, [[1, 2], { date_start: "2021-04-01" }]);
                    }
                },
            });

            // Test manually edit the date without using the daterange picker
            await click(target.querySelector(".o_list_record_selector input"));
            await click(target.querySelector(".o_data_row .o_data_cell")); // edit first row

            // Change the date in the first datetime
            await editInput(
                target,
                ".o_data_row .o_data_cell .o_field_daterange[name='date_start'] input[data-field='date_start']",
                "2021-04-01 11:00:00"
            );
            triggerHotkey("Enter");
            await nextTick();
            assert.containsOnce(
                target,
                ".modal",
                "The confirm dialog should appear to confirm the multi edition."
            );

            const changesTable = target.querySelector(".modal-body .o_modal_changes");
            assert.strictEqual(
                changesTable.innerText.replaceAll("\n", "").replaceAll("\t", ""),
                "Field:Date StartUpdate to:04/01/202101/26/2017"
            );

            // Valid the confirm dialog
            await click(target, ".modal .btn-primary");
            assert.containsNone(target, ".modal");
        }
    );

    QUnit.test("list daterange with start date and empty end date", async (assert) => {
        serverData.models.foo.fields.date_end = { string: "Some Date", type: "date" };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: /* xml */ `
                <tree>
                    <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
                </tree>`,
        });

        const arrowIcon = target.querySelector(".fa-long-arrow-right");
        const textSiblings = [...arrowIcon.parentNode.childNodes]
            .map((node) => {
                if (node === arrowIcon) {
                    return "->";
                } else if (node.nodeType === Node.TEXT_NODE) {
                    return node.nodeValue.trim();
                } else {
                    return node.innerText?.trim();
                }
            })
            .filter(Boolean);

        assert.deepEqual(textSiblings, ["01/25/2017", "->"]);
    });

    QUnit.test("list daterange with start date and empty end date", async (assert) => {
        serverData.models.foo.fields.date_end = { string: "Some Date", type: "date" };
        const [firstRecord] = serverData.models.foo.records;
        [firstRecord.date, firstRecord.date_end] = [firstRecord.date_end, firstRecord.date];

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: /* xml */ `
                <tree>
                    <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
                </tree>`,
        });

        const arrowIcon = target.querySelector(".fa-long-arrow-right");
        const textSiblings = [...arrowIcon.parentNode.childNodes]
            .map((node) => {
                if (node === arrowIcon) {
                    return "->";
                } else if (node.nodeType === Node.TEXT_NODE) {
                    return node.nodeValue.trim();
                } else {
                    return node.innerText?.trim();
                }
            })
            .filter(Boolean);

        assert.deepEqual(textSiblings, ["->", "01/25/2017"]);
    });

    QUnit.test("editable list view: contexts are correctly sent", async function (assert) {
        patchWithCleanup(session.user_context, { someKey: "some value" });
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            mockRPC(route, args) {
                if (args.method !== "get_views") {
                    const context = args.kwargs.context;
                    assert.strictEqual(context.active_field, 2, "context should be correct");
                    assert.strictEqual(context.someKey, "some value", "context should be correct");
                }
            },
            context: { active_field: 2 },
        });

        await click(target.querySelector(".o_data_cell"));
        await editInput(target.querySelector(".o_field_widget[name=foo] input"), null, "abc");
        await click($(".o_list_button_save:visible").get(0));
    });

    QUnit.test("editable list view: contexts with multiple edit", async function (assert) {
        assert.expect(4);

        patchWithCleanup(session.user_context, { someKey: "some value" });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree multi_edit="1"><field name="foo"/></tree>',
            mockRPC(route, args) {
                if (
                    route === "/web/dataset/call_kw/foo/write" ||
                    route === "/web/dataset/call_kw/foo/web_read"
                ) {
                    const context = args.kwargs.context;
                    assert.strictEqual(context.active_field, 2, "context should be correct");
                    assert.strictEqual(context.someKey, "some value", "context should be correct");
                }
            },
            context: { active_field: 2 },
        });

        // Uses the main selector to select all lines.
        await click(target.querySelector(".o_list_record_selector input"));
        await click(target.querySelector(".o_data_row .o_data_cell"));

        // Edits first record then confirms changes.
        await editInput(target, ".o_data_row [name=foo] input", "legion");
        await click(target, ".modal-dialog button.btn-primary");
    });

    QUnit.test("editable list view: single edition with selected records", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="top" multi_edit="1"><field name="foo"/></tree>`,
        });

        // Select first record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));

        // Edit the second
        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        await editInput(target, ".o_data_cell input", "oui");
        await click($(".o_list_button_save:visible").get(0));

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "yop",
            "oui",
            "gnap",
            "blip",
        ]);
    });

    QUnit.test(
        "editable list view: non dirty record with required fields",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="foo" required="1"/>
                        <field name="int_field"/>
                    </tree>`,
            });
            assert.containsN(target, ".o_data_row", 4);

            await click($(".o_list_button_add:visible").get(0));
            assert.containsN(target, ".o_data_row", 5);
            assert.containsOnce(target, ".o_selected_row");

            // do not change anything and then click outside should discard record
            await click(target, ".o_list_view");
            assert.containsN(target, ".o_data_row", 4);
            assert.containsNone(target, ".o_selected_row");

            await click($(".o_list_button_add:visible").get(0));
            assert.containsN(target, ".o_data_row", 5);
            assert.containsOnce(target, ".o_selected_row");

            // do not change anything and then click save button should not allow to discard record
            await click($(".o_list_button_save:visible").get(0));
            assert.containsN(target, ".o_data_row", 5);
            assert.containsOnce(target, ".o_selected_row");

            // selecting some other row should discard non dirty record
            await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
            assert.containsN(target, ".o_data_row", 4);
            assert.containsOnce(target, ".o_selected_row");

            // click somewhere else to discard currently selected row
            await click(target, ".o_list_view");
            assert.containsN(target, ".o_data_row", 4);
            assert.containsNone(target, ".o_selected_row");

            await click($(".o_list_button_add:visible").get(0));
            assert.containsN(target, ".o_data_row", 5);
            assert.containsOnce(target, ".o_selected_row");

            // do not change anything and press Enter key should not allow to discard record
            triggerHotkey("Enter");
            await nextTick();
            assert.containsOnce(target, ".o_selected_row");

            // discard row and create new record and keep required field empty and click anywhere
            await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));
            await click($(".o_list_button_add:visible").get(0));
            assert.containsOnce(target, ".o_selected_row", "row should be selected");
            await editInput(target, ".o_selected_row [name=int_field] input", 123);
            await click(target, ".o_list_view");
            assert.containsOnce(target, ".o_selected_row", "row should still be in edition");
        }
    );

    QUnit.test("editable list view: multi edition", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom" multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args,
                        [[1, 2], { int_field: 666 }],
                        "should write on multi records"
                    );
                } else if (args.method === "web_read") {
                    if (args.args[0].length !== 1) {
                        assert.deepEqual(args.args, [[1, 2]], "should batch the read");
                        assert.deepEqual(args.kwargs.specification, { foo: {}, int_field: {} });
                    }
                }
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);

        // select two records
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");

        // edit a line without modifying a field
        await click(rows[0].querySelector(".o_data_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

        await click(target, ".o_list_view");
        assert.containsNone(target, ".o_selected_row");

        // create a record and edit its value
        await click($(".o_list_button_add:visible").get(0));
        assert.verifySteps(["onchange"]);

        await editInput(target, ".o_selected_row [name=int_field] input", 123);
        assert.containsNone(document.body, ".modal");

        await clickSave(target);
        assert.verifySteps(["web_save"]);

        // edit a field
        await click(rows[0].querySelector("[name=int_field]"));
        await editInput(rows[0], "[name=int_field] input", 666);
        assert.containsOnce(target, ".modal");

        await click(target, ".modal .btn.btn-secondary");
        assert.containsN(target, ".o_list_record_selector input:checked", 2);
        assert.deepEqual(
            [...rows[0].querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["yop", "10"]
        );
        assert.strictEqual(
            document.activeElement,
            rows[0].querySelector(".o_data_cell[name=int_field]")
        );

        await click(rows[0].querySelectorAll(".o_data_cell")[1]);
        await editInput(target, ".o_data_row [name=int_field] input", 666);
        assert.ok(
            $(".modal").text().includes("those 2 records"),
            "the number of records should be correctly displayed"
        );

        await click(target, ".modal .btn-primary");
        assert.containsNone(
            target,
            ".o_data_cell input.o_field_widget",
            "no field should be editable anymore"
        );
        assert.containsNone(
            target,
            ".o_list_record_selector input:checked",
            "no record should be selected anymore"
        );
        assert.verifySteps(["write", "web_read"]);
        assert.strictEqual(
            $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
            "yop666",
            "the first row should be updated"
        );
        assert.strictEqual(
            $(target).find(".o_data_row:eq(1) .o_data_cell").text(),
            "blip666",
            "the second row should be updated"
        );
        assert.containsNone(
            target,
            ".o_data_cell input.o_field_widget",
            "no field should be editable anymore"
        );
    });

    QUnit.test("editable list view: multi edit a field with string attr", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="foo" string="Custom Label"/>
                    <field name="int_field"/>
                </tree>`,
        });

        // select two records
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");

        // edit foo
        await click(rows[0].querySelector(".o_data_cell"));
        await editInput(target, ".o_data_row [name=foo] input", "new value");

        assert.containsOnce(target, ".modal");
        const changesTable = target.querySelector(".modal-body .o_modal_changes");
        assert.strictEqual(
            changesTable.innerText.replaceAll("\n", "").replaceAll("\t", ""),
            "Field:Custom LabelUpdate to:new value"
        );
    });

    QUnit.test("create in multi editable list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            createRecord: () => {
                assert.step("createRecord");
            },
        });

        // click on CREATE (should trigger a switch_view)
        await click($(".o_list_button_add:visible").get(0));
        assert.verifySteps(["createRecord"]);
    });

    QUnit.test("editable list view: multi edition cannot call onchanges", async function (assert) {
        serverData.models.foo.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length;
            },
        };
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "write") {
                    args.args[1].int_field = args.args[1].foo.length;
                }
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);

        // select and edit a single record
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[0].querySelector(".o_data_cell"));
        await editInput(target, ".o_data_row [name=foo] input", "hi");
        assert.containsNone(target, ".modal");
        assert.deepEqual(
            [...rows[0].querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["hi", "2"]
        );
        assert.deepEqual(
            [...rows[1].querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["blip", "9"]
        );

        assert.verifySteps(["write", "web_read"]);
        // select the second record (the first one is still selected)
        assert.containsNone(target, ".o_list_record_selector input:checked");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");

        // edit foo, first row
        await click(rows[0].querySelector(".o_data_cell"));
        await editInput(target, ".o_data_row [name=foo] input", "hello");
        assert.containsOnce(target, ".modal"); // save dialog

        await click(target, ".modal .btn-primary");
        assert.deepEqual(
            [...rows[0].querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["hello", "5"]
        );
        assert.deepEqual(
            [...rows[1].querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["hello", "5"]
        );

        assert.verifySteps(
            ["write", "web_read"],
            "should not perform the onchange in multi edition"
        );
    });

    QUnit.test(
        "editable list view: multi edition error and cancellation handling",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree multi_edit="1">
                        <field name="foo" required="1"/>
                        <field name="int_field"/>
                    </tree>`,
            });

            assert.containsN(target, ".o_list_record_selector input:enabled", 5);

            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");

            // edit a line and cancel
            await click(rows[0].querySelector(".o_data_cell"));
            assert.containsNone(target, ".o_list_record_selector input:enabled");
            await editInput(target, ".o_selected_row [name=foo] input", "abc");
            await click(target, ".modal .btn.btn-secondary");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "yop10",
                "first cell should have discarded any change"
            );
            assert.containsN(target, ".o_list_record_selector input:enabled", 5);

            // edit a line with an invalid format type
            await click(rows[0].querySelectorAll(".o_data_cell")[1]);
            assert.containsNone(target, ".o_list_record_selector input:enabled");

            await editInput(target, ".o_selected_row [name=int_field] input", "hahaha");
            assert.containsOnce(target, ".modal", "there should be an opened modal");

            await click(target, ".modal .btn-primary");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "yop10",
                "changes should be discarded"
            );
            assert.containsN(target, ".o_list_record_selector input:enabled", 5);

            // edit a line with an invalid value
            await click(rows[0].querySelector(".o_data_cell"));
            assert.containsNone(target, ".o_list_record_selector input:enabled");

            await editInput(target, ".o_selected_row [name=foo] input", "");
            assert.containsOnce(target, ".modal", "there should be an opened modal");
            await click(target, ".modal .btn-primary");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "yop10",
                "changes should be discarded"
            );
            assert.containsN(target, ".o_list_record_selector input:enabled", 5);
        }
    );

    QUnit.test("multi edition: many2many_tags in many2many field", async function (assert) {
        for (let i = 4; i <= 10; i++) {
            serverData.models.bar.records.push({ id: i, display_name: "Value" + i });
        }

        serverData.views = {
            "bar,false,list": '<tree><field name="name"/></tree>',
            "bar,false,search": "<search></search>",
        };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree multi_edit="1"><field name="m2m" widget="many2many_tags"/></tree>',
        });

        assert.containsN(target, ".o_list_record_selector input:enabled", 5);

        // select two records and enter edit mode
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");
        await click(rows[0].querySelector(".o_data_cell"));
        await selectDropdownItem(target, "m2m", "Search More...");
        assert.containsOnce(document.body, ".modal", "should have open the modal");

        await click(target.querySelector(".modal .o_data_row .o_field_cell"));
        assert.containsOnce(
            target,
            ".modal [role='alert']",
            "should have open the confirmation modal"
        );
        assert.containsN(target, ".modal .o_field_many2many_tags .badge", 3);
        assert.strictEqual(
            target
                .querySelector(".modal .o_field_many2many_tags .badge:nth-child(3)")
                .textContent.trim(),
            "Value 3",
            "should have display_name in badge"
        );
    });

    QUnit.test("multi edition: many2many field in grouped list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            groupBy: ["m2m"],
        });

        await click(target.querySelectorAll(".o_group_header")[1]); // open Value 1 group
        await click(target.querySelectorAll(".o_group_header")[2]); // open Value 2 group

        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[0].querySelectorAll(".o_data_cell")[1]);
        await selectDropdownItem(target, "m2m", "Value 3");
        assert.strictEqual(
            rows[0].querySelectorAll(".o_data_cell")[1].textContent,
            "Value 1Value 2Value 3",
            "should have a right value in many2many field"
        );
        assert.strictEqual(
            rows[3].querySelectorAll(".o_data_cell")[1].textContent,
            "Value 1Value 2Value 3",
            "should have same value in many2many field on all other records with same res_id"
        );
    });

    QUnit.test(
        "editable list view: multi edition of many2one: set same value",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree multi_edit="1">
                        <field name="foo"/>
                        <field name="m2o"/>
                    </tree>`,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(
                            args.args,
                            [[1, 2, 3, 4], { m2o: 2 }],
                            "should force write value on all selected records"
                        );
                    }
                },
            });

            assert.strictEqual(
                $(target).find(".o_list_many2one").text(),
                "Value 1Value 2Value 1Value 1"
            );

            // select all records (the first one has value 1 for m2o)
            await click(target.querySelector(".o_list_record_selector input"));

            // set m2o to 1 in first record
            await click(target.querySelector(".o_data_row .o_data_cell"));
            await editInput(target, ".o_data_row [name=m2o] input", "Value 2");
            await click(target.querySelector(".o-autocomplete--dropdown-item"));
            assert.containsOnce(target, ".modal");

            await click(target, ".modal .modal-footer .btn-primary");
            assert.strictEqual(
                $(target).find(".o_list_many2one").text(),
                "Value 2Value 2Value 2Value 2"
            );
        }
    );

    QUnit.test(
        'editable list view: clicking on "Discard changes" in multi edition',
        async function (assert) {
            await makeView({
                type: "list",
                arch: `
                    <tree editable="top" multi_edit="1">
                        <field name="foo"/>
                    </tree>`,
                serverData,
                resModel: "foo",
            });

            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");
            await click(rows[0].querySelector(".o_data_cell"));
            target.querySelector(".o_data_row .o_data_cell input").value = "oof";

            const discardButton = $(".o_list_button_discard:visible").get(0);
            // Simulates an actual click (event chain is: mousedown > change > blur > focus > mouseup > click)
            await triggerEvents(discardButton, null, ["mousedown"]);
            await triggerEvents(target.querySelector(".o_data_row .o_data_cell input"), null, [
                "change",
                "blur",
                "focusout",
            ]);
            await triggerEvents(discardButton, null, ["focus"]);
            await triggerEvents(discardButton, null, ["mouseup"]);
            await click(discardButton);

            assert.containsNone(document.body, ".modal", "should not open modal");

            assert.strictEqual(
                $(target).find(".o_data_row:first() .o_data_cell:first()").text(),
                "yop"
            );
        }
    );

    QUnit.test(
        'editable list view: mousedown on "Discard", mouseup somewhere else (no multi-edit)',
        async function (assert) {
            await makeView({
                type: "list",
                arch: `
                    <tree editable="top">
                        <field name="foo"/>
                    </tree>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
                serverData,
                resModel: "foo",
            });

            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");
            await click(rows[0].querySelector(".o_data_cell"));
            target.querySelector(".o_data_row .o_data_cell input").value = "oof";

            await triggerEvents($(".o_list_button_discard:visible").get(0), null, ["mousedown"]);
            await triggerEvents(target, ".o_data_row .o_data_cell input", [
                "change",
                "blur",
                "focusout",
            ]);
            await triggerEvents(target, null, ["focus"]);
            await triggerEvents(target, null, ["mouseup"]);
            await click(target);

            assert.containsNone(document.body, ".modal", "should not open modal");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "oof",
                "blip",
                "gnap",
                "blip",
            ]);
            assert.verifySteps(["get_views", "web_search_read", "web_save"]);
        }
    );

    QUnit.test(
        'multi edit list view: mousedown on "Discard" with invalid field',
        async function (assert) {
            await makeView({
                type: "list",
                arch: `
                    <tree multi_edit="1">
                        <field name="int_field"/>
                    </tree>`,
                serverData,
                resModel: "foo",
            });

            assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").innerText, "10");

            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");

            // edit the numeric field with an invalid value
            await click(rows[0].querySelector(".o_data_cell"));
            target.querySelector(".o_data_row .o_data_cell input").value = "oof";
            await triggerEvents(target, ".o_data_row .o_data_cell input", ["input"]);

            // mousedown on Discard and then mouseup also on Discard
            await triggerEvents($(".o_list_button_discard:visible").get(0), null, ["mousedown"]);
            await triggerEvents(target, ".o_data_row .o_data_cell input", [
                "change",
                "blur",
                "focusout",
            ]);
            await triggerEvents($(".o_list_button_discard:visible").get(0), null, ["focus"]);
            assert.containsNone(target, ".o_dialog", "should not display an invalid field dialog");
            await triggerEvents($(".o_list_button_discard:visible").get(0), null, ["mouseup"]);
            await click(target.querySelector(".o_list_button_discard:not(.dropdown-item)"));
            assert.containsNone(target, ".o_dialog", "should not display an invalid field dialog");
            assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").innerText, "10");

            // edit again with an invalid value
            await click(rows[0].querySelector(".o_data_cell"));
            target.querySelector(".o_data_row .o_data_cell input").value = "oof2";
            await triggerEvents(target, ".o_data_row .o_data_cell input", ["input"]);

            // mousedown on Discard (simulate a mousemove) and mouseup somewhere else
            await triggerEvents($(".o_list_button_discard:visible").get(0), null, ["mousedown"]);
            await triggerEvents(target, ".o_data_row .o_data_cell input", [
                "change",
                "blur",
                "focusout",
            ]);
            await triggerEvents(target, null, ["focus"]);
            assert.containsNone(target, ".o_dialog", "should not display an invalid field dialog");
            await triggerEvents(target, null, ["mouseup"]);
            await click(target);
            assert.containsOnce(target, ".o_dialog", "should display an invalid field dialog");
            await click(target, ".o_dialog .modal-footer .btn-primary"); // click OK
            assert.strictEqual(target.querySelector(".o_data_row .o_data_cell").innerText, "10");
        }
    );

    QUnit.test(
        'editable list view (multi edition): mousedown on "Discard", but mouseup somewhere else',
        async function (assert) {
            await makeView({
                type: "list",
                arch: `
                    <tree multi_edit="1">
                        <field name="foo"/>
                    </tree>`,
                serverData,
                resModel: "foo",
            });

            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");
            await click(rows[0].querySelector(".o_data_cell"));
            target.querySelector(".o_data_row .o_data_cell input").value = "oof";

            const discardButton = $(".o_list_button_discard:visible").get(0);
            // Simulates an actual click (event chain is: mousedown > change > blur > focus > mouseup > click)
            await triggerEvents(discardButton, null, ["mousedown"]);
            await triggerEvents(target.querySelector(".o_data_row .o_data_cell input"), null, [
                "change",
                "blur",
                "focusout",
            ]);
            await triggerEvents(discardButton, null, ["focus"]);
            await triggerEvents(document.body, null, ["mouseup"]);
            await triggerEvents(document.body, null, ["click"]);

            assert.ok(
                $(".modal").text().includes("Confirmation"),
                "Modal should ask to save changes"
            );
            await click(target, ".modal .btn-primary");
        }
    );

    QUnit.test(
        "editable list view (multi edition): writable fields in readonly (force save)",
        async function (assert) {
            assert.expect(8);

            // boolean toogle widget allows for writing on the record even in readonly mode
            await makeView({
                type: "list",
                arch: `
                    <tree multi_edit="1">
                        <field name="bar" widget="boolean_toggle"/>
                    </tree>`,
                serverData,
                resModel: "foo",
                mockRPC(route, args) {
                    assert.step(args.method || route);
                    if (args.method === "write") {
                        assert.deepEqual(args.args, [[1, 3], { bar: false }]);
                    }
                },
            });

            assert.verifySteps(["get_views", "web_search_read"]);
            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[2], ".o_list_record_selector input");
            await click(rows[0].querySelector(".o_boolean_toggle input"));

            assert.ok(
                $(".modal").text().includes("Confirmation"),
                "Modal should ask to save changes"
            );
            await click(target, ".modal .btn-primary");
            assert.verifySteps(["write", "web_read"]);
        }
    );

    QUnit.test(
        "editable list view: multi edition with readonly modifiers",
        async function (assert) {
            assert.expect(5);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree multi_edit="1">
                        <field name="id"/>
                        <field name="foo"/>
                        <field name="int_field" readonly="id > 2"/>
                    </tree>`,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(
                            args.args,
                            [[1, 2], { int_field: 666 }],
                            "should only write on the valid records"
                        );
                    }
                },
            });

            // select all records
            await click(target.querySelector(".o_list_record_selector input"));
            ``; // edit a field
            await click(target.querySelectorAll(".o_data_row .o_data_cell")[1]);
            await editInput(target, ".o_data_row [name=int_field] input", 666);

            const modalText = target
                .querySelector(".modal-body")
                .textContent.split(" ")
                .filter((w) => w.trim() !== "")
                .join(" ")
                .split("\n")
                .join("");
            assert.strictEqual(
                modalText,
                "Among the 4 selected records, 2 are valid for this update. Are you sure you want to " +
                    "perform the following update on those 2 records? Field:int_fieldUpdate to:666"
            );
            assert.strictEqual(
                target.querySelector(".modal .o_modal_changes .o_field_widget").parentNode.style
                    .pointerEvents,
                "none",
                "pointer events should be deactivated on the demo widget"
            );

            await click(target, ".modal .btn-primary");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "1yop666",
                "the first row should be updated"
            );
            assert.strictEqual(
                $(target).find(".o_data_row:eq(1) .o_data_cell").text(),
                "2blip666",
                "the second row should be updated"
            );
        }
    );

    QUnit.test(
        "editable list view: multi edition when the domain is selected",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree multi_edit="1" limit="2">
                        <field name="id"/>
                        <field name="int_field"/>
                    </tree>`,
            });

            // select all records, and then select all domain
            await click(target.querySelector(".o_list_record_selector input"));
            await click(target.querySelector(".o_list_selection_box .o_list_select_domain"));

            // edit a field
            await click(target.querySelectorAll(".o_data_row .o_data_cell")[1]);
            await editInput(target, ".o_data_row [name=int_field] input", 666);
            assert.ok(
                target
                    .querySelector(".modal-body")
                    .textContent.includes(
                        "This update will only consider the records of the current page."
                    )
            );
        }
    );

    QUnit.test("editable list view: many2one with readonly modifier", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="m2o" readonly="1"/>
                    <field name="foo"/>
                </tree>`,
        });

        // edit a field
        await click(target.querySelector(".o_data_row .o_data_cell"));

        assert.containsOnce(target, '.o_data_row:eq(0) .o_data_cell:eq(0) div[name="m2o"] a');
        assert.strictEqual(
            document.activeElement,
            target.querySelectorAll(".o_data_row .o_data_cell")[1].querySelector("input"),
            "focus should go to the char input"
        );
    });

    QUnit.test("editable list view: multi edition server error handling", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree multi_edit="1"><field name="foo" required="1"/></tree>',
            mockRPC(route, args) {
                if (args.method === "write") {
                    return Promise.reject();
                }
            },
        });

        // select two records
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");

        // edit a line and confirm
        await click(rows[0].querySelector(".o_data_cell"));
        await editInput(target, ".o_selected_row [name=foo] input", "abc");
        await click(target, ".o_list_view");
        await click(target, ".modal .btn-primary");
        // Server error: if there was a crash manager, there would be an open error at this point...
        assert.strictEqual(
            $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
            "yop",
            "first cell should have discarded any change"
        );
        assert.strictEqual(
            $(target).find(".o_data_row:eq(1) .o_data_cell").text(),
            "blip",
            "second selected record should not have changed"
        );
        assert.containsNone(
            target,
            ".o_data_cell input.o_field_widget",
            "no field should be editable anymore"
        );
    });

    QUnit.test("editable readonly list view: navigation", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            selectRecord: (resId) => {
                assert.step(`resId: ${resId}`);
            },
        });

        assert.strictEqual(document.activeElement, target.querySelector(".o_searchview_input"));

        // ArrowDown two times must get to the checkbox selector of first data row
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child .o_list_record_selector input")
        );

        // select the second record
        triggerHotkey("ArrowDown");
        await nextTick();
        let checkbox = target.querySelector(
            ".o_data_row:nth-child(2) .o_list_record_selector input"
        );
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(!checkbox.checked);
        let event = triggerEvent(checkbox, null, "keydown", { key: "Space" }, { sync: true });
        assert.ok(!event.defaultPrevented);
        checkbox.checked = true;
        await nextTick();
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(checkbox.checked);

        await triggerEvent(document.activeElement, null, "input");
        await triggerEvent(document.activeElement, null, "change");
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(checkbox.checked);

        // select the fourth record
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        await nextTick();
        checkbox = target.querySelector(".o_data_row:nth-child(4) .o_list_record_selector input");
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(!checkbox.checked);
        event = triggerEvent(checkbox, null, "keydown", { key: "Space" }, { sync: true });
        assert.ok(!event.defaultPrevented);
        checkbox.checked = true;
        await nextTick();
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(checkbox.checked);

        await triggerEvent(document.activeElement, null, "input");
        await triggerEvent(document.activeElement, null, "change");
        assert.strictEqual(document.activeElement, checkbox);
        assert.ok(checkbox.checked);

        // toggle a row mode
        triggerHotkey("ArrowUp");
        triggerHotkey("ArrowUp");
        triggerHotkey("ArrowRight");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(2) [name=foo]")
        );
        triggerHotkey("Enter");
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(2) [name=foo] input")
        );

        // Keyboard navigation only interracts with selected elements
        triggerHotkey("Enter");
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(4)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(4) [name=foo] input")
        );

        triggerHotkey("Tab"); // go to 4th row int_field
        triggerHotkey("Tab"); // go to 2nd row foo field
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(2) [name=foo] input")
        );

        triggerHotkey("Tab"); // go to 2nd row int_field
        triggerHotkey("Tab"); // go to 4th row foo field
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(4)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(4) [name=foo] input")
        );

        triggerHotkey("Shift+Tab"); // go to 2nd row int_field
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(2)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(2) [name=int_field] input")
        );

        triggerHotkey("Shift+Tab"); // go to 2nd row foo field
        triggerHotkey("Shift+Tab"); // go to 4th row int_field field
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(4)"), "o_selected_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(4) [name=int_field] input")
        );

        // Clicking on an unselected row while a row is being edited will leave the edition
        await click(target, ".o_data_row:nth-child(3) [name=foo]");
        assert.containsNone(target, ".o_selected_row");

        // Clicking on an unselected record while no row is being edited will open the record
        assert.verifySteps([]);
        await click(target, ".o_data_row:nth-child(3) [name=foo]");
        assert.verifySteps([`resId: 3`]);
    });

    QUnit.test(
        "editable list view: multi edition: edit and validate last row",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree multi_edit="1">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </tree>`,
            });
            assert.containsN(target, ".o_data_row", 4);
            await click(target.querySelector(".o_list_view .o_list_record_selector input"));

            await click(target, ".o_data_row:last-child [name=int_field]");
            const input = target.querySelector(".o_data_row:last-child [name=int_field] input");
            input.value = 7;
            await triggerEvent(input, null, "input");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_row:last-child [name=int_field] input")
            );
            triggerHotkey("Enter");
            await nextTick();
            assert.containsOnce(target, ".modal");
            await click(target, ".modal .btn-primary");
            assert.containsN(target, ".o_data_row", 4);
        }
    );

    QUnit.test("editable readonly list view: navigation in grouped list", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "foo",
            arch: `<tree multi_edit="1"><field name="foo"/></tree>`,
            groupBy: ["bar"],
            selectRecord: (resId) => {
                assert.step(`resId: ${resId}`);
            },
        });

        // Open both groups
        const groupHeaders = [...target.querySelectorAll(".o_group_header")];
        assert.containsN(target, ".o_group_header", 2);
        await click(groupHeaders.shift());
        await click(groupHeaders.shift());

        // select 2 records
        const rows = [...target.querySelectorAll(".o_data_row")];
        assert.containsN(target, ".o_data_row", 4);
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[2], ".o_list_record_selector input");

        // toggle a row mode
        await click(rows[0].querySelector("[name=foo]"));
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(rows[0], "o_selected_row");
        assert.strictEqual(document.activeElement, rows[0].querySelector("[name=foo] input"));

        // Keyboard navigation only interracts with selected elements
        triggerHotkey("Enter");
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(rows[2], "o_selected_row");
        assert.strictEqual(document.activeElement, rows[2].querySelector("[name=foo] input"));

        triggerHotkey("Tab");
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(rows[0], "o_selected_row");
        assert.strictEqual(document.activeElement, rows[0].querySelector("[name=foo] input"));

        triggerHotkey("Tab");
        await nextTick();
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(rows[2], "o_selected_row");
        assert.strictEqual(document.activeElement, rows[2].querySelector("[name=foo] input"));

        // Click on a non selected row
        await click(rows[3].querySelector("[name=foo]"));
        assert.containsNone(target, ".o_selected_row");

        // Click again should select the clicked record
        await click(rows[3].querySelector("[name=foo]"));
        assert.verifySteps(["resId: 3"]);
    });

    QUnit.test(
        "editable readonly list view: single edition does not behave like a multi-edition",
        async function (assert) {
            await makeView({
                type: "list",
                arch: `
                    <tree multi_edit="1">
                        <field name="foo" required="1"/>
                    </tree>`,
                serverData,
                resModel: "foo",
            });

            // select a record
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");

            // edit a field (invalid input)
            await click(rows[0].querySelector(".o_data_cell"));
            await editInput(target, ".o_data_row [name=foo] input", "");
            assert.containsOnce(target, ".modal", "should have a modal (invalid fields)");

            await click(target, ".modal button.btn");

            // edit a field
            await click(rows[0].querySelector(".o_data_cell"));
            await editInput(target, ".o_data_row [name=foo] input", "bar");
            assert.containsNone(target, ".modal", "should not have a modal");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "bar",
                "the first row should be updated"
            );
        }
    );

    QUnit.test("non editable list view: multi edition", async function (assert) {
        await makeView({
            type: "list",
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            serverData,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args,
                        [[1, 2], { int_field: 666 }],
                        "should write on multi records"
                    );
                } else if (args.method === "web_read") {
                    if (args.args[0].length !== 1) {
                        assert.deepEqual(args.args, [[1, 2]], "should batch the read");
                        assert.deepEqual(args.kwargs.specification, { foo: {}, int_field: {} });
                    }
                }
            },
            resModel: "foo",
        });

        assert.verifySteps(["get_views", "web_search_read"]);

        // select two records
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");

        // edit a field
        await click(rows[0].querySelectorAll(".o_data_cell")[1]);
        await editInput(target, ".o_data_row [name=int_field] input", 666);
        await click(rows[0].querySelector(".o_data_cell"));
        assert.containsOnce(target, ".modal", "modal appears when switching cells");

        await click(target, ".modal .btn-secondary");
        assert.strictEqual(
            $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
            "yop10",
            "changes have been discarded and row is back to readonly"
        );

        await click(rows[0].querySelectorAll(".o_data_cell")[1]);
        await editInput(target, ".o_data_row [name=int_field] input", 666);
        assert.containsOnce(target, ".modal", "there should be an opened modal");
        assert.ok(
            $(".modal").text().includes("those 2 records"),
            "the number of records should be correctly displayed"
        );

        await click(target, ".modal .btn-primary");
        assert.verifySteps(["write", "web_read"]);
        assert.strictEqual(
            $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
            "yop666",
            "the first row should be updated"
        );
        assert.strictEqual(
            $(target).find(".o_data_row:eq(1) .o_data_cell").text(),
            "blip666",
            "the second row should be updated"
        );
        assert.containsNone(
            target,
            ".o_data_cell input.o_field_widget",
            "no field should be editable anymore"
        );
    });

    QUnit.test("editable list view: m2m tags in grouped list", async function (assert) {
        await makeView({
            arch: `
                <tree editable="top" multi_edit="1">
                    <field name="bar"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            groupBy: ["bar"],
            resModel: "foo",
            serverData,
            type: "list",
        });

        // Opens first group
        await click(target.querySelectorAll(".o_group_header")[1]);
        assert.notEqual(
            target.querySelector(".o_data_row").innerText,
            target.querySelectorAll(".o_data_row")[1].innerText,
            "First row and last row should have different values"
        );

        await click(target.querySelector("thead .o_list_record_selector input"));
        await click(target.querySelector(".o_data_row .o_field_many2many_tags"));
        await click(target.querySelector(".o_selected_row .o_field_many2many_tags .o_delete"));
        await click(target.querySelector(".modal .btn-primary"));
        assert.strictEqual(
            target.querySelector(".o_data_row").innerText,
            target.querySelectorAll(".o_data_row")[0].innerText,
            "All rows should have been correctly updated"
        );
    });

    QUnit.test("editable list: edit many2one from external link", async function (assert) {
        serverData.views = {
            "bar,false,form": `<form><field name="display_name"/></form>`,
        };

        await makeViewInDialog({
            arch: `
                <tree editable="top" multi_edit="1">
                    <field name="m2o"/>
                </tree>`,
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "get_formview_id") {
                    return false;
                }
            },
            resModel: "foo",
            type: "list",
        });

        assert.containsOnce(target, ".o_dialog .o_list_view");
        assert.containsNone(target, ".o_selected_row");
        await click(target.querySelector("thead .o_list_record_selector input"));
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_selected_row", "in edit mode");
        await click(target.querySelector(".o_external_button"));

        // Clicking somewhere on the form dialog should not close it
        // and should not leave edit mode
        assert.containsN(target, ".modal[role='dialog']", 2);
        await click(target.querySelector(".modal[role='dialog']"));
        assert.containsN(target, ".modal[role='dialog']", 2);
        assert.containsOnce(target, ".o_selected_row", "in edit mode");

        // Change the M2O value in the Form dialog (will open a confirmation dialog)
        await editInput(target.querySelectorAll(".modal")[1], "input", "OOF");
        await click(target.querySelectorAll(".modal")[1], ".o_form_button_save");
        assert.containsN(target, ".modal[role='dialog']", 3);
        const confirmationDialog = target.querySelectorAll(".modal")[2];
        assert.strictEqual(
            confirmationDialog.querySelector(".modal .o_field_widget[name=m2o]").innerText,
            "OOF",
            "Value of the m2o should be updated in the confirmation dialog"
        );

        // Close the confirmation dialog
        await click(confirmationDialog, ".btn-primary");

        assert.strictEqual(
            target.querySelector(".o_data_cell").innerText,
            "OOF",
            "Value of the m2o should be updated in the list"
        );
    });

    QUnit.test("editable list with fields with readonly modifier", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="bar"/>
                    <field name="foo" readonly="bar"/>
                    <field name="m2o" readonly="not bar"/>
                    <field name="int_field"/>
                </tree>`,
        });

        await click($(".o_list_button_add:visible").get(0));
        assert.containsOnce(target, ".o_selected_row");
        assert.notOk(target.querySelector(".o_selected_row .o_field_boolean input").checked);
        assert.doesNotHaveClass(
            target.querySelector(".o_selected_row .o_field_char"),
            "o_readonly_modifier"
        );
        assert.hasClass(
            target.querySelector(".o_selected_row .o_field_many2one"),
            "o_readonly_modifier"
        );

        await click(target.querySelector(".o_selected_row .o_field_boolean input"));
        assert.ok(target.querySelector(".o_selected_row .o_field_boolean input").checked);
        assert.hasClass(
            target.querySelector(".o_selected_row .o_field_char"),
            "o_readonly_modifier"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_selected_row .o_field_many2one"),
            "o_readonly_modifier"
        );

        await click(target.querySelector(".o_selected_row .o_field_many2one"));
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_selected_row .o_field_many2one input")
        );
    });

    QUnit.test(
        "editable form with many2one: click out does not discard the row",
        async function (assert) {
            serverData.models.bar.fields.m2o = {
                string: "M2O field",
                type: "many2one",
                relation: "foo",
            };

            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="o2m">
                            <tree editable="bottom">
                                <field name="m2o" required="1"/>
                            </tree>
                        </field>
                    </form>`,
            });

            assert.containsNone(target, ".o_data_row");

            await click(target.querySelector(".o_field_x2many_list_row_add > a"));
            assert.containsOnce(target, ".o_data_row");

            // focus and write something in the m2o
            await editInput(target, ".o_field_many2one input", "abcdef");
            await nextTick();

            // simulate focus out
            await triggerEvent(target, ".o_field_many2one input", "blur");

            assert.containsOnce(target, ".modal", "should ask confirmation to create a record");
            assert.containsOnce(target, ".o_data_row", "the row should still be there");
        }
    );

    QUnit.test(
        "editable form alongside html field: click out to unselect the row",
        async function (assert) {
            // FIXME WOWL hack: add back the text field as html field removed by web_editor html_field file
            registry.category("fields").add("html", textField, { force: true });

            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                arch: `
                    <form>
                        <field name="text" widget="html"/>
                        <field name="o2m">
                            <tree editable="bottom">
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </form>`,
            });

            assert.containsNone(target, ".o_data_row");

            await addRow(target);
            assert.containsOnce(target, ".o_data_row");
            assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

            await editInput(
                target,
                '[name="o2m"] .o_field_x2many .o_selected_row [name="display_name"] input',
                "new value"
            );

            // click outside to unselect the row
            await click(target.querySelector(".o_form_view"));
            assert.containsOnce(target, ".o_data_row");
            assert.doesNotHaveClass(target.querySelector(".o_data_row"), "o_selected_row");
        }
    );

    QUnit.test("list grouped by date:month", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="date"/></tree>',
            groupBy: ["date:month"],
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_group_header")].map((el) => el.innerText),
            ["January 2017 (1)", "None (3)"],
            "the group names should be correct"
        );
    });

    QUnit.test("grouped list edition with boolean_favorite widget", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="bar" widget="boolean_favorite"/></tree>',
            groupBy: ["m2o"],
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args[1],
                        { bar: false },
                        "should write the correct value"
                    );
                }
            },
        });

        await click(target.querySelector(".o_group_header"));
        assert.containsOnce(
            target,
            ".o_data_row:first .fa-star",
            "boolean value of the first record should be true"
        );
        await click(target.querySelector(".o_data_row .fa-star"));
        assert.containsOnce(
            target,
            ".o_data_row:first .fa-star-o",
            "boolean value of the first record should have been updated"
        );
    });

    QUnit.test("grouped list view, indentation for empty group", async function (assert) {
        serverData.models.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [
                [1, "Low"],
                [2, "Medium"],
                [3, "High"],
            ],
            default: 1,
        };
        serverData.models.foo.records.push({
            id: 5,
            foo: "blip",
            int_field: -7,
            m2o: 1,
            priority: 2,
        });
        serverData.models.foo.records.push({
            id: 6,
            foo: "blip",
            int_field: 5,
            m2o: 1,
            priority: 3,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="id"/></tree>',
            groupBy: ["priority", "m2o"],
            mockRPC(route, args) {
                // Override of the read_group to display the row even if there is no record in it,
                // to mock the behavihour of some fields e.g stage_id on the sale order.
                if (args.method === "web_read_group" && args.kwargs.groupby[0] === "m2o") {
                    return Promise.resolve({
                        groups: [
                            {
                                id: 8,
                                m2o: [1, "Value 1"],
                                m2o_count: 0,
                            },
                            {
                                id: 2,
                                m2o: [2, "Value 2"],
                                m2o_count: 1,
                            },
                        ],
                        length: 1,
                    });
                }
            },
        });

        // open the first group
        await click(target.querySelector(".o_group_header"));
        assert.containsOnce(
            target,
            "tr:nth-child(1) th.o_group_name .fa",
            "There should be an element creating the indentation for the subgroup."
        );
        assert.notStrictEqual(
            getCssVar(
                target.querySelector("tr:nth-child(1) th.o_group_name span"),
                "--o-list-group-level"
            ).trim(),
            "",
            "The element creating the indentation should have a group level to use for margin css calculation."
        );
    });

    QUnit.test("use the limit attribute in arch", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.limit, 2, "should use the correct limit value");
                }
            },
        });
        assert.deepEqual(getPagerValue(target), [1, 2]);
        assert.strictEqual(getPagerLimit(target), 4);
        assert.containsN(target, ".o_data_row", 2, "should display 2 data rows");
    });

    QUnit.test("concurrent reloads finishing in inverse order", async function (assert) {
        let blockSearchRead = false;
        const def = makeDeferred();
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: async function (route, args) {
                if (args.method === "web_search_read" && blockSearchRead) {
                    await def;
                }
            },
            searchViewArch: `
                <search>
                    <filter name="yop" domain="[('foo', '=', 'yop')]"/>
                </search>`,
        });

        assert.containsN(
            target,
            ".o_list_view .o_data_row",
            4,
            "list view should contain 4 records"
        );

        // reload with a domain (this request is blocked)
        blockSearchRead = true;
        // list.reload({ domain: [["foo", "=", "yop"]] });
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "yop");
        assert.containsN(
            target,
            ".o_list_view .o_data_row",
            4,
            "list view should still contain 4 records (search_read being blocked)"
        );

        // reload without the domain
        blockSearchRead = false;
        // list.reload({ domain: [] });
        // await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "yop");
        assert.containsN(
            target,
            ".o_list_view .o_data_row",
            4,
            "list view should still contain 4 records"
        );

        // unblock the RPC
        def.resolve();
        await nextTick();
        assert.containsN(
            target,
            ".o_list_view .o_data_row",
            4,
            "list view should still contain 4 records"
        );
    });

    QUnit.test(
        "list view move to previous page when all records from last page deleted",
        async function (assert) {
            assert.expect(8);

            let checkSearchRead = false;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="3"><field name="display_name"/></tree>',
                mockRPC(route, args) {
                    if (checkSearchRead && args.method === "web_search_read") {
                        assert.strictEqual(args.kwargs.limit, 3, "limit should 3");
                        assert.notOk(
                            args.kwargs.offset,
                            "offset should not be passed i.e. offset 0 by default"
                        );
                    }
                },
                actionMenus: {},
            });

            assert.deepEqual(getPagerValue(target), [1, 3]);
            assert.strictEqual(getPagerLimit(target), 4);

            // move to next page
            await pagerNext(target);
            assert.deepEqual(getPagerValue(target), [4, 4]);
            assert.strictEqual(getPagerLimit(target), 4);

            // delete a record
            await click(target.querySelector("tbody .o_data_row td.o_list_record_selector input"));
            checkSearchRead = true;
            await click(target.querySelector(".o_cp_action_menus .dropdown-toggle"));
            const deleteMenuItem = [
                ...target.querySelectorAll(".o_cp_action_menus .o_menu_item"),
            ].filter((el) => el.innerText === "Delete")[0];
            await click(deleteMenuItem);
            await click(target, ".modal button.btn-primary");
            assert.deepEqual(getPagerValue(target), [1, 3]);
            assert.strictEqual(getPagerLimit(target), 3);
        }
    );

    QUnit.test(
        "grouped list view move to previous page of group when all records from last page deleted",
        async function (assert) {
            assert.expect(10);

            let checkSearchRead = false;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="2"><field name="display_name"/></tree>',
                mockRPC(route, args) {
                    if (checkSearchRead && args.method === "web_search_read") {
                        assert.strictEqual(args.kwargs.limit, 2, "limit should 2");
                        assert.notOk(
                            args.kwargs.offset,
                            "offset should not be passed i.e. offset 0 by default"
                        );
                    }
                },
                actionMenus: {},
                groupBy: ["m2o"],
            });

            assert.strictEqual(
                $(target).find("th:contains(Value 1 (3))").length,
                1,
                "Value 1 should contain 3 records"
            );
            assert.strictEqual(
                $(target).find("th:contains(Value 2 (1))").length,
                1,
                "Value 2 should contain 1 record"
            );
            const groupheader = target.querySelector(".o_group_header");
            await click(groupheader);
            assert.deepEqual(getPagerValue(groupheader), [1, 2]);
            assert.strictEqual(getPagerLimit(groupheader), 3);

            // move to next page
            await pagerNext(groupheader);
            assert.deepEqual(getPagerValue(groupheader), [3, 3]);
            assert.strictEqual(getPagerLimit(groupheader), 3);

            // delete a record
            await click(target.querySelector(".o_data_row .o_list_record_selector input"));
            checkSearchRead = true;
            await click(target, ".o_cp_action_menus .dropdown-toggle");
            await click(
                [...target.querySelectorAll(".dropdown-item")].filter(
                    (el) => el.innerText === "Delete"
                )[0]
            );
            await click(target, ".modal .btn-primary");

            assert.strictEqual(
                $(target).find("th.o_group_name:eq(0) .o_pager_counter").text().trim(),
                "",
                "should be on first page now"
            );
            assert.containsN(target, ".o_data_row", 2);
        }
    );

    QUnit.test(
        "grouped list view move to next page when all records from the current page deleted",
        async function (assert) {
            serverData.models.foo.records = [1, 2, 3, 4, 5, 6]
                .map((i) => ({
                    id: i,
                    foo: `yop${i}`,
                    m2o: 1,
                }))
                .concat([{ id: 7, foo: "blip", m2o: 2 }]);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="2"><field name="foo"/></tree>',
                actionMenus: {},
                groupBy: ["m2o"],
            });

            assert.strictEqual(
                target.querySelector("tr.o_group_header:first-child th").textContent.trim(),
                "Value 1 (6)"
            );
            assert.strictEqual(
                target.querySelector("tr.o_group_header:nth-child(2) th").textContent.trim(),
                "Value 2 (1)"
            );
            const firstGroup = target.querySelector("tr.o_group_header:first-child");
            await click(firstGroup);
            assert.deepEqual(getPagerValue(firstGroup), [1, 2]);
            assert.strictEqual(getPagerLimit(firstGroup), 6);

            // delete all records from current page
            await click(target.querySelector("thead .o_list_record_selector input"));
            await click(target, ".o_cp_action_menus .dropdown-toggle");
            await click(
                [...target.querySelectorAll(".dropdown-item")].filter(
                    (el) => el.innerText === "Delete"
                )[0]
            );
            await click(target, ".modal .btn-primary");

            const groupLabel = "Value 1 (4)";
            const pagerText = "1-2 / 4";
            assert.strictEqual(
                target.querySelector(".o_group_header:nth-child(1) .o_group_name").textContent,
                `${groupLabel} ${pagerText}`
            );
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map((row) => row.textContent),
                ["yop3", "yop4"]
            );
        }
    );

    QUnit.test(
        "list view move to previous page when all records from last page archive/unarchived",
        async function (assert) {
            // add active field on foo model and make all records active
            serverData.models.foo.fields.active = {
                string: "Active",
                type: "boolean",
                default: true,
            };

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="3"><field name="display_name"/></tree>',
                actionMenus: {},
                mockRPC(route) {
                    if (route === "/web/dataset/call_kw/foo/action_archive") {
                        serverData.models.foo.records[3].active = false;
                        return {};
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_pager_counter").textContent.trim(),
                "1-3 / 4",
                "should have 2 pages and current page should be first page"
            );
            assert.strictEqual(
                target.querySelectorAll("tbody td.o_list_record_selector").length,
                3,
                "should have 3 records"
            );

            // move to next page
            await click(target, ".o_pager_next");
            assert.strictEqual(
                target.querySelector(".o_pager_counter").textContent.trim(),
                "4-4 / 4",
                "should be on second page"
            );
            assert.strictEqual(
                target.querySelectorAll("tbody td.o_list_record_selector").length,
                1,
                "should have 1 records"
            );
            assert.containsNone(
                target,
                ".o_control_panel_actions .o_cp_action_menus",
                "sidebar should not be available"
            );

            await click(
                target,
                "tbody .o_data_row:first-child td.o_list_record_selector:first-child input"
            );
            assert.containsOnce(
                target,
                ".o_control_panel_actions .o_cp_action_menus",
                "sidebar should be available"
            );

            // archive all records of current page
            await toggleActionMenu(target);
            await toggleMenuItem(target, "Archive");
            assert.strictEqual(
                document.querySelectorAll(".modal").length,
                1,
                "a confirm modal should be displayed"
            );

            await click(document, ".modal-footer .btn-primary");
            assert.strictEqual(
                target.querySelectorAll("tbody td.o_list_record_selector").length,
                3,
                "should have 3 records"
            );
            assert.strictEqual(
                target.querySelector(".o_pager_counter").textContent.trim(),
                "1-3 / 3",
                "should have 1 page only"
            );
        }
    );

    QUnit.test("list should ask to scroll to top on page changes", async function (assert) {
        patchWithCleanup(ListController.prototype, {
            onPageChangeScroll() {
                super.onPageChangeScroll(...arguments);
                assert.step("scroll");
            },
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree limit="3"><field name="display_name"/></tree>`,
        });

        // switch pages (should ask to scroll)
        await click(target, ".o_pager_next");
        await click(target, ".o_pager_previous");
        assert.verifySteps(["scroll", "scroll"], "should ask to scroll when switching pages");

        // change the limit (should not ask to scroll)
        await click(target.querySelector(".o_pager_value"));
        await editInput(target, ".o_pager_value", "1-2");
        await nextTick();
        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1-2");
        assert.verifySteps([], "should not ask to scroll when changing the limit");

        // switch pages again (should still ask to scroll)
        await click(target, ".o_pager_next");

        assert.verifySteps(["scroll"], "this is still working after a limit change");
    });

    QUnit.test(
        "list with handle field, override default_get, bottom when inline",
        async function (assert) {
            serverData.models.foo.fields.int_field.default = 10;

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom" default_order="int_field">
                        <field name="int_field" widget="handle"/>
                        <field name="foo"/>
                    </tree>`,
            });

            // starting condition
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell.o_list_char")].map(
                    (el) => el.textContent
                ),
                ["blip", "blip", "yop", "gnap"]
            );

            // click add a new line
            // save the record
            // check line is at the correct place

            const inputText = "ninja";
            await click($(".o_list_button_add:visible").get(0));
            await editInput(target, '[name="foo"] input', inputText);
            await clickSave(target);
            await click($(".o_list_button_add:visible").get(0));

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell.o_list_char")].map(
                    (el) => el.textContent
                ),
                ["blip", "blip", "yop", "gnap", inputText, ""]
            );
        }
    );

    QUnit.test("create record on list with modifiers depending on id", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="id" column_invisible="1"/>
                    <field name="foo" readonly="id"/>
                    <field name="int_field" invisible="id"/>
                </tree>`,
        });

        // add a new record
        await click($(".o_list_button_add:visible").get(0));

        // modifiers should be evaluted to false
        assert.containsOnce(target, ".o_selected_row");
        assert.doesNotHaveClass(
            target.querySelector(".o_selected_row [name=foo].o_field_widget"),
            "o_readonly_modifier"
        );
        assert.containsOnce(target, ".o_selected_row div[name=int_field]");

        // set a value and save
        await editInput(target, ".o_selected_row [name=foo] input", "some value");
        await clickSave(target);
        // int_field should not be displayed
        assert.strictEqual(target.querySelectorAll(".o_data_row .o_data_cell")[1].innerText, "");

        // edit again the just created record
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");
        // modifiers should be evaluated to true
        assert.hasClass(
            target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
            "o_readonly_modifier"
        );
        assert.containsNone(target, ".o_selected_row div[name=int_field]");
    });

    QUnit.test("readonly boolean in editable list is readonly", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="bar" readonly="foo != 'yop'"/>
                </tree>`,
        });

        // clicking on disabled checkbox with active row does not work
        const rows = target.querySelectorAll(".o_data_row");
        const disabledCell = rows[1].querySelector("[name=bar]");
        await click(rows[1].querySelector(".o_data_cell"));
        assert.containsOnce(disabledCell, ":disabled:checked");
        await click(rows[1].querySelector("[name=bar] div"));
        assert.containsOnce(disabledCell, ":checked", "clicking disabled checkbox did not work");
        assert.ok(
            $(document.activeElement).is('input[type="text"]'),
            "disabled checkbox is not focused after click"
        );

        // clicking on enabled checkbox with active row toggles check mark
        await click(rows[0].querySelector(".o_data_cell"));
        const enabledCell = rows[0].querySelector("div[name=bar]");
        assert.containsOnce(enabledCell, ":checked:not(:disabled)");
        await click(rows[0].querySelector("div[name=bar] div"));
        assert.containsNone(
            enabledCell,
            ":checked",
            "clicking enabled checkbox worked and unchecked it"
        );
        assert.ok(
            $(document.activeElement).is('input[type="checkbox"]'),
            "enabled checkbox is focused after click"
        );
    });

    QUnit.test("grouped list with groups_limit attribute", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree groups_limit="3"><field name="foo"/></tree>',
            groupBy: ["int_field"],
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        assert.containsN(target, ".o_group_header", 3); // page 1
        assert.containsNone(target, ".o_data_row");
        assert.containsOnce(target, ".o_pager"); // has a pager

        await pagerNext(target); // switch to page 2
        assert.containsN(target, ".o_group_header", 1); // page 2
        assert.containsNone(target, ".o_data_row");

        assert.verifySteps([
            "get_views",
            "web_read_group", // read_group page 1
            "web_read_group", // read_group page 2
        ]);
    });

    QUnit.test("ungrouped list with groups_limit attribute, then group", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree groups_limit="3"><field name="foo"/></tree>',
            searchViewArch: `
                <search>
                    <filter name="int_field" string="GroupBy IntField" context="{'group_by': 'int_field'}"/>
                </search>`,
        });

        assert.containsN(target, ".o_data_row", 4);

        // add a custom group in searchview groupby
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "GroupBy IntField");

        assert.containsN(target, ".o_group_header", 3);
        assert.strictEqual(
            target.querySelector(".o_pager_value").innerText,
            "1-3",
            "pager should be correct"
        );
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
    });

    QUnit.test("grouped list with groups_limit attribute, then ungroup", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree groups_limit="3"><field name="foo"/></tree>',
            irFilters: [
                {
                    context: "{'group_by': ['int_field']}",
                    domain: "[]",
                    id: 8,
                    is_default: true,
                    name: "GroupBy IntField",
                    sort: "[]",
                    user_id: [2, "Mitchell Admin"],
                },
            ],
        });

        assert.containsN(target, ".o_group_header", 3);
        assert.strictEqual(
            target.querySelector(".o_pager_value").innerText,
            "1-3",
            "pager should be correct"
        );
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");

        // remove groupby
        await removeFacet(target);

        assert.containsN(target, ".o_data_row", 4);
    });

    QUnit.test("multi level grouped list with groups_limit attribute", async function (assert) {
        for (let i = 50; i < 55; i++) {
            serverData.models.foo.records.push({ id: i, foo: "foo", int_field: i });
        }
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree groups_limit="3"><field name="foo"/></tree>',
            groupBy: ["foo", "int_field"],
        });

        assert.containsN(target, ".o_group_header", 3);
        assert.strictEqual(
            target.querySelector(".o_pager_value").innerText,
            "1-3",
            "pager should be correct"
        );
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_group_header")), [
            "blip (2) ",
            "foo (5) ",
            "gnap (1) ",
        ]);

        // open foo group
        await click(target.querySelectorAll(".o_group_header")[1]);

        assert.containsN(target, ".o_group_header", 6);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_group_header")), [
            "blip (2) ",
            "foo (5) 1-3 / 5",
            "50 (1) ",
            "51 (1) ",
            "52 (1) ",
            "gnap (1) ",
        ]);
    });

    QUnit.test("grouped list with expand attribute", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ["bar"],
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        assert.containsN(target, ".o_group_header", 2);
        assert.containsN(target, ".o_data_row", 4);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["blip", "yop", "blip", "gnap"]
        );

        assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_search_read"]);
    });

    QUnit.test("grouped list with dynamic expand attribute (eval true)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree expand="context.get('expand', False)"><field name="foo"/></tree>`,
            context: {
                expand: true,
            },
            groupBy: ["bar"],
        });

        assert.containsN(target, ".o_group_header", 2);
        assert.containsN(target, ".o_data_row", 4);
    });

    QUnit.test("grouped list with dynamic expand attribute (eval false)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree expand="context.get('expand', False)"><field name="foo"/></tree>`,
            context: {
                expand: false,
            },
            groupBy: ["bar"],
        });

        assert.containsN(target, ".o_group_header", 2);
        assert.containsNone(target, ".o_data_row");
    });

    QUnit.test("grouped list (two levels) with expand attribute", async function (assert) {
        // the expand attribute only opens the first level groups
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ["bar", "int_field"],
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        assert.containsN(target, ".o_group_header", 6);

        assert.verifySteps([
            "get_views",
            "web_read_group", // global
            "web_read_group", // first group
            "web_read_group", // second group
        ]);
    });

    QUnit.test("grouped lists with expand attribute and a lot of groups", async function (assert) {
        for (var i = 0; i < 15; i++) {
            serverData.models.foo.records.push({ foo: "record " + i, int_field: i });
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ["int_field"],
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    assert.step(args.method);
                }
            },
        });

        assert.containsN(target, ".o_group_header", 10); // page 1
        assert.containsN(target, ".o_data_row", 10); // two groups contains two records
        assert.containsOnce(target, ".o_pager"); // has a pager

        assert.deepEqual(
            [...target.querySelectorAll(".o_group_name")].map((el) => el.innerText),
            [
                "-4 (1)",
                "0 (1)",
                "1 (1)",
                "2 (1)",
                "3 (1)",
                "4 (1)",
                "5 (1)",
                "6 (1)",
                "7 (1)",
                "8 (1)",
            ]
        );
        await pagerNext(target); // switch to page 2

        assert.containsN(target, ".o_group_header", 7); // page 2
        assert.containsN(target, ".o_data_row", 9); // two groups contains two records

        assert.deepEqual(
            [...target.querySelectorAll(".o_group_name")].map((el) => el.innerText),
            ["9 (2)", "10 (2)", "11 (1)", "12 (1)", "13 (1)", "14 (1)", "17 (1)"]
        );

        assert.verifySteps([
            "web_read_group", // read_group page 1
            "web_read_group", // read_group page 2
        ]);
    });

    QUnit.test("add filter in a grouped list with a pager", async function (assert) {
        serverData.actions = {
            11: {
                id: 11,
                name: "Action 11",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[3, "list"]],
                search_view_id: [9, "search"],
                context: { group_by: ["int_field"] },
            },
        };

        serverData.views = {
            "foo,3,list": '<tree groups_limit="3"><field name="foo"/></tree>',
            "foo,9,search": `
                <search>
                    <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                </search>`,
        };

        const mockRPC = (route, args) => {
            if (args.method === "web_read_group") {
                assert.step(JSON.stringify(args.kwargs.domain) + ", " + args.kwargs.offset);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 11);
        assert.containsOnce(target, ".o_list_view");
        assert.deepEqual(getPagerValue(target), [1, 3]);
        assert.containsN(target, ".o_group_header", 3); // page 1

        await pagerNext(target);
        assert.deepEqual(getPagerValue(target), [4, 4]);
        assert.containsN(target, ".o_group_header", 1); // page 2

        // toggle a filter -> there should be only one group left (on page 1)
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, 0);
        assert.deepEqual(getPagerValue(target), [1, 1]);
        assert.containsN(target, ".o_group_header", 1); // page 1

        assert.verifySteps(["[], 0", "[], 3", '[["bar","=",false]], 0']);
    });

    QUnit.test("editable grouped lists", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            searchViewArch: `
                <search>
                    <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
                </search>`,
        });
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "bar");
        await click(target.querySelector(".o_group_header"));

        // enter edition (grouped case)
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");

        // click on the body should leave the edition
        await click(target, ".o_list_view");
        assert.containsNone(target, ".o_selected_row");

        // reload without groupBy
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "bar");

        // enter edition (ungrouped case)
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");

        // click on the body should leave the edition
        await click(target, ".o_list_view");
        assert.containsNone(target, ".o_selected_row");
    });

    QUnit.test("grouped lists are editable (ungrouped first)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            searchViewArch: `
                <search>
                    <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
                </search>`,
        });

        // enter edition (ungrouped case)
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");

        // reload with a groupby
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "bar");

        // open first group
        await click(target.querySelector(".o_group_header"));

        // enter edition (grouped case)
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");
    });

    QUnit.test("char field edition in editable grouped list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
        });
        await click(target.querySelector(".o_group_header"));
        await click(target.querySelector(".o_data_cell"));
        await editInput(target, '.o_selected_row .o_data_cell [name="foo"] input', "pla");
        await clickSave(target);
        assert.strictEqual(
            serverData.models.foo.records[3].foo,
            "pla",
            "the edition should have been properly saved"
        );
        assert.containsOnce(target, ".o_data_row:first:contains(pla)");
    });

    QUnit.test("control panel buttons in editable grouped list views", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            searchViewArch: `
                <search>
                    <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
                </search>`,
        });

        assert.containsN(
            target,
            ".o_list_button_add",
            2,
            "Should have 2 add button (small and xl screens)"
        );

        // reload with a groupby
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "bar");

        assert.containsOnce(target, ".o_list_button_add:visible");

        // reload without groupby
        await toggleMenuItem(target, "bar");

        assert.containsN(
            target,
            ".o_list_button_add",
            2,
            "Should have 2 add button (small and xl screens)"
        );
    });

    QUnit.test(
        "control panel buttons in multi editable grouped list views",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["foo"],
                arch: `
                    <tree multi_edit="1">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </tree>`,
            });

            assert.containsNone(target, ".o_data_row", "all groups should be closed");
            assert.strictEqual(
                $(".o_list_button_add:visible").length,
                1,
                "should have a visible Create button"
            );

            await click(target.querySelector(".o_group_header"));
            assert.containsN(target, ".o_data_row", 2, "first group should be opened");
            assert.strictEqual(
                $(".o_list_button_add:visible").length,
                1,
                "should have a visible Create button"
            );

            await click(target.querySelector(".o_data_row .o_list_record_selector input"));
            assert.containsOnce(
                target,
                ".o_data_row:eq(0) .o_list_record_selector input:enabled",
                "should have selected first record"
            );
            assert.strictEqual(
                $(".o_list_button_add:visible").length,
                1,
                "should have a visible Create button"
            );

            await click([...target.querySelectorAll(".o_group_header")].pop());
            assert.containsN(target, ".o_data_row", 3, "two groups should be opened");
            assert.strictEqual(
                $(".o_list_button_add:visible").length,
                1,
                "should have a visible Create button"
            );
        }
    );

    QUnit.test("edit a line and discard it in grouped editable", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
            groupBy: ["bar"],
        });

        await click(target, ".o_group_header:nth-child(2)");
        await click(target, ".o_data_row:nth-child(5) .o_data_cell:nth-child(2)");
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(5)"), "o_selected_row");

        await click($(".o_list_button_discard:visible").get(0));
        await click(target, ".o_data_row:nth-child(3) .o_data_cell:nth-child(2)");
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(3)"), "o_selected_row");

        await click($(".o_list_button_discard:visible").get(0));
        assert.containsNone(target, ".o_selected_row");

        await click(target, ".o_data_row:nth-child(5) .o_data_cell:nth-child(2)");
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(5)"), "o_selected_row");
    });

    QUnit.test(
        "add and discard a record in a multi-level grouped list view",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
                groupBy: ["foo", "bar"],
            });

            // unfold first subgroup
            await click(target.querySelector(".o_group_header"));
            await click(target.querySelectorAll(".o_group_header")[1]);
            assert.hasClass(target.querySelector(".o_group_header"), "o_group_open");
            assert.hasClass(target.querySelectorAll(".o_group_header")[1], "o_group_open");
            assert.containsOnce(target, ".o_data_row");

            // add a record to first subgroup
            await click(target, ".o_group_field_row_add a");
            assert.containsN(target, ".o_data_row", 2);

            // discard
            await clickDiscard(target);
            assert.containsOnce(target, ".o_data_row");
        }
    );

    QUnit.test(
        "pressing ESC in editable grouped list should discard the current line changes",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
                groupBy: ["bar"],
            });

            await click(target.querySelectorAll(".o_group_header")[1]); // open second group
            assert.containsN(target, "tr.o_data_row", 3);

            await click(target.querySelector(".o_data_cell"));

            // update foo field of edited row
            await editInput(target, ".o_data_cell [name=foo] input", "new_value");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_cell [name=foo] input")
            );
            // discard by pressing ESC
            triggerHotkey("Escape");
            await nextTick();
            assert.containsNone(target, ".modal");

            assert.containsOnce(target, "tbody tr td:contains(yop)");
            assert.containsN(target, "tr.o_data_row", 3);
            assert.containsNone(target, "tr.o_data_row.o_selected_row");
            assert.isNotVisible(target.querySelector(".o_list_button_save"));
        }
    );

    QUnit.test('pressing TAB in editable="bottom" grouped list', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            groupBy: ["bar"],
        });

        // open two groups
        await click(getGroup(1));
        assert.containsN(target, ".o_data_row", 1, "first group contains 1 row");

        await click(getGroup(2));
        assert.containsN(target, ".o_data_row", 4, "second group contains 3 rows");

        await click(target.querySelector(".o_data_cell"));
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");

        // Press 'Tab' -> should go to first line of second group
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in second group)
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in second group)
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:nth(3)"), "o_selected_row");

        // Press 'Tab' -> should go back to first line of first group
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
    });

    QUnit.test('pressing TAB in editable="top" grouped list', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                </tree>`,
            groupBy: ["bar"],
        });

        // open two groups
        await click(target.querySelector(".o_group_header"));
        assert.containsN(target, ".o_data_row", 1);

        await click(target.querySelector(".o_group_header:last-child"));
        assert.containsN(target, ".o_data_row", 4);

        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

        const dataRows = [...target.querySelectorAll(".o_data_row")];
        dataRows.push(dataRows.shift());
        for (const row of dataRows) {
            triggerHotkey("Tab");
            await nextTick();
            assert.hasClass(row, "o_selected_row");
        }
    });

    QUnit.test("pressing TAB in editable grouped list with create=0", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
            groupBy: ["bar"],
        });

        // open two groups
        await click(getGroup(1));
        assert.containsN(target, ".o_data_row", 1, "first group contains 1 rows");
        await click(getGroup(2));
        assert.containsN(target, ".o_data_row", 4, "first group contains 3 row");

        await click(target.querySelector(".o_data_cell"));
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");

        // Press 'Tab' -> should go to the second group
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in second group)
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in second group)
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:nth(3)"), "o_selected_row");

        // Press 'Tab' -> should go back to first line of first group
        triggerHotkey("Tab");
        await nextTick();
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
    });

    QUnit.test('pressing SHIFT-TAB in editable="bottom" grouped list', async function (assert) {
        serverData.models.foo.records[2].bar = false;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo" required="1"/>
                </tree>`,
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_header"));
        assert.containsN(target, ".o_data_row", 2);
        await click(target.querySelector(".o_group_header:last-child"));
        assert.containsN(target, ".o_data_row", 4);

        // navigate inside a group
        const secondRow = target.querySelectorAll(".o_data_row")[1];
        await click(secondRow, ".o_data_cell");
        assert.hasClass(secondRow, "o_selected_row");

        triggerHotkey("shift+Tab");
        await nextTick();

        const firstRow = target.querySelector(".o_data_row");
        assert.hasClass(firstRow, "o_selected_row");
        assert.doesNotHaveClass(secondRow, "o_selected_row");

        // navigate between groups
        const thirdRow = target.querySelectorAll(".o_data_row")[2];
        await click(thirdRow, ".o_data_cell");

        assert.hasClass(thirdRow, "o_selected_row");

        triggerHotkey("shift+Tab");
        await nextTick();

        assert.hasClass(secondRow, "o_selected_row");
    });

    QUnit.test('pressing SHIFT-TAB in editable="top" grouped list', async function (assert) {
        serverData.models.foo.records[2].bar = false;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo" required="1"/>
                </tree>`,
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_header"));
        assert.containsN(target, ".o_data_row", 2);
        await click(target.querySelector(".o_group_header:last-child"));
        assert.containsN(target, ".o_data_row", 4);

        // navigate inside a group
        const secondRow = target.querySelectorAll(".o_data_row")[1];
        await click(secondRow, ".o_data_cell");
        assert.hasClass(secondRow, "o_selected_row");

        triggerHotkey("shift+Tab");
        await nextTick();

        const firstRow = target.querySelector(".o_data_row");
        assert.hasClass(firstRow, "o_selected_row");
        assert.doesNotHaveClass(secondRow, "o_selected_row");

        // navigate between groups
        const thirdRow = target.querySelectorAll(".o_data_row")[2];
        await click(thirdRow, ".o_data_cell");

        assert.hasClass(thirdRow, "o_selected_row");

        triggerHotkey("shift+Tab");
        await nextTick();

        assert.hasClass(secondRow, "o_selected_row");
    });

    QUnit.test(
        'pressing SHIFT-TAB in editable grouped list with create="0"',
        async function (assert) {
            serverData.models.foo.records[2].bar = false;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top" create="0">
                        <field name="foo" required="1"/>
                    </tree>`,
                groupBy: ["bar"],
            });

            await click(target.querySelector(".o_group_header"));
            assert.containsN(target, ".o_data_row", 2);
            await click(target.querySelector(".o_group_header:last-child"));
            assert.containsN(target, ".o_data_row", 4);

            // navigate inside a group
            const secondRow = target.querySelectorAll(".o_data_row")[1];
            await click(secondRow, ".o_data_cell");
            assert.hasClass(secondRow, "o_selected_row");

            triggerHotkey("shift+Tab");
            await nextTick();

            const firstRow = target.querySelector(".o_data_row");
            assert.hasClass(firstRow, "o_selected_row");
            assert.doesNotHaveClass(secondRow, "o_selected_row");

            // navigate between groups
            const thirdRow = target.querySelectorAll(".o_data_row")[2];
            await click(thirdRow, ".o_data_cell");

            assert.hasClass(thirdRow, "o_selected_row");

            triggerHotkey("shift+Tab");
            await nextTick();

            assert.hasClass(secondRow, "o_selected_row");
        }
    );

    QUnit.test("editing then pressing TAB in editable grouped list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
            groupBy: ["bar"],
        });

        // open two groups
        await click(getGroup(1));
        assert.containsN(target, ".o_data_row", 1, "first group contains 1 rows");
        await click(getGroup(2));
        assert.containsN(target, ".o_data_row", 4, "first group contains 3 row");

        // select and edit last row of first group
        await click(target.querySelector(".o_data_row").querySelector(".o_data_cell"));
        assert.hasClass($(target).find(".o_data_row:nth(0)"), "o_selected_row");
        await editInput(target, '.o_selected_row [name="foo"] input', "new value");

        // Press 'Tab' -> should create a new record as we edited the previous one
        triggerHotkey("Tab");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

        // fill foo field for the new record and press 'tab' -> should create another record
        await editInput(target, '.o_selected_row [name="foo"] input', "new record");
        triggerHotkey("Tab");
        await nextTick();

        assert.containsN(target, ".o_data_row", 6);
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        // leave this new row empty and press tab -> should discard the new record and move to the
        // next group
        triggerHotkey("Tab");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        assert.verifySteps([
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "web_save",
            "onchange",
            "web_save",
            "onchange",
        ]);
    });

    QUnit.test(
        "editing then pressing TAB (with a readonly field) in grouped list",
        async function (assert) {
            serverData.models.foo.records[0].bar = false;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                        <field name="int_field" readonly="1"/>
                    </tree>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
                groupBy: ["bar"],
            });

            await click(target.querySelector(".o_group_header"));
            await click(target.querySelector(".o_data_row [name=foo]"));

            await editInput(target, ".o_selected_row [name=foo] input", "new value");

            triggerHotkey("Tab");
            await nextTick();

            assert.strictEqual(
                target.querySelector(".o_data_row [name=foo]").innerText,
                "new value"
            );

            const secondDataRow = target.querySelectorAll(".o_data_row")[1];
            assert.strictEqual(
                document.activeElement,
                secondDataRow.querySelector(".o_selected_row [name=foo] input")
            );

            assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_save"]);
        }
    );

    QUnit.test('pressing ENTER in editable="bottom" grouped list view', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
            groupBy: ["bar"],
        });

        await click(getGroup(1)); // open first group
        await click(getGroup(2)); // open second group
        assert.containsN(target, "tr.o_data_row", 4);

        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[2].querySelector(".o_data_cell"));
        assert.hasClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");

        // press enter in input should move to next record
        triggerHotkey("Enter");
        await nextTick();

        assert.hasClass($(target).find("tr.o_data_row:eq(3)"), "o_selected_row");
        assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");

        // press enter on last row should create a new record
        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, "tr.o_data_row", 5);
        assert.hasClass($(target).find("tr.o_data_row:eq(4)"), "o_selected_row");

        assert.verifySteps([
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "onchange",
        ]);
    });

    QUnit.test('pressing ENTER in editable="top" grouped list view', async function (assert) {
        serverData.models.foo.records[2].bar = false;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                </tree>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_header"));
        await click(target.querySelector(".o_group_header:last-child"));
        assert.containsN(target, "tr.o_data_row", 4);

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

        triggerHotkey("Enter");
        await nextTick();

        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");

        triggerHotkey("Enter");
        await nextTick();

        assert.hasClass(target.querySelectorAll(".o_data_row")[2], "o_selected_row");

        assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_search_read"]);
    });

    QUnit.test(
        "pressing ENTER in editable grouped list view with create=0",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
                mockRPC(route, { method }) {
                    assert.step(method);
                },
                groupBy: ["bar"],
            });
            assert.containsN(target, ".o_group_header", 2);
            assert.containsNone(target, ".o_data_row");
            assert.verifySteps(["get_views", "web_read_group"]);

            // Open group headers
            const [firstGroupHeader, secondGroupHeader] = [
                ...target.querySelectorAll(".o_group_header"),
            ];
            await click(firstGroupHeader);
            await click(secondGroupHeader);
            assert.containsN(target, ".o_data_row", 4);
            assert.containsNone(target, ".o_selected_row");
            assert.verifySteps(["web_search_read", "web_search_read"]);

            // Click on first data row
            const dataRows = [...target.querySelectorAll(".o_data_row")];
            await click(dataRows[0].querySelector("[name=foo]"));
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(dataRows[0], "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                dataRows[0].querySelector("[name=foo] input")
            );
            assert.strictEqual(dataRows[0], target.querySelector("tbody tr:nth-child(2)"));

            // Press enter in input should move to next record, even if record is in another group
            triggerHotkey("Enter");
            await nextTick();
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(dataRows[1], "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                dataRows[1].querySelector("[name=foo] input")
            );
            assert.strictEqual(dataRows[1], target.querySelector("tbody tr:nth-child(4)"));

            // Press enter in input should move to next record
            triggerHotkey("Enter");
            await nextTick();
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(dataRows[2], "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                dataRows[2].querySelector("[name=foo] input")
            );
            assert.strictEqual(dataRows[2], target.querySelector("tbody tr:nth-child(5)"));

            // Once again
            triggerHotkey("Enter");
            await nextTick();
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(dataRows[3], "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                dataRows[3].querySelector("[name=foo] input")
            );
            assert.strictEqual(dataRows[3], target.querySelector("tbody tr:nth-child(6)"));

            // Once again on the last data row should cycle to the first data row
            triggerHotkey("Enter");
            await nextTick();
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(dataRows[0], "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                dataRows[0].querySelector("[name=foo] input")
            );
            assert.strictEqual(dataRows[0], target.querySelector("tbody tr:nth-child(2)"));

            assert.verifySteps([]);
        }
    );

    QUnit.test("cell-level keyboard navigation in non-editable list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo" required="1"/></tree>',
            selectRecord: (resId) => {
                assert.step(`resId: ${resId}`);
            },
        });

        assert.strictEqual(document.activeElement, target.querySelector(".o_searchview_input"));

        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("thead .o_list_record_selector input")
        );

        triggerHotkey("ArrowUp");
        await nextTick();
        assert.strictEqual(document.activeElement, target.querySelector(".o_searchview_input"));

        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:first-child .o_list_record_selector input")
        );

        triggerHotkey("ArrowRight");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:first-child .o_field_cell[name=foo]")
        );
        assert.strictEqual(document.activeElement.textContent, "yop");

        triggerHotkey("ArrowRight");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:first-child .o_field_cell[name=foo]")
        );

        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(2) .o_field_cell[name=foo]")
        );
        assert.strictEqual(document.activeElement.textContent, "blip");

        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(3) .o_field_cell[name=foo]")
        );
        assert.strictEqual(document.activeElement.textContent, "gnap");

        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(4) .o_field_cell[name=foo]")
        );
        assert.strictEqual(document.activeElement.textContent, "blip");

        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(4) .o_field_cell[name=foo]")
        );
        assert.strictEqual(document.activeElement.textContent, "blip");

        triggerHotkey("ArrowRight");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(4) .o_field_cell[name=foo]")
        );
        assert.strictEqual(document.activeElement.textContent, "blip");

        triggerHotkey("ArrowLeft");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(4) .o_list_record_selector input")
        );

        triggerHotkey("ArrowLeft");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(4) .o_list_record_selector input")
        );

        triggerHotkey("ArrowUp");
        triggerHotkey("ArrowRight");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody tr:nth-child(3) .o_field_cell[name=foo]")
        );
        assert.strictEqual(document.activeElement.textContent, "gnap");

        triggerHotkey("Enter");
        await nextTick();
        assert.verifySteps(["resId: 3"]);
    });

    QUnit.test("keyboard navigation from last cell in editable list", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>
            `,
        });

        // Click on last cell
        await click(target, ".o_data_row:last-child [name=int_field]");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:last-child [name=int_field] input")
        );

        // Tab should focus the first field of first row
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child [name=foo] input")
        );

        // Shift+Tab should focus back the last field of last row
        triggerHotkey("Shift+Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:last-child [name=int_field] input")
        );

        // Enter should add a new row at the bottom
        assert.containsN(target, ".o_data_row", 4);
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:last-child [name=foo] input")
        );

        // Enter should discard the edited row as it is pristine + get to first row
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 4);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child [name=foo] input")
        );

        // Click on last cell
        await click(target, ".o_data_row:last-child [name=int_field]");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:last-child [name=int_field] input")
        );

        // Enter should add a new row at the bottom
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);

        // Edit the row and press enter: should add a new row
        const input = target.querySelector(".o_data_row:last-child [name=foo] input");
        assert.strictEqual(document.activeElement, input);
        input.value = "blork";
        await triggerEvent(input, null, "input");
        triggerHotkey("Enter");
        await triggerEvent(input, null, "change");
        assert.containsN(target, ".o_data_row", 6);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:last-child [name=foo] input")
        );

        // Escape should discard the added row as it is pristine + view should go into readonly mode
        triggerHotkey("Escape");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.containsNone(target, ".o_selected_row");
    });

    QUnit.test("keyboard navigation from last cell in editable grouped list", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["bar"],
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>
            `,
        });

        assert.containsNone(target, ".o_data_row");
        assert.containsN(target, ".o_group_header", 2);

        // Open first and second groups
        await click(getGroup(1));
        await click(getGroup(2));
        assert.containsN(target, ".o_data_row", 4);

        // Click on last cell
        await click(getDataRow(4).querySelector("[name=int_field]"));
        assert.strictEqual(
            document.activeElement,
            getDataRow(4).querySelector("[name=int_field] input")
        );

        // Tab should focus the first field of first data row
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(document.activeElement, getDataRow(1).querySelector("[name=foo] input"));

        // Shift+Tab should focus back the last field of last row
        triggerHotkey("Shift+Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            getDataRow(4).querySelector("[name=int_field] input")
        );

        // Enter should add a new row at the bottom
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.strictEqual(document.activeElement, getDataRow(5).querySelector("[name=foo] input"));

        // Enter should discard the edited row as it is pristine + get to first row
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 4);
        assert.strictEqual(document.activeElement, getDataRow(1).querySelector("[name=foo] input"));

        // Click on last cell
        await click(getDataRow(4).querySelector("[name=int_field]"));
        assert.strictEqual(
            document.activeElement,
            getDataRow(4).querySelector("[name=int_field] input")
        );

        // Enter should add a new row at the bottom
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);

        // Edit the row and press enter: should add a new row
        let input = getDataRow(5).querySelector("[name=foo] input");
        assert.strictEqual(document.activeElement, input);
        input.value = "blork";
        await triggerEvent(input, null, "input");
        triggerHotkey("Enter");
        await triggerEvent(input, null, "change");
        assert.containsN(target, ".o_data_row", 6);
        assert.strictEqual(document.activeElement, getDataRow(6).querySelector("[name=foo] input"));

        // Escape should discard the added row as it is pristine + view should go into readonly mode
        triggerHotkey("Escape");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.containsNone(target, ".o_selected_row");

        // Click on last data row of first group
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (1) -4");
        await click(getDataRow(1).querySelector("[name=foo]"));
        assert.strictEqual(document.activeElement, getDataRow(1).querySelector("[name=foo] input"));

        // Enter should add a new row in the first group
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 6);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (2) -4");

        // Enter should discard the edited row as it is pristine + get to next data row
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (1) -4");
        assert.strictEqual(document.activeElement, getDataRow(2).querySelector("[name=foo] input"));

        // Shift+Tab should focus back the last field of first row
        triggerHotkey("Shift+Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            getDataRow(1).querySelector("[name=int_field] input")
        );

        // Enter should add a new row in the first group
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 6);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (2) -4");

        // Edit the row and press enter: should add a new row
        input = getDataRow(2).querySelector("[name=foo] input");
        assert.strictEqual(document.activeElement, input);
        input.value = "zzapp";
        await triggerEvent(input, null, "input");
        triggerHotkey("Enter");
        await triggerEvent(input, null, "change");
        assert.containsN(target, ".o_data_row", 7);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (3) -4");
        assert.strictEqual(document.activeElement, getDataRow(3).querySelector("[name=foo] input"));
    });

    QUnit.test("keyboard navigation from last cell in multi-edit list", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["bar"],
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>
            `,
        });

        assert.containsNone(target, ".o_data_row");
        assert.containsN(target, ".o_group_header", 2);

        // Open first and second groups
        await click(getGroup(1));
        await click(getGroup(2));
        assert.containsN(target, ".o_data_row", 4);

        // Click on last cell
        await click(getDataRow(4).querySelector("[name=int_field]"));
        assert.strictEqual(
            document.activeElement,
            getDataRow(4).querySelector("[name=int_field] input")
        );

        // Tab should focus the first field of first data row
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(document.activeElement, getDataRow(1).querySelector("[name=foo] input"));

        // Shift+Tab should focus back the last field of last row
        triggerHotkey("Shift+Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            getDataRow(4).querySelector("[name=int_field] input")
        );

        // Enter should add a new row at the bottom
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.strictEqual(document.activeElement, getDataRow(5).querySelector("[name=foo] input"));

        // Enter should discard the edited row as it is pristine + get to first row
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 4);
        assert.strictEqual(document.activeElement, getDataRow(1).querySelector("[name=foo] input"));

        // Click on last cell
        await click(getDataRow(4).querySelector("[name=int_field]"));
        assert.strictEqual(
            document.activeElement,
            getDataRow(4).querySelector("[name=int_field] input")
        );

        // Enter should add a new row at the bottom
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);

        // Edit the row and press enter: should add a new row
        let input = getDataRow(5).querySelector("[name=foo] input");
        assert.strictEqual(document.activeElement, input);
        input.value = "blork";
        await triggerEvent(input, null, "input");
        triggerHotkey("Enter");
        await triggerEvent(input, null, "change");
        assert.containsN(target, ".o_data_row", 6);
        assert.strictEqual(document.activeElement, getDataRow(6).querySelector("[name=foo] input"));

        // Escape should discard the added row as it is pristine + view should go into readonly mode
        triggerHotkey("Escape");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.containsNone(target, ".o_selected_row");

        // Click on last data row of first group
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (1) -4");
        await click(getDataRow(1).querySelector("[name=foo]"));
        assert.strictEqual(document.activeElement, getDataRow(1).querySelector("[name=foo] input"));

        // Enter should add a new row in the first group
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 6);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (2) -4");

        // Enter should discard the edited row as it is pristine + get to next data row
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (1) -4");
        assert.strictEqual(document.activeElement, getDataRow(2).querySelector("[name=foo] input"));

        // Shift+Tab should focus back the last field of first row
        triggerHotkey("Shift+Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            getDataRow(1).querySelector("[name=int_field] input")
        );

        // Enter should add a new row in the first group
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 6);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (2) -4");

        // Edit the row and press enter: should add a new row
        input = getDataRow(2).querySelector("[name=foo] input");
        assert.strictEqual(document.activeElement, input);
        input.value = "zzapp";
        await triggerEvent(input, null, "input");
        triggerHotkey("Enter");
        await triggerEvent(input, null, "change");
        assert.containsN(target, ".o_data_row", 7);
        assert.equal(getGroup(1).innerText.replace(/[\s\n]+/g, " "), "No (3) -4");
        assert.strictEqual(document.activeElement, getDataRow(3).querySelector("[name=foo] input"));
    });

    QUnit.test("keyboard navigation with date range", async (assert) => {
        serverData.models.foo.fields.date_end = { string: "Date End", type: "date" };
        serverData.models.foo.records[0].date_end = "2017-01-26";

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
                    <field name="int_field"/>
                </tree>
            `,
        });

        await click(target, ".o_data_row:first-child [name=foo]");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child [name=foo] input")
        );

        triggerHotkey("Tab");
        await nextTick();

        const [startDateInput, endDateInput] = target.querySelectorAll(
            ".o_data_row:first-child [name=date] input"
        );

        assert.strictEqual(document.activeElement, startDateInput);

        triggerHotkey("Tab");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            startDateInput,
            "programmatic tab shouldn't toggle focus"
        );

        await click(endDateInput);

        assert.strictEqual(document.activeElement, endDateInput);

        triggerHotkey("Tab");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child [name=int_field] input")
        );
    });

    QUnit.test("keyboard navigation with Many2One field", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="m2o"/>
                    <field name="int_field"/>
                </tree>
            `,
        });

        await click(target, ".o_data_row:first-child [name=foo]");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child [name=foo] input")
        );

        triggerHotkey("Tab");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child [name=m2o] input")
        );

        triggerHotkey("Tab");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:first-child [name=int_field] input")
        );
    });

    QUnit.test("multi-edit records with ENTER does not crash", async (assert) => {
        serviceRegistry.add("error", errorService);

        const def = makeDeferred();
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>
            `,
            async mockRPC(route, args) {
                if (args.method === "write") {
                    await def;
                }
            },
        });

        await click(getDataRow(2).querySelector(".o_data_row .o_list_record_selector input"));
        await click(getDataRow(3).querySelector(".o_data_row .o_list_record_selector input"));
        await click(getDataRow(2).querySelector(".o_data_row .o_data_cell[name=int_field]"));

        assert.containsOnce(target, ".o_selected_row");
        const input = getDataRow(2).querySelector("[name=int_field] input");
        assert.strictEqual(document.activeElement, input);
        input.value = "234";
        await triggerEvent(input, null, "input");
        triggerHotkey("Enter");
        await triggerEvent(input, null, "change");

        assert.containsOnce(target, ".o_dialog"); // confirmation dialog
        await click(target.querySelector(".o_dialog .modal-footer .btn-primary"));
        await new Promise((r) => setTimeout(r, 20)); // delay a bit the save s.t. there's a rendering
        def.resolve();
        await nextTick();
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_number")),
            ["10", "234", "234", "-4"]
        );
        assert.containsNone(target, ".o_dialog"); // no more confirmation dialog, no error dialog
    });

    QUnit.test(
        "editable grouped list: adding a second record pass the first in readonly",
        async (assert) => {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["bar"],
                arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                </tree>
            `,
            });

            assert.containsNone(target, ".o_data_row");
            assert.containsN(target, ".o_group_header", 2);

            // Open first and second groups
            await click(getGroup(1));
            await click(getGroup(2));
            assert.containsN(target, ".o_data_row", 4);
            assert.equal(getGroup(1).innerText, "No (1)");
            assert.equal(getGroup(2).innerText, "Yes (3)");

            // add a row in first group
            await click(target.querySelectorAll(".o_group_field_row_add a")[0]);
            assert.containsOnce(target, ".o_selected_row");
            assert.containsN(target, ".o_data_row", 5);
            assert.equal(getGroup(1).innerText, "No (2)");
            assert.strictEqual(
                document.activeElement,
                getDataRow(2).querySelector("[name=foo] input")
            );

            // add a row in second group
            await click(target.querySelectorAll(".o_group_field_row_add a")[1]);
            assert.containsOnce(target, ".o_selected_row");
            assert.containsN(target, ".o_data_row", 5);
            assert.equal(getGroup(2).innerText, "Yes (4)");
            assert.equal(getGroup(1).innerText, "No (1)");
            assert.strictEqual(
                document.activeElement,
                getDataRow(5).querySelector("[name=foo] input")
            );
        }
    );

    QUnit.test("removing a groupby while adding a line from list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1" editable="bottom">
                    <field name="display_name"/>
                    <field name="foo"/>
                </tree>`,
            searchViewArch: `
                <search>
                    <field name="foo"/>
                    <group expand="1" string="Group By">
                        <filter name="groupby_foo" context="{'group_by': 'foo'}"/>
                    </group>
                </search>`,
        });

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Foo");

        // expand group
        await click(target.querySelector("th.o_group_name"));
        assert.containsNone(target, ".o_selected_row");
        await click(target.querySelector("td.o_group_field_row_add a"));
        assert.containsOnce(target, ".o_selected_row");
        await click(target, ".o_searchview_facet .o_facet_remove");
        assert.containsNone(target, ".o_selected_row");
    });

    QUnit.test("cell-level keyboard navigation in editable grouped list", async function (assert) {
        serverData.models.foo.records[0].bar = false;
        serverData.models.foo.records[1].bar = false;
        serverData.models.foo.records[2].bar = false;
        serverData.models.foo.records[3].bar = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo" required="1"/>
                </tree>`,
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_name"));
        const secondDataRow = target.querySelectorAll(".o_data_row")[1];
        await click(secondDataRow, "[name=foo]");
        assert.hasClass(secondDataRow, "o_selected_row");

        await editInput(secondDataRow, "[name=foo] input", "blipbloup");

        triggerHotkey("Escape");
        await nextTick();

        assert.containsNone(document.body, ".modal");

        assert.doesNotHaveClass(secondDataRow, "o_selected_row");

        assert.strictEqual(document.activeElement, secondDataRow.querySelector("[name=foo]"));

        assert.strictEqual(document.activeElement.textContent, "blip");

        triggerHotkey("ArrowLeft");

        assert.strictEqual(
            document.activeElement,
            secondDataRow.querySelector("input[type=checkbox]")
        );

        triggerHotkey("ArrowUp");
        triggerHotkey("ArrowRight");

        const firstDataRow = target.querySelector(".o_data_row");
        assert.strictEqual(document.activeElement, firstDataRow.querySelector("[name=foo]"));

        triggerHotkey("Enter");
        await nextTick();

        assert.hasClass(firstDataRow, "o_selected_row");
        await editInput(firstDataRow, "[name=foo] input", "Zipadeedoodah");

        triggerHotkey("Enter");
        await nextTick();

        assert.strictEqual(firstDataRow.querySelector("[name=foo]").innerText, "Zipadeedoodah");
        assert.doesNotHaveClass(firstDataRow, "o_selected_row");
        assert.hasClass(secondDataRow, "o_selected_row");
        assert.strictEqual(document.activeElement, secondDataRow.querySelector("[name=foo] input"));
        assert.strictEqual(document.activeElement.value, "blip");

        triggerHotkey("ArrowUp");
        triggerHotkey("ArrowRight");
        await nextTick();

        assert.strictEqual(document.activeElement, secondDataRow.querySelector("[name=foo] input"));
        assert.strictEqual(document.activeElement.value, "blip");

        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowLeft");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            secondDataRow.querySelector("td[name=foo] input")
        );
        assert.strictEqual(document.activeElement.value, "blip");

        triggerHotkey("Escape");
        await nextTick();

        assert.doesNotHaveClass(secondDataRow, "o_selected_row");

        assert.strictEqual(document.activeElement, secondDataRow.querySelector("td[name=foo]"));

        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_field_row_add a")
        );

        triggerHotkey("ArrowDown");

        const secondGroupHeader = target.querySelectorAll(".o_group_name")[1];
        assert.strictEqual(document.activeElement, secondGroupHeader);

        assert.containsN(target, ".o_data_row", 3);

        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, ".o_data_row", 4);

        assert.strictEqual(document.activeElement, secondGroupHeader);

        triggerHotkey("ArrowDown");

        const fourthDataRow = target.querySelectorAll(".o_data_row")[3];
        assert.strictEqual(document.activeElement, fourthDataRow.querySelector("[name=foo]"));

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelectorAll(".o_group_field_row_add a")[1]
        );

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelectorAll(".o_group_field_row_add a")[1]
        );

        // default Enter on a A tag
        const event = await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.ok(!event.defaultPrevented);
        await click(target.querySelectorAll(".o_group_field_row_add a")[1]);

        const fifthDataRow = target.querySelectorAll(".o_data_row")[4];
        assert.strictEqual(document.activeElement, fifthDataRow.querySelector("[name=foo] input"));

        await editInput(
            fifthDataRow.querySelector("[name=foo] input"),
            null,
            "cheateur arrete de cheater"
        );

        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, ".o_data_row", 6);

        triggerHotkey("Escape");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            target.querySelectorAll(".o_group_field_row_add a")[1]
        );

        // come back to the top
        for (let i = 0; i < 9; i++) {
            triggerHotkey("ArrowUp");
        }

        assert.strictEqual(document.activeElement, target.querySelector("thead th:nth-child(2)"));

        triggerHotkey("ArrowLeft");

        assert.strictEqual(
            document.activeElement,
            target.querySelector("thead th.o_list_record_selector input")
        );

        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowRight");

        assert.strictEqual(document.activeElement, firstDataRow.querySelector("td[name=foo]"));

        triggerHotkey("ArrowUp");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        assert.containsN(target, ".o_data_row", 5);

        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowRight");
        await nextTick();

        assert.containsN(target, ".o_data_row", 5);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowRight");
        await nextTick();

        assert.containsN(target, ".o_data_row", 5);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowLeft");
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowLeft");
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(2) .o_group_name")
        );

        triggerHotkey("ArrowDown");

        const firstVisibleDataRow = target.querySelector(".o_data_row");
        assert.strictEqual(document.activeElement, firstVisibleDataRow.querySelector("[name=foo]"));

        triggerHotkey("ArrowDown");

        const secondVisibleDataRow = target.querySelectorAll(".o_data_row")[1];
        assert.strictEqual(
            document.activeElement,
            secondVisibleDataRow.querySelector("[name=foo]")
        );

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_field_row_add a")
        );

        triggerHotkey("ArrowUp");

        assert.strictEqual(
            document.activeElement,
            secondVisibleDataRow.querySelector("[name=foo]")
        );

        triggerHotkey("ArrowUp");
        assert.strictEqual(document.activeElement, firstVisibleDataRow.querySelector("[name=foo]"));
    });

    QUnit.test("execute group header button with keyboard navigation", async function (assert) {
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <groupby name="m2o">
                        <button type="object" name="some_method" string="Do this"/>
                    </groupby>
                </tree>`,
            groupBy: ["m2o"],
        });

        patchWithCleanup(list.env.services.action, {
            doActionButton: ({ name }) => {
                assert.step(name);
            },
        });

        assert.containsNone(target, ".o_data_row");

        // focus create button as a starting point
        assert.containsN(
            target,
            ".o_list_button_add",
            2,
            "Should have 2 add button (small and xl screens)"
        );
        $(".o_list_button_add:visible").get(0).focus();
        assert.strictEqual(document.activeElement, $(".o_list_button_add:visible").get(0));

        triggerHotkey("ArrowDown");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            target.querySelector("thead th.o_list_record_selector input")
        );

        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        // unfold first group
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 3);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        // move to first record of opened group
        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tbody .o_data_row td[name=foo]")
        );

        // move back to the group header
        triggerHotkey("ArrowUp");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        // fold the group
        triggerHotkey("Enter");
        await nextTick();
        assert.containsNone(target, ".o_data_row");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        // unfold the group
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 3);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        // tab to the group header button
        triggerHotkey("Tab");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header .o_group_buttons button:first-child")
        );

        // click on the button by pressing enter
        assert.verifySteps([]);
        triggerHotkey("Enter");
        await nextTick();
        assert.containsN(target, ".o_data_row", 3);
        assert.verifySteps(["some_method"]);
    });

    QUnit.test('add a new row in grouped editable="top" list', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_header")); // open group "No"
        await click(target, ".o_group_field_row_add a"); // add a new row
        assert.hasClass(target.querySelectorAll(".o_data_row")[0], "o_selected_row");
        assert.strictEqual(
            target.querySelector(".o_selected_row [name=foo] input"),
            document.activeElement,
            "The first input of the line should have the focus"
        );
        assert.containsN(target, ".o_data_row", 2);

        await clickDiscard(target);
        await click(target.querySelectorAll(".o_group_header")[1]); // open second group "Yes"
        assert.containsN(target, ".o_data_row", 4);

        await click(target.querySelectorAll(".o_group_field_row_add a")[1]); // create row in second group "Yes"
        assert.strictEqual(
            target.querySelectorAll(".o_group_name")[1].innerText,
            "Yes (4)",
            "group should have correct name and count"
        );
        assert.containsN(target, ".o_data_row", 5);
        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");

        await editInput(target, '.o_selected_row [name="foo"] input', "pla");
        await clickSave(target);
        assert.containsN(target, ".o_data_row", 5);
    });

    QUnit.test('add a new row in grouped editable="bottom" list', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ["bar"],
        });
        await click(target.querySelector(".o_group_header")); // open group "No"
        await click(target, ".o_group_field_row_add a"); // add a new row
        assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");
        assert.containsN(target, ".o_data_row", 2);

        await clickDiscard(target);
        await click(target.querySelectorAll(".o_group_header")[1]); // open second group
        assert.containsN(target, ".o_data_row", 4);
        await click(target.querySelectorAll(".o_group_field_row_add a")[1]); // create row in second group "Yes"
        assert.hasClass(target.querySelectorAll(".o_data_row")[4], "o_selected_row");

        await editInput(target, '.o_selected_row [name="foo"] input', "pla");
        await clickSave(target);
        assert.containsN(target, ".o_data_row", 5);
    });

    QUnit.test(
        "add and discard a line through keyboard navigation without crashing",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
                groupBy: ["bar"],
            });

            // open the last group
            await click(target, ".o_group_header:last-child");
            assert.containsN(target, ".o_data_row", 3);

            // Can trigger ENTER on "Add a line" link ?
            assert.containsOnce(target, ".o_group_field_row_add a");
            target.querySelector(".o_group_field_row_add a").focus();
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_group_field_row_add a")
            );
            const event = await triggerEvent(document.activeElement, null, "keydown", {
                key: "Enter",
            });
            assert.ok(!event.defaultPrevented);
            // Simulate "enter" keydown
            await click(target, ".o_group_field_row_add a");

            assert.containsN(target, ".o_data_row", 4);
            await click($(".o_list_button_discard:visible").get(0));
            // At this point, a crash manager should appear if no proper link targetting
            assert.containsN(target, ".o_data_row", 3);
        }
    );

    QUnit.test("discard an invalid row in a list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
        });

        await click(target.querySelector(".o_data_cell"));
        assert.containsNone(target, ".o_field_invalid");
        assert.containsOnce(target, ".o_selected_row");

        await editInput(target, "[name='foo'] input", "");
        await click(target, ".o_list_view");
        assert.containsOnce(target, ".o_field_invalid");
        assert.containsOnce(target, ".o_selected_row");
        assert.strictEqual(target.querySelector("[name='foo'] input").value, "");

        await clickDiscard(target);
        assert.containsNone(target, ".o_field_invalid");
        assert.containsNone(target, ".o_selected_row");
        assert.strictEqual(target.querySelector("[name='foo']").textContent, "yop");
    });

    QUnit.test('editable grouped list with create="0"', async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top" create="0"><field name="foo" required="1"/></tree>',
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_header")); // open group
        assert.containsNone(
            target,
            ".o_group_field_row_add a",
            "Add a line should not be available in readonly"
        );
    });

    QUnit.test("add a new row in (selection) grouped editable list", async function (assert) {
        serverData.models.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [
                [1, "Low"],
                [2, "Medium"],
                [3, "High"],
            ],
            default: 1,
        };
        serverData.models.foo.records.push({
            id: 5,
            foo: "blip",
            int_field: -7,
            m2o: 1,
            priority: 2,
        });
        serverData.models.foo.records.push({
            id: 6,
            foo: "blip",
            int_field: 5,
            m2o: 1,
            priority: 3,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="priority"/>
                    <field name="m2o"/>
                </tree>`,
            groupBy: ["priority"],
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step(args.kwargs.context.default_priority.toString());
                }
            },
        });
        await click(target.querySelector(".o_group_header")); // open group
        await click(target.querySelector(".o_group_field_row_add a")); // add a new row
        await editInput(target, '[name="foo"] input', "xyz"); // make record dirty
        await click(target, ".o_list_view"); // unselect row
        assert.verifySteps(["1"]);
        assert.strictEqual(
            target.querySelectorAll(".o_data_row .o_data_cell")[1].textContent,
            "Low",
            "should have a column name with a value from the groupby"
        );

        await click(target.querySelectorAll(".o_group_header")[1]); // open second group
        await click(target.querySelectorAll(".o_group_field_row_add a")[1]); // create row in second group
        await click(target, ".o_list_view"); // unselect row
        assert.strictEqual(
            target.querySelectorAll(".o_data_row")[5].querySelectorAll(".o_data_cell")[1]
                .textContent,
            "Medium",
            "should have a column name with a value from the groupby"
        );
        assert.verifySteps(["2"]);
    });

    QUnit.test("add a new row in (m2o) grouped editable list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="m2o"/>
                </tree>`,
            groupBy: ["m2o"],
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step(args.kwargs.context.default_m2o.toString());
                }
            },
        });
        await click(target.querySelector(".o_group_header")); // open group
        await click(target.querySelector(".o_group_field_row_add a")); // add a new row
        await click(target, ".o_list_view"); // unselect row
        assert.strictEqual(
            target.querySelector(".o_data_row").querySelectorAll(".o_data_cell")[1].textContent,
            "Value 1",
            "should have a column name with a value from the groupby"
        );
        assert.verifySteps(["1"]);

        await click(target.querySelectorAll(".o_group_header")[1]); // open second group
        await click(target.querySelectorAll(".o_group_field_row_add a")[1]); // create row in second group
        await click(target, ".o_list_view"); // unselect row
        assert.strictEqual(
            target.querySelectorAll(".o_data_row")[3].querySelectorAll(".o_data_cell")[1]
                .textContent,
            "Value 2",
            "should have a column name with a value from the groupby"
        );
        assert.verifySteps(["2"]);
    });

    QUnit.test("list view with optional fields rendering", async function (assert) {
        patchWithCleanup(localization, {
            direction: "ltr",
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="m2o" optional="hide"/>
                    <field name="amount"/>
                    <field name="reference" optional="hide"/>
                </tree>`,
        });

        assert.containsN(
            target,
            "th",
            4,
            "should have 4 th, 1 for selector, 2 for columns and 1 for optional columns"
        );

        assert.containsN(
            target,
            "tfoot td",
            4,
            "should have 4 td, 1 for selector, 2 for columns and 1 for optional columns"
        );

        assert.containsOnce(
            target,
            "table .o_optional_columns_dropdown",
            "should have the optional columns dropdown toggle inside the table"
        );

        assert.containsOnce(
            target,
            "table > thead > tr > th:last-child .o_optional_columns_dropdown",
            "The optional fields toggler is in the last header column"
        );

        // optional fields
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        assert.containsN(
            target,
            "div.o_optional_columns_dropdown span.dropdown-item",
            2,
            "dropdown have 2 optional field foo with checked and bar with unchecked"
        );

        // enable optional field
        await click(target, "div.o_optional_columns_dropdown span.dropdown-item:first-child");
        // 5 th (1 for checkbox, 3 for columns, 1 for optional columns)
        assert.containsN(target, "th", 5, "should have 5 th");
        assert.containsN(target, "tfoot td", 5, "should have 5 td");
        assert.ok(
            $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field

        assert.strictEqual(
            target.querySelectorAll(
                "div.o_optional_columns_dropdown span.dropdown-item:first-child input:checked"
            )[0],
            [...target.querySelectorAll("div.o_optional_columns_dropdown span.dropdown-item")]
                .filter((el) => el.innerText === "M2O field")[0]
                .querySelector("input"),
            "m2o advanced field check box should be checked in dropdown"
        );

        await click(target, "div.o_optional_columns_dropdown span.dropdown-item:first-child");
        // 4 th (1 for checkbox, 2 for columns, 1 for optional columns)
        assert.containsN(target, "th", 4, "should have 4 th");
        assert.containsN(target, "tfoot td", 4, "should have 4 td");
        assert.notOk(
            $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
            "should not have a visible m2o field"
        ); //m2o field not displayed

        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        assert.notOk(
            $(target)
                .find('div.o_optional_columns_dropdown span.dropdown-item [name="m2o"]')
                .is(":checked")
        );
    });

    QUnit.test("list view with optional fields rendering in RTL mode", async function (assert) {
        patchWithCleanup(localization, {
            direction: "rtl",
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="m2o" optional="hide"/>
                    <field name="amount"/>
                    <field name="reference" optional="hide"/>
                </tree>`,
        });

        assert.containsOnce(
            target.querySelector("table"),
            ".o_optional_columns_dropdown",
            "should have the optional columns dropdown toggle inside the table"
        );

        assert.containsOnce(
            target,
            "table > thead > tr > th:last-child .o_optional_columns_dropdown",
            "The optional fields toggler is in the last header column"
        );
    });

    QUnit.test(
        "optional fields do not disappear even after listview reload",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="m2o" optional="hide"/>
                        <field name="amount"/>
                        <field name="reference" optional="hide"/>
                    </tree>`,
            });

            assert.containsN(
                target,
                "th",
                4,
                "should have 3 th, 1 for selector, 2 for columns, 1 for optional columns"
            );

            // enable optional field
            await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
            assert.notOk(
                target.querySelector(
                    "div.o_optional_columns_dropdown span.dropdown-item:first-child input"
                ).checked
            );
            await click(target, "div.o_optional_columns_dropdown span.dropdown-item:first-child");
            assert.containsN(
                target,
                "th",
                5,
                "should have 5 th 1 for selector, 3 for columns, 1 for optional columns"
            );
            assert.ok(
                $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
                "should have a visible m2o field"
            ); //m2o field

            var firstRowSelector = target.querySelector("tbody .o_list_record_selector input");
            await click(firstRowSelector);
            await reloadListView(target);
            assert.containsN(
                target,
                "th",
                5,
                "should have 5 th 1 for selector, 3 for columns, 1 for optional columns ever after listview reload"
            );
            assert.ok(
                $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
                "should have a visible m2o field even after listview reload"
            );

            await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
            assert.ok(
                target.querySelector(
                    "div.o_optional_columns_dropdown span.dropdown-item:first-child input"
                ).checked
            );
        }
    );

    QUnit.test("optional fields is shown only if enabled", async function (assert) {
        serverData.actions = {
            1: {
                id: 1,
                name: "Currency Action 1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[1, "list"]],
            },
        };

        serverData.views = {
            "foo,1,list": `
                    <tree>
                        <field name="currency_id" optional="show"/>
                        <field name="company_currency_id" optional="show"/>
                    </tree>`,
            "foo,false,search": "<search/>",
        };

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        assert.containsN(
            target,
            "th",
            4,
            "should have 4 th, 1 for selector, 2 for columns, 1 for optional columns"
        );

        // disable optional field
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        await click(target, "div.o_optional_columns_dropdown span.dropdown-item:first-child");
        assert.containsN(
            target,
            "th",
            3,
            "should have 3 th, 1 for selector, 1 for columns, 1 for optional columns"
        );

        await doAction(webClient, 1);
        assert.containsN(
            target,
            "th",
            3,
            "should have 3 th, 1 for selector, 1 for columns, 1 for optional columns ever after listview reload"
        );
    });

    QUnit.test("selection is kept when optional fields are toggled", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="m2o" optional="hide"/>
                </tree>`,
        });

        assert.containsN(target, "th", 3);

        // select a record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(target, ".o_list_record_selector input:checked");

        // add an optional field
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");
        assert.containsN(target, "th", 4);
        assert.containsOnce(target, ".o_list_record_selector input:checked");

        // select all records
        await click(target, "thead .o_list_record_selector input");
        assert.containsN(target, ".o_list_record_selector input:checked", 5);

        // remove an optional field
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");
        assert.containsN(target, "th", 3);
        assert.containsN(target, ".o_list_record_selector input:checked", 5);
    });

    QUnit.test("list view with optional fields and async rendering", async function (assert) {
        assert.expect(14);

        const def = makeDeferred();
        const fieldRegistry = registry.category("fields");
        const charField = fieldRegistry.get("char");

        class AsyncCharField extends charField.component {
            setup() {
                super.setup();
                onWillStart(async () => {
                    assert.ok(true, "the rendering must be async");
                    await def;
                });
            }
        }
        fieldRegistry.add("asyncwidget", { component: AsyncCharField });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="m2o"/>
                    <field name="foo" widget="asyncwidget" optional="hide"/>
                </tree>`,
        });

        assert.containsN(target, "th", 3);
        assert.containsNone(target, ".o_optional_columns_dropdown.show");

        // add an optional field (we click on the label on purpose, as it will trigger
        // a second event on the input)
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        assert.containsOnce(target, ".o_optional_columns_dropdown.show");
        assert.containsNone(target, ".o_optional_columns_dropdown input:checked");

        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");
        assert.containsN(target, "th", 3);
        assert.containsOnce(target, ".o_optional_columns_dropdown.show");
        assert.containsOnce(target, ".o_optional_columns_dropdown input:checked");

        def.resolve();
        await nextTick();
        assert.containsN(target, "th", 4);
        assert.containsOnce(target, ".o_optional_columns_dropdown.show");
        assert.containsOnce(target, ".o_optional_columns_dropdown input:checked");
    });

    QUnit.test("change the viewType of the current action", async function (assert) {
        serverData.actions = {
            1: {
                id: 1,
                name: "Partners Action 1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[1, "kanban"]],
            },
            2: {
                id: 2,
                name: "Partners",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [1, "kanban"],
                ],
            },
        };

        serverData.views = {
            "foo,1,kanban":
                '<kanban><templates><t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
                "</t></templates></kanban>",

            "foo,false,list":
                '<tree limit="3">' +
                '<field name="foo"/>' +
                '<field name="m2o" optional="hide"/>' +
                '<field name="o2m" optional="show"/></tree>',

            "foo,false,search": '<search><field name="foo" string="Foo"/></search>',
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 2);

        assert.containsOnce(target, ".o_list_view", "should have rendered a list view");

        assert.containsN(
            target,
            "th",
            4,
            "should display 4 th (selector + 2 fields + optional columns)"
        );

        // enable optional field
        await click(target, "table .o_optional_columns_dropdown_toggle");

        assert.notOk(
            $(target)
                .find('div.o_optional_columns_dropdown span.dropdown-item [name="m2o"]')
                .is(":checked")
        );
        assert.ok(
            $(target)
                .find('div.o_optional_columns_dropdown span.dropdown-item [name="o2m"]')
                .is(":checked")
        );

        await click(target.querySelector("div.o_optional_columns_dropdown span.dropdown-item"));
        assert.containsN(
            target,
            "th",
            5,
            "should display 5 th (selector + 3 fields + optional columns)"
        );
        assert.ok(
            $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field

        // switch to kanban view
        await loadState(webClient, {
            action: 2,
            view_type: "kanban",
        });

        assert.containsNone(target, ".o_list_view", "should not display the list view anymore");
        assert.containsOnce(target, ".o_kanban_view", "should have switched to the kanban view");

        // switch back to list view
        await loadState(webClient, {
            action: 2,
            view_type: "list",
        });

        assert.containsNone(target, ".o_kanban_view", "should not display the kanban view anymoe");
        assert.containsOnce(target, ".o_list_view", "should display the list view");

        assert.containsN(target, "th", 5, "should display 5 th");
        assert.ok(
            $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field
        assert.ok(
            $(target).find("th:not(.o_list_actions_header):contains(O2M field)").is(":visible"),
            "should have a visible o2m field"
        ); //o2m field

        // disable optional field
        await click(target, "table .o_optional_columns_dropdown_toggle");
        assert.ok(
            $(target)
                .find('div.o_optional_columns_dropdown span.dropdown-item [name="m2o"]')
                .is(":checked")
        );
        assert.ok(
            $(target)
                .find('div.o_optional_columns_dropdown span.dropdown-item [name="o2m"]')
                .is(":checked")
        );
        await click(
            target.querySelectorAll("div.o_optional_columns_dropdown span.dropdown-item input")[1]
        );
        assert.ok(
            $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field
        assert.notOk(
            $(target).find("th:not(.o_list_actions_header):contains(O2M field)").is(":visible"),
            "shouldn't have a visible o2m field"
        ); //o2m field
        assert.containsN(target, "th", 4, "should display 4 th");

        await doAction(webClient, 1);

        assert.containsNone(target, ".o_list_view", "should not display the list view anymore");
        assert.containsOnce(target, ".o_kanban_view", "should have switched to the kanban view");

        await doAction(webClient, 2);

        assert.containsNone(target, ".o_kanban_view", "should not havethe kanban view anymoe");
        assert.containsOnce(target, ".o_list_view", "should display the list view");

        assert.containsN(target, "th", 4, "should display 4 th");
        assert.ok(
            $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field
        assert.notOk(
            $(target).find("th:not(.o_list_actions_header):contains(O2M field)").is(":visible"),
            "shouldn't have a visible o2m field"
        ); //o2m field
    });

    QUnit.test(
        "list view with optional fields rendering and local storage mock",
        async function (assert) {
            let forceLocalStorage = true;

            patchWithCleanup(browser.localStorage, {
                getItem(key) {
                    assert.step("getItem " + key);
                    return forceLocalStorage ? "m2o" : super.getItem(arguments);
                },
                setItem(key, value) {
                    assert.step("setItem " + key + " to " + JSON.stringify(String(value)));
                    return super.setItem(arguments);
                },
            });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="m2o" optional="hide"/>
                        <field name="reference" optional="show"/>
                    </tree>`,
                viewId: 42,
            });

            const localStorageKey = "optional_fields,foo,list,42,foo,m2o,reference";

            assert.verifySteps(["getItem " + localStorageKey]);

            assert.containsN(
                target,
                "th",
                4,
                "should have 4 th, 1 for selector, 2 for columns, 1 for optional columns"
            );

            assert.ok(
                $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
                "should have a visible m2o field"
            ); //m2o field

            assert.notOk(
                $(target)
                    .find("th:not(.o_list_actions_header):contains(Reference Field)")
                    .is(":visible"),
                "should not have a visible reference field"
            );

            // optional fields
            await click(target.querySelector("table .o_optional_columns_dropdown button"));
            assert.containsN(
                target,
                "div.o_optional_columns_dropdown span.dropdown-item",
                2,
                "dropdown have 2 optional fields"
            );

            forceLocalStorage = false;
            // enable optional field
            await click(
                $(target).find("div.o_optional_columns_dropdown span.dropdown-item:eq(1) input")[0]
            );

            // Only a setItem since the list view maintains its own internal state of toggled
            // optional columns.
            assert.verifySteps(["setItem " + localStorageKey + ' to "m2o,reference"']);

            // 5 th (1 for checkbox, 3 for columns, 1 for optional columns)
            assert.containsN(target, "th", 5, "should have 5 th");

            assert.ok(
                $(target).find("th:not(.o_list_actions_header):contains(M2O field)").is(":visible"),
                "should have a visible m2o field"
            ); //m2o field

            assert.ok(
                $(target)
                    .find("th:not(.o_list_actions_header):contains(Reference Field)")
                    .is(":visible"),
                "should have a visible reference field"
            );
        }
    );

    QUnit.test("quickcreate in a many2one in a list", async function (assert) {
        await makeView({
            type: "list",
            arch: '<tree editable="top"><field name="m2o"/></tree>',
            serverData,
            resModel: "foo",
        });
        await click(target.querySelector(".o_data_row .o_data_cell"));

        const input = target.querySelector(".o_data_row .o_data_cell input");
        await editInput(input, null, "aaa");
        await triggerEvents(input, null, ["keyup", "blur"]);
        document.body.click();
        await nextTick();
        assert.containsOnce(target, ".modal", "the quick_create modal should appear");

        await click(target.querySelector(".modal .btn-primary"));
        await click(target.querySelector(".o_list_view"));
        assert.strictEqual(
            target.getElementsByClassName("o_data_cell")[0].innerHTML,
            "aaa",
            "value should have been updated"
        );
    });

    QUnit.test("float field render with digits attribute on listview", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="qux" digits="[12,6]"/></tree>',
        });

        assert.strictEqual(
            target.querySelector("td.o_list_number").textContent,
            "0.400000",
            "should contain 6 digits decimal precision"
        );
    });

    QUnit.test("list: column: resize, reorder, resize again", async function (assert) {
        serverData.models.foo.fields.foo.sortable = true;
        serverData.models.foo.fields.int_field.sortable = true;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
        });

        // pointer doesn't perfectly match the resized th.
        const PIXEL_TOLERANCE = 3;
        const assertAlmostEqual = (v1, v2) => Math.abs(v1 - v2) <= PIXEL_TOLERANCE;

        // 1. Resize column foo to middle of column int_field.
        const originalWidths = [...target.querySelectorAll(".o_list_table th")].map(
            (th) => th.offsetWidth
        );
        const th2 = target.querySelector("th:nth-child(2)");
        const th3 = target.querySelector("th:nth-child(3)");
        const resizeHandle = th2.querySelector(".o_resize");

        await dragAndDrop(resizeHandle, th3);

        const widthsAfterResize = [...target.querySelectorAll(".o_list_table th")].map(
            (th) => th.offsetWidth
        );

        assert.strictEqual(widthsAfterResize[0], originalWidths[0]);
        assertAlmostEqual(widthsAfterResize[1], originalWidths[1] + originalWidths[2] / 2);

        // 2. Reorder column foo.
        await click(th2);
        const widthsAfterReorder = [...target.querySelectorAll(".o_list_table th")].map(
            (th) => th.offsetWidth
        );

        assert.strictEqual(widthsAfterResize[0], widthsAfterReorder[0]);
        assert.strictEqual(widthsAfterResize[1], widthsAfterReorder[1]);

        // 3. Resize again, this time check sizes while dragging and after drop.
        const { drop } = await drag(resizeHandle, th3);
        assertAlmostEqual(th2.offsetWidth, widthsAfterReorder[1] + widthsAfterReorder[2] / 2);

        await drop();
        assertAlmostEqual(th2.offsetWidth, widthsAfterReorder[1] + widthsAfterReorder[2] / 2);
    });

    QUnit.test("list: resize column and toggle one checkbox", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
        });

        // 1. Resize column foo to middle of column int_field.
        const th2 = target.querySelector("th:nth-child(2)");
        const th3 = target.querySelector("th:nth-child(3)");
        const resizeHandle = th2.querySelector(".o_resize");

        await dragAndDrop(resizeHandle, th3);

        const widthsAfterResize = [...target.querySelectorAll(".o_list_table th")].map(
            (th) => th.offsetWidth
        );

        // 2. Column size should be the same after selecting a row
        await click(target.querySelector("tbody .o_list_record_selector"));
        const widthsAfterSelectRow = [...target.querySelectorAll(".o_list_table th")].map(
            (th) => th.offsetWidth
        );
        assert.strictEqual(
            widthsAfterResize[0],
            widthsAfterSelectRow[0],
            "Width must not have been changed after selecting a row"
        );
        assert.strictEqual(
            widthsAfterResize[1],
            widthsAfterSelectRow[1],
            "Width must not have been changed after selecting a row"
        );
    });

    QUnit.test("list: resize column and toggle check all", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
        });

        // 1. Resize column foo to middle of column int_field.
        const th2 = target.querySelector("th:nth-child(2)");
        const th3 = target.querySelector("th:nth-child(3)");
        const resizeHandle = th2.querySelector(".o_resize");

        await dragAndDrop(resizeHandle, th3);

        const widthsAfterResize = [...target.querySelectorAll(".o_list_table th")].map(
            (th) => th.offsetWidth
        );

        // 2. Column size should be the same after selecting all
        await click(target.querySelector("thead .o_list_record_selector"));
        const widthsAfterSelectAll = [...target.querySelectorAll(".o_list_table th")].map(
            (th) => th.offsetWidth
        );
        assert.strictEqual(
            widthsAfterResize[0],
            widthsAfterSelectAll[0],
            "Width must not have been changed after selecting all"
        );
        assert.strictEqual(
            widthsAfterResize[1],
            widthsAfterSelectAll[1],
            "Width must not have been changed after selecting all"
        );
    });

    QUnit.test("editable list: resize column headers", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="reference" optional="hide"/>
                </tree>`,
        });

        const originalWidths = [...target.querySelectorAll(".o_list_table th")].map((th) =>
            Math.floor(th.offsetWidth)
        );
        const th = target.querySelector("th:nth-child(2)");
        const resizeHandle = th.querySelector(".o_resize");
        const expectedWidth = Math.floor(originalWidths[1] / 2 + resizeHandle.offsetWidth / 2);
        await dragAndDrop(resizeHandle, th);

        const finalWidths = [...target.querySelectorAll(".o_list_table th")].map((th) =>
            Math.floor(th.offsetWidth)
        );
        assert.strictEqual(finalWidths[0], originalWidths[0]);
        assert.ok(Math.abs(finalWidths[1] - expectedWidth) <= 1); // rounding
        assert.strictEqual(finalWidths[2], originalWidths[2]);
    });

    QUnit.test("editable list: resize column headers", async function (assert) {
        // This test will ensure that, on resize list header,
        // the resized element have the correct size and other elements are not resized
        serverData.models.foo.records[0].foo = "a".repeat(200);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="reference" optional="hide"/>
                </tree>`,
        });

        // Target handle
        const th = target.querySelector("th:nth-child(2)");
        const thNext = target.querySelector("th:nth-child(3)");
        const resizeHandle = th.querySelector(".o_resize");
        const nextResizeHandle = thNext.querySelector(".o_resize");
        const thOriginalWidth = th.getBoundingClientRect().width;
        const thNextOriginalWidth = thNext.getBoundingClientRect().width;
        const thExpectedWidth = thOriginalWidth + thNextOriginalWidth;

        await dragAndDrop(resizeHandle, nextResizeHandle);

        const thFinalWidth = th.getBoundingClientRect().width;
        const thNextFinalWidth = thNext.getBoundingClientRect().width;

        assert.ok(
            Math.abs(Math.floor(thFinalWidth) - Math.floor(thExpectedWidth)) <= 1,
            `Wrong width on resize (final: ${thFinalWidth}, expected: ${thExpectedWidth})`
        );
        assert.strictEqual(
            Math.floor(thNextOriginalWidth),
            Math.floor(thNextFinalWidth),
            "Width must not have been changed"
        );
    });

    QUnit.test("resize column with several x2many lists in form group", async function (assert) {
        /** @param {number} index */
        const getTableWidth = (index) =>
            Math.floor(target.querySelectorAll(".o_field_x2many_list table")[index].offsetWidth);

        serverData.models.bar.fields.text = { string: "Text field", type: "char" };
        serverData.models.foo.records[0].o2m = [1, 2];

        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="o2m">
                            <tree editable="bottom">
                                <field name="display_name"/>
                                <field name="text"/>
                            </tree>
                        </field>
                        <field name="m2m">
                            <tree editable="bottom">
                                <field name="display_name"/>
                                <field name="text"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        const th = target.querySelector("th");
        const resizeHandle = th.querySelector(".o_resize");
        const initialWidths = [getTableWidth(0), getTableWidth(1)];

        assert.strictEqual(
            initialWidths[0],
            initialWidths[1],
            "both table columns have same width"
        );

        await dragAndDrop(resizeHandle, target.getElementsByTagName("th")[1], "right");

        assert.notEqual(
            initialWidths[0],
            getTableWidth(0),
            "first o2m table is resized and width of table has changed"
        );
        assert.strictEqual(
            initialWidths[1],
            getTableWidth(1),
            "second o2m table should not be impacted on first o2m in group resized"
        );
    });

    QUnit.test(
        "resize column with x2many list with several fields in form notebook",
        async function (assert) {
            serverData.models.foo.records[0].o2m = [1, 2];

            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <notebook>
                                <page string="Page 1">
                                    <field name="o2m">
                                        <tree editable="bottom">
                                            <field name="display_name"/>
                                            <field name="display_name"/>
                                            <field name="display_name"/>
                                            <field name="display_name"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            const th = target.querySelector("th");
            const resizeHandle = th.querySelector(".o_resize");
            const listInitialWidth = target.querySelector(".o_list_renderer").offsetWidth;

            await dragAndDrop(resizeHandle, target.getElementsByTagName("th")[1], {
                position: "right",
            });

            assert.strictEqual(
                target.querySelector(".o_list_renderer").offsetWidth,
                listInitialWidth,
                "resizing the column should not impact the width of list"
            );
        }
    );

    QUnit.test("enter edition in editable list with multi_edit = 0", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top" multi_edit="0">
                    <field name="int_field"/>
                </tree>`,
        });

        // click on int_field cell of first row
        await click(target.querySelector(".o_data_row .o_data_cell"));
        const intFieldInput = target.querySelector(
            ".o_selected_row .o_field_widget[name=int_field] input"
        );
        assert.strictEqual(document.activeElement, intFieldInput);
    });

    QUnit.test("enter edition in editable list with multi_edit = 1", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top" multi_edit="1">
                    <field name="int_field"/>
                </tree>`,
        });

        // click on int_field cell of first row
        await click(target.querySelector(".o_data_row .o_data_cell"));
        const intFieldInput = target.querySelector(
            ".o_selected_row .o_field_widget[name=int_field] input"
        );
        assert.strictEqual(document.activeElement, intFieldInput);
    });

    QUnit.test(
        "continue creating new lines in editable=top on keyboard nav",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree editable="top">
                    <field name="int_field"/>
                </tree>`,
            });

            const initialRowCount = $(".o_data_cell[name=int_field]").length;

            // click on int_field cell of first row
            await click($(".o_list_button_add:visible").get(0));

            await editInput(target, ".o_data_cell[name=int_field] input", "1");
            triggerHotkey("Tab");
            await nextTick();

            await editInput(target, ".o_data_cell[name=int_field] input", "2");
            triggerHotkey("Enter");
            await nextTick();

            // 3 new rows: the two created ("1" and "2", and a new still in edit mode)
            assert.strictEqual($(".o_data_cell[name=int_field]").length, initialRowCount + 3);
        }
    );

    QUnit.test("Date in evaluation context works with date field", async function (assert) {
        patchDate(1997, 0, 9, 12, 0, 0);

        serverData.models.foo.fields.birthday = { string: "Birthday", type: "date" };
        serverData.models.foo.records[0].birthday = "1997-01-08";
        serverData.models.foo.records[1].birthday = "1997-01-09";
        serverData.models.foo.records[2].birthday = "1997-01-10";

        await makeView({
            type: "list",
            arch: `
                <tree>
                    <field name="birthday" decoration-danger="birthday > today"/>
                </tree>`,
            serverData,
            resModel: "foo",
        });

        assert.containsOnce(target, ".o_data_row .text-danger");
    });

    QUnit.test("Datetime in evaluation context works with datetime field", async function (assert) {
        patchDate(1997, 0, 9, 12, 0, 0);

        /**
         * Returns "1997-01-DD HH:MM:00" with D, H and M holding current UTC values
         * from patched date + (deltaMinutes) minutes.
         * This is done to allow testing from any timezone since UTC values are
         * calculated with the offset of the current browser.
         */
        function dateStringDelta(deltaMinutes) {
            const d = new Date(Date.now() + 1000 * 60 * deltaMinutes);
            return `1997-01-${String(d.getUTCDate()).padStart(
                2,
                "0"
            )} ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}:00`;
        }

        // "datetime" field may collide with "datetime" object in context
        serverData.models.foo.fields.birthday = { string: "Birthday", type: "datetime" };
        serverData.models.foo.records[0].birthday = dateStringDelta(-30);
        serverData.models.foo.records[1].birthday = dateStringDelta(0);
        serverData.models.foo.records[2].birthday = dateStringDelta(+30);

        await makeView({
            type: "list",
            arch: `
                <tree>
                    <field name="birthday" decoration-danger="birthday > now"/>
                </tree>`,
            serverData,
            resModel: "foo",
        });

        assert.containsOnce(target, ".o_data_row .text-danger");
    });

    QUnit.test("Auto save: add a record and leave action", async function (assert) {
        serverData.actions = {
            1: {
                id: 1,
                name: "Action 1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[2, "list"]],
                search_view_id: [1, "search"],
            },
            2: {
                id: 2,
                name: "Action 2",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[3, "list"]],
                search_view_id: [1, "search"],
            },
        };
        serverData.views = {
            "foo,1,search": "<search></search>",
            "foo,2,list": '<tree editable="top"><field name="foo"/></tree>',
            "foo,3,list": '<tree editable="top"><field name="foo"/></tree>',
        };
        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip"]
        );
        assert.containsN(target, ".o_data_row", 4);

        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, '.o_data_cell [name="foo"] input', "test");

        // change action and come back
        await doAction(webClient, 2);
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip", "test"]
        );
        assert.containsN(target, ".o_data_row", 5);
    });

    QUnit.test(
        "Auto save: create a new record without modifying it and leave action",
        async function (assert) {
            serverData.models.foo.fields.foo.required = true;
            serverData.actions = {
                1: {
                    id: 1,
                    name: "Action 1",
                    res_model: "foo",
                    type: "ir.actions.act_window",
                    views: [[2, "list"]],
                    search_view_id: [1, "search"],
                },
                2: {
                    id: 2,
                    name: "Action 2",
                    res_model: "foo",
                    type: "ir.actions.act_window",
                    views: [[3, "list"]],
                    search_view_id: [1, "search"],
                },
            };
            serverData.views = {
                "foo,1,search": "<search></search>",
                "foo,2,list": '<tree editable="top"><field name="foo"/></tree>',
                "foo,3,list": '<tree editable="top"><field name="foo"/></tree>',
            };
            const webClient = await createWebClient({ serverData });

            await doAction(webClient, 1);
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
                ["yop", "blip", "gnap", "blip"]
            );
            assert.containsN(target, ".o_data_row", 4);

            await click($(".o_list_button_add:visible").get(0));
            assert.containsN(target, ".o_data_row", 5);

            // change action and come back
            await doAction(webClient, 2);
            await doAction(webClient, 1, { clearBreadcrumbs: true });
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
                ["yop", "blip", "gnap", "blip"]
            );
            assert.containsN(target, ".o_data_row", 4);
        }
    );

    QUnit.test("Auto save: modify a record and leave action", async function (assert) {
        serverData.actions = {
            1: {
                id: 1,
                name: "Action 1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[2, "list"]],
                search_view_id: [1, "search"],
            },
            2: {
                id: 2,
                name: "Action 2",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[3, "list"]],
                search_view_id: [1, "search"],
            },
        };
        serverData.views = {
            "foo,1,search": "<search></search>",
            "foo,2,list": '<tree editable="top"><field name="foo"/></tree>',
            "foo,3,list": '<tree editable="top"><field name="foo"/></tree>',
        };
        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip"]
        );

        await click(target.querySelector(".o_data_cell"));
        await editInput(target, '.o_data_cell [name="foo"] input', "test");

        // change action and come back
        await doAction(webClient, 2);
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["test", "blip", "gnap", "blip"]
        );
    });

    QUnit.test("Auto save: modify a record and leave action (reject)", async function (assert) {
        serverData.actions = {
            1: {
                id: 1,
                name: "Action 1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[2, "list"]],
                search_view_id: [1, "search"],
            },
            2: {
                id: 2,
                name: "Action 2",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[3, "list"]],
                search_view_id: [1, "search"],
            },
        };
        serverData.views = {
            "foo,1,search": "<search></search>",
            "foo,2,list": '<tree editable="top"><field name="foo" required="1"/></tree>',
            "foo,3,list": '<tree editable="top"><field name="foo"/></tree>',
        };
        const webClient = await createWebClient({ serverData });

        patchWithCleanup(webClient.env.services.notification, {
            add: (message, options) => {
                assert.step(options.title.toString());
                assert.step(message.toString());
            },
        });

        await doAction(webClient, 1);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip"]
        );

        await click(target.querySelector(".o_data_cell"));
        await editInput(target, '.o_data_cell [name="foo"] input', "");
        doAction(webClient, 2);
        await nextTick();
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["", "blip", "gnap", "blip"]
        );
        assert.hasClass(target.querySelector('.o_data_cell [name="foo"]'), "o_field_invalid");
        assert.containsN(target, ".o_data_row", 4);

        assert.verifySteps(["Invalid fields: ", "<ul><li>Foo</li></ul>"]);
    });

    QUnit.test("Auto save: add a record and change page", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top" limit="3">
                    <field name="foo"/>
                </tree>`,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap"]
        );

        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, '.o_data_cell [name="foo"] input', "test");
        await pagerNext(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["blip", "test"]
        );

        await pagerPrevious(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap"]
        );
    });

    QUnit.test("Auto save: modify a record and change page", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top" limit="3">
                    <field name="foo"/>
                </tree>`,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap"]
        );

        await click(target.querySelector(".o_data_cell"));
        await editInput(target, ".o_data_cell input", "test");
        await pagerNext(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["blip"]
        );

        await pagerPrevious(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["test", "blip", "gnap"]
        );
    });

    QUnit.test("Auto save: modify a record and change page (reject)", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top" limit="3">
                    <field name="foo" required="1"/>
                </tree>`,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["yop", "blip", "gnap"]
        );

        await click(target.querySelector(".o_data_cell"));
        await editInput(target, ".o_data_cell input", "");
        await pagerNext(target);
        assert.hasClass(target.querySelector('.o_data_cell [name="foo"]'), "o_field_invalid");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["", "blip", "gnap"]
        );
    });

    QUnit.test("Auto save: save on closing tab/browser", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                </tree>`,
            mockRPC(route, { args, method, model }) {
                if (model === "foo" && method === "web_save") {
                    assert.step("save"); // should be called
                    assert.deepEqual(args, [[1], { foo: "test" }]);
                }
            },
        });
        await click(target.querySelector(".o_data_cell"));
        await editInput(target, '.o_data_cell [name="foo"] input', "test");

        const evnt = new Event("beforeunload");
        evnt.preventDefault = () => assert.step("prevented");
        window.dispatchEvent(evnt);
        await nextTick();
        assert.verifySteps(["save"]);
    });

    QUnit.test("Auto save: save on closing tab/browser (pending changes)", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                </tree>`,
            mockRPC(route, { args, method, model }) {
                if (model === "foo" && method === "web_save") {
                    assert.deepEqual(args, [[1], { foo: "test" }]);
                }
            },
        });
        await click(target.querySelector(".o_data_cell"));
        const input = target.querySelector('.o_data_cell [name="foo"] input');
        input.value = "test";
        await triggerEvent(input, null, "input");

        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();
    });

    QUnit.test("Auto save: save on closing tab/browser (invalid field)", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo" required="1"/>
                </tree>`,
            mockRPC(route, { args, method, model }) {
                if (model === "foo" && method === "write") {
                    assert.step("save"); // should not be called
                }
            },
        });

        await click(target.querySelector(".o_data_cell"));
        await editInput(target, '.o_data_cell [name="foo"] input', "");

        const evnt = new Event("beforeunload");
        evnt.preventDefault = () => assert.step("prevented");
        window.dispatchEvent(evnt);
        await nextTick();

        assert.verifySteps(["prevented"], "should not save because of invalid field");
    });

    QUnit.test(
        "Auto save: save on closing tab/browser (onchanges + pending changes)",
        async function (assert) {
            assert.expect(1);

            serverData.models.foo.onchanges = {
                int_field: function (obj) {
                    obj.foo = `${obj.int_field}`;
                },
            };

            const def = makeDeferred();
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="top">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </tree>`,
                mockRPC(route, { args, method, model }) {
                    if (model === "foo" && method === "onchange") {
                        return def;
                    }
                    if (model === "foo" && method === "web_save") {
                        assert.deepEqual(args, [[1], { int_field: 2021 }]);
                    }
                },
            });
            await click(target.querySelector(".o_data_cell"));
            await editInput(target, '.o_data_cell [name="int_field"] input', "2021");

            window.dispatchEvent(new Event("beforeunload"));
            await nextTick();
        }
    );

    QUnit.test("Auto save: save on closing tab/browser (onchanges)", async function (assert) {
        assert.expect(1);

        serverData.models.foo.onchanges = {
            int_field: function (obj) {
                obj.foo = `${obj.int_field}`;
            },
        };

        const def = makeDeferred();
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            mockRPC(route, { args, method, model }) {
                if (model === "foo" && method === "onchange") {
                    return def;
                }
                if (model === "foo" && method === "web_save") {
                    assert.deepEqual(args, [[1], { foo: "test", int_field: 2021 }]);
                }
            },
        });
        await click(target.querySelector(".o_data_cell"));
        await editInput(target, '.o_data_cell [name="int_field"] input', "2021");
        const input = target.querySelector('.o_data_cell [name="foo"] input');
        input.value = "test";
        await triggerEvent(input, null, "input");

        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();
    });

    QUnit.test(
        "edition, then navigation with tab (with a readonly re-evaluated field and onchange)",
        async function (assert) {
            // This test makes sure that if we have a cell in a row that will become
            // read-only after editing another cell, in case the keyboard navigation
            // move over it before it becomes read-only and there are unsaved changes
            // (which will trigger an onchange), the focus of the next activable
            // field will not crash
            serverData.models.bar.onchanges = {
                o2m: function () {},
            };
            serverData.models.bar.fields.o2m = {
                string: "O2M field",
                type: "one2many",
                relation: "foo",
            };
            serverData.models.bar.records[0].o2m = [1, 4];

            await makeView({
                type: "form",
                resModel: "bar",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="display_name"/>
                            <field name="o2m">
                                <tree editable="bottom">
                                    <field name="foo"/>
                                    <field name="date" readonly="foo != 'yop'"/>
                                    <field name="int_field"/>
                                </tree>
                            </field>
                        </group>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.step(`onchange:${args.model}`);
                    }
                },
            });

            await click(target.querySelector(".o_data_cell"));
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_cell[name=foo] input")
            );
            await editInput(target, ".o_data_cell[name=foo] input", "new value");

            triggerHotkey("Tab");
            await nextTick();

            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_cell[name=int_field] input")
            );

            assert.verifySteps(["onchange:bar"]);
        }
    );

    QUnit.test(
        "selecting a row after another one containing a table within an html field should be the correct one",
        async function (assert) {
            // FIXME WOWL hack: add back the text field as html field removed by web_editor html_field file
            registry.category("fields").add("html", textField, { force: true });
            serverData.models.foo.fields.html = { string: "HTML field", type: "html" };
            serverData.models.foo.records[0].html = `
                <table class="table table-bordered">
                    <tbody>
                        <tr>
                            <td><br></td>
                            <td><br></td>
                        </tr>
                         <tr>
                            <td><br></td>
                            <td><br></td>
                        </tr>
                    </tbody>
                </table>`;

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top" multi_edit="1"><field name="html"/></tree>',
            });

            await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
            assert.ok(
                $("table.o_list_table > tbody > tr:eq(1)")[0].classList.contains("o_selected_row"),
                "The second row should be selected"
            );
        }
    );

    QUnit.test(
        "archive/unarchive not available on active readonly models",
        async function (assert) {
            serverData.models.foo.fields.active = {
                string: "Active",
                type: "boolean",
                default: true,
                readonly: true,
            };

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="3"><field name="display_name"/></tree>',
                actionMenus: {},
            });

            await click(target.querySelector("tbody .o_data_row td.o_list_record_selector input"));
            assert.containsOnce(target, ".o_cp_action_menus", "sidebar should be available");

            await click(target, "div.o_control_panel .o_cp_action_menus .dropdown button");
            assert.containsNone(
                target,
                "a:contains(Archive)",
                "Archive action should not be available"
            );
        }
    );

    QUnit.test("open groups are kept when leaving and coming back", async (assert) => {
        serverData.views = {
            "foo,false,list": `<tree><field name="foo"/></tree>`,
            "foo,false,search": "<search/>",
            "foo,false,form": "<form/>",
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partners",
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            context: {
                group_by: ["bar"],
            },
        });

        assert.containsOnce(target, ".o_list_view");
        assert.containsN(target, ".o_group_header", 2);
        assert.containsNone(target, ".o_group_open");
        assert.containsNone(target, ".o_data_row");

        // unfold the second group
        await click(target.querySelectorAll(".o_group_header")[1]);
        assert.containsOnce(target, ".o_group_open");
        assert.containsN(target, ".o_data_row", 3);

        // open a record and go back
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_form_view");
        await click(target.querySelector(".breadcrumb-item a"));

        assert.containsOnce(target, ".o_group_open");
        assert.containsN(target, ".o_data_row", 3);
    });

    QUnit.test(
        "open groups are kept when leaving and coming back (grouped by date)",
        async (assert) => {
            serverData.models.foo.fields.date.default = "2022-10-10";
            serverData.views = {
                "foo,false,list": `<tree><field name="foo"/></tree>`,
                "foo,false,search": "<search/>",
                "foo,false,form": "<form/>",
            };
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                name: "Partners",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                context: {
                    group_by: ["date"],
                },
            });

            assert.containsOnce(target, ".o_list_view");
            assert.containsN(target, ".o_group_header", 2);
            assert.containsNone(target, ".o_group_open");
            assert.containsNone(target, ".o_data_row");

            // unfold the second group
            await click(target.querySelectorAll(".o_group_header")[1]);
            assert.containsOnce(target, ".o_group_open");
            assert.containsN(target, ".o_data_row", 3);

            // open a record and go back
            await click(target.querySelector(".o_data_cell"));
            assert.containsOnce(target, ".o_form_view");
            await click(target.querySelector(".breadcrumb-item a"));

            assert.containsOnce(target, ".o_group_open");
            assert.containsN(target, ".o_data_row", 3);
        }
    );

    QUnit.test(
        "go to the next page after leaving and coming back to a grouped list view",
        async (assert) => {
            serverData.views = {
                "foo,false,list": `<tree groups_limit="1"><field name="foo"/></tree>`,
                "foo,false,search": "<search/>",
                "foo,false,form": "<form/>",
            };
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                name: "Partners",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                context: {
                    group_by: ["bar"],
                },
            });
            assert.containsOnce(target, ".o_list_view");
            assert.containsOnce(target, ".o_group_header");
            assert.strictEqual(target.querySelector(".o_group_header").textContent, "No (1) ");

            // unfold the second group
            await click(target, ".o_group_header");
            assert.containsOnce(target, ".o_group_open");
            assert.containsOnce(target, ".o_data_row");

            // open a record and go back
            await click(target.querySelector(".o_data_cell"));
            assert.containsOnce(target, ".o_form_view");

            await click(target.querySelector(".breadcrumb-item a"));
            assert.containsOnce(target, ".o_group_header");
            assert.strictEqual(target.querySelector(".o_group_header").textContent, "No (1) ");

            await pagerNext(target);
            assert.containsOnce(target, ".o_group_header");
            assert.strictEqual(target.querySelector(".o_group_header").textContent, "Yes (3) ");
        }
    );

    QUnit.test("keep order after grouping", async (assert) => {
        serverData.models.foo.fields.foo.sortable = true;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                </tree>`,
            searchViewArch: `
                <search>
                    <filter name="group_by_foo" string="Foo" context="{'group_by':'foo'}"/>
                </search>`,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row td[name=foo]")].map((r) => r.innerText),
            ["yop", "blip", "gnap", "blip"]
        );

        // Descending order on Bar
        await click(target, "th.o_column_sortable[data-name=foo]");
        await click(target, "th.o_column_sortable[data-name=foo]");

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row td[name=foo]")].map((r) => r.innerText),
            ["yop", "gnap", "blip", "blip"]
        );

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Foo");

        assert.deepEqual(
            [...target.querySelectorAll(".o_group_name")].map((r) => r.innerText),
            ["yop (1)", "gnap (1)", "blip (2)"]
        );

        await toggleMenuItem(target, "Foo");

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row td[name=foo]")].map((r) => r.innerText),
            ["yop", "gnap", "blip", "blip"]
        );
    });

    QUnit.test("editable list header click should unselect record", async (assert) => {
        await makeView({
            resModel: "foo",
            type: "list",
            arch: `<list editable="top"><field name="display_name" /></list>`,
            serverData,
        });

        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");
        await editInput(target, ".o_data_cell input", "someInput");
        await click(target.querySelector("thead th:nth-child(2)"));
        await triggerEvent(target.querySelector("thead th"), null, "keydown", { key: "ArrowDown" });

        assert.containsNone(target, ".o_selected_row");
    });

    QUnit.test("editable list group header click should unselect record", async (assert) => {
        await makeView({
            resModel: "foo",
            type: "list",
            arch: `<list editable="top"><field name="display_name" /></list>`,
            serverData,
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_header"));
        await click(target.querySelector(".o_group_header:not(.o_group_open)"));

        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");
        await editInput(target, ".o_data_cell input", "someInput");
        await click(target.querySelectorAll(".o_group_header")[1]);

        assert.containsNone(target, ".o_selected_row");
    });

    QUnit.test("renders banner_route", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree banner_route="/mybody/isacage">
                    <field name="foo"/>
                </tree>`,
            async mockRPC(route) {
                if (route === "/mybody/isacage") {
                    assert.step(route);
                    return { html: `<div class="setmybodyfree">myBanner</div>` };
                }
            },
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(target, ".setmybodyfree");
    });

    QUnit.test("fieldDependencies support for fields", async (assert) => {
        serverData.models.foo.records = [{ id: 1, int_field: 2 }];

        const customField = {
            component: class CustomField extends Component {
                static template = xml`<span t-esc="props.record.data.int_field"/>`;
            },
            fieldDependencies: [{ name: "int_field", type: "integer" }],
        };
        registry.category("fields").add("custom_field", customField);

        await makeView({
            resModel: "foo",
            type: "list",
            arch: `
                <list>
                    <field name="foo" widget="custom_field"/>
                </list>
            `,
            serverData,
        });

        assert.strictEqual(target.querySelector("[name=foo] span").innerText, "2");
    });

    QUnit.test(
        "fieldDependencies support for fields: dependence on a relational field",
        async (assert) => {
            const customField = {
                component: class CustomField extends Component {
                    static template = xml`<span t-esc="props.record.data.m2o[0]"/>`;
                },
                fieldDependencies: [{ name: "m2o", type: "many2one", relation: "bar" }],
            };
            registry.category("fields").add("custom_field", customField);

            await makeView({
                resModel: "foo",
                type: "list",
                arch: `
                    <list>
                        <field name="foo" widget="custom_field"/>
                    </list>
                `,
                serverData,
                mockRPC: (route, args) => {
                    assert.step(args.method);
                },
            });

            assert.strictEqual(target.querySelector("[name=foo] span").innerText, "1");
            assert.verifySteps(["get_views", "web_search_read"]);
        }
    );

    QUnit.test("editable list correctly saves dirty fields ", async (assert) => {
        serverData.models.foo.records = [serverData.models.foo.records[0]];

        await makeView({
            resModel: "foo",
            type: "list",
            arch: `<list editable="bottom">
                    <field name="display_name" />
                </list>`,
            serverData,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save");
                    assert.deepEqual(args.args, [[1], { display_name: "test" }]);
                }
            },
        });

        await click(target.querySelector(".o_data_cell"));
        const input = target.querySelector(".o_data_cell input");
        input.value = "test";
        await triggerEvent(input, null, "input");
        triggerHotkey("Tab");
        await nextTick();

        assert.verifySteps(["web_save"]);
    });

    QUnit.test("edit a field with a slow onchange in a new row", async function (assert) {
        serverData.models.foo.onchanges = {
            int_field: function () {},
        };
        serverData.models.foo.records = [];

        let def;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="int_field"/>
                </tree>`,
            async mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "onchange") {
                    await Promise.resolve(def);
                }
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);

        const value = "14";
        // add a new line
        await click($(".o_list_button_add:visible").get(0));

        assert.verifySteps(["onchange"]);

        // we want to add a delay to simulate an onchange
        def = makeDeferred();

        // write something in the field
        await editInput(target, "[name=int_field] input", value);
        assert.strictEqual(target.querySelector("[name=int_field] input").value, value);

        await click(target, ".o_list_view");

        // check that nothing changed before the onchange finished
        assert.strictEqual(target.querySelector("[name=int_field] input").value, value);
        assert.verifySteps(["onchange"]);

        // unlock onchange
        def.resolve();
        await nextTick();

        // check the current line is added with the correct content
        assert.strictEqual(target.querySelector(".o_data_row [name=int_field]").innerText, value);
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("create a record with the correct context", async (assert) => {
        serverData.models.foo.fields.text.required = true;
        serverData.models.foo.records = [];

        await makeView({
            resModel: "foo",
            type: "list",
            arch: ` <list editable="bottom">
                        <field name="display_name"/>
                        <field name="text"/>
                    </list>`,
            serverData,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save");
                    const { context } = args.kwargs;
                    assert.strictEqual(context.default_text, "yop");
                    assert.strictEqual(context.test, true);
                }
            },
            context: {
                default_text: "yop",
                test: true,
            },
        });
        await click($(".o_list_button_add:visible").get(0));
        await editInput(target, "[name='display_name'] input", "blop");
        assert.containsOnce(target, ".o_selected_row");

        await click(target, ".o_list_view");
        assert.containsNone(target, ".o_selected_row");

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row .o_data_cell")].map((el) => el.textContent)[
                ("blop", "yop")
            ]
        );

        assert.verifySteps(["web_save"]);
    });

    QUnit.test("create a record with the correct context in a group", async (assert) => {
        serverData.models.foo.fields.text.required = true;

        await makeView({
            resModel: "foo",
            type: "list",
            arch: ` <list editable="bottom">
                        <field name="display_name"/>
                        <field name="text"/>
                    </list>`,
            groupBy: ["bar"],
            serverData,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save");
                    const { context } = args.kwargs;
                    assert.strictEqual(context.default_bar, true);
                    assert.strictEqual(context.default_text, "yop");
                    assert.strictEqual(context.test, true);
                }
            },
            context: {
                default_text: "yop",
                test: true,
            },
        });
        await click(target.querySelectorAll(".o_group_name")[1]);

        await click(target.querySelector(".o_group_field_row_add a"));
        await editInput(target, "[name='display_name'] input", "blop");
        assert.containsOnce(target, ".o_selected_row");

        await click(target, ".o_list_view");
        assert.containsNone(target, ".o_selected_row");

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row .o_data_cell")].map((el) => el.textContent)[
                ("blop", "yop")
            ]
        );

        assert.verifySteps(["web_save"]);
    });

    QUnit.test(
        "classNames given to a field are set on the right field directly",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree editable="bottom">
                    <field class="d-flex align-items-center" name="int_field" widget="progressbar" options="{'editable': true}" />
                    <field class="d-none" name="bar" />
                </tree>`,
            });
            assert.doesNotHaveClass(
                target.querySelectorAll(".o_field_cell")[2],
                "d-flex align-items-center",
                "classnames are not set on the first cell"
            );
            assert.hasClass(
                target.querySelector(".o_field_progressbar"),
                "d-flex align-items-center",
                "classnames are set on the corresponding field div directly"
            );
            assert.hasClass(
                target.querySelectorAll(".o_field_cell")[3],
                "d-none",
                "classnames are set on the second cell"
            );
        }
    );

    QUnit.test("use a filter_domain in a list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="m2o"/></tree>',
            searchViewArch: `
                <search>
                    <field name="m2o" filter_domain="[('m2o', 'child_of', raw_value)]"/>
                </search>`,
            context: {
                search_default_m2o: 1,
            },
        });

        assert.containsN(target, ".o_data_row", 3);
    });

    QUnit.test("Formatted group operator", async function (assert) {
        serverData.models.foo.records[0].qux = 0.4;
        serverData.models.foo.records[1].qux = 0.2;
        serverData.models.foo.records[2].qux = 0.01;
        serverData.models.foo.records[3].qux = 0.48;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="qux" widget="percentage"/></tree>',
            groupBy: ["bar"],
        });
        const [td1, td2] = target.querySelectorAll("td.o_list_number");
        assert.strictEqual(td1.textContent, "48%");
        assert.strictEqual(td2.textContent, "61%");
    });

    QUnit.test(
        "Formatted group operator with digit precision on the field definition",
        async function (assert) {
            serverData.models.foo.fields.qux.digits = [16, 3];
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree><field name="qux"/></tree>',
                groupBy: ["bar"],
            });
            const [td1, td2] = target.querySelectorAll("td.o_list_number");
            assert.strictEqual(td1.textContent, "9.000");
            assert.strictEqual(td2.textContent, "10.400");
        }
    );

    QUnit.test("list view does not crash when clicked button cell", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                </tree>
            `,
        });

        assert.containsN(target, ".o_data_row:first-child td.o_list_button", 1);
        await click(target, ".o_data_row:first-child td.o_list_button");
    });

    QUnit.test("group by going to next page then back to first", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree groups_limit="1"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
        });

        assert.deepEqual([...getPagerValue(target), getPagerLimit(target)], [1, 2]);
        await pagerNext(target);
        assert.deepEqual([...getPagerValue(target), getPagerLimit(target)], [2, 2]);
        await pagerPrevious(target);
        assert.deepEqual([...getPagerValue(target), getPagerLimit(target)], [1, 2]);
    });

    QUnit.test("list with group_by_no_leaf and group by", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ["currency_id"],
            context: { group_by_no_leaf: true },
        });

        const groups = target.querySelectorAll(".o_group_name");
        const groupsRecords = [...target.querySelectorAll(".o_data_row .o_data_cell")];
        assert.strictEqual(groups.length, 2, "There should be 2 groups");
        assert.strictEqual(groups[0].textContent, "USD (3) ", "Second group should have 3 records");
        assert.strictEqual(groups[1].textContent, "EUR (1) ", "First group should have 1 record");
        assert.deepEqual(
            groupsRecords.map((groupEl) => groupEl.textContent),
            ["blip", "gnap", "blip", "yop"],
            "Groups should contains correct records"
        );
    });

    QUnit.test("sort on a non sortable field with allow_order option", async function (assert) {
        serverData.models.foo.records = [{ bar: true }, { bar: false }, { bar: true }];

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <list>
                    <field name="bar" options="{ 'allow_order': true }"/>
                </list>
            `,
        });

        assert.deepEqual(
            [...target.querySelectorAll("[name=bar] input")].map((el) => el.checked),
            [true, false, true]
        );
        assert.hasClass(target.querySelectorAll("th[data-name=bar]"), "o_column_sortable");
        assert.doesNotHaveClass(target.querySelectorAll("th[data-name=bar]"), "table-active");

        await click(target, "th[data-name=bar]");

        assert.deepEqual(
            [...target.querySelectorAll("[name=bar] input")].map((el) => el.checked),
            [false, true, true]
        );
        assert.hasClass(target.querySelectorAll("th[data-name=bar]"), "o_column_sortable");
        assert.hasClass(target.querySelectorAll("th[data-name=bar]"), "table-active");
        assert.hasClass(target.querySelectorAll("th[data-name=bar] i"), "fa-angle-up");
    });

    QUnit.test("sort rows in a grouped list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <list>
                    <field name="int_field"/>
                </list>`,
            groupBy: ["bar"],
        });

        await click(target.querySelectorAll(".o_group_header")[1]);

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "10",
            "9",
            "17",
        ]);
        assert.hasClass(target.querySelectorAll("th[data-name=int_field]"), "o_column_sortable");

        await click(target, "th[data-name=int_field]");

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "9",
            "10",
            "17",
        ]);
        assert.hasClass(target.querySelectorAll("th[data-name=int_field]"), "o_column_sortable");
        assert.hasClass(target.querySelectorAll("th[data-name=int_field] i"), "fa-angle-up");
    });

    QUnit.test(
        "have some records, then go to next page in pager then group by some field: at least one group should be visible",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <list limit="2">
                        <field name="foo"/>
                        <field name="bar"/>
                    </list>
                `,
                searchViewArch: `
                    <search>
                        <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                    </search>
                `,
            });
            assert.containsN(target, "tbody .o_data_row", 2);
            assert.deepEqual(
                [...target.querySelectorAll("tbody .o_data_row")].map((el) => el.innerText.trim()),
                ["yop", "blip"]
            );

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Bar");
            assert.containsN(target, "tbody .o_group_header", 2);
            assert.deepEqual(
                [...target.querySelectorAll("tbody .o_group_header")].map((el) =>
                    el.innerText.trim()
                ),
                ["No (1)", "Yes (3)"]
            );

            await removeFacet(target);
            assert.containsN(target, "tbody .o_data_row", 2);
            assert.deepEqual(
                [...target.querySelectorAll("tbody .o_data_row")].map((el) => el.innerText.trim()),
                ["yop", "blip"]
            );

            await pagerNext(target);
            assert.containsN(target, "tbody .o_data_row", 2);
            assert.deepEqual(
                [...target.querySelectorAll("tbody .o_data_row")].map((el) => el.innerText.trim()),
                ["gnap", "blip"]
            );

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Bar");
            assert.containsN(target, "tbody .o_group_header", 2);
            assert.deepEqual(
                [...target.querySelectorAll("tbody .o_group_header")].map((el) =>
                    el.innerText.trim()
                ),
                ["No (1)", "Yes (3)"]
            );
        }
    );

    QUnit.test("optional field selection do not unselect current row", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="top">
                        <field name="text" optional="hide"/>
                        <field name="foo" optional="show"/>
                        <field name="bar" optional="hide"/>
                    </tree>`,
        });

        await clickAdd();

        assert.containsOnce(target, ".o_selected_row");
        assert.containsOnce(target, "div[name=foo] input:focus");

        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");

        assert.containsOnce(target, ".o_selected_row");
        assert.containsOnce(target, "div[name=foo] input:focus");

        await click(target, ".o_optional_columns_dropdown span.dropdown-item:nth-child(3) label");

        assert.containsOnce(target, ".o_selected_row");
        assert.containsOnce(target, "div[name=foo] input:focus");
        assert.containsOnce(target, ".o_selected_row div[name=bar]");

        await click(target, ".o_optional_columns_dropdown span.dropdown-item:nth-child(1) label");

        assert.containsOnce(target, ".o_selected_row");
        // This below would be better if it still focused foo, but it is an acceptable tradeoff.
        assert.containsOnce(target, "div[name=text] textarea:focus");
        assert.containsOnce(target, ".o_selected_row div[name=text]");
    });

    QUnit.test("view widgets are rendered in list view", async function (assert) {
        class TestWidget extends Component {
            static template = xml`<div class="test_widget" t-esc="props.record.data.bar"/>`;
        }
        const testWidget = {
            component: TestWidget,
        };
        registry.category("view_widgets").add("test_widget", testWidget);
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <list>
                    <field name="bar" column_invisible="1"/>
                    <widget name="test_widget"/>
                </list>
            `,
        });
        assert.containsN(
            target,
            "td .test_widget",
            4,
            "there should be one widget (inside td) per record"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".test_widget")].map((w) => w.textContent),
            ["true", "true", "true", "false"],
            "the widget has access to the record's data"
        );
    });

    QUnit.test(
        "edit a record then select another record with a throw error when saving",
        async function (assert) {
            serviceRegistry.add("error", errorService);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree editable="bottom">
                        <field name="foo"/>
                    </tree>`,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        throw makeServerError({ message: "Can't write" });
                    }
                },
            });

            await click(target.querySelectorAll(".o_data_cell")[1]);
            await editInput(target, "[name='foo'] input", "plop");
            assert.containsOnce(target, "[name='foo'] input");

            await click(target.querySelectorAll(".o_data_cell")[0]);
            await nextTick();
            assert.containsOnce(target, ".o_error_dialog");

            await click(target, ".o_error_dialog .btn-primary.o-default-button");
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");

            await click(target.querySelectorAll(".o_data_cell")[0]);
            await nextTick();
            assert.containsOnce(target, ".o_error_dialog");

            await click(target, ".o_error_dialog .btn-primary.o-default-button");
            assert.containsOnce(target, ".o_selected_row");
            assert.hasClass(target.querySelectorAll(".o_data_row")[1], "o_selected_row");
        }
    );

    QUnit.test("no highlight of a (sortable) column without label", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree default_order="foo">
                    <field name="foo" nolabel="1"/>
                    <field name="bar"/>
                </tree>
            `,
        });
        assert.containsOnce(target, "thead th[data-name=foo]");
        assert.doesNotHaveClass(target.querySelector("thead th[data-name=foo]"), "table-active");
    });

    QUnit.test("highlight of a (sortable) column with label", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree default_order="foo">
                    <field name="foo"/>
                </tree>
            `,
        });
        assert.containsOnce(target, "thead th[data-name=foo]");
        assert.hasClass(target.querySelector("thead th[data-name=foo]"), "table-active");
    });

    QUnit.test("Search more in a many2one", async function (assert) {
        serverData.views = {
            "bar,false,list": `
                <list>
                    <field name="display_name"/>
                </list>
            `,
            "bar,false,search": `<search/>`,
        };

        patchWithCleanup(browser, {
            setTimeout: () => {},
        });

        patchWithCleanup(Many2XAutocomplete.defaultProps, {
            searchLimit: 1,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                </tree>
            `,
            mockRPC(_, args) {
                if (args.method === "web_read") {
                    assert.step(`web_read ${args.args[0]}`);
                } else if (args.method === "web_save") {
                    assert.step(`web_save ${args.args[0]}`);
                }
            },
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row td[name=m2o]")].map((el) => el.innerText),
            ["Value 1", "Value 2", "Value 1", "Value 1"]
        );

        await click(target, ".o_data_row:nth-child(1) td.o_list_many2one");
        await click(target, ".o_field_many2one_selection .o-autocomplete--input");
        await clickOpenedDropdownItem(target, "m2o", "Search More...");

        assert.verifySteps([]);

        await click(target, ".modal .o_data_row:nth-child(3) td[name=display_name]");

        assert.verifySteps(["web_read 3"]);

        await clickSave(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row td[name=m2o]")].map((el) => el.innerText),
            ["Value 3", "Value 2", "Value 1", "Value 1"]
        );
        assert.verifySteps(["web_save 1"]);
    });

    QUnit.test("view's context is passed down as evalContext", async (assert) => {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            context: {
                default_global_key: "some_value",
            },
            arch: `
                <tree editable="bottom">
                    <field name="m2o" domain="[['someField', '=', context.get('default_global_key', 'nope')]]"/>
                </tree>
            `,
            mockRPC(_, args) {
                if (args.method === "name_search") {
                    assert.step(`name_search`);
                    assert.deepEqual(args.kwargs.args, [["someField", "=", "some_value"]]);
                }
            },
        });

        await click(target, ".o_data_row:nth-child(1) td.o_list_many2one");
        await click(target, ".o_field_many2one_selection .o-autocomplete--input");
        assert.verifySteps(["name_search"]);
    });

    QUnit.test("list view with default_group_by", async (assert) => {
        serverData.models.foo.fields.m2m.store = true;

        let readGroupCount = 0;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree default_group_by="bar">
                    <field name="bar"/>
                </tree>
            `,
            async mockRPC(route, { kwargs }) {
                if (route === "/web/dataset/call_kw/partner/web_read_group") {
                    readGroupCount++;
                    switch (readGroupCount) {
                        case 1:
                            return assert.deepEqual(kwargs.groupby, ["bar"]);
                        case 2:
                            return assert.deepEqual(kwargs.groupby, ["m2m"]);
                        case 3:
                            return assert.deepEqual(kwargs.groupby, ["bar"]);
                    }
                }
            },
        });

        assert.hasClass(target.querySelector(".o_list_renderer table"), "o_list_table_grouped");
        assert.containsN(target, ".o_group_header", 2);

        await groupByMenu(target, "m2m");
        assert.containsN(target, ".o_group_header", 4);

        await toggleMenuItem(target, "M2M field");
        assert.containsN(target, ".o_group_header", 2);
    });

    QUnit.test("ungrouped list, apply filter, decrease limit", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree limit="4"><field name="foo"/></tree>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('id', '>', 1)]"/>
                </search>`,
        });

        assert.containsN(target, ".o_data_row", 4);

        // apply the filter to trigger a reload of datapoints
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "My Filter");

        assert.containsN(target, ".o_data_row", 3);

        // edit the pager with a smaller limit
        await click(target.querySelector(".o_pager_value"));
        await editInput(target, ".o_pager_value", "1-2");

        assert.containsN(target, ".o_data_row", 2);
    });

    QUnit.test("Properties: char", async (assert) => {
        const definition = {
            type: "char",
            name: "property_char",
            string: "Property char",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: "CHAR" }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [
                        [1],
                        { properties: [{ ...definition, value: "TEST" }] },
                    ]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_char']");
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_char']")
                .textContent,
            "Property char"
        );
        assert.containsN(target, ".o_field_cell.o_char_cell", 3);
        assert.strictEqual(target.querySelector(".o_field_cell.o_char_cell").textContent, "CHAR");

        await click(target.querySelector(".o_field_cell.o_char_cell"));
        await editInput(target, ".o_field_cell.o_char_cell input", "TEST");
        assert.strictEqual(target.querySelector(".o_field_cell.o_char_cell input").value, "TEST");

        await click(target.querySelector("[name='m2o']"));
        assert.strictEqual(target.querySelector(".o_field_cell.o_char_cell input").value, "TEST");

        await clickSave(target);
        assert.strictEqual(target.querySelector(".o_field_cell.o_char_cell").textContent, "TEST");
    });

    QUnit.test("Properties: boolean", async (assert) => {
        const definition = {
            type: "boolean",
            name: "property_boolean",
            string: "Property boolean",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: true }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [
                        [1],
                        { properties: [{ ...definition, value: false }] },
                    ]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_boolean']");
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_boolean']")
                .textContent,
            "Property boolean"
        );
        assert.containsN(target, ".o_field_cell.o_boolean_cell", 3);

        await click(target.querySelector(".o_field_cell.o_boolean_cell"));
        await click(target.querySelector(".o_field_cell.o_boolean_cell input"));
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_cell.o_boolean_cell input").checked,
            false
        );
    });

    QUnit.test("Properties: integer", async (assert) => {
        const definition = {
            type: "integer",
            name: "property_integer",
            string: "Property integer",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: 123 }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [[1], { properties: [{ ...definition, value: 321 }] }]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_integer']");
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_integer']")
                .textContent,
            "Property integer"
        );
        assert.containsN(target, ".o_field_cell.o_integer_cell", 3);

        await click(target.querySelector(".o_field_cell.o_integer_cell"));
        await editInput(target, ".o_field_cell.o_integer_cell input", 321);
        await clickSave(target);

        assert.strictEqual(target.querySelector(".o_field_cell.o_integer_cell").textContent, "321");
        assert.strictEqual(
            target.querySelector(".o_list_footer .o_list_number").textContent,
            "567",
            "First property is 321, second is zero because it has a different parent and the 2 others are 123 so the total should be 321 + 123 * 2 = 567"
        );
    });

    QUnit.test("Properties: float", async (assert) => {
        const definition = {
            type: "float",
            name: "property_float",
            string: "Property float",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: 123.45 }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [[1], { properties: [{ ...definition, value: 3.21 }] }]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_float']");
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_float']")
                .textContent,
            "Property float"
        );
        assert.containsN(target, ".o_field_cell.o_float_cell", 3);

        await click(target.querySelector(".o_field_cell.o_float_cell"));
        await editInput(target, ".o_field_cell.o_float_cell input", 3.21);
        await clickSave(target);

        assert.strictEqual(target.querySelector(".o_field_cell.o_float_cell").textContent, "3.21");
        assert.strictEqual(
            target.querySelector(".o_list_footer .o_list_number").textContent,
            "250.11",
            "First property is 3.21, second is zero because it has a different parent and the 2 others are 123.45 so the total should be 3.21 + 123.45 * 2 = 250.11"
        );
    });

    QUnit.test("Properties: date", async (assert) => {
        const definition = {
            type: "date",
            name: "property_date",
            string: "Property date",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: "2022-12-12" }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [
                        [1],
                        { properties: [{ ...definition, value: "2022-12-19" }] },
                    ]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_date']");
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_date']")
                .textContent,
            "Property date"
        );
        assert.containsN(target, ".o_field_cell.o_date_cell", 3);

        await click(target.querySelector(".o_field_cell.o_date_cell"));
        await click(target, ".o_field_date input");
        await click(getPickerCell("19"));
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_cell.o_date_cell").textContent,
            "12/19/2022"
        );
    });

    QUnit.test("Properties: datetime", async (assert) => {
        patchTimeZone(0);
        const definition = {
            type: "datetime",
            name: "property_datetime",
            string: "Property datetime",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: "2022-12-12 12:12:00" }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [
                        [1],
                        { properties: [{ ...definition, value: "2022-12-19 12:12:00" }] },
                    ]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(
            target,
            ".o_list_renderer th[data-name='properties.property_datetime']"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_datetime']")
                .textContent,
            "Property datetime"
        );
        assert.containsN(target, ".o_field_cell.o_datetime_cell", 3);

        await click(target.querySelector(".o_field_cell.o_datetime_cell"));
        await click(target, ".o_field_datetime input");
        await click(getPickerCell("19"));
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_cell.o_datetime_cell").textContent,
            "12/19/2022 12:12:00"
        );
    });

    QUnit.test("Properties: selection", async (assert) => {
        const definition = {
            type: "selection",
            name: "property_selection",
            string: "Property selection",
            selection: [
                ["a", "A"],
                ["b", "B"],
                ["c", "C"],
            ],
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: "b" }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [[1], { properties: [{ ...definition, value: "a" }] }]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(
            target,
            ".o_list_renderer th[data-name='properties.property_selection']"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_selection']")
                .textContent,
            "Property selection"
        );
        assert.containsN(target, ".o_field_cell.o_selection_cell", 3);

        await click(target.querySelector(".o_field_cell.o_selection_cell"));
        await editSelect(target, ".o_field_cell.o_selection_cell select", `"a"`);
        await clickSave(target);

        assert.strictEqual(target.querySelector(".o_field_cell.o_selection_cell").textContent, "A");
    });

    QUnit.test("Properties: tags", async (assert) => {
        const definition = {
            type: "tags",
            name: "property_tags",
            string: "Property tags",
            tags: [
                ["a", "A", 1],
                ["b", "B", 2],
                ["c", "C", 3],
            ],
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: ["a", "c"] }];
            }
        }

        let expectedValue = null;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [
                        [1],
                        { properties: [{ ...definition, value: expectedValue }] },
                    ]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_tags']");
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_tags']")
                .textContent,
            "Property tags"
        );
        assert.containsN(target, ".o_field_cell.o_property_tags_cell", 3);

        await click(target.querySelector(".o_field_cell.o_property_tags_cell"));
        await click(target.querySelectorAll(".o_field_cell.o_property_tags_cell .o_delete")[0]);
        expectedValue = ["c"];
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_cell.o_property_tags_cell").textContent,
            "C"
        );

        await click(target.querySelector(".o_field_cell.o_property_tags_cell"));
        await selectDropdownItem(target, "properties.property_tags", "B");
        expectedValue = ["c", "b"];
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_cell.o_property_tags_cell").textContent,
            "BC"
        );
    });

    QUnit.test("Properties: many2one", async (assert) => {
        const definition = {
            type: "many2one",
            name: "property_many2one",
            string: "Property many2one",
            comodel: "res_currency",
            domain: "[]",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: [1, "USD"] }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [
                        [1],
                        { properties: [{ ...definition, value: [2, "EUR"] }] },
                    ]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(
            target,
            ".o_list_renderer th[data-name='properties.property_many2one']"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_many2one']")
                .textContent,
            "Property many2one"
        );
        assert.containsN(target, ".o_field_cell.o_many2one_cell", 3);

        await click(target.querySelector(".o_field_cell.o_many2one_cell"));
        await selectDropdownItem(target, "properties.property_many2one", "EUR");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_cell.o_many2one_cell").textContent,
            "EUR"
        );
    });

    QUnit.test("Properties: many2many", async (assert) => {
        const definition = {
            type: "many2many",
            name: "property_many2many",
            string: "Property many2many",
            comodel: "res_currency",
            domain: "[]",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: [[1, "USD"]] }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args, [[1], { properties: [{ ...definition, value: [] }] }]);
                }
            },
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(target, ".o_optional_columns_dropdown input[type='checkbox']");

        assert.containsOnce(
            target,
            ".o_list_renderer th[data-name='properties.property_many2many']"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer th[data-name='properties.property_many2many']")
                .textContent,
            "Property many2many"
        );
        assert.containsN(target, ".o_field_cell.o_many2many_tags_cell", 3);
    });

    QUnit.test("multiple sources of properties definitions", async (assert) => {
        const definition0 = {
            type: "char",
            name: "property_char",
            string: "Property char",
        };
        const definition1 = {
            type: "boolean",
            name: "property_boolean",
            string: "Property boolean",
        };
        serverData.models.bar.records[0].definitions = [definition0];
        serverData.models.bar.records[1].definitions = [definition1];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition0, value: "0" }];
            } else if (record.m2o === 2) {
                record.properties = [{ ...definition1, value: true }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
        });

        await click(target, ".o_optional_columns_dropdown_toggle");
        await click(
            target.querySelectorAll(".o_optional_columns_dropdown input[type='checkbox']")[0]
        );
        await click(
            target.querySelectorAll(".o_optional_columns_dropdown input[type='checkbox']")[1]
        );

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_char']");
        assert.containsN(target, ".o_field_cell.o_char_cell", 3);

        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_boolean']");
        assert.containsOnce(target, ".o_field_cell.o_boolean_cell", 1);
    });

    QUnit.test("toggle properties", async (assert) => {
        const definition0 = {
            type: "char",
            name: "property_char",
            string: "Property char",
        };
        const definition1 = {
            type: "boolean",
            name: "property_boolean",
            string: "Property boolean",
        };
        serverData.models.bar.records[0].definitions = [definition0];
        serverData.models.bar.records[1].definitions = [definition1];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition0, value: "0" }];
            } else if (record.m2o === 2) {
                record.properties = [{ ...definition1, value: true }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
        });

        await click(target, ".o_optional_columns_dropdown_toggle");

        await click(
            target.querySelectorAll(".o_optional_columns_dropdown input[type='checkbox']")[0]
        );
        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_char']");
        assert.containsNone(target, ".o_list_renderer th[data-name='properties.property_boolean']");

        await click(
            target.querySelectorAll(".o_optional_columns_dropdown input[type='checkbox']")[1]
        );
        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_char']");
        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_boolean']");

        await click(
            target.querySelectorAll(".o_optional_columns_dropdown input[type='checkbox']")[0]
        );
        assert.containsNone(target, ".o_list_renderer th[data-name='properties.property_char']");
        assert.containsOnce(target, ".o_list_renderer th[data-name='properties.property_boolean']");

        await click(
            target.querySelectorAll(".o_optional_columns_dropdown input[type='checkbox']")[1]
        );
        assert.containsNone(target, ".o_list_renderer th[data-name='properties.property_char']");
        assert.containsNone(target, ".o_list_renderer th[data-name='properties.property_boolean']");
    });

    QUnit.test("reload properties definitions when domain change", async (assert) => {
        const definition0 = {
            type: "char",
            name: "property_char",
            string: "Property char",
        };
        serverData.models.bar.records[0].definitions = [definition0];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition0, value: "AA" }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route) {
                assert.step(route);
            },
            irFilters: [
                {
                    context: "{}",
                    domain: "[['id', '=', 1]]",
                    id: 7,
                    name: "only one",
                    sort: "[]",
                    user_id: [2, "Mitchell Admin"],
                },
            ],
        });

        assert.verifySteps([
            "/web/dataset/call_kw/foo/get_views",
            "/web/dataset/call_kw/foo/web_search_read",
        ]);

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "only one");

        assert.verifySteps(["/web/dataset/call_kw/foo/web_search_read"]);
    });

    QUnit.test("do not reload properties definitions when page change", async (assert) => {
        const definition0 = {
            type: "char",
            name: "property_char",
            string: "Property char",
        };
        serverData.models.bar.records[0].definitions = [definition0];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition0, value: "0" }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom" limit="2">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route) {
                assert.step(route);
            },
        });

        assert.verifySteps([
            "/web/dataset/call_kw/foo/get_views",
            "/web/dataset/call_kw/foo/web_search_read",
        ]);

        await pagerNext(target);

        assert.verifySteps(["/web/dataset/call_kw/foo/web_search_read"]);
    });

    QUnit.test("load properties definitions only once when grouped", async (assert) => {
        const definition0 = {
            type: "char",
            name: "property_char",
            string: "Property char",
        };
        serverData.models.bar.records[0].definitions = [definition0];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition0, value: "0" }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" />
                </tree>
            `,
            mockRPC(route) {
                assert.step(route);
            },
            groupBy: ["m2o"],
        });

        assert.verifySteps([
            "/web/dataset/call_kw/foo/get_views",
            "/web/dataset/call_kw/foo/web_read_group",
        ]);

        await click(target.querySelector(".o_group_header"));
        assert.verifySteps(["/web/dataset/call_kw/foo/web_search_read"]);
    });

    QUnit.test("Invisible Properties", async (assert) => {
        const definition = {
            type: "integer",
            name: "property_integer",
            string: "Property integer",
        };
        serverData.models.bar.records[0].definitions = [definition];
        for (const record of serverData.models.foo.records) {
            if (record.m2o === 1) {
                record.properties = [{ ...definition, value: 123 }];
            }
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="m2o"/>
                    <field name="properties" column_invisible="1"/>
                </tree>
            `,
            mockRPC(route, { method, args }) {
                assert.step(method);
            },
        });

        assert.containsNone(target, ".o_optional_columns_dropdown_toggle");
        assert.verifySteps(["get_views", "web_search_read"]);
    });

    QUnit.test("header buttons in list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <header>
                        <button name="a" type="object" string="Confirm" confirm="Are you sure?" />
                    </header>
                    <field name="foo"/>
                    <field name="bar" />
                </tree>`,

            mockRPC: async (route, args) => {
                if (route === "/web/dataset/call_button") {
                    assert.step(args.method);
                    return true;
                }
            },
        });
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        await click(target.querySelector('.o_control_panel_actions button[name="a"]'));
        assert.containsOnce(document.body, ".modal");
        const modalText = target.querySelector(".modal-body").textContent;
        assert.strictEqual(modalText, "Are you sure?");
        await click(document, "body .modal footer button.btn-primary");
        assert.verifySteps(["a"]);
    });

    QUnit.test("restore orderBy from state when using default order", async (assert) => {
        serverData.models.foo.fields.amount.sortable = true;
        serverData.models.foo.fields.foo.sortable = true;
        serverData.actions = {
            1: {
                id: 1,
                name: "Foo",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        };
        serverData.views = {
            "foo,false,list": `
                <tree default_order="foo">
                    <field name="foo"/>
                    <field name="amount"/>
                </tree>`,
            "foo,false,form": `
                <form>
                    <field name="amount"/>
                    <field name="foo"/>
                </form>`,
            "foo,false,search": "<search/>",
        };
        const webclient = await createWebClient({
            serverData,
            async mockRPC(route, { kwargs, method }) {
                if (method === "web_search_read") {
                    assert.step("order:" + kwargs.order);
                }
            },
        });
        await doAction(webclient, 1);

        await click(target.querySelector("th[data-name=amount]")); // order by amount
        await click(target.querySelector(".o_data_row .o_data_cell")); // switch to the form view
        await click(target.querySelector(".breadcrumb-item")); // go back to the list view

        assert.verifySteps([
            "order:foo ASC", // initial list view
            "order:amount ASC, foo ASC", // order by amount
            "order:amount ASC, foo ASC", // go back to the list view, it should still be ordered by amount
        ]);
    });

    QUnit.test("x2many onchange, check result", async function (assert) {
        const def = makeDeferred();
        serverData.models.foo.onchanges = {
            m2m: function () {},
        };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="bottom">
                    <field name="m2m" widget="many2many_tags"/>
                    <field name="m2o"/>
                </tree>`,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange");
                    await def;
                    return { value: { m2o: [3, "Value 3"] } };
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_data_cell.o_many2many_tags_cell").textContent,
            "Value 1Value 2"
        );
        assert.strictEqual(
            target.querySelector(".o_data_cell.o_list_many2one").textContent,
            "Value 1"
        );
        await click(target.querySelector(".o_data_cell.o_many2many_tags_cell"));
        await selectDropdownItem(target, "m2m", "Value 3");

        assert.verifySteps(["onchange"]);
        await click(target.querySelector(".o_list_button_save:not(.btn-link)"));
        def.resolve();
        await nextTick();

        assert.strictEqual(
            target.querySelector(".o_data_cell.o_many2many_tags_cell").textContent,
            "Value 1Value 2Value 3"
        );
        assert.strictEqual(
            target.querySelector(".o_data_cell.o_list_many2one").textContent,
            "Value 3",
            "onchange result should be applied"
        );
    });

    QUnit.test(
        "list view: prevent record selection when editable list in edit mode",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree editable="top">
                    <field name="foo" />
                </tree>`,
            });

            //  When we try to select new record in edit mode
            await click(
                target.querySelector(
                    ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_add"
                )
            );
            await click(target.querySelector(".o_data_row .o_list_record_selector"));
            assert.strictEqual(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
                    .checked,
                false
            );

            //  When we try to select all records in edit mode
            await click(target.querySelector("th.o_list_record_selector.o_list_controller"));
            assert.strictEqual(
                target.querySelector('.o_list_controller input[type="checkbox"]').checked,
                false
            );
        }
    );

    QUnit.test("context keys not passed down the stack and not to fields", async (assert) => {
        patchWithCleanup(AutoComplete, {
            timeout: 0,
        });
        serverData.actions = {
            1: {
                id: 1,
                name: "Foo",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
                context: {
                    tree_view_ref: "foo_view_ref",
                    search_default_bar: true,
                },
            },
        };
        serverData.views = {
            "foo,foo_view_ref,list": `
                <tree default_order="foo" editable="top">
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            "foo,false,search": "<search/>",
            "bar,false,list": `<tree><field name="name" /></tree>`,
            "bar,false,search": "<search/>",
        };

        const barRecs = [];
        for (let i = 1; i < 50; i++) {
            barRecs.push({
                id: i,
                display_name: `Value ${i}`,
            });
        }
        serverData.models.bar.records = barRecs;

        const mockRPC = (route, args) => {
            if (args.method) {
                assert.step(
                    `${args.model}: ${args.method}: ${JSON.stringify(args.kwargs.context)}`
                );
            }
        };
        const wc = await createWebClient({ serverData, mockRPC });
        await doAction(wc, 1);
        assert.verifySteps([
            `foo: get_views: {"lang":"en","uid":7,"tz":"taht","tree_view_ref":"foo_view_ref"}`,
            `foo: web_search_read: {"lang":"en","uid":7,"tz":"taht","bin_size":true,"tree_view_ref":"foo_view_ref"}`,
        ]);

        await click(target.querySelectorAll(".o_data_row .o_data_cell")[1]);

        const input = target.querySelector(".o_selected_row .o_field_many2many_tags input");
        await triggerEvent(input, null, "focus");
        await click(input);
        await nextTick();
        assert.verifySteps([`bar: name_search: {"lang":"en","uid":7,"tz":"taht"}`]);

        const items = Array.from(
            target.querySelectorAll(".o_selected_row .o_field_many2many_tags .dropdown-item")
        );
        await click(items.find((el) => el.textContent.trim() === "Search More..."));
        assert.verifySteps([
            `bar: get_views: {"lang":"en","uid":7,"tz":"taht"}`,
            `bar: web_search_read: {"lang":"en","uid":7,"tz":"taht","bin_size":true}`,
        ]);
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal .modal-header .modal-title").textContent,
            "Search: M2M field"
        );
    });

    QUnit.test("search nested many2one field with early option selection", async (assert) => {
        const deferred = makeDeferred();
        serverData.models.parent = {
            fields: {
                foo: { string: "Foo", type: "one2many", relation: "foo" },
            },
        };
        await makeView({
            type: "form",
            resModel: "parent",
            serverData,
            arch: `
            <form>
                <field name="foo">
                    <tree editable="bottom">
                        <field name="m2o"/>
                    </tree>
                </field>
            </form>`,
            mockRPC: async (route, { method }) => {
                if (method === "name_search") {
                    await deferred;
                }
            },
        });

        await triggerEvent(document.querySelector(".o_field_x2many_list_row_add a"), null, "click");

        const input = document.activeElement;
        input.value = "alu";
        triggerEvent(document.activeElement, null, "input");
        await nextTick();

        input.value = "alue";
        triggerEvent(document.activeElement, null, "input");
        triggerHotkey("Enter");
        await nextTick();

        deferred.resolve();
        await nextTick();

        assert.strictEqual(input, document.activeElement);
        assert.strictEqual(input.value, "Value 1");
    });

    QUnit.test("monetary field display for rtl languages", async function (assert) {
        patchWithCleanup(localization, {
            direction: "rtl",
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="amount_currency"/></tree>',
        });

        assert.containsOnce(
            target,
            "thead th:nth(2) .o_list_number_th",
            "header cells of monetary fields should have o_list_number_th class"
        );
        assert.strictEqual(
            $(target).find("thead th:nth(2)").css("text-align"),
            "right",
            "header cells of monetary fields should be right alined"
        );

        assert.strictEqual(
            $(target).find("tbody tr:first td:nth(2)").css("text-align"),
            "right",
            "Monetary cells should be right alined"
        );

        assert.strictEqual(
            $(target).find("tbody tr:first td:nth(2)").css("direction"),
            "ltr",
            "Monetary cells should have ltr direction"
        );
    });

    QUnit.test("add record in editable list view with sample data", async function (assert) {
        serverData.models.foo.records = [];
        let def;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree sample="1" editable="top"><field name="int_field"/></tree>',
            noContentHelp: "click to add a record",
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    return def;
                }
            },
        });

        assert.containsOnce(target, ".o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent");
        assert.containsN(target, ".o_data_row", 10);

        def = makeDeferred();
        await clickAdd();

        assert.containsOnce(target, ".o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent");
        assert.containsN(target, ".o_data_row", 10);

        def.resolve();
        await nextTick();

        assert.containsNone(target, ".o_view_sample_data");
        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(target, ".o_data_row");
        assert.containsOnce(target, ".o_data_row.o_selected_row");
    });
});
