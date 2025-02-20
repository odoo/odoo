import { describe, expect, getFixture, test } from "@odoo/hoot";
import {
    clear,
    click,
    edit,
    hover,
    keyDown,
    keyUp,
    pointerDown,
    pointerUp,
    press,
    queryAll,
    queryAllProperties,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryRect,
    queryText,
    unload,
    waitFor,
} from "@odoo/hoot-dom";
import {
    animationFrame,
    Deferred,
    mockDate,
    mockTimeZone,
    runAllTimers,
    tick,
} from "@odoo/hoot-mock";
import { Component, markup, onRendered, onWillStart, useRef, xml } from "@odoo/owl";
import {
    getPickerApplyButton,
    getPickerCell,
} from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    clickModalButton,
    clickSave,
    contains,
    defineActions,
    defineModels,
    defineParams,
    editFavoriteName,
    fields,
    getFacetTexts,
    getPagerLimit,
    getPagerValue,
    getService,
    installLanguages,
    makeServerError,
    mockService,
    models,
    mountView,
    mountViewInDialog,
    mountWithCleanup,
    onRpc,
    pagerNext,
    pagerPrevious,
    patchWithCleanup,
    removeFacet,
    saveFavorite,
    selectFieldDropdownItem,
    selectGroup,
    serverState,
    stepAllNetworkCalls,
    toggleMenuItem,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
    webModels,
} from "@web/../tests/web_test_helpers";

import { currencies } from "@web/core/currency";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { session } from "@web/session";
import { floatField } from "@web/views/fields/float/float_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ListController } from "@web/views/list/list_controller";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

const { ResCompany, ResPartner, ResUsers } = webModels;

class Foo extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    date = fields.Date();
    datetime = fields.Datetime();
    int_field = fields.Integer();
    qux = fields.Float();
    m2o = fields.Many2one({ relation: "bar" });
    o2m = fields.One2many({ relation: "bar" });
    m2m = fields.Many2many({ relation: "bar" });
    text = fields.Text();
    amount = fields.Monetary({ currency_field: "currency_id" });
    currency_id = fields.Many2one({ relation: "res.currency", default: 1 });
    reference = fields.Reference({
        selection: [
            ["bar", "Bar"],
            ["res.currency", "Currency"],
        ],
    });
    properties = fields.Properties({
        definition_record: "m2o",
        definition_record_field: "definitions",
    });

    _records = [
        {
            id: 1,
            foo: "yop",
            bar: true,
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
            int_field: 10,
            qux: 0.4,
            m2o: 1,
            m2m: [1, 2],
            amount: 1200,
            currency_id: 2,
            reference: "bar,1",
            properties: {},
        },
        {
            id: 2,
            foo: "blip",
            bar: true,
            int_field: 9,
            qux: 13,
            m2o: 2,
            m2m: [1, 2, 3],
            amount: 500,
            reference: "res.currency,1",
            properties: {},
        },
        {
            id: 3,
            foo: "gnap",
            bar: true,
            int_field: 17,
            qux: -3,
            m2o: 1,
            m2m: [],
            amount: 300,
            reference: "res.currency,2",
            properties: {},
        },
        {
            id: 4,
            foo: "blip",
            bar: false,
            int_field: -4,
            qux: 9,
            m2o: 1,
            m2m: [1],
            amount: 0,
            properties: {},
        },
    ];
}

class Bar extends models.Model {
    name = fields.Char();
    definitions = fields.PropertiesDefinition();

    _records = [
        { id: 1, name: "Value 1", definitions: [] },
        { id: 2, name: "Value 2", definitions: [] },
        { id: 3, name: "Value 3", definitions: [] },
    ];
}

class Currency extends models.Model {
    _name = "res.currency";

    name = fields.Char();
    symbol = fields.Char();
    position = fields.Selection({
        selection: [
            ["after", "A"],
            ["before", "B"],
        ],
    });

    _records = [
        { id: 1, name: "USD", symbol: "$", position: "before" },
        { id: 2, name: "EUR", symbol: "€", position: "after" },
    ];
}

defineModels([Foo, Bar, Currency, ResCompany, ResPartner, ResUsers]);

test(`simple readonly list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="int_field"/></list>`,
    });

    // 3 th (1 for checkbox, 2 for columns)
    expect(`th`).toHaveCount(3, { message: "should have 3 columns" });
    expect(`td:contains(gnap)`).toHaveCount(1, { message: "should contain gnap" });
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });
    expect(`th.o_column_sortable`).toHaveCount(2, { message: "should have 2 sortable column" });
    expect(`thead th:eq(2) .o_list_number_th`).toHaveCount(1, {
        message: "header cells of integer fields should have o_list_number_th class",
    });
    expect(`tbody tr:eq(0) td:eq(2)`).toHaveStyle(
        { "text-align": "right" },
        { message: "integer cells should be right aligned" }
    );
    expect(`.o_list_button_add`).toBeVisible();
    expect(`.o_list_button_save`).not.toBeVisible();
    expect(`.o_list_button_discard`).not.toBeVisible();
});

test(`select record range with shift click`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="int_field"/></list>`,
    });
    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("1\nselected");
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(1);

    // shift click the 4th record to have 0-1-2-3 toggled
    await contains(`.o_data_row .o_list_record_selector input:eq(3)`).click({ shiftKey: true });
    expect(`.o_list_selection_box`).toHaveText("4\nselected");
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(4);

    // shift click the 3rd record to untoggle 2-3
    await contains(`.o_data_row .o_list_record_selector input:eq(2)`).click({ shiftKey: true });
    expect(`.o_list_selection_box`).toHaveText("2\nselected");
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(2);

    // shift click the 1st record to untoggle 0-1
    await contains(`.o_data_row .o_list_record_selector input:eq(0)`).click({ shiftKey: true });
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0);
});

test(`select record range with shift+space`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="int_field"/></list>`,
    });

    // Go to the first checkbox and check it
    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeFocused();

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeChecked();

    // Go to the fourth checkbox and shift+space
    await press("ArrowDown");
    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).toBeFocused();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).not.toBeChecked();

    await press(["shift", "space"]);
    await animationFrame();
    // focus is on the input and not in the td cell
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).toBeFocused();

    // Check that all checkbox is checked
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(1) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(2) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).toBeChecked();
});

test(`expand range of checkbox with shift+arrow`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="int_field"/></list>`,
    });

    // Go to the first checkbox and check it
    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeFocused();

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeChecked();

    // expand the checkbox with arrowdown
    await press(["shift", "ArrowDown"]);
    await press(["shift", "ArrowDown"]);
    await press(["shift", "ArrowDown"]);
    await press(["shift", "ArrowUp"]);
    await animationFrame();
    expect(`.o_data_row:eq(2) .o_list_record_selector input`).toBeFocused();
    expect(`.o_data_row:eq(2) .o_list_record_selector input`).toBeChecked();

    // Check that the three checkbox are checked
    expect(`.o_data_row:eq(1) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(2) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).toBeChecked();
});

test(`multiple interactions to change the range of checked boxes`, async () => {
    for (let i = 0; i < 5; i++) {
        Foo._records.push({ id: 5 + i, bar: true, foo: "foo" + i });
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="int_field"/></list>`,
    });

    await press("down");
    await animationFrame();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).not.toBeFocused();

    await keyDown("shift");
    await press("down");
    await animationFrame();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeFocused();

    await press("down");
    await press("down");
    await press("down");
    await press("up");
    await keyUp("shift");
    await press("down");
    await press("down");
    await press(["shift", "down"]);
    await animationFrame();

    await contains(`.o_data_row:eq(7) .o_list_record_selector .o-checkbox`).click();
    await press(["shift", "down"]);
    await animationFrame();

    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(1) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(2) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).not.toBeChecked();
    expect(`.o_data_row:eq(4) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(5) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(6) .o_list_record_selector input`).not.toBeChecked();
    expect(`.o_data_row:eq(7) .o_list_record_selector input`).toBeChecked();
    expect(`.o_data_row:eq(8) .o_list_record_selector input`).toBeChecked();
});

test(`list with class and style attributes`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list class="myClass" style="border: 1px solid red;">
                <field name="foo"/>
            </list>
        `,
    });
    expect(
        `.o_view_controller[style*='border: 1px solid red;'], .o_view_controller [style*='border: 1px solid red;']`
    ).toHaveCount(0, { message: "style attribute should not be copied" });
    expect(`.o_view_controller.o_list_view.myClass`).toHaveCount(1, {
        message: "class attribute should be passed to the view controller",
    });
    expect(`.myClass`).toHaveCount(1, {
        message: "class attribute should ONLY be passed to the view controller",
    });
});

test(`list with integer field with human_readable option`, async () => {
    Foo._records[0].int_field = 5 * 1000 * 1000;
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="int_field" options="{'human_readable': true}"/>
            </list>`,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["5M", "9", "17", "-4"]);
    expect(".o_field_widget").toHaveCount(0);
});

test(`list with create="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list create="0"><field name="foo"/></list>`,
    });
    expect(`.o_list_button_add`).toHaveCount(0, { message: "should not have the 'Create' button" });
});

test(`searchbar in listview doesn't take focus after unselected all items`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
    });
    expect(`.o_searchview_input`).toBeFocused({
        message: "The search input should be have the focus",
    });

    await contains(`tbody .o_data_row:eq(0) input[type="checkbox"]`).click();
    await contains(`tbody input[type="checkbox"]:checked`).click();
    expect(`.o_searchview_input`).not.toBeFocused({
        message: "The search input shouldn't have the focus",
    });
});

test(`basic list view and command palette`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
    });

    await press(["control", "k"]);
    await animationFrame();
    expect(queryAllTexts(`.o_command_hotkey`)).toEqual([
        "New\nALT + C",
        "Actions\nALT + U",
        "Search...\nALT + Q",
        "Toggle search panel\nALT + SHIFT + Q",
    ]);
});

test(`list with delete="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list delete="0"><field name="foo"/></list>`,
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`tbody td.o_list_record_selector`).toHaveCount(4, { message: "should have 4 records" });

    await contains(`tbody td.o_list_record_selector input`).click();
    expect(`.o-dropdown--menu`).toHaveCount(0);
});

test(`editable list with edit="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" edit="0"><field name="foo"/></list>`,
        selectRecord(resId, options) {
            expect.step(`switch to form - resId: ${resId} activeIds: ${options.activeIds}`);
        },
    });
    expect(`tbody td.o_list_record_selector`).toHaveCount(4);

    await contains(`.o_data_cell`).click();
    expect(`tbody tr.o_selected_row`).toHaveCount(0, { message: "should not have editable row" });
    expect.verifySteps(["switch to form - resId: 1 activeIds: 1,2,3,4"]);
});

test(`non-editable list with open_form_view`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list open_form_view="1"><field name="foo"/></list>`,
    });
    expect(".o_optional_columns_dropdown").toHaveCount(0);
    expect(`td.o_list_record_open_form_view`).toHaveCount(0, {
        message: "button to open form view should not be present on non-editable list",
    });
});

test(`editable list with open_form_view not set`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    expect(`td.o_list_record_open_form_view`).toHaveCount(0, {
        message: "button to open form view should not be present",
    });
});

test(`editable list with open_form_view`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" open_form_view="1"><field name="foo"/></list>`,
        selectRecord(resId, options) {
            expect.step(`switch to form - resId: ${resId} activeIds: ${options.activeIds}`);
        },
    });
    expect(".o_optional_columns_dropdown").toHaveCount(0);
    expect(`td.o_list_record_open_form_view`).toHaveCount(4, {
        message: "button to open form view should be present on each rows",
    });

    await contains(`td.o_list_record_open_form_view`).click();
    expect.verifySteps(["switch to form - resId: 1 activeIds: 1,2,3,4"]);
});

test(`editable list with open_form_view in debug`, async () => {
    serverState.debug = true;
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" open_form_view="1"><field name="foo"/></list>`,
    });
    expect(".o_optional_columns_dropdown").toHaveCount(0);
    expect(`td.o_list_record_open_form_view`).toHaveCount(4, {
        message: "button to open form view should be present on each rows",
    });
});

test(`editable list without open_form_view in debug`, async () => {
    patchWithCleanup(localStorage, {
        getItem(key) {
            const value = super.getItem(...arguments);
            if (key.startsWith("debug_open_view")) {
                expect.step(["getItem", key, value]);
            }
            return value;
        },
        setItem(key, value) {
            if (key.startsWith("debug_open_view")) {
                expect.step(["setItem", key, value]);
            }
            super.setItem(...arguments);
        },
    });
    serverState.debug = true;
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
        selectRecord(resId, options) {
            expect.step(`switch to form - resId: ${resId} activeIds: ${options.activeIds}`);
        },
    });
    const localStorageKey = "debug_open_view,foo,list,123456789,foo";
    expect.verifySteps([["getItem", localStorageKey, null]]);
    expect(`td.o_list_record_open_form_view`).toHaveCount(0);
    expect(".o_optional_columns_dropdown").toHaveCount(1);
    await contains(".o_optional_columns_dropdown button").click();
    expect(".o-dropdown-item:contains('View Button')").toHaveCount(1);
    await contains(".o-dropdown-item:contains('View Button')").click();
    expect.verifySteps([
        ["setItem", localStorageKey, true],
        ["getItem", localStorageKey, "true"],
    ]);

    expect(`td.o_list_record_open_form_view`).toHaveCount(4, {
        message: "button to open form view should be present on each rows",
    });

    await contains(`td.o_list_record_open_form_view`).click();
    expect.verifySteps(["switch to form - resId: 1 activeIds: 1,2,3,4"]);

    await contains(".o_optional_columns_dropdown button").click();
    await contains(".o-dropdown-item:contains('View Button')").click();
    expect.verifySteps([
        ["setItem", localStorageKey, false],
        ["getItem", localStorageKey, "false"],
    ]);
    expect(`td.o_list_record_open_form_view`).toHaveCount(0, {
        message: "button to open form view should no longer be present",
    });
});

test(`non-editable list in debug`, async () => {
    serverState.debug = true;
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
    });
    expect(".o_optional_columns_dropdown").toHaveCount(0);
});

test(`editable readonly list with open_form_view`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });
    Foo._records.push({ id: 5, bar: true, foo: "xxx" }, { id: 6, bar: true, foo: "yyy" });
    Foo._records[0].foo_o2m = [5, 6];

    await mountView({
        resModel: "foo",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <field name="foo_o2m" readonly="1">
                        <list editable="top" open_form_view="1">
                            <field name="foo"/>
                            <field name="bar"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
    });
    expect(`td.o_list_record_open_form_view`).toHaveCount(2, {
        message: "button to open form view should be present on each rows",
    });
});

test(`export feature in list for users not in base.group_allow_export`, async () => {
    onRpc("has_group", ({ args }) => args[1] !== "base.group_allow_export");
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(4);
    expect(`div.o_control_panel .o_cp_buttons .o_list_export_xlsx`).toHaveCount(0);

    await contains(`tbody td.o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts(`.o-dropdown--menu .o_menu_item`)).toEqual(["Duplicate", "Delete"], {
        message: "action menu should not contain the Export button",
    });
});

test(`list with export button`, async () => {
    onRpc("has_group", ({ args }) => args[1] === "base.group_allow_export");
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`tbody td.o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts(`.o-dropdown--menu .o_menu_item`)).toEqual(
        ["Export", "Duplicate", "Delete"],
        { message: "action menu should have Export button" }
    );
});

test(`Direct export button invisible`, async () => {
    onRpc("has_group", ({ args }) => args[1] === "base.group_allow_export");
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list export_xlsx="0"><field name="foo"/></list>`,
    });
    expect(`.o_list_export_xlsx`).toHaveCount(0);
});

test(`list view with adjacent buttons`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <button name="a" type="object" icon="fa-car"/>
                <field name="foo"/>
                <button name="x" type="object" icon="fa-star"/>
                <button name="y" type="object" icon="fa-refresh"/>
                <button name="z" type="object" icon="fa-exclamation"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(4, {
        message: "adjacent buttons in the arch must be grouped in a single column",
    });
    expect(`.o_data_row:eq(0) td.o_list_button`).toHaveCount(2);
});

test(`list view with adjacent buttons and invisible field and button`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <button name="a" type="object" icon="fa-car"/>
                <field name="foo" column_invisible="1"/>
                <!--Here the column_invisible=1 is used to simulate a group on the case that the user
                    don't have the rights to see the button.-->
                <button name="b" type="object" icon="fa-car" column_invisible="1"/>
                <button name="x" type="object" icon="fa-star"/>
                <button name="y" type="object" icon="fa-refresh"/>
                <button name="z" type="object" icon="fa-exclamation"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(3, {
        message: "adjacent buttons in the arch must be grouped in a single column",
    });
    expect(`tr:first-child button`).toHaveCount(4, { message: "Only 4 buttons should be visible" });
    expect(`.o_data_row:first-child td.o_list_button`).toHaveCount(2);
});

test(`list view with adjacent buttons and invisible field (modifier)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <button name="a" type="object" icon="fa-car"/>
                <field name="foo" invisible="foo == 'blip'"/>
                <button name="x" type="object" icon="fa-star"/>
                <button name="y" type="object" icon="fa-refresh"/>
                <button name="z" type="object" icon="fa-exclamation"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(4, {
        message: "adjacent buttons in the arch must be grouped in a single column",
    });
    expect(`.o_data_row:eq(0) td.o_list_button`).toHaveCount(2);
});

test(`list view with adjacent buttons and optional field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <button name="a" type="object" icon="fa-car"/>
                <field name="foo" optional="hide"/>
                <button name="x" type="object" icon="fa-star"/>
                <button name="y" type="object" icon="fa-refresh"/>
                <button name="z" type="object" icon="fa-exclamation"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(4, {
        message: "adjacent buttons in the arch must be grouped in a single column",
    });
    expect(`.o_data_row:eq(0) td.o_list_button`).toHaveCount(2);
});

test(`list view with adjacent buttons with invisible modifier`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <button name="x" type="object" icon="fa-star" invisible="foo == 'blip'"/>
                <button name="y" type="object" icon="fa-refresh" invisible="foo == 'yop'"/>
                <button name="z" type="object" icon="fa-exclamation" invisible="foo == 'gnap'"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(3, {
        message: "adjacent buttons in the arch must be grouped in a single column",
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_data_row td.o_list_button`).toHaveCount(4);
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "", "blip", "", "gnap", "", "blip", ""]);
    expect(`td button i.fa-star`).toHaveCount(2);
    expect(`td button i.fa-refresh`).toHaveCount(3);
    expect(`td button i.fa-exclamation`).toHaveCount(3);
});

test(`list view with adjacent buttons with width attribute`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <button icon="fa-play"/>
                <button icon="fa-heart" width="25px"/>
                <button icon="fa-cog"/>
                <button icon="fa-list"/>
            </list>
        `,
    });
    expect(`th:not(.o_list_record_selector)`).toHaveCount(4, {
        message: "adjacent buttons with no width in the arch must be grouped in a single column",
    });
    expect(".o_data_row td:not(.o_list_record_selector):nth-child(3) .fa-play").toHaveCount(4);
    expect(".o_data_row td:not(.o_list_record_selector):nth-child(4) .fa-heart").toHaveCount(4);
    expect(".o_data_row td:not(.o_list_record_selector):nth-child(5) .fa-cog").toHaveCount(4);
    expect(".o_data_row td:not(.o_list_record_selector):nth-child(5) .fa-list").toHaveCount(4);
});

test(`list view with icon buttons`, async () => {
    Foo._records.splice(1);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <button name="x" type="object" icon="fa-asterisk"/>
                <button name="x" type="object" icon="fa-star" class="o_yeah"/>
                <button name="x" type="object" icon="fa-refresh" string="Refresh" class="o_yeah"/>
                <button name="x" type="object" icon="fa-exclamation" string="Danger" class="o_yeah btn-danger"/>
            </list>
        `,
    });
    expect(`button.btn.btn-link i.fa.fa-asterisk`).toHaveCount(1);
    expect(`button.btn.btn-link.o_yeah i.fa.fa-star`).toHaveCount(1);
    expect(`button.btn.btn-link.o_yeah:contains(Refresh) i.fa.fa-refresh`).toHaveCount(1);
    expect(`button.btn.btn-danger.o_yeah:contains(Danger) i.fa.fa-exclamation`).toHaveCount(1);
    expect(`button.btn.btn-link.btn-danger`).toHaveCount(0);
});

test(`list view with disabled button`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <button name="a" icon="fa-coffee"/>
                <button name="b" icon="fa-car" disabled="disabled"/>
            </list>
        `,
    });
    expect(queryAll(`button[name='a']`).every((btn) => !btn.disabled)).toBe(true);
    expect(queryAll(`button[name='b']`).every((btn) => btn.disabled)).toBe(true);
});

test(`list view: action button in controlPanel basic rendering`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button name="x" type="object" class="plaf" string="plaf"/>
                    <button name="y" type="object" class="plouf" string="plouf" invisible="not context.get('bim')"/>
                </header>
                <field name="foo"/>
            </list>
        `,
    });
    expect(`.o_control_panel_actions button[name=x]`).toHaveCount(0);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);
    expect(`.o_control_panel_actions button[name="y"]`).toHaveCount(0);

    await contains(`.o_data_row .o_list_record_selector input[type="checkbox"]`).click();
    expect(`.o_control_panel_actions button[name=x]`).toHaveCount(1);
    expect(`.o_control_panel_actions button[name=x]`).toHaveClass("btn btn-secondary plaf");
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(queryFirst(`.o_control_panel_actions button[name=x]`).previousElementSibling).toBe(
        queryFirst(`.o_control_panel_actions .o_list_selection_box`)
    );
    expect(`.o_control_panel_actions button[name=y]`).toHaveCount(0);

    await contains(`.o_data_row .o_list_record_selector input[type="checkbox"]`).click();
    expect(`.o_control_panel_actions button[name=x]`).toHaveCount(0);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);
    expect(`.o_control_panel_actions button[name="y"]`).toHaveCount(0);
});

test(`list view: action button in controlPanel with display='always'`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button name="display" type="object" class="display" string="display" display="always"/>
                    <button name="display" type="object" class="display_invisible" string="invisible 1" display="always" invisible="1"/>
                    <button name="display" type="object" class="display_invisible" string="invisible context" display="always" invisible="context.get('a')"/>
                    <button name="default-selection" type="object" class="default-selection" string="default-selection"/>
                </header>
                <field name="foo"/>
            </list>
        `,
        context: {
            a: true,
        },
    });
    expect(
        queryAllTexts(`div.o_control_panel_breadcrumbs button, div.o_control_panel_actions button`)
    ).toEqual([
        "New",
        "display",
        "", // magnifying glass btn
        "", // cog dropdown
        "", // search btn
    ]);

    await contains(`.o_data_row .o_list_record_selector input[type="checkbox"]`).click();
    expect(
        queryAllTexts(`div.o_control_panel_breadcrumbs button, div.o_control_panel_actions button`)
    ).toEqual(["New", "display", "" /* unselect all btn */, "default-selection"]);

    await contains(`.o_data_row .o_list_record_selector input[type="checkbox"]`).click();
    expect(
        queryAllTexts(`div.o_control_panel_breadcrumbs button, div.o_control_panel_actions button`)
    ).toEqual([
        "New",
        "display",
        "", // magnifying glass btn
        "", // cog dropdown
        "", // search btn
    ]);
});

test(`list view: give a context dependent on the current context to a header button`, async () => {
    mockService("action", {
        doActionButton(action) {
            expect.step("doActionButton");
            expect(action.buttonContext).toEqual({
                active_domain: [],
                active_ids: [],
                active_model: "foo",
                b: "yop",
            });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button name="toDo" type="object" string="toDo" display="always" context="{'b': context.get('a')}"/>
                </header>
                <field name="foo"/>
            </list>
        `,
        context: {
            a: "yop",
        },
    });
    await contains(`button[name=toDo]`).click();
    expect.verifySteps(["doActionButton"]);
});

test(`list view: action button executes action on click: buttons are disabled and re-enabled`, async () => {
    const executeActionDef = new Deferred();
    mockService("action", {
        async doActionButton() {
            await executeActionDef;
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button name="x" type="object" class="plaf" string="plaf"/>
                </header>
                <field name="foo"/>
            </list>
        `,
    });
    await contains(`.o_data_row .o_list_record_selector input[type="checkbox"]`).click();
    const cpButtons = queryAll`div.o_control_panel_breadcrumbs button, div.o_control_panel_actions button`;
    expect(cpButtons.every((btn) => !btn.disabled)).toBe(true);

    await contains(`button[name=x]`).click();
    expect(cpButtons.every((btn) => btn.disabled)).toBe(true);

    executeActionDef.resolve();
    await animationFrame();
    expect(cpButtons.every((btn) => !btn.disabled)).toBe(true);
});

test(`list view: buttons handler is called once on double click`, async () => {
    const executeActionDef = new Deferred();
    mockService("action", {
        async doActionButton() {
            expect.step("execute_action");
            await executeActionDef;
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <button name="x" type="object" class="do_something" string="Do Something"/>
            </list>
        `,
    });
    await contains(`tbody .o_list_button button:eq(0)`).click();
    expect(`tbody .o_list_button button:eq(0)`).toHaveProperty("disabled", true);

    executeActionDef.resolve();
    await animationFrame();
    expect(`tbody .o_list_button button:eq(0)`).toHaveProperty("disabled", false);
    expect.verifySteps(["execute_action"]);
});

test(`list view: click on an action button saves the record before executing the action`, async () => {
    onRpc("/web/dataset/call_button/*", () => true);
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <button name="toDo" type="object" class="do_something" string="Do Something"/>
            </list>
        `,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_data_row [name='foo'] input`).edit("plop", { confirm: false });
    expect(`.o_data_row [name='foo'] input`).toHaveValue("plop");

    await contains(`.o_data_row button`).click();
    expect(queryFirst(`.o_data_row [name='foo']`)).toHaveText("plop");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        "web_save",
        "toDo",
        "web_search_read",
    ]);
});

test(`list view: action button executes action on click: correct parameters`, async () => {
    mockService("action", {
        async doActionButton(params) {
            expect.step("doActionButton");

            const { buttonContext, context, name, resModel, resIds, type } = params;
            // Action's own properties
            expect(name).toBe("x");
            expect(type).toBe("object");

            // The action's execution context
            expect(buttonContext).toEqual({
                active_domain: [],
                // active_id: 1, //FGE TODO
                active_ids: [1],
                active_model: "foo",
                plouf: "plif",
            });

            expect(resModel).toBe("foo");
            expect([...resIds]).toEqual([1]);
            expect(context).toEqual({
                lang: "en",
                paf: "pif",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
            });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                        <button name="x" type="object" class="plaf" string="plaf" context="{'plouf': 'plif'}"/>
                </header>
                <field name="foo"/>
            </list>
        `,
        context: {
            paf: "pif",
        },
    });
    await contains(`.o_data_row .o_list_record_selector input[type="checkbox"]`).click();
    await contains(`button[name=x]`).click();
    expect.verifySteps(["doActionButton"]);
});

test(`list view: action button executes action on click with domain selected: correct parameters`, async () => {
    mockService("action", {
        async doActionButton(params) {
            expect.step("doActionButton");

            const { buttonContext, context, name, resModel, resIds, type } = params;
            expect.step("execute_action");
            // Action's own properties
            expect(name).toBe("x");
            expect(type).toBe("object");

            // The action's execution context
            expect(buttonContext).toEqual({
                active_domain: [],
                // active_id: 1, // FGE TODO
                active_ids: [1, 2, 3, 4],
                active_model: "foo",
            });

            expect(context).toEqual({
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
            });
            expect(resModel).toBe("foo");
            expect(resIds).toEqual([1, 2, 3, 4]);
        },
    });

    onRpc("search", ({ args, model }) => {
        expect.step("search");
        expect(model).toBe("foo");
        expect(args).toEqual([[]]); // empty domain since no domain in searchView
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list limit="1">
                <header>
                        <button name="x" type="object" class="plaf" string="plaf"/>
                </header>
                <field name="foo"/>
            </list>
        `,
    });
    await contains(`.o_data_row .o_list_record_selector input[type="checkbox"]`).click();
    await contains(`.o_list_select_domain`).click();
    expect.verifySteps([]);

    await contains(`button[name="x"]`).click();
    expect.verifySteps(["search", "doActionButton", "execute_action"]);
});

test(`list view: press "hotkey" to execute header button action`, async () => {
    mockService("action", {
        doActionButton(params) {
            const { name } = params;
            expect.step(`execute_action: ${name}`);
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button name="toDo" type="object" string="toDo" display="always" data-hotkey="a"/>
                </header>
                <field name="foo"/>
            </list>
        `,
    });
    await press(["alt", "a"]);
    await tick();
    expect.verifySteps(["execute_action: toDo"]);
});

test(`column names (noLabel, label, string and default)`, async () => {
    const charField = registry.category("fields").get("char");

    class NoLabelCharField extends charField.component {}
    registry.category("fields").add("nolabel_char", {
        ...charField,
        component: NoLabelCharField,
        label: false,
    });

    class LabelCharField extends charField.component {}
    registry.category("fields").add("label_char", {
        ...charField,
        component: LabelCharField,
        label: "Some static label",
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="display_name" widget="nolabel_char" optional="show"/>
                <field name="foo" widget="label_char" optional="show"/>
                <field name="int_field" string="My custom label" optional="show"/>
                <field name="text" optional="show"/>
            </list>
        `,
    });
    expect(queryAllTexts(`thead th`)).toEqual([
        "",
        "",
        "Some static label",
        "My custom label",
        "Text",
        "",
    ]);

    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(queryAllTexts(`.o-dropdown--menu .dropdown-item`)).toEqual([
        "Display name",
        "Some static label",
        "My custom label",
        "Text",
    ]);
});

test(`simple editable rendering`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`th`).toHaveCount(3);
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);
    expect(`td:contains(yop)`).toHaveCount(1);
    expect(`.o_list_button_add`).toHaveCount(1);
    expect(`.o_list_button_save`).toHaveCount(0);
    expect(`.o_list_button_discard`).toHaveCount(0);

    await contains(`.o_field_cell`).click();
    expect(`.o_list_button_add`).toHaveCount(0);
    expect(`.o_list_button_save`).toHaveCount(1);
    expect(`.o_list_button_discard`).toHaveCount(1);
    expect(`.o_list_record_selector input:enabled`).toHaveCount(0);

    await contains(`.o_list_button_save`).click();
    expect(`.o_list_button_add`).toHaveCount(1);
    expect(`.o_list_button_save`).toHaveCount(0);
    expect(`.o_list_button_discard`).toHaveCount(0);
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);
});

test(`invisible columns are not displayed`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="bar" column_invisible="1"/>
            </list>
        `,
    });

    // 1 th for checkbox, 1 for 1 visible column
    expect(`th`).toHaveCount(2, { message: "should have 2 th" });
});

test(`invisible column based on the context are correctly displayed`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="date" column_invisible="True"/>
                <field name="foo" column_invisible="context.get('notInvisible')"/>
                <field name="bar" column_invisible="context.get('invisible')"/>
            </list>
        `,
        context: {
            invisible: true,
            notInvisible: false,
        },
    });

    // 1 th for checkbox, 1 for 1 visible column (foo)
    expect(`th`).toHaveCount(2, { message: "should have 2 th" });
    expect(`th:eq(1)`).toHaveAttribute("data-name", "foo");
});

test(`invisible column based on the context are correctly displayed in o2m`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="foo_o2m">
                        <list>
                            <field name="foo" column_invisible="context.get('notInvisible')"/>
                            <field name="bar" column_invisible="context.get('invisible')"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
        context: {
            invisible: true,
            notInvisible: false,
        },
    });

    // 1 for 1 visible column (foo), 1 th for delete button
    expect(`th`).toHaveCount(2, { message: "should have 2 th" });
    expect(`th:eq(0)`).toHaveAttribute("data-name", "foo");
});

test(`invisible column based on the parent are correctly displayed in o2m`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="int_field"/>
                    <field name="m2m" invisible="True"/>
                    <field name="properties" invisible="True"/>
                    <field name="foo_o2m">
                        <list>
                            <field name="date" column_invisible="True"/>
                            <field name="foo" column_invisible="parent.int_field == 3"/>
                            <field name="bar" column_invisible="parent.int_field == 10"/>
                            <field name="qux" column_invisible="parent.m2m"/>
                            <field name="amount" column_invisible="parent.properties"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    // 1 for 2 visible column (foo, properties), 1 th for delete button
    expect(`th`).toHaveCount(3, { message: "should have 3 th" });
    expect(`th:eq(0)`).toHaveAttribute("data-name", "foo");
    expect(`th:eq(1)`).toHaveAttribute("data-name", "amount");
});

test(`save a record with an invisible required field`, async () => {
    Foo._fields.foo = fields.Char({ required: true });

    stepAllNetworkCalls();
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ int_field: 1, foo: false });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo" column_invisible="1"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await contains(`.o_list_button_add`).click();
    await contains(`[name='int_field'] input`).edit("1", { confirm: false });
    await contains(`.o_list_view`).click();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(0) [name='int_field']`).toHaveText("1");
    expect.verifySteps(["onchange", "web_save"]);
});

test.todo(
    `multi_edit: edit a required field with invalid value and click 'Ok' of alert dialog`,
    async () => {
        Foo._fields.foo = fields.Char({ required: true });

        stepAllNetworkCalls();
        await mountView({
            resModel: "foo",
            type: "list",
            arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
        });
        expect(`.o_data_row`).toHaveCount(4);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "get_views",
            "web_search_read",
            "has_group",
        ]);

        await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
        await contains(`.o_data_row:eq(0) .o_data_cell[name='foo']`).click();
        await contains(`.o_field_widget[name=foo] input`).clear();
        expect(`.modal`).toHaveCount(1);
        expect(`.modal .btn`).toHaveText("Ok");

        await contains(`.modal .btn`).click();
        expect(`.o_data_row:eq(0) .o_data_cell[name='foo']`).toHaveText("yop");
        expect(`.o_data_row:eq(0)`).toHaveClass("o_data_row_selected");
        expect.verifySteps([]);
    }
);

test.todo(
    `multi_edit: edit a required field with invalid value and dismiss alert dialog`,
    async () => {
        Foo._fields.foo = fields.Char({ required: true });

        stepAllNetworkCalls();
        await mountView({
            resModel: "foo",
            type: "list",
            arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
        });
        expect(`.o_data_row`).toHaveCount(4);
        expect.verifySteps([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "get_views",
            "web_search_read",
            "has_group",
        ]);

        await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
        await contains(`.o_data_row:eq(0) .o_data_cell[name='foo']`).click();
        await contains(`.o_field_widget[name=foo] input`).clear();
        expect(`.modal`).toHaveCount(1);

        await contains(`.modal-header .btn-close`).click();
        expect(`.o_data_row:eq(0) .o_data_cell[name='foo']`).toHaveText("yop");
        expect(`.o_data_row:eq(0)`).toHaveClass("o_data_row_selected");
        expect.verifySteps([]);
    }
);

test(`multi_edit: clicking on a readonly field switches the focus to the next editable field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="int_field" readonly="1"/>
                <field name="foo"/>
            </list>
        `,
    });
    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) [name=int_field]`).click();
    expect(`.o_field_widget[name=foo] input`).toBeFocused();

    await contains(`.o_data_row:eq(0) [name=int_field]`).click();
    expect(`.o_field_widget[name=foo] input`).toBeFocused();
});

test(`save a record with an required field computed by another`, async () => {
    Foo._onChanges = {
        foo(record) {
            if (record.foo) {
                record.text = "plop";
            }
        },
    };

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="int_field"/>
                <field name="text" required="1"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`.o_list_button_add`).click();
    await contains(`[name='int_field'] input`).edit("1");
    await contains(`.o_list_view`).click();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_field_invalid`).toHaveCount(1);
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`[name=foo] input`).edit("hello");
    expect(`.o_field_invalid`).toHaveCount(0);
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_list_view`).click();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(0);
});

test(`field with nolabel has no title`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo" nolabel="1"/></list>`,
    });
    expect(`thead tr:eq(0) th:eq(1)`).toHaveText("");
});

test(`field titles are not escaped`, async () => {
    Foo._records[0].foo = "<div>Hello</div>";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
    });
    expect(`tbody tr:eq(0) .o_data_cell`).toHaveText("<div>Hello</div>");
    expect(`tbody tr:eq(0) .o_data_cell`).toHaveAttribute("data-tooltip", "<div>Hello</div>");
});

test(`record-depending invisible lines are correctly aligned`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="bar" invisible="id == 1"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_data_row td`).toHaveCount(16); // 4 cells per row
    expect(`.o_data_row td:eq(2)`).toHaveInnerHTML("");
});

test(`invisble fields must not have a tooltip`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo" invisible="id == 1"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_data_row td[data-tooltip]`).toHaveCount(3);
});

test(`do not perform extra RPC to read invisible many2one fields`, async () => {
    Foo._fields.m2o = fields.Many2one({ relation: "bar", default: 2 });

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="m2o" column_invisible="1"/>
            </list>
        `,
    });

    await contains(`.o_list_button_add`).click();
    // no nameget should be done
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        "onchange",
    ]);
});

test(`editable list datepicker destroy widget (edition)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="date"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_field_date input`).click();
    expect(`.o_datetime_picker`).toHaveCount(1);

    await press("Escape");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(4);
});

test(`editable list datepicker destroy widget (new line)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="date"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(4, { message: "There should be 4 rows" });

    await contains(`.o_list_button_add`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_field_date input`).click();
    expect(`.o_datetime_picker`).toHaveCount(1, { message: "datepicker should be opened" });

    await press("escape");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(0, { message: "the row is no longer in edition" });
    expect(`.o_data_row`).toHaveCount(4, { message: "There should still be 4 rows" });
});

test(`at least 4 rows are rendered, even if less data`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="bar"/></list>`,
        domain: [["bar", "=", true]],
    });
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });
});

test(`discard a new record in editable="top" list with less than 4 records`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="bar"/></list>`,
        domain: [["bar", "=", true]],
    });
    expect(`.o_data_row`).toHaveCount(3);
    expect(`tbody tr`).toHaveCount(4);

    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`tbody tr:eq(0)`).toHaveClass("o_selected_row");

    await contains(`.o_list_button_discard:not(.dropdown-item)`).click();
    expect(`.o_data_row`).toHaveCount(3);
    expect(`tbody tr`).toHaveCount(4);
    expect(`tbody tr:eq(0)`).toHaveClass("o_data_row");
});

test(`basic grouped list rendering`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
    });
    expect(`th:contains(Foo)`).toHaveCount(1, { message: "should contain Foo" });
    expect(`th:contains(Bar)`).toHaveCount(1, { message: "should contain Bar" });
    expect(`tr.o_group_header`).toHaveCount(2, { message: "should have 2 .o_group_header" });
    expect(`th.o_group_name`).toHaveCount(2, { message: "should have 2 .o_group_name" });
});

test(`basic grouped list rendering with widget="handle" col`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="int_field" widget="handle"/>
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`thead th`).toHaveCount(3); // record selector + Foo + Bar
    expect(`thead th.o_list_record_selector`).toHaveCount(1);
    expect(`thead th[data-name=foo]`).toHaveCount(1);
    expect(`thead th[data-name=bar]`).toHaveCount(1);
    expect(`thead th[data-name=int_field]`).toHaveCount(0);
    expect(`tr.o_group_header`).toHaveCount(2);
    expect(`th.o_group_name`).toHaveCount(2);
    expect(`.o_group_header:eq(0) th`).toHaveCount(2); // group name + colspan 2
    expect(`.o_group_header:eq(0) .o_list_number`).toHaveCount(0);
});

test(`basic grouped list rendering with a date field between two fields with a aggregator`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="int_field"/>
                <field name="date"/>
                <field name="int_field"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`thead th`).toHaveCount(4); // record selector + Foo + Int + Date + Int
    expect(`thead th.o_list_record_selector`).toHaveCount(1);
    expect(queryAllTexts(`thead th`)).toEqual(["", "Int field", "Date", "Int field"]);
    expect(`tr.o_group_header`).toHaveCount(2);
    expect(`th.o_group_name`).toHaveCount(2);
    expect(queryAllTexts(`.o_group_header:eq(0) td`)).toEqual(["-4", "", "-4"]);
});

test(`basic grouped list rendering 1 col without selector`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        groupBy: ["bar"],
        allowSelectors: false,
    });
    expect(`.o_group_header:eq(0) th`).toHaveCount(1);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "1");
});

test(`basic grouped list rendering 1 col with selector`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    expect(`.o_group_header:eq(0) th`).toHaveCount(1);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "2");
});

test(`basic grouped list rendering 2 cols without selector`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
        allowSelectors: false,
    });
    expect(`.o_group_header:eq(0) th`).toHaveCount(2);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "1");
});

test(`basic grouped list rendering 3 cols without selector`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/><field name="text"/></list>`,
        groupBy: ["bar"],
        allowSelectors: false,
    });
    expect(`.o_group_header:eq(0) th`).toHaveCount(2);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "2");
});

test(`basic grouped list rendering 2 col with selector`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
        allowSelectors: true,
    });
    expect(`.o_group_header:eq(0) th`).toHaveCount(2);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "2");
});

test(`basic grouped list rendering 3 cols with selector`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/><field name="text"/></list>`,
        groupBy: ["bar"],
        allowSelectors: true,
    });

    expect(`.o_group_header:eq(0) th`).toHaveCount(2);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "3");
});

test(`basic grouped list rendering 7 cols with aggregates and selector`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="datetime"/>
                <field name="foo"/>
                <field name="int_field" sum="Sum1"/>
                <field name="bar"/>
                <field name="qux" sum="Sum2"/>
                <field name="date"/>
                <field name="text"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_group_header:eq(0) th, .o_group_header:eq(0) td`).toHaveCount(5);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "3");
    expect(`.o_group_header:eq(0) td`).toHaveCount(3, {
        message: "there should be 3 tds (aggregates + fields in between)",
    });
    expect(`.o_group_header th:eq(-1)`).toHaveAttribute("colspan", "2", {
        message:
            "header last cell should span on the two last fields (to give space for the pager) (colspan 2)",
    });
});

test(`basic grouped list rendering 7 cols with aggregates, selector and optional`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="datetime"/>
                <field name="foo"/>
                <field name="int_field" sum="Sum1"/>
                <field name="bar"/>
                <field name="qux" sum="Sum2"/>
                <field name="date"/>
                <field name="text" optional="show"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_group_header:eq(0) th, .o_group_header:eq(0) td`).toHaveCount(5);
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "3");
    expect(`.o_group_header:eq(0) td`).toHaveCount(3, {
        message: "there should be 3 tds (aggregates + fields in between)",
    });
    expect(`.o_group_header th:eq(-1)`).toHaveAttribute("colspan", "3", {
        message:
            "header last cell should span on the two last fields (to give space for the pager) (colspan 2)",
    });
});

test(`basic grouped list rendering 4 cols with aggregates, selector and openFormView`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list open_form_view="True">
                <field name="datetime"/>
                <field name="int_field" sum="Sum1"/>
                <field name="bar"/>
                <field name="qux" sum="Sum2" optional="hide"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "2");
    expect(`.o_group_header th:eq(-1)`).toHaveAttribute("colspan", "2");
});

test(`basic grouped list rendering 4 cols with aggregates, selector, optional and openFormView`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list open_form_view="True">
                <field name="datetime"/>
                <field name="int_field" sum="Sum1"/>
                <field name="bar"/>
                <field name="qux" sum="Sum2" optional="show"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_group_header th:eq(0)`).toHaveAttribute("colspan", "2");
    expect(`.o_group_header th:eq(-1)`).toHaveAttribute("colspan", "1");
});

test(`group a list view with the aggregable field 'value'`, async () => {
    Foo._fields.value = fields.Integer();
    for (const record of Foo._records) {
        record.value = 1;
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="bar"/>
                <field name="value" sum="Sum1"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(queryAllTexts(`.o_group_header`)).toEqual(["No (1)\n 1", "Yes (3)\n 3"]);
});

test(`basic grouped list rendering with groupby m2m field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["m2m"],
    });
    expect(`.o_group_header`).toHaveCount(4, { message: "should contain 4 open groups" });
    expect(`.o_group_open`).toHaveCount(0, { message: "no group is open" });
    expect(queryAllTexts(`.o_group_header .o_group_name`)).toEqual([
        "Value 1 (3)",
        "Value 2 (2)",
        "Value 3 (1)",
        "None (1)",
    ]);

    // Open all groups
    await contains(`.o_group_name`).click();
    await contains(`.o_group_name:eq(1)`).click();
    await contains(`.o_group_name:eq(2)`).click();
    await contains(`.o_group_name:eq(3)`).click();
    expect(`.o_group_open`).toHaveCount(4, { message: "all groups are open" });
    expect(queryAllTexts(`.o_list_view tbody > tr`)).toEqual([
        "Value 1 (3)",
        "yop \nValue 1\nValue 2",
        "blip \nValue 1\nValue 2\nValue 3",
        "blip \nValue 1",
        "Value 2 (2)",
        "yop \nValue 1\nValue 2",
        "blip \nValue 1\nValue 2\nValue 3",
        "Value 3 (1)",
        "blip \nValue 1\nValue 2\nValue 3",
        "None (1)",
        "gnap",
    ]);
});

test(`grouped list rendering with groupby m2o and m2m field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2o"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["m2o", "m2m"],
    });
    expect(queryAllTexts(`tbody > tr`)).toEqual(["Value 1 (3)", "Value 2 (1)"]);

    await contains(`th.o_group_name`).click();
    expect(queryAllTexts(`tbody > tr`)).toEqual([
        "Value 1 (3)",
        "Value 1 (2)",
        "Value 2 (1)",
        "None (1)",
        "Value 2 (1)",
    ]);

    await contains(`tbody th.o_group_name:eq(4)`).click();
    expect(queryAllTexts(`.o_list_view tbody > tr`)).toEqual([
        "Value 1 (3)",
        "Value 1 (2)",
        "Value 2 (1)",
        "None (1)",
        "Value 2 (1)",
        "Value 1 (1)",
        "Value 2 (1)",
        "Value 3 (1)",
    ]);
});

test(`grouped list with (disabled) pager inside group`, async () => {
    let def;
    onRpc("web_search_read", () => def);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list limit="2">
                <field name="foo"/>
            </list>
        `,
        groupBy: ["m2o"],
    });

    expect(".o_group_header").toHaveCount(2);

    await contains(".o_group_header:first").click();

    expect(".o_data_row").toHaveCount(2);
    expect(".o_group_header .o_pager").toHaveCount(1);

    def = new Deferred();

    await click(".o_group_header .o_pager_next:enabled");
    await animationFrame();

    expect(".o_group_header .o_pager_next").toHaveAttribute("disabled");

    await click(".o_group_header .o_pager_next");
    await click(".o_group_header .o_pager_next");
    await animationFrame();

    expect(".o_data_row").toHaveCount(2);
});

test(`list view with multiple groupbys`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar", "foo"],
        noContentHelp: "<p>should not be displayed</p>",
    });
    expect(`.o_view_nocontent`).toHaveCount(0);
    expect(`.o_group_has_content`).toHaveCount(2);
    expect(queryAllTexts(`.o_group_has_content`)).toEqual(["No (1)", "Yes (3)"]);
});

test(`enabling archive in list when groupby m2m field`, async () => {
    onRpc("has_group", () => false);
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
    });
    await contains(`.o_group_name:eq(0)`).click(); // open group "Value 1"
    await contains(`.o_group_name:eq(1)`).click(); // open group "Value 2"
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(5, { message: "Checking initial number of records" });

    await contains(`.o_data_row .o_list_record_selector input`).click(); // select first task
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions
    // check that all the options are available
    expect(`.o-dropdown--menu .o_menu_item`).toHaveCount(4, {
        message: "archive, unarchive, duplicate and delete option should be present",
    });

    await toggleMenuItem("Archive"); // toggle archive action
    await contains(`.modal-footer .btn-primary`).click(); // confirm the archive action
    // check that after archive the record is removed from both 2nd and 3rd groups
    expect(`.o_data_row`).toHaveCount(3, {
        message: "record should be archived from both the groups",
    });
});

test(`enabling archive in list when groupby m2m field and multi selecting the same record`, async () => {
    onRpc("has_group", () => false);
    onRpc("action_archive", ({ args }) => {
        expect.step("action_archive");
        expect(args[0]).toEqual([1], {
            message: "the archive action rpc should only contain unique ids in arguments",
        });
    });
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
    });
    await contains(`.o_group_name:eq(0)`).click(); // open group "Value 1"
    await contains(`.o_group_name:eq(1)`).click(); // open group "Value 2"
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(5, { message: "Checking initial number of records" });

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click(); // select first record
    await contains(`.o_data_row:eq(3) .o_list_record_selector input`).click(); // select the same record in another group
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions

    await toggleMenuItem("Archive"); // toggle archive action
    await contains(`.modal-footer .btn-primary`).click(); // confirm the archive action
    // check that after archive the record is removed from both 2nd and 3rd groups
    expect(`.o_data_row`).toHaveCount(3, {
        message: "record should be archived from both the groups",
    });
    expect.verifySteps(["action_archive"]);
});

test(`enabling duplicate in list when groupby m2m field`, async () => {
    onRpc("has_group", () => false);
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
    });
    await contains(`.o_group_name:eq(0)`).click(); // open group "Value 1"
    await contains(`.o_group_name:eq(1)`).click(); // open group "Value 2"
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(5, { message: "Checking initial number of records" });

    await contains(`.o_data_row .o_list_record_selector input`).click(); // select first task
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions
    // check that all the options are available
    expect(`.o-dropdown--menu .o_menu_item`).toHaveCount(4, {
        message: "archive, unarchive, duplicate and delete option should be present",
    });

    await toggleMenuItem("Duplicate"); // toggle duplicate action
    // check that after duplicate the record is duplicated in both 2nd and 3rd groups
    expect(`.o_data_row`).toHaveCount(7, {
        message: "record should be duplicated in both the groups",
    });
});

test(`enabling duplicate in list when groupby m2m field and multi selecting the same record`, async () => {
    onRpc("has_group", () => false);
    onRpc("copy", ({ args }) => {
        expect.step("copy");
        expect(args[0]).toEqual([1], {
            message: "the copy rpc should only contain unique ids in arguments",
        });
    });
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
    });
    await contains(`.o_group_name:eq(0)`).click(); // open group "Value 1"
    await contains(`.o_group_name:eq(1)`).click(); // open group "Value 2"
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(5, { message: "Checking initial number of records" });

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click(); // select first record
    await contains(`.o_data_row:eq(3) .o_list_record_selector input`).click(); // select the same record in another group
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions

    await toggleMenuItem("Duplicate"); // toggle duplicate action
    // check that after duplicate the record is duplicated in both 2nd and 3rd groups
    expect(`.o_data_row`).toHaveCount(7, {
        message: "record should be duplicated in both the groups",
    });
    expect.verifySteps(["copy"]);
});

test(`enabling delete in list when groupby m2m field`, async () => {
    onRpc("has_group", () => false);
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
    });
    await contains(`.o_group_name:eq(0)`).click(); // open group "Value 1"
    await contains(`.o_group_name:eq(1)`).click(); // open group "Value 2"
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(5, { message: "Checking initial number of records" });

    await contains(`.o_data_row .o_list_record_selector input`).click(); // select first task
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions
    // check that all the options are available
    expect(`.o-dropdown--menu .o_menu_item`).toHaveCount(4, {
        message: "archive, unarchive, duplicate and delete option should be present",
    });

    await toggleMenuItem("Delete"); // toggle delete action
    await contains(`.modal-footer .btn-primary`).click(); // confirm the delete action
    // check that after delete the record is deleted in both 2nd and 3rd groups
    expect(`.o_data_row`).toHaveCount(3, {
        message: "record should be deleted from both the groups",
    });
});

test(`enabling delete in list when groupby m2m field and multi selecting the same record`, async () => {
    onRpc("has_group", () => false);
    onRpc("unlink", ({ args }) => {
        expect.step("unlink");
        expect(args[0]).toEqual([1], {
            message: "the unlink rpc should only contain unique ids in arguments",
        });
    });
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
    });
    await contains(`.o_group_name:eq(0)`).click(); // open group "Value 1"
    await contains(`.o_group_name:eq(1)`).click(); // open group "Value 2"
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(5, { message: "Checking initial number of records" });

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click(); // select first record
    await contains(`.o_data_row:eq(3) .o_list_record_selector input`).click(); // select the same record in another group
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions

    await toggleMenuItem("Delete"); // toggle delete action
    await contains(`.modal-footer .btn-primary`).click(); // confirm the delete action
    // check that after delete the record is deleted in both 2nd and 3rd groups
    expect(`.o_data_row`).toHaveCount(3, {
        message: "record should be deleted from both the groups",
    });
    expect.verifySteps(["unlink"]);
});

test(`enabling unarchive in list when groupby m2m field`, async () => {
    onRpc("has_group", () => false);
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });
    // creating archived records
    Foo._records = [
        { id: 1, foo: "First record", m2m: [1, 2], active: false },
        { id: 2, foo: "Second record", m2m: [1, 2], active: false },
    ];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
        // apply the filter to show only records with active = false
        domain: [["active", "=", false]],
    });

    await contains(`.o_group_name:eq(0)`).click(); // open first group
    await contains(`.o_group_name:eq(1)`).click(); // open second group
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(4, { message: "Checking initial number of records" });

    await contains(`.o_data_row .o_list_record_selector input`).click(); // select first task
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions
    // check that all the options are available
    expect(`.o-dropdown--menu .o_menu_item`).toHaveCount(4, {
        message: "archive, unarchive, duplicate and delete option should be present",
    });

    await toggleMenuItem("Unarchive"); // toggle unarchive action
    // check that after unarchive the record is unarchived in both 1st and 2nd groups
    expect(`.o_data_row`).toHaveCount(2, {
        message: "record should be unarchived from both the groups",
    });
});

test(`enabling unarchive in list when groupby m2m field and multi selecting the same record`, async () => {
    onRpc("has_group", () => false);
    onRpc("action_unarchive", ({ args }) => {
        expect.step("action_unarchive");
        expect(args[0]).toEqual([1], {
            message: "the unarchive action rpc should only contain unique ids in arguments",
        });
    });
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });
    // creating archived records
    Foo._records = [
        { id: 1, foo: "First record", m2m: [1, 2], active: false },
        { id: 2, foo: "Second record", m2m: [1, 2], active: false },
    ];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        actionMenus: {},
        groupBy: ["m2m"],
        // apply the filter to show only records with active = false
        domain: [["active", "=", false]],
    });

    await contains(`.o_group_name:eq(0)`).click(); // open first group
    await contains(`.o_group_name:eq(1)`).click(); // open second group
    // Check for the initial number of records
    expect(`.o_data_row`).toHaveCount(4, { message: "Checking initial number of records" });

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click(); // select first record
    await contains(`.o_data_row:eq(2) .o_list_record_selector input`).click(); // select the same record in another group
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click(); // click on actions

    await toggleMenuItem("Unarchive"); // toggle unarchive action
    // check that after unarchive the record is unarchived in both 1st and 2nd groups
    expect(`.o_data_row`).toHaveCount(2, {
        message: "record should be unarchived from both the groups",
    });
    expect.verifySteps(["action_unarchive"]);
});

test(`add record in list grouped by m2m`, async () => {
    onRpc("onchange", ({ kwargs }) => {
        expect.step("onchange");
        expect(kwargs.context.default_m2m).toEqual([1]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["m2m"],
    });

    expect(`.o_group_header`).toHaveCount(4);
    expect(queryAllTexts(`.o_group_header`)).toEqual([
        "Value 1 (3)",
        "Value 2 (2)",
        "Value 3 (1)",
        "None (1)",
    ]);

    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(3);

    await contains(`.o_group_field_row_add a`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_selected_row .o_field_tags .o_tag`).toHaveCount(1);
    expect(`.o_selected_row .o_field_tags .o_tag`).toHaveText("Value 1");
    expect.verifySteps(["onchange"]);
});

test(`editing a record should change same record in other groups when grouped by m2m field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["m2m"],
    });
    await contains(`.o_group_header`).click(); // open Value 1 group
    await contains(`.o_group_header:eq(1)`).click(); // open Value 2 group
    expect(queryAllTexts(`.o_list_char`)).toEqual(["yop", "blip", "blip", "yop", "blip"]);

    await contains(`.o_data_row .o_list_record_selector input`).click();
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_data_row .o_list_char input`).edit("xyz");
    await contains(`.o_list_view`).click();
    expect(queryAllTexts(`.o_list_char`)).toEqual(["xyz", "blip", "blip", "xyz", "blip"]);
});

test(`selecting the same record on different groups and editing it when grouping by m2m field`, async () => {
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[0]).toEqual([1], {
            message: "the write rpc should only contain unique ids in arguments",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["m2m"],
    });

    await contains(`.o_group_header`).click(); // open Value 1 group
    await contains(`.o_group_header:eq(1)`).click(); // open Value 2 group
    expect(queryAllTexts(`.o_list_char`)).toEqual(["yop", "blip", "blip", "yop", "blip"]);

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click(); // select first record
    await contains(`.o_data_row:eq(3) .o_list_record_selector input`).click(); // select the same record in another group
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_data_row .o_list_char input`).edit("xyz");
    await contains(`.o_list_view`).click();
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .modal-footer .btn-primary`).click();
    expect(`.modal`).toHaveCount(0);
    expect(queryAllTexts(`.o_list_char`)).toEqual(["xyz", "blip", "blip", "xyz", "blip"]);
    expect.verifySteps(["write"]);
});

test(`change a record field in readonly should change same record in other groups when grouped by m2m field`, async () => {
    Foo._fields.priority = fields.Selection({
        selection: [
            [0, "Not Prioritary"],
            [1, "Prioritary"],
        ],
        default: 0,
    });

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[0]).toEqual([1], { message: "should write on the correct record" });
        expect(args[1]).toEqual({
            priority: 1,
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="priority" widget="priority"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["m2m"],
        domain: [["m2o", "=", 1]],
    });
    await contains(`.o_group_header`).click(); // open Value 1 group
    await contains(`.o_group_header:eq(1)`).click(); // open Value 2 group
    expect(queryAllTexts(`.o_list_char`)).toEqual(["yop", "blip", "yop"]);
    expect(`.o_priority_star.fa-star`).toHaveCount(0, {
        message: "should not have any starred records",
    });

    await contains(`.o_priority_star`).click();
    expect(`.o_priority_star.fa-star`).toHaveCount(2, {
        message: "both 'yop' records should have been starred",
    });
    expect.verifySteps(["web_save"]);
});

test(`ordered target, sort attribute in context`, async () => {
    onRpc("create_or_replace", ({ args }) => {
        const favorite = args[0];
        expect.step(favorite.sort);
        return 7;
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="date"/></list>`,
    });

    // Descending order on Foo
    await contains(`th.o_column_sortable[data-name=foo]`).click();
    await contains(`th.o_column_sortable[data-name=foo]`).click();

    // Ascending order on Date
    await contains(`th.o_column_sortable[data-name=date]`).click();
    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("My favorite");
    await saveFavorite();
    expect.verifySteps([`["date","foo desc"]`]);
});

test(`Loading a filter with a sort attribute`, async () => {
    Foo._filters = [
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
    ];

    onRpc("web_search_read", ({ kwargs }) => expect.step(kwargs.order));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="date"/>
            </list>
        `,
        loadIrFilters: true,
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("My second favorite");
    expect.verifySteps(["date ASC, foo DESC", "date DESC, foo ASC"]);
});

test(`many2one field rendering`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="m2o"/></list>`,
    });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["Value 1", "Value 2", "Value 1", "Value 1"]);
});

test(`many2one field rendering with many2one widget`, async () => {
    Bar._records[0].name = false;
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="m2o" widget="many2one"/></list>`,
    });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["Unnamed", "Value 2", "Unnamed", "Unnamed"]);
});

test(`many2one field rendering when display_name is falsy`, async () => {
    Bar._records[0].name = false;

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="m2o"/></list>`,
    });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["Unnamed", "Value 2", "Unnamed", "Unnamed"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test(`grouped list view, with 1 open group`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="int_field"/></list>`,
        groupBy: ["foo"],
    });
    expect(`tr.o_group_header`).toHaveCount(3);
    expect(`tr.o_data_row`).toHaveCount(0);

    await contains(`th.o_group_name`).click();
    expect(`tr.o_group_header`).toHaveCount(3);
    expect(`tr.o_data_row`).toHaveCount(2);
    expect(`td:contains(9)`).toHaveCount(1, { message: "should contain 9" });
    expect(`td:contains(-4)`).toHaveCount(1, { message: "should contain -4" });
    expect(`td:contains(10)`).toHaveCount(1, { message: "should contain 10" }); // FIXME: missing aggregates
    expect(`tr.o_group_header td:contains(10)`).toHaveCount(1, {
        message: "but 10 should be in a header",
    });
});

test(`opening records when clicking on record`, async () => {
    const listView = registry.category("views").get("list");
    class CustomListController extends listView.Controller {
        openRecord(record) {
            expect.step("openRecord");
            expect(record.resId).toBe(2);
        }
    }
    registry.category("views").add("custom_list", {
        ...listView,
        Controller: CustomListController,
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="custom_list"><field name="foo"/></list>`,
    });
    await contains(`tr:nth-child(2) td:not(.o_list_record_selector)`).click();
    await selectGroup("foo");
    expect(`tr.o_group_header`).toHaveCount(3, { message: "list should be grouped" });

    await contains(`th.o_group_name`).click();
    await contains(`tr:not(.o_group_header) td:not(.o_list_record_selector)`).click();
    expect.verifySteps(["openRecord", "openRecord"]);
});

test(`execute an action before and after each valid save in a list view`, async () => {
    const listView = registry.category("views").get("list");
    class CustomListController extends listView.Controller {
        async onRecordSaved(record) {
            expect.step(`onRecordSaved ${record.resId}`);
        }

        async onWillSaveRecord(record) {
            expect.step(`onWillSaveRecord ${record.resId}`);
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

    onRpc("web_save", ({ args }) => expect.step(`web_save ${args[0]}`));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="custom_list" editable="top"><field name="foo" required="1"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    await contains(`[name=foo] input`).edit("");
    await contains(`.o_list_view`).click();
    expect.verifySteps([]);

    await contains(`[name=foo] input`).edit("YOLO");
    await contains(`.o_list_view`).click();
    expect.verifySteps(["onWillSaveRecord 1", "web_save 1", "onRecordSaved 1"]);
});

test(`execute an action before and after each valid save in a grouped list view`, async () => {
    const listView = registry.category("views").get("list");
    class CustomListController extends listView.Controller {
        async onRecordSaved(record) {
            expect.step(`onRecordSaved ${record.resId}`);
        }

        async onWillSaveRecord(record) {
            expect.step(`onWillSaveRecord ${record.resId}`);
        }
    }
    registry.category("views").add("custom_list", {
        ...listView,
        Controller: CustomListController,
    });

    onRpc("web_save", ({ args }) => expect.step(`web_save ${args[0]}`));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="custom_list" editable="top" expand="1"><field name="foo" required="1"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_data_cell[name='foo']`).click();
    await contains(`[name=foo] input`).edit("");
    await contains(`.o_list_view`).click();
    expect.verifySteps([]);

    await contains(`[name=foo] input`).edit("YOLO");
    await contains(`.o_list_view`).click();
    expect.verifySteps(["onWillSaveRecord 4", "web_save 4", "onRecordSaved 4"]);
});

test(`don't exec a valid save with onWillSaveRecord in a list view`, async () => {
    const listView = registry.category("views").get("list");
    class ListViewCustom extends listView.Controller {
        async onRecordSaved(record) {
            throw new Error("should not execute onRecordSaved");
        }

        async onWillSaveRecord(record) {
            expect.step(`onWillSaveRecord ${record.resId}`);
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

    onRpc("web_save", () => {
        throw new Error("should not save the record");
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo" required="1"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    await contains(`[name=foo] input`).edit("");
    await contains(`.o_list_view`).click();
    expect.verifySteps([]);

    await contains(`.o_data_cell`).click();
    await contains(`[name=foo] input`).edit("YOLO", { confirm: false });
    await contains(`.o_list_view`).click();
    expect.verifySteps(["onWillSaveRecord 1"]);
});

test(`action/type attributes on tree arch, type='object'`, async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step(`doActionButton type ${params.type} name ${params.name}`);
            params.onClose();
        },
    });

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list action="a1" type="object"><field name="foo"/></list>`,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await contains(`.o_data_cell`).click();
    expect.verifySteps(["doActionButton type object name a1", "web_search_read"]);
});

test(`action/type attributes on tree arch, type='action'`, async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step(`doActionButton type ${params.type} name ${params.name}`);
            params.onClose();
        },
    });

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list action="a1" type="action"><field name="foo"/></list>`,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await contains(`.o_data_cell`).click();
    expect.verifySteps(["doActionButton type action name a1", "web_search_read"]);
});

test(`editable list view: readonly fields cannot be edited`, async () => {
    Foo._fields.foo = fields.Char({ readonly: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field" readonly="1"/>
            </list>
        `,
    });
    await contains(`.o_field_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row", {
        message: "row should be in edit mode",
    });
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_readonly_modifier", {
        message: "foo field should be readonly in edit mode",
    });
    expect(`.o_field_widget[name=bar]`).not.toHaveClass("o_readonly_modifier", {
        message: "bar field should be editable",
    });
    expect(`.o_field_widget[name=int_field]`).toHaveClass("o_readonly_modifier", {
        message: "int_field field should be readonly in edit mode",
    });
    expect(`.o_data_cell:eq(0)`).toHaveClass("o_readonly_modifier");
});

test(`editable list view: line with no active element`, async () => {
    Bar._fields.titi = fields.Char();
    Bar._fields.grosminet = fields.Boolean();
    Bar._records = [
        { id: 1, titi: "cui", grosminet: true },
        { id: 2, titi: "cuicui", grosminet: false },
        { id: 3, titi: "cuicuicui", grosminet: false },
    ];
    Foo._records[0].o2m = [1, 2];

    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <field name="o2m">
                    <list editable="top">
                        <field name="titi" readonly="1"/>
                        <field name="grosminet" widget="boolean_toggle"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_data_cell:eq(1)`).toHaveClass("o_boolean_toggle_cell");

    await contains(`.o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_cell:eq(0)`).toHaveClass("o_readonly_modifier");

    await contains(`.o_data_cell:eq(1) .o_boolean_toggle input`).click();
    expect.verifySteps([]);
});

test(`editable list view: click on last element after creation empty new line`, async () => {
    Bar._fields.titi = fields.Char({ required: true });
    Bar._fields.int_field = fields.Integer({ required: true });
    Bar._records = [
        { id: 1, titi: "cui", int_field: 2 },
        { id: 2, titi: "cuicui", int_field: 4 },
        { id: 3, titi: "cuicuicui", int_field: 1 },
    ];
    Foo._records[0].o2m = [1, 2];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <field name="o2m">
                    <list editable="top">
                        <field name="int_field" widget="handle"/>
                        <field name="titi"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_data_row:last td.o_list_char`).click();
    // This test ensure that they aren't traceback when clicking on the last row.
    expect(`.o_data_row`).toHaveCount(2, { message: "list should have exactly 2 rows" });
});

test(`edit field in editable field without editing the row`, async () => {
    // some widgets are editable in readonly (e.g. priority, boolean_toggle...) and they
    // thus don't require the row to be switched in edition to be edited

    onRpc("web_save", ({ args }) => expect.step("web_save: " + args[1].bar));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="bar" widget="boolean_toggle"/>
            </list>
        `,
    });

    // toggle the boolean value of the first row without editing the row
    expect(`.o_data_row:eq(0) .o_boolean_toggle input`).toBeChecked();
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`.o_data_row .o_boolean_toggle input`).click();
    expect(`.o_data_row:eq(0) .o_boolean_toggle input`).not.toBeChecked();
    expect(`.o_selected_row`).toHaveCount(0);
    expect.verifySteps(["web_save: false"]);

    // toggle the boolean value after switching the row in edition
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`.o_data_row .o_data_cell .o_field_boolean_toggle div`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_selected_row .o_field_boolean_toggle div`).click();
    expect.verifySteps(["web_save: true"]);
});

test(`basic operations for editable list renderer`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_data_row .o_selected_row`).toHaveCount(0);

    await contains(`.o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
});

test(`editable list: add a line and discard`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="bar"/></list>`,
        domain: [["foo", "=", "yop"]],
    });
    expect(`tbody tr`).toHaveCount(4, { message: "list should contain 4 rows" });
    expect(`.o_data_row`).toHaveCount(1, {
        message: "list should contain one record (and thus 3 empty rows)",
    });
    expect(`.o_pager_value`).toHaveText("1-1", { message: "pager should be correct" });

    await contains(`.o_list_button_add`).click();
    expect(`tbody tr`).toHaveCount(4, { message: "list should still contain 4 rows" });
    expect(`.o_data_row`).toHaveCount(2, {
        message: "list should contain two record (and thus 2 empty rows)",
    });
    expect(`.o_pager_value`).toHaveText("1-2", { message: "pager should be correct" });

    await contains(`.o_list_button_discard:not(.dropdown-item)`).click();
    expect(`tbody tr`).toHaveCount(4, { message: "list should still contain 4 rows" });
    expect(`.o_data_row`).toHaveCount(1, {
        message: "list should contain one record (and thus 3 empty rows)",
    });
    expect(`.o_pager_value`).toHaveText("1-1", { message: "pager should be correct" });
});

test(`grouped editable list: edit a record and click on "Add a line"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo" required="1"/><field name="bar"/></list>`,
        groupBy: ["foo"],
    });

    expect(".o_group_header").toHaveCount(3);
    expect(".o_data_row").toHaveCount(0);

    await contains(".o_group_header").click();
    expect(".o_data_row").toHaveCount(2);

    // edit an existing row and click on "Add a line" => edited record should not be discarded
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_data_row .o_data_cell .o_field_widget[name=foo] input").edit("coucou");
    await contains(".o_group_field_row_add a").click();
    expect(".o_data_row .o_data_cell:first").toHaveText("coucou");
    expect(".o_data_row").toHaveCount(3);

    // edit the new line, and click again on "Add a line" => created record should not be discarded
    await contains(".o_data_row .o_data_cell .o_field_widget[name=foo] input").edit("new line");
    await contains(".o_group_field_row_add a").click();
    expect(".o_data_row").toHaveCount(4);
});

test(`field changes are triggered correctly`, async () => {
    Foo._onChanges = {
        foo() {
            expect.step("onchange");
        },
    };

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="bar"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await contains(`.o_field_widget[name=foo] input`).edit("abc");
    expect.verifySteps(["onchange"]);

    await contains(`.o_data_cell:eq(2)`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect.verifySteps([]);
});

test(`editable list view: basic char field edition`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="bar"/></list>`,
    });
    await contains(`.o_field_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await contains(`.o_field_char input`).edit("abc", { confirm: false });
    expect(`.o_field_char input`).toHaveValue("abc", {
        message: "char field has been edited correctly",
    });

    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_field_cell:eq(0)`).toHaveText("abc", {
        message: "changes should be saved correctly",
    });
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row`).not.toHaveClass("o_selected_row", {
        message: "saved row should be in readonly mode",
    });
    expect(Foo._records[0].foo).toBe("abc", {
        message: "the edition should have been properly saved",
    });
});

test(`editable list view: save data when list sorting in edit mode`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { foo: "xyz" }], {
            message: "should correctly save the edited record",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("xyz");
    await contains(`.o_column_sortable`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    expect.verifySteps(["web_save"]);
});

test(`editable list view: check that controlpanel buttons are updating when groupby applied`, async () => {
    Foo._fields.foo = fields.Char({ required: true });
    Foo._views = {
        "list,3": `<list editable="top"><field name="display_name"/><field name="foo"/></list>`,
        "search,9": `
            <search>
                <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
            </search>
        `,
    };

    defineActions([
        {
            id: 11,
            name: "Partners Action 11",
            res_model: "foo",
            views: [[3, "list"]],
            search_view_id: [9, "search"],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(11);
    await contains(`.o_list_button_add`).click();
    expect(`.o_list_button_add`).toHaveCount(0);
    expect(`.o_list_button_save`).toHaveCount(1, {
        message: "Should have 2 save button (small and xl screens)",
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("candle");
    expect(`.o_list_button_add`).toHaveCount(1, {
        message: "Create available as list is grouped",
    });
    expect(`.o_list_button_save`).toHaveCount(0, {
        message: "Save not available as no row in edition",
    });
});

test(`editable list view: check that add button is present when groupby applied`, async () => {
    Foo._fields.foo = fields.Char({ required: true });
    Foo._views = {
        "list,3": `<list editable="top"><field name="display_name"/><field name="foo"/></list>`,
        "form,4": `<form><field name="display_name"/><field name="foo"/></form>`,
        "search,9": `
            <search>
                <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
            </search>
        `,
    };

    defineActions([
        {
            id: 11,
            name: "Partners Action 11",
            res_model: "foo",
            views: [
                [3, "list"],
                [4, "form"],
            ],
            search_view_id: [9, "search"],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(11);
    expect(`.o_list_button_add`).toHaveCount(1);

    await contains(`.o_searchview_dropdown_toggler`).click();
    await contains(`.o_menu_item:contains(candle)`).click();
    expect(`.o_list_button_add`).toHaveCount(1);
    expect(`.o_list_view`).toHaveCount(1);

    await contains(`.o_list_button_add`).click();
    expect(`.o_form_view`).toHaveCount(1);
});

test(`list view not groupable`, async () => {
    Foo._views = {
        search: `
            <search>
                <filter context="{'group_by': 'foo'}" name="foo"/>
            </search>
        `,
    };

    onRpc("read_group", () => {
        throw new Error("Should not do a read_group RPC");
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="display_name"/>
                <field name="foo"/>
            </list>
        `,
        searchMenuTypes: ["filter", "favorite"],
        context: { search_default_foo: 1 },
    });
    expect(`.o_control_panel div.o_search_options div.o_group_by_menu`).toHaveCount(0, {
        message: "there should not be groupby menu",
    });
    expect(getFacetTexts()).toEqual([]);
});

test("group order by count", async () => {
    let readGroupCount = 0;
    onRpc("foo", "web_read_group", async ({ kwargs, parent }) => {
        if (readGroupCount < 2) {
            readGroupCount++;
        } else {
            expect(kwargs.groupby).toHaveLength(1);
            expect.step(`read_group ${kwargs.groupby[0]} order by ${kwargs.orderby}`);
            // The mock server cannot handle orderby count
            kwargs.orderby = "";
            return parent();
        }
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list>
                    <field name="foo"/>
                    <field name="bar"/>
                </list>`,
    });
    await toggleSearchBarMenu();
    await selectGroup("foo");
    await selectGroup("currency_id");
    expect("tr.o_group_header").toHaveCount(3, { message: "list should be grouped" });
    await contains(".o_searchview_facet_label").click();
    expect.verifySteps(["read_group foo order by __count DESC"]);
    await contains("tr.o_group_header:eq(0)").click();
    expect.verifySteps(["read_group currency_id order by __count DESC"]);
    await contains(".o_searchview_facet_label").click();
    expect.verifySteps([
        "read_group foo order by __count ASC",
        "read_group currency_id order by __count ASC",
    ]);
    await contains(".o_searchview_facet_label").click();
    expect.verifySteps([
        "read_group foo order by __count DESC",
        "read_group currency_id order by __count DESC",
    ]);
});

test("order by count reset", async () => {
    let readGroupCount = 0;
    onRpc("foo", "web_read_group", async ({ kwargs, parent }) => {
        if (readGroupCount < 2) {
            readGroupCount++;
        } else {
            expect(kwargs.groupby).toHaveLength(1);
            expect.step(`read_group ${kwargs.groupby[0]} order by ${kwargs.orderby}`);
            // The mock server cannot handle orderby count
            kwargs.orderby = "";
            return parent();
        }
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list>
                    <field name="foo"/>
                    <field name="bar"/>
                </list>`,
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My Filter" domain="[('id', '=', 0)]"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();
    await selectGroup("foo");
    await selectGroup("currency_id");
    await toggleMenuItem("My Filter");
    await contains(".o_searchview_facet_label").click();
    expect.verifySteps(["read_group foo order by ", "read_group foo order by __count DESC"]);
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect.verifySteps(["read_group foo order by __count DESC"]);
    await toggleMenuItem("My Filter");
    expect.verifySteps(["read_group foo order by __count DESC"]);
    await toggleMenuItem("Currency");
    expect.verifySteps(["read_group foo order by __count DESC"]);
    await toggleMenuItem("Foo");
    await toggleMenuItem("Foo");
    expect.verifySteps(["read_group foo order by "]);
});

test(`selection changes are triggered correctly`, async () => {
    patchWithCleanup(ListController.prototype, {
        setup() {
            super.setup(...arguments);
            onRendered(() => {
                expect.step("onRendered ListController");
            });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no record should be selected",
    });
    expect.verifySteps(["onRendered ListController"]);

    // tbody checkbox click
    await contains(`tbody .o_list_record_selector input`).click();
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(1, {
        message: "only 1 record should be selected",
    });
    expect.verifySteps(["onRendered ListController"]);

    await contains(`tbody .o_list_record_selector input`).click();
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no record should be selected",
    });
    expect.verifySteps(["onRendered ListController"]);

    // head checkbox click
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(4, {
        message: "all records should be selected",
    });
    expect.verifySteps(["onRendered ListController"]);

    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no records should be selected",
    });
    expect.verifySteps(["onRendered ListController"]);
});

test(`Row selection checkbox can be toggled by clicking on the cell`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no record should be selected",
    });

    await contains(`tbody .o_list_record_selector`).click();
    expect(`tbody .o_list_record_selector input:checked`).toHaveCount(1);
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(1, {
        message: "only 1 record should be selected",
    });

    await contains(`tbody .o_list_record_selector`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(0);
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no record should be selected",
    });

    await contains(`thead .o_list_record_selector`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(5);
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(4, {
        message: "all records should be selected",
    });

    await contains(`thead .o_list_record_selector`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(0);
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no record should be selected",
    });
});

test(`head selector is toggled by the other selectors`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
    });
    expect(`thead .o_list_record_selector input`).not.toBeChecked({
        message: "Head selector should be unchecked",
    });

    await contains(`.o_group_header:nth-child(2)`).click();
    await contains(`thead .o_list_record_selector input`).click();
    expect(`tbody .o_list_record_selector input:checked`).toHaveCount(3, {
        message: "All visible checkboxes should be checked",
    });

    await contains(`.o_group_header:eq(0)`).click();
    expect(`thead .o_list_record_selector input`).not.toBeChecked({
        message: "Head selector should be unchecked",
    });

    await contains(`tbody:nth-child(2) .o_list_record_selector input`).click();
    expect(`thead .o_list_record_selector input`).toBeChecked({
        message: "Head selector should be checked",
    });

    await contains(`tbody .o_list_record_selector input`).click();
    expect(`thead .o_list_record_selector input`).not.toBeChecked({
        message: "Head selector should be unchecked",
    });

    await contains(`.o_group_header`).click();
    expect(`thead .o_list_record_selector input`).toBeChecked({
        message: "Head selector should be checked",
    });
});

test(`selection box is properly displayed (single page)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);

    // select a record
    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("1\nselected");

    // select all records of first page
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("4\nselected");

    // unselect a record
    await contains(`.o_data_row .o_list_record_selector input:eq(1)`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("3\nselected");

    await contains(`.o_list_unselect_all`).click();
    expect(`.o_list_selection_box`).toHaveCount(0, {
        message: "selection options are no longer visible",
    });
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no records should be selected",
    });
});

test(`selection box is properly displayed (multi pages)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="3"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(3);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);

    // select a record
    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("1\nselected");

    // select all records of first page
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("3\nselected\n Select all 4");

    // select all domain
    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    await contains(`.o_list_unselect_all`).click();
    expect(`.o_list_selection_box`).toHaveCount(0, {
        message: "selection options are no longer visible",
    });
});

test(`selection box is properly displayed (group list)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["foo"],
    });
    expect(`.o_group_header`).toHaveCount(3);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);

    // open first group
    await contains(`.o_group_header`).click();

    // select a record
    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("1\nselected");

    // select all records of first page
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("2\nselected\n Select all 4");

    // select all domain
    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    await contains(`.o_list_unselect_all`).click();
    expect(`.o_list_selection_box`).toHaveCount(0, {
        message: "selection options are no longer visible",
    });
});

test(`selection box: grouped list, all groups folded`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["foo"],
    });
    expect(`.o_group_header`).toHaveCount(3);
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_searchview`).toHaveCount(1);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);
    expect(`.o_control_panel_breadcrumbs_actions .o_cp_action_menus`).toHaveCount(1);

    // click on the checkbox in the thead
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_control_panel_breadcrumbs_actions .o_cp_action_menus`).toHaveCount(0);
    expect(`.o_searchview`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    // remove selection by clicking on the cross in the selection box
    await contains(`.o_list_unselect_all`).click();
    expect(`.o_list_selection_box`).toHaveCount(0);

    // click again on the checkbox in the thead
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    // remove selection by clicking on the checkbox in the thead
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_searchview`).toHaveCount(1);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);
});

test(`selection box in grouped list, multi pages`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: '<list groups_limit="2"><field name="foo"/><field name="bar"/></list>',
        groupBy: ["int_field"],
    });

    expect(".o_group_header").toHaveCount(2);
    expect(".o_list_selection_box").toHaveCount(0);
    expect(".o_pager_value").toHaveText("1-2");
    expect(".o_pager_limit").toHaveText("4");

    // open first group and select all records of first page
    await contains(".o_group_header").click();
    expect(".o_data_row").toHaveCount(1);
    await contains("thead .o_list_record_selector input").click();
    expect(".o_control_panel_actions .o_list_selection_box").toHaveCount(1);
    expect(".o_list_selection_box .o_list_select_domain").toHaveCount(1);
    expect(queryOne(".o_list_selection_box").innerText.replace(/\s+/g, " ").trim()).toBe(
        "1 selected Select all" // we don't know the total count, so we don't display it
    );

    // select all domain
    await contains(".o_list_selection_box .o_list_select_domain").click();
    expect(".o_control_panel_actions .o_list_selection_box").toHaveCount(1);
    expect(".o_list_selection_box").toHaveText("All 4 selected");
});

test(`selection box: grouped list, select domain, open group`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: '<list><field name="foo"/><field name="bar"/></list>',
        groupBy: ["foo"],
    });

    expect(".o_group_header").toHaveCount(3);
    expect(".o_data_row").toHaveCount(0);
    expect(".o_control_panel_actions .o_list_selection_box").toHaveCount(0);

    // select all domain by ticking the thead checkbox
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    // open first group
    await contains(".o_group_header").click();
    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row .o_list_record_selector input:checked").toHaveCount(2);

    // open another group
    await contains(queryAll(".o_group_header")[1]).click();
    expect(".o_data_row").toHaveCount(3);
    expect(".o_data_row .o_list_record_selector input:checked").toHaveCount(3);
});

test(`selection box: grouped list, select domain, use pager (inside group)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: '<list limit="2"><field name="foo"/><field name="bar"/></list>',
        groupBy: ["bar"],
    });

    expect(".o_group_header").toHaveCount(2);
    expect(".o_data_row").toHaveCount(0);
    expect(".o_control_panel_actions .o_list_selection_box").toHaveCount(0);

    // open second group and select all domain
    await contains(queryAll(".o_group_header")[1]).click();
    await contains("thead .o_list_record_selector input").click();
    await contains(".o_list_selection_box .o_list_select_domain").click();
    expect(".o_data_row").toHaveCount(2);
    expect(".o_group_header .o_pager_value").toHaveText("1-2");
    expect(".o_group_header .o_pager_limit").toHaveText("3");
    expect(".o_control_panel_actions .o_list_selection_box").toHaveCount(1);
    expect(".o_list_selection_box").toHaveText("All 4 selected");

    // click pager next in the opened group
    await contains(".o_group_header .o_pager_next").click();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row .o_list_record_selector input:checked").toHaveCount(1);
    expect(".o_list_selection_box").toHaveText("All 4 selected");
});

test(`selection box: grouped list, select domain, use main pager`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: '<list groups_limit="2"><field name="foo"/><field name="bar"/></list>',
        groupBy: ["foo"],
    });

    expect(".o_group_header").toHaveCount(2);
    expect(".o_data_row").toHaveCount(0);
    expect(".o_control_panel_actions .o_list_selection_box").toHaveCount(0);

    // select all domain by ticking the thead checkbox
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    // go to second page
    await contains(".o_pager_next").click();
    expect(".o_group_header").toHaveCount(1);
    expect(".o_data_row").toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    // open a group
    await contains(".o_group_header").click();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row .o_list_record_selector input:checked").toHaveCount(1);

    // go to previous page and come back, to check that selection is still ok
    await contains(".o_pager_previous").click();
    await contains(".o_pager_next").click();
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_row .o_list_record_selector input:checked").toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");
});

test(`selection box: grouped list, select domain, reduce limit`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: '<list><field name="foo"/><field name="bar"/></list>',
        groupBy: ["foo"],
    });

    expect(".o_group_header").toHaveCount(3);
    expect(".o_data_row").toHaveCount(0);
    expect(".o_control_panel_actions .o_list_selection_box").toHaveCount(0);

    // select all domain by ticking the thead checkbox
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    // reduce limit to 2
    await contains(".o_pager_value").click();
    await contains("input.o_pager_value").edit("1-2");
    expect(".o_group_header").toHaveCount(2);
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");
});

test(`selection box is displayed as first action button`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button name="x" type="object" class="plaf" string="plaf"/>
                    <button name="y" type="object" class="plouf" string="plouf"/>
                </header>
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);

    // select a record
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    const firstElement = queryFirst(`.o_control_panel_actions > div`).firstElementChild;
    expect(firstElement).toBe(queryFirst(`.o_control_panel_actions .o_list_selection_box`), {
        message: "last element should selection box",
    });
    expect(`.o_list_selection_box`).toHaveText("1\nselected");
});

test(`selection box: select domain, then untick a record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);

    // select all records of first page
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);
    expect(queryOne(".o_list_selection_box").innerText.replace(/\s+/g, " ").trim()).toBe(
        "2 selected Select all 4"
    );

    // select domain
    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    expect(`.o_list_selection_box`).toHaveText("All 4 selected");

    // untick a record
    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(queryOne(`.o_list_selection_box`).innerText.replace(/\s+/g, " ").trim()).toBe(
        "1 selected"
    );
    expect(`thead .o_list_record_selector input`).not.toBeChecked();
});

test(`selection box is not removed after multi record edition`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list multi_edit="1"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(4, { message: "there should be 4 records" });
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0, {
        message: "list selection box should not be displayed",
    });

    // select all records
    await contains(`.o_list_record_selector input`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1, {
        message: "list selection box should be displayed",
    });
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(4, {
        message: "all 4 records should be selected",
    });

    // edit selected records
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_data_row [name=foo] input`).edit("legion");
    await contains(`.modal-dialog button.btn-primary`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1, {
        message: "list selection box should still be displayed",
    });
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(4, {
        message: "same records should be selected",
    });
});

test(`selection is reset on reload`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="int_field" sum="Sum"/>
            </list>
        `,
    });
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);
    expect(`tfoot .o_list_number`).toHaveText("32", {
        message: "total should be 32 (no record selected)",
    });

    // select first record
    await contains(`tbody .o_list_record_selector input`).click();
    expect(`tbody .o_list_record_selector input:eq(0)`).toBeChecked({
        message: "first row should be selected",
    });
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
    expect(`tfoot .o_list_number`).toHaveText("10", {
        message: "total should be 10 (first record selected)",
    });

    await contains(`.o_pager_value`).click();
    await contains(`input.o_pager_value`).edit("1-4");
    expect(`tbody .o_list_record_selector input:eq(0)`).not.toBeChecked({
        message: "first row should be selected",
    });
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);
    expect(`tfoot .o_list_number`).toHaveText("32", {
        message: "total should be 10 (first record selected)",
    });
});

test(`selection is kept on render without reload`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="int_field" sum="Sum"/>
            </list>
        `,
        groupBy: ["foo"],
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);

    // open blip grouping and check all lines
    await contains(`.o_group_header:contains(blip (2))`).click();
    await contains(`.o_data_row input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);

    // open yop grouping and verify blip are still checked
    await contains(`.o_group_header:contains(yop (1))`).click();
    expect(`.o_data_row input:checked`).toHaveCount(1, {
        message: "opening a grouping does not uncheck others",
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);

    // close and open blip grouping and verify blip are unchecked
    await contains(`.o_group_header:contains(blip (2))`).click();
    await contains(`.o_group_header:contains(blip (2))`).click();
    expect(`.o_data_row input:checked`).toHaveCount(0, {
        message: "opening and closing a grouping uncheck its elements",
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);
});

test(`select a record in list grouped by date with granularity`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["date:year"],
        // keep the actionMenus, it is relevant as it computes isM2MGrouped which crashes if we
        // don't correctly extract the fieldName/granularity from the groupBy
        actionMenus: {},
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(0);

    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(1);

    await contains(`.o_data_row .o_list_record_selector`).click();
    expect(`.o_control_panel_actions .o_list_selection_box`).toHaveCount(1);
});

test(`aggregates are computed correctly`, async () => {
    // map: foo record id -> qux value
    const quxVals = { 1: 1.0, 2: 2.0, 3: 3.0, 4: 0 };

    Foo._records = Foo._records.map((r) => ({
        ...r,
        qux: quxVals[r.id],
    }));

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="int_field" sum="Sum"/>
                <field name="qux" avg="Average"/>
            </list>
        `,
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My Filter" domain="[('id', '=', 0)]"/>
            </search>
        `,
    });
    expect(queryAllTexts(`tfoot td`)).toEqual(["", "", "32", "1.50"]);

    await contains(`tbody .o_list_record_selector input:eq(0)`).click();
    await contains(`tbody .o_list_record_selector input:eq(3)`).click();
    expect(queryAllTexts(`tfoot td`)).toEqual(["", "", "6", "0.50"]);

    await contains(`thead .o_list_record_selector input`).click();
    expect(queryAllTexts(`tfoot td`)).toEqual(["", "", "32", "1.50"]);

    // Let's update the view to dislay NO records
    await contains(`.o_list_unselect_all`).click();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(queryAllTexts(`tfoot td`)).toEqual(["", "", "", ""]);
});

test(`aggregates are computed correctly in grouped lists`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["m2o"],
        arch: `<list editable="bottom"><field name="foo"/><field name="int_field" sum="Sum"/></list>`,
    });
    expect(`.o_group_header:eq(0) td:eq(-1)`).toHaveText("23", {
        message: "first group total should be 23",
    });
    expect(`.o_group_header:eq(1) td:eq(-1)`).toHaveText("9", {
        message: "second group total should be 9",
    });
    expect(`tfoot td:eq(-1)`).toHaveText("32", { message: "total should be 32" });
    await contains(`.o_group_header:eq(0)`).click();
    await contains(`tbody .o_list_record_selector input:eq(0)`).click();
    expect(`tfoot td:eq(-1)`).toHaveText("10", {
        message: "total should be 10 as first record of first group is selected",
    });
});

test(`aggregates are formatted correctly in grouped lists`, async () => {
    // in this scenario, there is a widget on an aggregated field, and this widget has no
    // associated formatter, so we fallback on the formatter corresponding to the field type
    registry.category("fields").add("my_float", floatField);
    Foo._records[0].qux = 5.1654846456;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="qux" widget="my_float" sum="Sum"/>
            </list>
        `,
        groupBy: ["int_field"],
    });
    expect(queryAllTexts(`.o_group_header .o_list_number`)).toEqual([
        "9.00",
        "13.00",
        "5.17",
        "-3.00",
    ]);
});

test(`aggregates in grouped lists with buttons`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["m2o"],
        arch: `
            <list>
                <field name="foo"/>
                <field name="int_field" sum="Sum"/>
                <button name="a" type="object"/>
                <field name="qux" sum="Sum"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_list_number`)).toEqual(["23", "6.40", "9", "13.00", "32", "19.40"]);
});

test(`date field aggregates in grouped lists`, async () => {
    // this test simulates a scenario where a date field has a aggregator
    // and the web_read_group thus return a value for that field for each group

    onRpc("web_read_group", async ({ parent }) => {
        const res = await parent();
        res.groups[0].date = "2021-03-15";
        res.groups[1].date = "2021-02-11";
        return res;
    });
    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["m2o"],
        arch: `
            <list>
                <field name="foo"/>
                <field name="date"/>
            </list>
        `,
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(queryAllTexts(`.o_group_header`)).toEqual([`Value 1 (3)`, `Value 2 (1)`]);
});

test(`hide aggregated value in grouped lists when no data provided by RPC call`, async () => {
    onRpc("web_read_group", async ({ parent }) => {
        const res = await parent();
        res.groups.forEach((group) => {
            delete group.qux;
        });
        return res;
    });
    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["bar"],
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="qux" widget="float_time" sum="Sum"/>
            </list>
        `,
    });
    expect(`tfoot td:eq(2)`).toHaveText("", { message: "There isn't any aggregated value" });
});

test(`aggregates are updated when a line is edited`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="int_field" sum="Sum"/></list>`,
    });
    expect(`span[data-tooltip="Sum"]`).toHaveText("32", { message: "current total should be 32" });

    await contains(`tr.o_data_row td.o_data_cell`).click();
    await contains(`td.o_data_cell input`).edit("15");
    expect(`span[data-tooltip="Sum"]`).toHaveText("37", { message: "current total should be 37" });
});

test(`aggregates are formatted according to field widget`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="qux" widget="float_time" sum="Sum"/>
            </list>
        `,
    });
    expect(`tfoot td:eq(2)`).toHaveText("19:24", {
        message: "total should be formatted as a float_time",
    });
});

test(`aggregates of monetary field with no currency field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="amount" widget="monetary" sum="Sum"/></list>`,
    });
    expect(`.o_data_row td:eq(1)`).toHaveText("1,200.00", {
        message: "field should still be formatted based on currency",
    });
    expect(`tfoot td:eq(1)`).toHaveText("—", {
        message: "aggregates monetary should never work if no currency field is present",
    });
});

test(`aggregates monetary (same currency)`, async () => {
    Foo._records[0].currency_id = 1;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="amount" widget="monetary" sum="Sum"/>
                <field name="currency_id"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody .o_monetary_cell`)).toEqual([
        "$ 1,200.00",
        "$ 500.00",
        "$ 300.00",
        "$ 0.00",
    ]);
    expect(`tfoot td:eq(1)`).toHaveText("$ 2,000.00");
});

test(`aggregates monetary (different currencies)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="amount" widget="monetary" sum="Sum"/>
                <field name="currency_id"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody .o_monetary_cell`)).toEqual([
        "1,200.00 €",
        "$ 500.00",
        "$ 300.00",
        "$ 0.00",
    ]);
    expect(`tfoot td:eq(1)`).toHaveText("—");
});

test(`aggregates monetary (currency field not in view)`, async () => {
    Foo._fields.currency_test = fields.Many2one({ relation: "res.currency", default: 1 });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="amount" widget="monetary" sum="Sum" options="{'currency_field': 'currency_test'}"/>
                <field name="currency_id"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody .o_monetary_cell`)).toEqual([
        "1,200.00",
        "500.00",
        "300.00",
        "0.00",
    ]);
    expect(`tfoot td:eq(1)`).toHaveText("—");
});

test(`aggregates monetary (currency field in view)`, async () => {
    Foo._fields.amount = fields.Monetary({ currency_field: "currency_test" });
    Foo._fields.currency_test = fields.Many2one({ relation: "res.currency", default: 1 });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="amount" widget="monetary" sum="Sum"/>
                <field name="currency_test"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody .o_monetary_cell`)).toEqual([
        "$ 1,200.00",
        "$ 500.00",
        "$ 300.00",
        "$ 0.00",
    ]);
    expect(`tfoot td:eq(1)`).toHaveText("$ 2,000.00");
});

test(`aggregates monetary with custom digits (same currency)`, async () => {
    Foo._records = Foo._records.map((record) => ({
        ...record,
        currency_id: 1,
    }));

    patchWithCleanup(currencies[1], { digits: [42, 4] });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="amount" sum="Sum"/>
                <field name="currency_id"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody [name='amount']`)).toEqual([
        "$ 1,200.0000",
        "$ 500.0000",
        "$ 300.0000",
        "$ 0.0000",
    ]);
    expect(`tfoot td:eq(1)`).toHaveText("$ 2,000.0000");
});

test(`aggregates float with monetary widget and custom digits (same currency)`, async () => {
    Foo._records = Foo._records.map((record) => ({
        ...record,
        currency_id: 1,
    }));

    patchWithCleanup(currencies[1], { digits: [42, 4] });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="qux" widget="monetary" sum="Sum"/>
                <field name="currency_id"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody .o_monetary_cell`)).toEqual([
        "$ 0.4000",
        "$ 13.0000",
        "$ -3.0000",
        "$ 9.0000",
    ]);
    expect(`tfoot td:eq(1)`).toHaveText("$ 19.4000");
});

test(`currency_field is taken into account when formatting monetary values`, async () => {
    Foo._fields.company_currency_id = fields.Many2one({ relation: "res.currency", default: 2 });
    Foo._fields.amount_currency = fields.Monetary({ currency_field: "company_currency_id" });
    Foo._records[0].amount_currency = 1100;
    Foo._records[0].company_currency_id = 1;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="company_currency_id" column_invisible="1"/>
                <field name="currency_id" column_invisible="1"/>
                <field name="amount" sum="Sum"/>
                <field name="amount_currency"/>
            </list>
        `,
    });
    expect(`.o_data_row:eq(0) td[name=amount]`).toHaveText("1,200.00 €", {
        message: "field should be formatted based on currency_id",
    });
    expect(`.o_data_row:eq(0) td[name=amount_currency]`).toHaveText("$ 1,100.00", {
        message: "field should be formatted based on company_currency_id",
    });
    expect(`tfoot td:eq(1)`).toHaveText("—", {
        message: "aggregates monetary should never work if different currencies are used",
    });
    expect(`tfoot td:eq(2)`).toHaveText("", {
        message:
            "monetary aggregation should only be attempted with an active aggregation function when using different currencies",
    });
});

test(`groups can not be sorted on a different field than the first field of the groupBy - 1`, async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step("web_read_group");
        expect(kwargs.orderby).toBe("", { message: "should not have an orderBy" });
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list default_order="foo"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
    });
    expect.verifySteps(["web_read_group"]);
});

test(`groups can not be sorted on a different field than the first field of the groupBy - 2`, async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step("web_read_group");
        expect(kwargs.orderby).toBe("", { message: "should not have an orderBy" });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list default_order="foo">
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
        groupBy: ["bar", "foo"],
    });
    expect.verifySteps(["web_read_group"]);
});

test(`groups can be sorted on the first field of the groupBy`, async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step("web_read_group");
        expect(kwargs.orderby).toBe("bar DESC", { message: "should have an orderBy" });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list default_order="bar desc"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
    });
    expect(`.o_group_header:eq(0)`).toHaveText("Yes (3)");
    expect(`.o_group_header:eq(-1)`).toHaveText("No (1)");
    expect.verifySteps(["web_read_group"]);
});

test(`groups can't be sorted on aggregates if there is no record`, async () => {
    Foo._records = [];

    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(kwargs.orderby || "default order");
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field" sum="Sum"/>
            </list>
        `,
        groupBy: ["foo"],
    });
    await contains(`.o_column_sortable`).click();
    expect.verifySteps(["default order"]);
});

test(`groups can be sorted on aggregates`, async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(kwargs.orderby || "default order");
    });

    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["foo"],
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field" sum="Sum"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody .o_list_number`)).toEqual(["5", "17", "10"], {
        message: "initial order should be 5, 17, 10",
    });
    expect(`tfoot td:eq(-1)`).toHaveText("32", { message: "total should be 32" });

    await contains(`.o_column_sortable[data-name=int_field]`).click();
    expect(queryAllTexts(`tbody .o_list_number`)).toEqual(["5", "10", "17"], {
        message: "order should be 5, 10, 17",
    });
    expect(`tfoot td:eq(-1)`).toHaveText("32", { message: "total should still be 32" });

    await contains(`.o_column_sortable[data-name=int_field]`).click();
    expect(queryAllTexts(`tbody .o_list_number`)).toEqual(["17", "10", "5"], {
        message: "initial order should be 17, 10, 5",
    });
    expect(`tfoot td:eq(-1)`).toHaveText("32", { message: "total should still be 32" });
    expect.verifySteps(["default order", "int_field ASC", "int_field DESC"]);
});

test(`groups cannot be sorted on non-aggregable fields if every group is folded`, async () => {
    Foo._fields.sort_field = fields.Char({ default: "value" });
    Foo._records.forEach((elem) => {
        elem.sort_field = "value" + elem.id;
    });

    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(kwargs.orderby || "default order");
    });

    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["foo"],
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field"/>
                <field name="sort_field"/>
            </list>
        `,
    });
    expect.verifySteps(["default order"]);

    // we cannot sort by sort_field since it doesn't have a aggregator
    await contains(`.o_column_sortable[data-name='sort_field']`).click();
    expect.verifySteps([]);

    // we can sort by int_field since it has a aggregator
    await contains(`.o_column_sortable[data-name='int_field']`).click();
    expect.verifySteps(["int_field ASC"]);

    // we keep previous order
    await contains(`.o_column_sortable[data-name='sort_field']`).click();
    expect.verifySteps([]);

    // we can sort on foo since we are groupped by foo + previous order
    await contains(`.o_column_sortable[data-name='foo']`).click();
    expect.verifySteps(["foo ASC, int_field ASC"]);
});

test(`groups can be sorted on non-aggregable fields if a group isn't folded`, async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(`web_read_group.orderby: ${kwargs.orderby || "default order"}`);
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(`web_search_read.order: ${kwargs.order || "default order"}`);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header:eq(1)`).click();
    expect(queryAllTexts(`.o_data_cell[name='foo']`)).toEqual(["yop", "blip", "gnap"]);
    expect.verifySteps([
        "web_read_group.orderby: default order",
        "web_search_read.order: default order",
    ]);

    await contains(`.o_column_sortable[data-name='foo']`).click();
    expect(queryAllTexts(`.o_data_cell[name='foo']`)).toEqual(["blip", "gnap", "yop"]);
    expect.verifySteps(["web_read_group.orderby: default order", "web_search_read.order: foo ASC"]);
});

test(`groups can be sorted on non-aggregable fields if a group isn't folded with expand='1'`, async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(`web_read_group.orderby: ${kwargs.orderby || "default order"}`);
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(`web_search_read.orderby: ${kwargs.order || "default order"}`);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom" expand="1"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    expect(queryAllTexts(`.o_data_cell[name='foo']`)).toEqual(["blip", "yop", "blip", "gnap"]);
    expect.verifySteps([
        "web_read_group.orderby: default order",
        "web_search_read.orderby: default order",
        "web_search_read.orderby: default order",
    ]);

    await contains(`.o_column_sortable[data-name='foo']`).click();
    expect(queryAllTexts(`.o_data_cell[name='foo']`)).toEqual(["blip", "blip", "gnap", "yop"]);
    expect.verifySteps([
        "web_read_group.orderby: default order",
        "web_search_read.orderby: foo ASC",
        "web_search_read.orderby: foo ASC",
    ]);
});

test(`properly apply onchange in simple case`, async () => {
    Foo._onChanges = {
        foo(record) {
            record.int_field = record.foo.length + 1000;
        },
    };

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="int_field"/></list>`,
    });
    await contains(`.o_field_cell`).click();
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("10", {
        message: "should contain initial value",
    });

    await contains(`.o_field_widget[name=foo] input`).edit("tralala", { confirm: "tab" });
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("1,007", {
        message: "should contain input with onchange applied",
    });
});

test(`colspan of empty lines is correct in readonly`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form edit="0">
                <sheet>
                    <field name="foo_o2m">
                        <list editable="bottom">
                            <field name="int_field"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    // in readonly mode, the delete action is not available
    expect(`tbody td:eq(0)`).toHaveAttribute("colspan", "1");
});

test(`colspan of empty lines is correct in edit`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="foo_o2m">
                        <list editable="bottom">
                            <field name="int_field"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    // in edit mode, the delete action is available and the empty lines should cover that col
    expect(`tbody td:eq(0)`).toHaveAttribute("colspan", "2");
});

test(`colspan of empty lines is correct in readonly with optional fields`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form edit="0">
                <sheet>
                    <field name="foo_o2m">
                        <list editable="bottom">
                            <field name="int_field"/>
                            <field name="foo" optional="hidden"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    // in readonly mode, the delete action is not available but the optional fields is and the empty lines should cover that col
    expect(`tbody td:eq(0)`).toHaveAttribute("colspan", "2");
});

test(`colspan of empty lines is correct in edit with optional fields`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="foo_o2m">
                        <list editable="bottom">
                            <field name="int_field"/>
                            <field name="foo" optional="hidden"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    // in edit mode, both the delete action and the optional fields are available and the empty lines should cover that col
    expect(`tbody td:eq(0)`).toHaveAttribute("colspan", "2");
});

test(`editable list: updating list state while invisible`, async () => {
    Foo._onChanges = {
        bar(record) {
            record.o2m = [[5], [0, null, { display_name: "Whatever" }]];
        },
    };

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <notebook>
                        <page string="Page 1"></page>
                        <page string="Page 2">
                            <field name="o2m">
                                <list editable="bottom">
                                    <field name="display_name"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.o_field_boolean input`).click();
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.nav-item:eq(-1) .nav-link`).click();
    expect(`.o_field_one2many`).toHaveCount(1);
    expect(`.o_field_one2many .o_data_row:eq(0)`).toHaveText("Whatever");
});

test(`editable list view, click on m2o dropdown does not close editable row`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="m2o"/></list>`,
    });
    await contains(`.o_list_button_add`).click();
    expect(`.o_selected_row .o_field_many2one input`).toHaveValue("");

    await contains(`.o_selected_row .o_field_many2one input`).click();
    expect(`.o_field_many2one .o-autocomplete--dropdown-menu`).toHaveCount(1);

    await contains(`.o_field_many2one .o-autocomplete--dropdown-menu .dropdown-item`).click();
    expect(`.o_selected_row .o_field_many2one input`).toHaveValue("Value 1");
    expect(`.o_selected_row`).toHaveCount(1, { message: "should still have editable row" });
});

test(`fields are translatable in list view`, async () => {
    serverState.multiLang = true;
    Foo._fields.foo = fields.Char({ translate: true });

    installLanguages({
        en_US: "English",
        fr_BE: "Frenglish",
    });

    onRpc("/web/dataset/call_kw/foo/get_field_translations", () => {
        return [
            [
                { lang: "en_US", source: "yop", value: "yop" },
                { lang: "fr_BE", source: "yop", value: "valeur français" },
            ],
            { translation_type: "char", translation_show_source: false },
        ];
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo" required="1"/></list>`,
    });
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await contains(`span.o_field_translate`).click();
    expect(`.o_translation_dialog`).toHaveCount(1);
    expect(`.o_translation_dialog .translation > input.o_field_char`).toHaveCount(2, {
        message: "modal should have 2 languages to translate",
    });
});

test(`long words in text cells should break into smaller lines`, async () => {
    Foo._records[0].text = "a";
    Foo._records[1].text = "pneumonoultramicroscopicsilicovolcanoconiosis"; // longest english word I could find

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="text"/></list>`,
    });

    // Intentionally set the table width to a small size
    queryOne("table").style.width = "100px";
    queryOne("th:eq(-1)").style.width = "100px";
    const shortText = queryRect(".o_data_row:eq(0) td:eq(-1)").height;
    const longText = queryRect(".o_data_row:eq(1) td:eq(-1)").height;
    const emptyText = queryRect(".o_data_row:eq(2) td:eq(-1)").height;

    expect(shortText).toBe(emptyText, {
        message: "Short word should not change the height of the cell",
    });
    expect(longText).toBeGreaterThan(emptyText, {
        message: "Long word should change the height of the cell",
    });
});

test(`deleting one record and verify context key`, async () => {
    onRpc("unlink", ({ kwargs }) => {
        expect.step("unlink");
        expect(kwargs.context.ctx_key).toBe("ctx_val");
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        actionMenus: {},
        context: {
            ctx_key: "ctx_val",
        },
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`tbody td.o_list_record_selector`).toHaveCount(4, { message: "should have 4 records" });

    await contains(`tbody td.o_list_record_selector:eq(0) input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    expect(document.body).toHaveClass("modal-open", {
        message: "body should have modal-open class",
    });

    await contains(`.modal footer button.btn-primary`).click();
    expect.verifySteps(["unlink"]);
    expect(`tbody td.o_list_record_selector`).toHaveCount(3, { message: "should have 3 records" });
});

test(`custom delete confirmation dialog`, async () => {
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

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="caution"><field name="foo"/></list>`,
        actionMenus: {},
    });
    await contains(`tbody td.o_list_record_selector:eq(0) input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    expect(`.modal:contains(you sure) .text-danger:contains(consequences)`).toHaveCount(1, {
        message: "confirmation dialog should have markup and more",
    });

    await contains(`.modal footer button.btn-secondary`).click();
    expect(`tbody td.o_list_record_selector`).toHaveCount(4, {
        message: "nothing deleted, 4 records remain",
    });
});

test(`deleting record which throws UserError should close confirmation dialog`, async () => {
    expect.errors(1);

    onRpc("unlink", () => {
        throw makeServerError({ message: "Odoo Server Error" });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        actionMenus: {},
        arch: `<list><field name="foo"/></list>`,
    });
    await contains(`tbody td.o_list_record_selector:eq(0) input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    expect(`.modal`).toHaveCount(1, { message: "should have open the confirmation dialog" });

    await contains(`.modal footer button.btn-primary`).click();
    await waitFor(".modal");
    expect(`.modal .modal-title`).toHaveText("Invalid Operation");
});

test(`delete all records matching the domain`, async () => {
    Foo._records.push({ id: 5, bar: true, foo: "xxx" });

    mockService("notification", {
        add() {
            expect.step("should not display a notification");
        },
    });

    onRpc("unlink", ({ args }) => {
        expect.step("unlink");
        expect(args[0]).toEqual([1, 2, 3, 5]);
    });

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `<list limit="2"><field name="foo"/></list>`,
        domain: [["bar", "=", true]],
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`tbody td.o_list_record_selector`).toHaveCount(2, { message: "should have 2 records" });

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);

    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal footer button.btn-primary`).click();
    expect.verifySteps(["unlink"]);
});

test(`delete all records matching the domain (limit reached)`, async () => {
    Foo._records.push({ id: 5, bar: true, foo: "xxx" });
    Foo._records.push({ id: 6, bar: true, foo: "yyy" });

    mockService("notification", {
        add() {
            expect.step("notify");
        },
    });

    patchWithCleanup(session, {
        active_ids_limit: 4,
    });

    onRpc("unlink", ({ args }) => {
        expect.step("unlink");
        expect(args[0]).toEqual([1, 2, 3, 5]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/></list>`,
        domain: [["bar", "=", true]],
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`tbody td.o_list_record_selector`).toHaveCount(2, { message: "should have 2 records" });

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);

    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal footer button.btn-primary`).click();
    expect.verifySteps(["unlink", "notify"]);
});

test(`duplicate one record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
        actionMenus: {},
    });

    // Initial state: there should be 4 records
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });

    // Duplicate one record
    await contains(`.o_data_row input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Duplicate");

    // Final state: there should be 5 records
    expect(`tbody tr`).toHaveCount(5, { message: "should have 5 rows" });
});

test(`duplicate all records`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
        actionMenus: {},
    });

    // Initial state: there should be 4 records
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });

    // Duplicate all records
    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Duplicate");

    // Final state: there should be 8 records
    expect(`tbody tr`).toHaveCount(8, { message: "should have 8 rows" });
});

test(`archiving one record`, async () => {
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        actionMenus: {},
        arch: `<list><field name="foo"/></list>`,
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`tbody td.o_list_record_selector`).toHaveCount(4, { message: "should have 4 records" });

    await contains(`tbody td.o_list_record_selector:eq(0) input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal-footer .btn-secondary`).click();
    expect(`tbody td.o_list_record_selector`).toHaveCount(4, {
        message: "still should have 4 records",
    });

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal-footer .btn-primary`).click();
    expect(`tbody td.o_list_record_selector`).toHaveCount(3, { message: "should have 3 records" });
    expect.verifySteps(["action_archive", "web_search_read"]);
});

test(`archive all records matching the domain`, async () => {
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });
    Foo._records.push({ id: 5, bar: true, foo: "xxx" });

    mockService("notification", {
        add() {
            expect.step("should not display a notification");
        },
    });

    onRpc("action_archive", ({ args }) => {
        expect.step("action_archive");
        expect(args[0]).toEqual([1, 2, 3, 5]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/></list>`,
        domain: [["bar", "=", true]],
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`tbody td.o_list_record_selector`).toHaveCount(2, { message: "should have 2 records" });

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);

    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal-footer .btn-primary`).click();
    expect.verifySteps(["action_archive"]);
});

test(`archive all records matching the domain (limit reached)`, async () => {
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });
    Foo._records.push({ id: 5, bar: true, foo: "xxx" });
    Foo._records.push({ id: 6, bar: true, foo: "yyy" });

    mockService("notification", {
        add() {
            expect.step("notify");
        },
    });

    patchWithCleanup(session, {
        active_ids_limit: 4,
    });

    onRpc("action_archive", ({ args }) => {
        expect.step("action_archive");
        expect(args[0]).toEqual([1, 2, 3, 5]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/></list>`,
        domain: [["bar", "=", true]],
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`tbody td.o_list_record_selector`).toHaveCount(2, { message: "should have 2 records" });

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);

    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal-footer .btn-primary`).click();
    expect.verifySteps(["action_archive", "notify"]);
});

test(`archive/unarchive handles returned action`, async () => {
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    Foo._views = {
        "list,3": `<list><field name="foo"/></list>`,
        "search,9": `
            <search>
                <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
            </search>
        `,
    };
    Bar._views = {
        form: `<form><field name="display_name"/></form>`,
    };

    defineActions([
        {
            id: 11,
            name: "Action 11",
            res_model: "foo",
            views: [[3, "list"]],
            search_view_id: [9, "search"],
        },
    ]);

    onRpc("/web/dataset/call_kw/foo/action_archive", () => ({
        type: "ir.actions.act_window",
        name: "Archive Action",
        res_model: "bar",
        view_mode: "form",
        target: "new",
        views: [[false, "form"]],
    }));

    await mountWithCleanup(WebClient);
    await getService("action").doAction(11);

    expect(`tbody td.o_list_record_selector`).toHaveCount(4, { message: "should have 4 records" });

    await contains(`tbody td.o_list_record_selector input`).click();
    expect(`.o_cp_action_menus`).toHaveCount(1, { message: "sidebar should be visible" });

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await contains(`.o-dropdown--menu .o_menu_item:contains(Archive)`).click();
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal .modal-footer .btn-primary`).click();
    expect(`.modal`).toHaveCount(1, { message: "archive action dialog should be displayed" });
    expect(`.modal .modal-title`).toHaveText("Archive Action", {
        message: "action wizard should have been opened",
    });
});

test(`apply custom static action menu (archive)`, async () => {
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    const listView = registry.category("views").get("list");
    class CustomListController extends listView.Controller {
        getStaticActionMenuItems() {
            const menuItems = super.getStaticActionMenuItems();
            menuItems.archive.callback = () => {
                expect.step("customArchive");
            };
            return menuItems;
        }
    }
    registry.category("views").add("custom_list", {
        ...listView,
        Controller: CustomListController,
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="custom_list"><field name="foo"/></list>`,
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Archive");
    expect.verifySteps(["customArchive"]);
});

test(`add custom static action menu`, async () => {
    const listView = registry.category("views").get("list");
    class CustomListController extends listView.Controller {
        getStaticActionMenuItems() {
            const menuItems = super.getStaticActionMenuItems();
            menuItems.customAvailable = {
                isAvailable: () => true,
                description: "Custom Available",
                sequence: 35,
                callback: () => {
                    expect.step("Custom Available");
                },
            };
            menuItems.customNotAvailable = {
                isAvailable: () => false,
                description: "Custom Not Available",
                callback: () => {
                    expect.step("Custom Not Available");
                },
            };
            menuItems.customDefaultAvailable = {
                description: "Custom Default Available",
                callback: () => {
                    expect.step("Custom Default Available");
                },
            };
            return menuItems;
        }
    }
    registry.category("views").add("custom_list", {
        ...listView,
        Controller: CustomListController,
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="custom_list"><field name="foo"/></list>`,
        actionMenus: {},
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts(`.o-dropdown--menu .dropdown-item`)).toEqual([
        "Custom Default Available",
        "Export",
        "Duplicate",
        "Custom Available",
        "Delete",
    ]);

    await toggleMenuItem("Custom Available");
    expect.verifySteps(["Custom Available"]);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Default Available");
    expect.verifySteps(["Custom Default Available"]);
});

test(`grouped, update the count of the group (and ancestors) when a record is deleted`, async () => {
    Foo._records = [
        { id: 121, foo: "blip", bar: true },
        { id: 122, foo: "blip", bar: true },
        { id: 123, foo: "blip", bar: true },
        { id: 124, foo: "blip", bar: true },
        { id: 125, foo: "blip", bar: false },
        { id: 126, foo: "blip", bar: false },
    ];
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="1"><field name="foo"/></list>`,
        groupBy: ["foo", "bar"],
        actionMenus: {},
    });
    expect(`.o_group_header:eq(0)`).toHaveText("blip (6)");
    expect(`.o_group_header:eq(1)`).toHaveText("No (2)");
    expect(`.o_group_header:eq(2)`).toHaveText("Yes (4)");

    await contains(`.o_group_header:eq(2)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_data_row input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    await contains(`.modal .btn-primary`).click();
    expect(`.o_group_header:eq(0)`).toHaveText("blip (5)");
    expect(`.o_group_header:eq(2)`).toHaveText("Yes (3)");
});

test(`grouped list, reload aggregates when a record is deleted`, async () => {
    Foo._records = [
        { id: 121, foo: "blip", int_field: 100 },
        { id: 122, foo: "blip", int_field: 300 },
        { id: 123, foo: "blip", int_field: 700 },
    ];
    await mountView({
        type: "list",
        resModel: "foo",
        arch: /*xml*/ `
            <list expand="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>`,
        groupBy: ["foo"],
        actionMenus: {},
    });

    expect(".o_group_header .o_list_number").toHaveText("1,100");

    await contains(".o_data_row input").click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    await contains(`.modal-footer .btn-primary`).click();
    expect(".o_group_header .o_list_number").toHaveText("1,000");
});

test(`pager (ungrouped and grouped mode), default limit`, async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.limit).toBe(80, {
            message: "default limit should be 80 in List",
        });
    });
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        searchViewArch: `
            <search>
                <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
            </search>
        `,
    });
    expect.verifySteps(["web_search_read"]);
    expect(`div.o_control_panel .o_cp_pager .o_pager`).toHaveCount(1);
    expect(`.o_pager_limit`).toHaveText("4");

    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");
    expect(`.o_pager_limit`).toHaveText("2");
});

test(`pager, ungrouped, with count limit reached`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    let expectedCountLimit = 4;
    stepAllNetworkCalls();
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.count_limit).toBe(expectedCountLimit);
    });
    onRpc("search_count", ({ kwargs }) => {
        expect(kwargs.context.xyz).toBe("abc");
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
        context: { xyz: "abc" },
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await contains(`.o_pager_limit`).click();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("4");
    expect.verifySteps(["search_count"]);

    expectedCountLimit = undefined;
    await contains(`.o_pager_next`).click();
    expect.verifySteps(["web_search_read"]);
});

test(`pager, ungrouped, with count limit reached, click next`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    stepAllNetworkCalls();
    let expectedCountLimit = 4;
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.count_limit).toBe(expectedCountLimit);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    expectedCountLimit = 5;
    await contains(`.o_pager_next`).click();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("3-4");
    expect(`.o_pager_limit`).toHaveText("4");
    expect.verifySteps(["web_search_read"]);
});

test(`pager, ungrouped, with count limit reached, click next (2)`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
    Foo._records.push({ id: 5, bar: true, foo: "xxx" });

    stepAllNetworkCalls();
    let expectedCountLimit = 4;
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.count_limit).toBe(expectedCountLimit);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    expectedCountLimit = 5;
    await contains(`.o_pager_next`).click();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("3-4");
    expect(`.o_pager_limit`).toHaveText("4+");
    expect.verifySteps(["web_search_read"]);

    expectedCountLimit = 7;
    await contains(`.o_pager_next`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_pager_value`).toHaveText("5-5");
    expect(`.o_pager_limit`).toHaveText("5");
    expect.verifySteps(["web_search_read"]);
});

test(`pager, ungrouped, with count limit reached, click previous`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
    Foo._records.push({ id: 5, bar: true, foo: "xxx" });

    stepAllNetworkCalls();
    let expectedCountLimit = 4;
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.count_limit).toBe(expectedCountLimit);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    expectedCountLimit = undefined;
    await contains(`.o_pager_previous`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_pager_value`).toHaveText("5-5");
    expect(`.o_pager_limit`).toHaveText("5");
    expect.verifySteps(["search_count", "web_search_read"]);
});

test(`pager, ungrouped, with count limit reached, edit pager`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
    Foo._records.push({ id: 5, bar: true, foo: "xxx" });

    stepAllNetworkCalls();
    let expectedCountLimit = 4;
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.count_limit).toBe(expectedCountLimit);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    expectedCountLimit = 5;
    await contains(`.o_pager_value`).click();
    // FIXME: we have to click out instead of confirming, because somehow if the
    // web_search_read calls come back too fast when pressing "Enter", another
    // RPC is triggered right after.
    await contains(`input.o_pager_value`).edit("2-4", { confirm: "blur" });
    expect(`.o_data_row`).toHaveCount(3);
    expect(`.o_pager_value`).toHaveText("2-4");
    expect(`.o_pager_limit`).toHaveText("4+");
    expect.verifySteps(["web_search_read"]);

    expectedCountLimit = 15;
    await contains(`.o_pager_value`).click();
    await contains(`input.o_pager_value`).edit("2-14", { confirm: "blur" });
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_pager_value`).toHaveText("2-5");
    expect(`.o_pager_limit`).toHaveText("5");
    expect.verifySteps(["web_search_read"]);
});

test(`pager, ungrouped, with count equals count limit`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 4 });

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("4");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test(`pager, ungrouped, reload while fetching count`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });

    stepAllNetworkCalls();
    const deferred = new Deferred();
    onRpc("search_count", () => deferred);

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await contains(`.o_pager_limit`).click();
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps(["search_count"]);

    await contains(`.o_searchview_input`).press("enter");
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps(["web_search_read"]);

    deferred.resolve();
    await animationFrame();
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([]);
});

test(`pager, ungrouped, next and fetch count simultaneously`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 5 });
    Foo._records.push({ id: 11, foo: "r11", bar: true });
    Foo._records.push({ id: 12, foo: "r12", bar: true });
    Foo._records.push({ id: 13, foo: "r13", bar: true });

    stepAllNetworkCalls();
    let deferred;
    onRpc("web_search_read", () => deferred);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("5+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    deferred = new Deferred();
    await contains(`.o_pager_next`).click(); // this request will be pending
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("5+");
    // can't fetch count simultaneously as it is temporarily disabled while updating
    expect(`.o_pager_limit`).toHaveClass("disabled");
    expect.verifySteps(["web_search_read"]);

    deferred.resolve();
    await animationFrame();
    expect(`.o_pager_limit`).not.toHaveClass("disabled");
});

test(`pager, grouped, with groups count limit reached`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
    Foo._records.push({ id: 398, foo: "ozfijz" }); // to have 4 groups

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list groups_limit="2"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["foo"],
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("4");
});

test(`pager, grouped, with count limit reached`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="1"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["foo"],
    });
    expect(`.o_group_header`).toHaveCount(3, { message: "should have 3 groups" });
    expect(`.o_group_header:first-of-type .o_group_name`).toHaveCount(1, {
        message: "first group should have a name",
    });
    expect(`.o_group_header:first-of-type .o_pager`).toHaveCount(0, {
        message: "pager shouldn't be present until unfolded",
    });

    // unfold
    await contains(`.o_group_header:first-of-type`).click();
    expect(`.o_group_header:first-of-type .o_group_name .o_pager`).toHaveCount(1, {
        message: "first group should have a pager",
    });
    expect(`.o_group_header:first-of-type .o_pager_value`).toHaveText("1");
    expect(`.o_group_header:first-of-type .o_pager_limit`).toHaveText("2");
});

test(`multi-level grouped list, pager inside a group`, async () => {
    for (const record of Foo._records) {
        record.bar = true;
    }

    Foo._records.forEach((r) => (r.bar = true));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2" groups_limit="3"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar", "foo"],
    });
    expect(`.o_group_header`).toHaveCount(1);

    await contains(`.o_group_header`).click();
    expect(`.o_group_header`).toHaveCount(4);
    expect(`.o_group_header:first-of-type .o_group_name .o_pager`).toHaveCount(0);
});

test(`multi-level grouped list, pager inside a group, reload`, async () => {
    for (const record of Foo._records) {
        record.bar = true;
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list groups_limit="2">
                <field name="foo"/>
                <field name="int_field"/>
                <field name="bar"/>
            </list>
        `,
        groupBy: ["bar", "foo"],
    });
    expect(`.o_group_header`).toHaveCount(1);

    await contains(`.o_group_header`).click();
    expect(`.o_group_header`).toHaveCount(3);
    expect(`.o_group_header .o_group_name .o_pager`).toHaveCount(1);
    expect(getPagerValue(queryFirst(`.o_group_header`))).toEqual([1, 2]);
    expect(getPagerLimit(queryFirst(`.o_group_header`))).toBe(3);
    expect(queryAllTexts`td.o_list_number`).toEqual(["32", "5", "17"]);

    await contains(`.o_list_table thead th[data-name=int_field]`).click();
    expect(getPagerValue(queryFirst(`.o_group_header`))).toEqual([1, 2]);
    expect(getPagerLimit(queryFirst(`.o_group_header`))).toBe(3);
    expect(queryAllTexts`td.o_list_number`).toEqual(["32", "5", "10"]);
});

test(`count_limit attrs set in arch`, async () => {
    stepAllNetworkCalls();
    let expectedCountLimit = 4;
    onRpc("web_search_read", ({ kwargs }) => {
        expect(kwargs.count_limit).toBe(expectedCountLimit);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2" count_limit="3"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("3+");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await contains(`.o_pager_limit`).click();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_pager_value`).toHaveText("1-2");
    expect(`.o_pager_limit`).toHaveText("4");
    expect.verifySteps(["search_count"]);

    expectedCountLimit = undefined;
    await contains(`.o_pager_next`).click();
    expect.verifySteps(["web_search_read"]);
});

test(`pager, grouped, pager limit should be based on the group's count`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
    Foo._records = [
        { id: 121, foo: "blip" },
        { id: 122, foo: "blip" },
        { id: 123, foo: "blip" },
        { id: 124, foo: "blip" },
        { id: 125, foo: "blip" },
        { id: 126, foo: "blip" },
    ];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["foo"],
    });

    // unfold
    await contains(`.o_group_header:first-of-type`).click();
    expect(`.o_group_header:first-of-type .o_pager_limit`).toHaveText("6");
});

test(`pager, grouped, group pager should update after removing a filter`, async () => {
    patchWithCleanup(RelationalModel, { DEFAULT_COUNT_LIMIT: 3 });
    Foo._records = [
        { id: 121, foo: "aaa" },
        { id: 122, foo: "blip" },
        { id: 123, foo: "blip" },
        { id: 124, foo: "blip" },
        { id: 125, foo: "blip" },
        { id: 126, foo: "blip" },
    ];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/><field name="bar"/></list>`,
        searchViewArch: `
            <search>
                <filter name="foo" domain="[('foo','=','aaa')]"/>
                <filter name="groupby_foo" context="{'group_by': 'bar'}"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");
    await toggleMenuItem("Bar");

    // expand group
    await contains(`th.o_group_name`).click();
    expect(`th.o_group_name .o_pager_counter`).toHaveCount(0);

    // remove filter
    await removeFacet("Foo");
    expect(`th.o_group_name:eq(0) .o_pager_counter`).toHaveText("1-2 / 6");
});

test(`grouped, show only limited records when the list view is initially expanded`, async () => {
    const forcedDefaultLimit = 3;
    patchWithCleanup(RelationalModel, { DEFAULT_LIMIT: forcedDefaultLimit });
    Foo._records = [
        { id: 121, foo: "blip" },
        { id: 122, foo: "blip" },
        { id: 123, foo: "blip" },
        { id: 124, foo: "blip" },
        { id: 125, foo: "blip" },
        { id: 126, foo: "blip" },
    ];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="1"><field name="foo"/></list>`,
        groupBy: ["foo"],
    });
    expect(`.o_data_row`).toHaveCount(forcedDefaultLimit);
});

test(`list keeps offset on switchView`, async () => {
    Foo._views = {
        search: `<search/>`,
        "list,99": `<list limit="1"><field name="display_name"/></list>`,
        "form,100": `<form><field name="display_name"/></form>`,
    };

    const offsets = [0, 1, 1];
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.offset).toBe(offsets.shift());
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [
            [99, "list"],
            [100, "form"],
        ],
    });
    expect.verifySteps(["web_search_read"]);

    await contains(`.o_pager_next`).click();
    expect.verifySteps(["web_search_read"]);

    await contains(`.o_data_cell`).click();
    await contains(`.o_back_button`).click();
    expect.verifySteps(["web_search_read"]);
});

test(`Navigate between the list and kanban view using the command palette`, async () => {
    Foo._views = {
        search: `<search/>`,
        list: `<list><field name="display_name"/></list>`,
        kanban: `
            <kanban class="o_kanban_test">
                <templates><t t-name="card">
                    <field name="foo"/>
                </t></templates>
            </kanban>
        `,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "kanban"],
        ],
    });
    expect(`.o_cp_switch_buttons`).toHaveCount(1);
    expect(`.o_switch_view`).toHaveCount(2);
    expect(`.o_list_view`).toHaveCount(1);

    await press("control+k");
    await animationFrame();
    expect(`.o_command_category .o_command:contains(Show Kanban view)`).toHaveCount(1);

    await contains(`.o_command:contains(Show Kanban view)`).click();
    expect(`.o_kanban_view`).toHaveCount(1);

    await press("control+k");
    await animationFrame();
    expect(`.o_command_category .o_command:contains(Show List view)`).toHaveCount(1);

    await contains(`.o_command:contains(Show List view)`).click();
    expect(`.o_list_view`).toHaveCount(1);
});

test(`grouped list keeps offset on switchView`, async () => {
    Foo._views = {
        search: `
            <search>
                <filter string="IntField" name="groupby" domain="[]" context="{'group_by': 'int_field'}"/>
            </search>
        `,
        "list,99": `<list groups_limit="1"><field name="display_name"/></list>`,
        "form,100": `<form><field name="display_name"/></form>`,
    };

    const offsets = [0, 1, 1];
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step("web_read_group");
        expect(kwargs.offset).toBe(offsets.shift());
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [
            [99, "list"],
            [100, "form"],
        ],
        context: {
            search_default_groupby: true,
        },
    });
    expect(`.o_list_view`).toHaveCount(1);
    expect.verifySteps(["web_read_group"]);

    await contains(`.o_pager_next`).click();
    expect(`.o_data_row`).toHaveCount(0);
    expect.verifySteps(["web_read_group"]);

    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(1);

    await contains(`.o_data_cell`).click();
    expect(`.o_form_view`).toHaveCount(1);

    await contains(`.o_back_button`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect.verifySteps(["web_read_group"]);
});

test(`can sort records when clicking on header`, async () => {
    onRpc("web_search_read", () => expect.step("web_search_read"));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
    });
    expect.verifySteps(["web_search_read"]);
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["yop", "blip", "gnap", "blip"]);

    await contains(`thead th:contains(Foo)`).click();
    expect.verifySteps(["web_search_read"]);
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["blip", "blip", "gnap", "yop"]);

    await contains(`thead th:contains(Foo)`).click();
    expect.verifySteps(["web_search_read"]);
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["yop", "gnap", "blip", "blip"]);
});

test(`do not sort records when clicking on header with nolabel`, async () => {
    onRpc("web_search_read", () => expect.step("web_search_read"));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo" nolabel="1"/><field name="int_field"/></list>`,
    });
    expect.verifySteps(["web_search_read"]);
    expect(queryAllTexts(`.o_data_cell`)).toEqual([
        "yop",
        "10",
        "blip",
        "9",
        "gnap",
        "17",
        "blip",
        "-4",
    ]);

    await contains(`thead th:eq(2)`).click();
    expect.verifySteps(["web_search_read"]);
    expect(queryAllTexts(`.o_data_cell`)).toEqual([
        "blip",
        "-4",
        "blip",
        "9",
        "yop",
        "10",
        "gnap",
        "17",
    ]);

    await contains(`thead th:eq(1)`).click();
    expect.verifySteps([]);
    expect(queryAllTexts(`.o_data_cell`)).toEqual([
        "blip",
        "-4",
        "blip",
        "9",
        "yop",
        "10",
        "gnap",
        "17",
    ]);
});

test(`use default_order`, async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.order).toBe("foo ASC", {
            message: "should correctly set the sort attribute",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list default_order="foo"><field name="foo"/><field name="bar"/></list>`,
    });
    expect.verifySteps(["web_search_read"]);
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["blip", "blip", "gnap", "yop"]);
});

test(`use more complex default_order`, async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.order).toBe("foo ASC, bar DESC, int_field ASC", {
            message: "should correctly set the sort attribute",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list default_order="foo, bar desc, int_field">
                <field name="foo"/><field name="bar"/>
            </list>
        `,
    });
    expect.verifySteps(["web_search_read"]);
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["blip", "blip", "gnap", "yop"]);
});

test(`use default_order on editable tree: sort on save`, async () => {
    Foo._records[0].o2m = [1, 3];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="o2m">
                        <list editable="bottom" default_order="name">
                            <field name="name"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(queryAllTexts(`.o_field_x2many_list .o_data_row`)).toEqual(["Value 1", "Value 3"]);

    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_field_widget[name=o2m] .o_field_widget input`).edit("Value 2");
    await contains(`.o_form_view`).click();
    expect(queryAllTexts(`.o_field_x2many_list .o_data_row`)).toEqual([
        "Value 1",
        "Value 3",
        "Value 2",
    ]);

    await clickSave();
    expect(queryAllTexts(`.o_field_x2many_list .o_data_row`)).toEqual([
        "Value 1",
        "Value 2",
        "Value 3",
    ]);
});

test(`use default_order on editable tree: sort on demand`, async () => {
    Foo._records[0].o2m = [1, 3];
    Bar._fields.name = fields.Char();
    Bar._records[0].name = "Value 1";
    Bar._records[2].name = "Value 3";

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="o2m">
                        <list editable="bottom" default_order="name">
                            <field name="name"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(queryAllTexts(`.o_field_x2many_list .o_data_row`)).toEqual(["Value 1", "Value 3"]);

    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_field_widget[name=o2m] .o_field_widget input`).edit("Value 2");
    await contains(`.o_form_view`).click();
    expect(queryAllTexts(`.o_field_x2many_list .o_data_row`)).toEqual([
        "Value 1",
        "Value 3",
        "Value 2",
    ]);

    await contains(`.o_field_widget[name=o2m] .o_column_sortable`).click();
    expect(queryAllTexts(`.o_field_x2many_list .o_data_row`)).toEqual([
        "Value 1",
        "Value 2",
        "Value 3",
    ]);

    await contains(`.o_field_widget[name=o2m] .o_column_sortable`).click();
    expect(queryAllTexts(`.o_field_x2many_list .o_data_row`)).toEqual([
        "Value 3",
        "Value 2",
        "Value 1",
    ]);
});

test(`use default_order on editable tree: sort on demand in page`, async () => {
    Bar._fields.name = fields.Char();

    const ids = [];
    for (let i = 0; i < 45; i++) {
        const id = 4 + i;
        ids.push(id);
        Bar._records.push({
            id: id,
            name: "Value " + (id < 10 ? "0" : "") + id,
        });
    }
    Foo._records[0].o2m = ids;

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="o2m">
                        <list editable="bottom" default_order="name">
                            <field name="name"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_field_widget .o_pager button.o_pager_next`).click();
    expect(queryAllTexts(`.o_data_cell`)).toEqual([
        "Value 44",
        "Value 45",
        "Value 46",
        "Value 47",
        "Value 48",
    ]);

    await contains(`.o_column_sortable`).click();
    expect(queryAllTexts(`.o_data_cell`)).toEqual([
        "Value 08",
        "Value 07",
        "Value 06",
        "Value 05",
        "Value 04",
    ]);
});

test(`can display button in edit mode`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <button name="notafield" type="object" icon="fa-asterisk" class="o_yeah"/>
            </list>
        `,
    });
    expect(`tbody button[name=notafield]`).toHaveCount(4);
    expect(`tbody button[name=notafield].o_yeah`).toHaveCount(4, {
        message: "class o_yeah should be set on the four button",
    });

    await contains(`.o_field_cell`).click();
    expect(`.o_selected_row button[name=notafield]`).toHaveCount(1);
});

test(`can display a list with a many2many field`, async () => {
    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="m2m"/></list>`,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
    expect(queryAllTexts(`.o_data_cell`)).toEqual([
        "2 records",
        "3 records",
        "No records",
        "1 record",
    ]);
});

test(`display a tooltip on a field`, async () => {
    serverState.debug = false;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="bar" widget="boolean_favorite"/>
            </list>
        `,
    });

    await hover(`th[data-name="foo"] div`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--technical`).toHaveCount(0);
    expect(`.o-tooltip`).toHaveCount(1);
    expect(`.o-tooltip`).toHaveText("Foo");

    serverState.debug = true;

    // it is necessary to rerender the list so tooltips can be properly created
    await validateSearch(); // reload view
    await hover(`th[data-name="bar"] div`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--technical`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="widget"]`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="widget"]`).toHaveText(
        "Widget:Favorite (boolean_favorite)"
    );
    expect(`.o-tooltip--technical > li[data-item="label"]`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="label"]`).toHaveText("Label:Bar");
});

test("field (with help) tooltip in non debug mode", async function () {
    serverState.debug = false;
    Foo._fields.foo.help = "This is a foo field";
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `<list><field name="foo"/></list>`,
    });
    await hover(`th[data-name="foo"] div`);
    await runAllTimers();
    expect(`.o-tooltip`).toHaveCount(1);
    expect(`.o-tooltip`).toHaveText("Foo\nThis is a foo field");
});

test(`support row decoration`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list decoration-info="int_field > 5">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`tbody tr.text-info`).toHaveCount(3, {
        message: "should have 3 columns with text-info class",
    });
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });
});

test(`support row decoration (with unset numeric values)`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" decoration-danger="int_field &lt; 0">
                <field name="int_field"/>
            </list>
        `,
    });

    await contains(`.o_list_button_add`).click();
    expect(`tr.o_data_row.text-danger`).toHaveCount(0, {
        message: "the data row should not have .text-danger decoration (int_field is unset)",
    });

    await contains(`[name="int_field"] input`).edit("-3");
    expect(`tr.o_data_row.text-danger`).toHaveCount(1, {
        message: "the data row should have .text-danger decoration (int_field is negative)",
    });
});

test(`support row decoration with date`, async () => {
    Foo._records[0].datetime = "2017-02-27 12:51:35";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list decoration-info="datetime == '2017-02-27 12:51:35'" decoration-danger="datetime &gt; '2017-02-27 12:51:35' and datetime &lt; '2017-02-27 10:51:35'">
                <field name="datetime"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`tbody tr.text-info`).toHaveCount(1, {
        message: "should have 1 columns with text-info class with good datetime",
    });
    expect(`tbody tr.text-danger`).toHaveCount(0, {
        message: "should have 0 columns with text-danger class with wrong timezone datetime",
    });
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });
});

test(`support row decoration (decoration-bf)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list decoration-bf="int_field > 5">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`tbody tr.fw-bold`).toHaveCount(3, {
        message: "should have 3 columns with fw-bold class",
    });
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });
});

test(`support row decoration (decoration-it)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list decoration-it="int_field > 5">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`tbody tr.fst-italic`).toHaveCount(3, {
        message: "should have 3 columns with fst-italic class",
    });
    expect(`tbody tr`).toHaveCount(4, { message: "should have 4 rows" });
});

test(`support field decoration`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo" decoration-danger="int_field > 5"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`tbody tr`).toHaveCount(4);
    expect(`tbody td.o_list_char`).toHaveCount(4);
    expect(`tbody td.text-danger`).toHaveCount(3);
    expect(`tbody td.o_list_number`).toHaveCount(4);
    expect(`tbody td.o_list_number.text-danger`).toHaveCount(0);
});

test(`support field decoration (decoration-bf)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo" decoration-bf="int_field > 5"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`tbody tr`).toHaveCount(4);
    expect(`tbody td.o_list_char`).toHaveCount(4);
    expect(`tbody td.fw-bold`).toHaveCount(3);
    expect(`tbody td.o_list_number`).toHaveCount(4);
    expect(`tbody td.o_list_number.fw-bold`).toHaveCount(0);
});

test(`support field decoration (decoration-it)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo" decoration-it="int_field > 5"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`tbody tr`).toHaveCount(4);
    expect(`tbody td.o_list_char`).toHaveCount(4);
    expect(`tbody td.fst-italic`).toHaveCount(3);
    expect(`tbody td.o_list_number`).toHaveCount(4);
    expect(`tbody td.o_list_number.fst-italic`).toHaveCount(0);
});

test(`bounce create button when no data and click on empty area`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        noContentHelp: "click to add a record",
        searchViewArch: `
            <search>
                <filter name="Empty List" domain="[('id', '&lt;', 0)]"/>
            </search>
        `,
    });
    expect(`.o_view_nocontent`).toHaveCount(0);

    await contains(`.o_list_view`).click();
    expect(`.o_list_button_add`).not.toHaveClass("o_catch_attention");

    await toggleSearchBarMenu();
    await toggleMenuItem("Empty List");
    expect(`.o_view_nocontent`).toHaveCount(1);

    await contains(`.o_list_renderer`).click();
    expect(`.o_list_button_add`).toHaveClass("o_catch_attention");
});

test(`no content helper when no data`, async () => {
    const records = Foo._records.slice(0);
    Foo._records.splice(0);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        noContentHelp: "click to add a partner",
    });
    expect(`.o_view_nocontent`).toHaveCount(1, { message: "should display the no content helper" });
    expect(`.o_list_view table`).toHaveCount(1, { message: "should have a table in the dom" });
    expect(`.o_view_nocontent`).toHaveText("click to add a partner");

    Foo._records.push(...records);
    await contains(`.o_searchview_input`).press("enter");
    expect(`.o_view_nocontent`).toHaveCount(0, {
        message: "should not display the no content helper",
    });
});

test(`no nocontent helper when no data and no help`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
    });
    expect(`.o_view_nocontent`).toHaveCount(0, {
        message: "should not display the no content helper",
    });
    expect(`tr.o_data_row`).toHaveCount(0, { message: "should not have any data row" });
    expect(`.o_list_view table`).toHaveCount(1, { message: "should have a table in the dom" });
});

test(`empty list with sample data`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
                <field name="m2o"/>
                <field name="m2m" widget="many2many_tags"/>
                <field name="date"/>
                <field name="datetime"/>
            </list>
        `,
        context: { search_default_empty: true },
        noContentHelp: "click to add a partner",
        searchViewArch: `
            <search>
                <filter name="empty" domain="[('id', '&lt;', 0)]"/>
                <filter name="True Domain" domain="[(1,'=',1)]"/>
                <filter name="False Domain" domain="[(1,'=',0)]"/>
            </search>
        `,
    });
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);
    expect(`.o_nocontent_help`).toHaveCount(1);

    // Check list sample data
    expect(`.o_data_row .o_data_cell:eq(0)`).toHaveText("", {
        message: "Char field should yield an empty element",
    });
    expect(`.o_data_row .o_data_cell:eq(1) .o-checkbox`).toHaveCount(1, {
        message: "Boolean field has been instantiated",
    });

    const cells = queryAllTexts(`.o_data_row:eq(0) > .o_data_cell`);
    expect(isNaN(cells[2])).toBe(false, { message: "Integer value is a number" });
    expect(!!cells[3]).toBe(true, { message: "Many2one field is a string" });
    expect(cells[4]).not.toHaveLength(0, {
        message: "Many2many contains at least one string tag",
    });
    expect(cells[5]).toMatch(/\d{2}\/\d{2}\/\d{4}/, {
        message: "Date field should have the right format",
    });
    expect(cells[6]).toMatch(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}/, {
        message: "Datetime field should have the right format",
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("empty");
    await toggleMenuItem("False Domain");
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_nocontent_help`).toHaveCount(1);

    await toggleMenuItem("False Domain");
    await toggleMenuItem("True Domain");
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_nocontent_help`).toHaveCount(0);
});

test(`refresh empty list with sample data`, async () => {
    Foo._views = {
        search: `
            <search>
                <filter name="empty" domain="[('id', '&lt;', 0)]"/>
            </search>
        `,
        list: `
            <list sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
                <field name="m2o"/>
                <field name="m2m" widget="many2many_tags"/>
                <field name="date"/>
                <field name="datetime"/>
            </list>
        `,
        kanban: `<kanban/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "kanban"],
        ],
        context: { search_default_empty: true },
        help: '<p class="hello">click to add a partner</p>',
    });
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);
    expect(`.o_nocontent_help`).toHaveCount(1);

    const textContent = queryText`.o_list_view table`;
    await contains(`.o_cp_switch_buttons .o_list`).click();
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);
    expect(`.o_nocontent_help`).toHaveCount(1);
    expect(`.o_list_view table`).toHaveText(textContent);
});

test(`empty list with sample data: toggle optional field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list sample="1">
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
            </list>
        `,
        domain: Domain.FALSE.toList(),
    });
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_data_row`).toHaveCount();
    expect(`th`).toHaveCount(3, {
        message: "should have 3 th, 1 for selector, 1 for foo and 1 for optional columns",
    });
    expect(`table .o_optional_columns_dropdown`).toHaveCount(1);

    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    await contains(`.o-dropdown--menu span.dropdown-item:eq(0) label`).click();
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_data_row`).toHaveCount();
    expect(`th`).toHaveCount(4);
});

test(`empty list with sample data: keyboard navigation`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
            </list>`,
        domain: Domain.FALSE.toList(),
    });

    // Check keynav is disabled
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");

    // From search bar
    expect(`.o_searchview_input`).toBeFocused();

    await press("arrowdown");
    await animationFrame();
    expect(`.o_searchview_input`).toBeFocused();

    // From 'Create' button
    await pointerDown(".o_list_button_add");
    await animationFrame();
    expect(`.o_list_button_add`).toBeFocused();

    await press("arrowdown");
    await animationFrame();
    expect(`.o_list_button_add`).toBeFocused();

    await press("tab");
    await animationFrame();
    expect(`.o-tooltip--string`).toHaveCount(0);
});

test(`empty list with sample data: group by date`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list sample="1">
                <field name="date"/>
            </list>`,
        domain: Domain.FALSE.toList(),
        groupBy: ["date:day"],
    });
    expect(`.o_list_view .o_view_sample_data`).toHaveCount(1);
    expect(`.o_group_header`).toHaveCount();

    await contains(`.o_group_has_content.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(4);
});

test(`non empty list with sample data`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
            </list>
        `,
        domain: Domain.TRUE.toList(),
        context: { search_default_true_domain: true },
        searchViewArch: `
            <search>
                <filter name="true_domain" domain="[(1,'=',1)]"/>
                <filter name="false_domain" domain="[(1,'=',0)]"/>
            </search>
        `,
    });
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");

    await toggleSearchBarMenu();
    await toggleMenuItem("true_domain");
    await toggleMenuItem("false_domain");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
});

test(`click on header in empty list with sample data`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
            </list>
        `,
        domain: Domain.FALSE.toList(),
    });
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);

    const content = queryText`.o_list_view`;
    await contains(`tr .o_column_sortable`).click();
    expect(`.o_list_view`).toHaveText(content, {
        message: "the content should still be the same",
    });
});

test(`non empty editable list with sample data: delete all records`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
            </list>
        `,
        domain: Domain.TRUE.toList(),
        noContentHelp: "click to add a partner",
        actionMenus: {},
    });

    // Initial state: all records displayed
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_nocontent_help`).toHaveCount(0);

    // Delete all records
    await contains(`thead .o_list_record_selector input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    await contains(`.modal-footer .btn-primary`).click();

    // Final state: no more sample data, but nocontent helper displayed
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_nocontent_help`).toHaveCount(1);
});

test(`empty editable list with sample data: start create record and cancel`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
            </list>
        `,
        domain: Domain.FALSE.toList(),
        noContentHelp: "click to add a partner",
    });

    // Initial state: sample data and nocontent helper displayed
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);
    expect(`.o_nocontent_help`).toHaveCount(1);

    // Start creating a record
    await contains(`.o_list_button_add`).click();
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_data_row`).toHaveCount(1);

    // Discard temporary record
    await contains(`.o_list_button_discard`).click();

    // Final state: there should be no table, but the no content helper
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_nocontent_help`).toHaveCount(1);
});

test(`empty editable list with sample data: create and delete record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
            </list>
        `,
        domain: Domain.FALSE.toList(),
        noContentHelp: "click to add a partner",
        actionMenus: {},
    });

    // Initial state: sample data and nocontent helper displayed
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);
    expect(`.o_nocontent_help`).toHaveCount(1);

    // Start creating a record
    await contains(`.o_list_button_add`).click();
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_data_row`).toHaveCount(1);

    // Save temporary record
    await contains(`.o_list_button_save`).click();
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_nocontent_help`).toHaveCount(0);

    // Delete newly created record
    await contains(`.o_data_row input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Delete");
    await contains(`.modal-footer .btn-primary`).click();

    // Final state: there should be no table, but the no content helper
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_nocontent_help`).toHaveCount(1);
});

test(`empty editable list with sample data: create and duplicate record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" sample="1">
                <field name="foo"/>
                <field name="bar"/>
                <field name="int_field"/>
            </list>
        `,
        domain: [["int_field", "=", 0]],
        noContentHelp: "click to add a partner",
        actionMenus: {},
    });

    // Initial state: sample data and nocontent helper displayed
    expect(`.o_list_view .o_content`).toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);
    expect(`.o_nocontent_help`).toHaveCount(1);

    // Start creating a record
    await contains(`.o_list_button_add`).click();
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_data_row`).toHaveCount(1);

    // Save temporary record
    await contains(`.o_list_button_save`).click();
    expect(`.o_list_view .o_content`).not.toHaveClass("o_view_sample_data");
    expect(`.o_list_table`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_nocontent_help`).toHaveCount(0);

    // Duplicate newly created record
    await contains(`.o_data_row input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Duplicate");

    // Final state: there should be 2 records
    expect(`.o_list_view .o_content .o_data_row`).toHaveCount(2, {
        message: "there should be 2 records",
    });
});

test(`groupby node with a button`, async () => {
    stepAllNetworkCalls();

    mockService("action", {
        doActionButton(params) {
            expect.step(params.name);
            expect(params.resId).toBe(1, { message: "should call with correct id" });
            expect(params.resModel).toBe("res.currency", {
                message: "should call with correct model",
            });
            expect(params.name).toBe("button_method", {
                message: "should call correct method",
            });
            expect(params.type).toBe("object", { message: "should have correct type" });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <groupby name="currency_id">
                    <button string="Button 1" type="object" name="button_method"/>
                </groupby>
            </list>
        `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
    expect(`thead th:not(.o_list_record_selector)`).toHaveCount(1, {
        message: "there should be only one column",
    });

    await selectGroup("currency_id");
    expect.verifySteps(["web_read_group"]);
    expect(`.o_group_header`).toHaveCount(2, { message: "there should be 2 group headers" });
    expect(`.o_group_header button`).toHaveCount(0, {
        message: "there should be no button in the header",
    });

    await contains(`.o_group_header:eq(0)`).click();
    expect.verifySteps(["web_search_read"]);
    expect(`.o_group_header button`).toHaveCount(1);

    await contains(`.o_group_header:eq(0) button`).click();
    expect.verifySteps(["button_method"]);
});

test(`groupby node with a button when many2one is None`, async () => {
    for (const record of Foo._records) {
        record.currency_id = false;
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list default_group_by="currency_id">
                <field name="foo"/>
                <groupby name="currency_id">
                    <field name="display_name"/>
                    <button string="Button 1" type="object" name="button_method"/>
                </groupby>
            </list>
        `,
    });
    expect(`.o_list_table_grouped`).toHaveCount(1);
    expect(`.o_group_header.o_group_open button`).toHaveCount(0);

    await contains(`.o_group_header:first-child`).click();
    expect(`.o_group_header.o_group_open`).toHaveCount(1);
    expect(`.o_group_header button`).toHaveCount(0);
});

test(`groupby node with a button in inner groupbys`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <groupby name="currency_id">
                    <button string="Button 1" type="object" name="button_method"/>
                </groupby>
            </list>
        `,
        groupBy: ["bar", "currency_id"],
    });
    expect(`.o_group_header`).toHaveCount(2, { message: "there should be 2 group headers" });
    expect(`.o_group_header button`).toHaveCount(0);

    await contains(`.o_group_header:eq(0)`).click();
    expect(`.o_list_view .o_group_header`).toHaveCount(3);
    expect(`.o_group_header button`).toHaveCount(0);

    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_group_header button`).toHaveCount(1);
});

test(`groupby node with a button with modifiers`, async () => {
    stepAllNetworkCalls();
    onRpc("res.currency", "web_read", ({ args, kwargs }) => {
        expect.step("res.currency:web_read");
        expect(args).toEqual([[1, 2]]);
        expect(kwargs.specification).toEqual({ position: {} });
    });

    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list>
                <field name="foo"/>
                <groupby name="currency_id">
                    <field name="position"/>
                    <button string="Button 1" type="object" name="button_method" invisible="position == 'after'"/>
                </groupby>
            </list>`,
        groupBy: ["currency_id"],
    });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_read",
        "res.currency:web_read",
    ]);
    expect(`.o_group_header button`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(0);

    await contains(`.o_group_header:eq(1)`).click();
    expect.verifySteps(["web_search_read"]);
    expect(`.o_group_header button`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(1);

    await contains(`.o_group_header:eq(0)`).click();
    expect.verifySteps(["web_search_read"]);
    expect(`.o_group_header button`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);
});

test(`groupby node with a button with modifiers using a many2one`, async () => {
    Currency._fields.m2o = fields.Many2one({ relation: "bar" });
    Currency._records[0].m2o = 1;

    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list expand="1">
                <field name="foo"/>
                <groupby name="currency_id">
                    <field name="m2o"/>
                    <button string="Button 1" type="object" name="button_method" invisible="not m2o"/>
                </groupby>
            </list>
        `,
        groupBy: ["currency_id"],
    });
    expect(`.o_group_header:eq(0) button`).toHaveCount(1);
    expect(`.o_group_header:eq(1) button`).toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
        "web_read",
    ]);
});

test(`reload list view with groupby node`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list expand="1">
                <field name="foo"/>
                <groupby name="currency_id">
                    <field name="position"/>
                    <button string="Button 1" type="object" name="button_method" invisible="position == 'after'"/>
                </groupby>
            </list>
        `,
        groupBy: ["currency_id"],
    });
    expect(`.o_group_header button`).toHaveCount(1);

    await contains(`.o_searchview_input`).press("enter");
    expect(`.o_group_header button`).toHaveCount(1);
});

test(`editable list view with groupby node and modifiers`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list expand="1" editable="bottom">
                <field name="foo"/>
                <groupby name="currency_id">
                    <field name="position"/>
                    <button string="Button 1" type="object" name="button_method" invisible="position == 'after'"/>
                </groupby>
            </list>
        `,
        groupBy: ["currency_id"],
    });
    expect(`.o_data_row:eq(0)`).not.toHaveClass("o_selected_row", {
        message: "first row should be in readonly mode",
    });

    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row", {
        message: "the row should be in edit mode",
    });

    await contains(`.o_data_cell input`).press("escape");
    expect(`.o_data_row:eq(0)`).not.toHaveClass("o_selected_row", {
        message: "the row should be back in readonly mode",
    });
});

test(`groupby node with edit button`, async () => {
    mockService("action", {
        doAction(action) {
            expect.step("doAction");
            expect(action).toEqual({
                context: { create: false },
                res_id: 2,
                res_model: "res.currency",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                flags: { mode: "edit" },
            });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list expand="1">
                <field name="foo"/>
                <groupby name="currency_id">
                    <button string="Button 1" type="edit" name="edit"/>
                </groupby>
            </list>
        `,
        groupBy: ["currency_id"],
    });

    await contains(`.o_group_header button:eq(1)`).click();
    expect.verifySteps(["doAction"]);
});

test(`groupby node with subfields, and onchange`, async () => {
    Foo._onChanges = {
        foo() {},
    };

    onRpc("onchange", ({ args }) => {
        expect.step("onchange");
        expect(args[3]).toEqual(
            {
                currency_id: {
                    fields: {
                        display_name: {},
                    },
                },
                foo: {},
            },
            { message: "onchange spec should not follow relation of many2one fields" }
        );
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" expand="1">
                <field name="foo"/>
                <field name="currency_id"/>
                <groupby name="currency_id">
                    <field name="position" column_invisible="1"/>
                </groupby>
            </list>
        `,
        groupBy: ["currency_id"],
    });
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    expect.verifySteps(["onchange"]);
});

test(`list view, editable, without data`, async () => {
    Foo._records = [];
    Foo._fields.date = fields.Date({ default: "2017-02-10" });

    onRpc("web_save", () => {
        expect.step("web_save");
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="date"/>
                <field name="m2o"/>
                <field name="foo"/>
                <button type="object" icon="fa-plus-square" name="method"/>
            </list>
        `,
        noContentHelp: "click to add a partner",
    });

    expect(`.o_view_nocontent`).toHaveCount(1, {
        message: "should have a no content helper displayed",
    });
    expect(`div.table-responsive`).toHaveCount(1, {
        message: "should have a div.table-responsive",
    });
    expect(`table`).toHaveCount(1, { message: "should have rendered a table" });

    await contains(`.o_list_button_add`).click();
    expect(`.o_view_nocontent`).toHaveCount(0, {
        message: "should not have a no content helper displayed",
    });
    expect(`tbody tr:eq(0)`).toHaveClass("o_selected_row", {
        message: "the date field td should be in edit mode",
    });
    expect(`tbody tr:eq(0) td:eq(1)`).toHaveText("", {
        message: "the date field td should not have any content",
    });
    expect(`tr.o_selected_row .o_list_record_selector input`).toHaveProperty("disabled", true, {
        message: "record selector checkbox should be disabled while the record is not yet created",
    });
    expect(`.o_list_button button:eq(0)`).toHaveProperty("disabled", false, {
        message: "buttons should not be disabled while the record is not yet created",
    });

    await contains(`.o_list_button_save`).click();
    expect(`tbody tr .o_list_record_selector input`).toHaveProperty("disabled", false, {
        message: "record selector checkbox should not be disabled once the record is created",
    });
    expect(`.o_list_button button:eq(0)`).toHaveProperty("disabled", false, {
        message: "buttons should not be disabled once the record is created",
    });
    expect.verifySteps(["web_save"]);
});

test(`list view, editable, with a button`, async () => {
    Foo._records = [];

    onRpc("web_save", () => {
        expect.step("web_save");
    });
    onRpc("/web/dataset/call_button/*", () => {
        expect.step("call_button");
        return true;
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <button string="abc" icon="fa-phone" type="object" name="schedule_another_phonecall"/>
            </list>
        `,
    });
    await contains(`.o_list_button_add`).click();
    expect(`table button i.o_button_icon.fa-phone`).toHaveCount(1, {
        message: "should have rendered a button",
    });
    expect(`table button:eq(0)`).toHaveProperty("disabled", false, {
        message: "button should not be disabled when creating the record",
    });

    await contains(`table button`).click();
    // clicking the button should save the record and then execute the action
    expect.verifySteps(["web_save", "call_button"]);
});

test(`list view with a button without icon`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <button string="abc" type="object" name="schedule_another_phonecall"/>
            </list>
        `,
    });
    expect(`table button:eq(0)`).toHaveText("abc", {
        message: "should have rendered a button with string attribute as label",
    });
});

test(`list view, editable, can discard`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    expect(`td:not(.o_list_record_selector) input`).toHaveCount(0, {
        message: "no input should be in the table",
    });
    expect(`.o_list_button_discard`).toHaveCount(0);

    await contains(`.o_data_cell`).click();
    expect(`td:not(.o_list_record_selector) input`).toHaveCount(1, {
        message: "first cell should be editable",
    });
    expect(`.o_list_button_discard`).toHaveCount(1);

    await contains(`.o_list_button_discard:not(.dropdown-item)`).click();
    expect(`td:not(.o_list_record_selector) input`).toHaveCount(0, {
        message: "no input should be in the table",
    });
    expect(`.o_list_button_discard`).toHaveCount(0);
});

test(`editable list view, click on the list to save`, async () => {
    Foo._records = [];
    Foo._fields.date = fields.Date({ default: "2017-02-10" });

    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="int_field" sum="Sum"/>
            </list>
        `,
    });
    await contains(`.o_list_button_add`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    await contains(`.o_list_renderer`).click();
    expect.verifySteps(["web_save"]);

    await contains(`.o_list_button_add`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    await contains(`tfoot`).click();
    expect.verifySteps(["web_save"]);

    await contains(`.o_list_button_add`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    await contains(`tbody tr:eq(2) .o_data_cell`).click();
    expect.verifySteps(["web_save"]);
});

test(`editable list view, should refocus date field`, async () => {
    mockDate("2017-02-10 12:00:00");

    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="date"/>
            </list>
        `,
    });
    await contains(`.o_list_button_add`).click();
    expect(`.o_field_widget[name=foo] input`).toBeFocused();

    await contains(`.o_field_widget[name=date] input`).click();
    expect(`.o_field_widget[name=date] input`).toBeFocused();
    expect(`.o_datetime_picker`).toHaveCount(1);

    await contains(getPickerCell("15")).click();
    expect(`.o_datetime_picker`).toHaveCount(0);
    expect(`.o_field_widget[name=date] input`).toHaveValue("02/15/2017");
    expect(`.o_field_widget[name=date] input`).toBeFocused();
});

test(`text field should keep it's selection when clicking on it`, async () => {
    Foo._records[0].text = "1234";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" limit="1">
                <field name="text"/>
            </list>
        `,
    });
    await contains(`td[name=text]`).click();
    expect(window.getSelection().toString()).toBe("1234", {
        message: "the entire content should be selected on initial click",
    });

    Object.assign(queryOne("[name=text] textarea"), {
        selectionStart: 0,
        selectionEnd: 1,
    });

    await contains(`[name=text] textarea`).click();
    expect(window.getSelection().toString()).toBe("1", {
        message: "the selection shouldn't be changed",
    });
});

test(`click on a button cell in a list view`, async () => {
    Foo._records[0].foo = "bar";

    mockService("action", {
        doActionButton(action) {
            expect.step("doActionButton");
            action.onClose();
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" limit="1">
                <field name="foo"/>
                <button name="action_do_something" type="object" string="Action"/>
            </list>
        `,
    });
    await contains(`.o_data_cell.o_list_button`).click();
    expect(window.getSelection().toString()).toBe("bar", {
        message: "Focus should have returned to the editable cell without throwing an error",
    });
    expect(`.o_selected_row`).toHaveCount(1);
    expect.verifySteps([]);
});

test(`click on a button in a list view`, async () => {
    mockService("action", {
        doActionButton(action) {
            expect.step("doActionButton");
            expect(action.resId).toBe(1, { message: "should call with correct id" });
            expect(action.resModel).toBe("foo", { message: "should call with correct model" });
            expect(action.name).toBe("button_action", {
                message: "should call correct method",
            });
            expect(action.type).toBe("object", { message: "should have correct type" });
            action.onClose();
        },
    });

    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <button string="a button" name="button_action" icon="fa-car" type="object"/>
            </list>
        `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
    expect(`tbody .o_list_button`).toHaveCount(4, {
        message: "there should be one button per row",
    });
    expect(`.o_data_row .o_list_button .o_button_icon.fa.fa-car`).toHaveCount(4);

    await contains(`.o_data_row .o_list_button button`).click();
    // should have reloaded the view (after the action is complete)
    expect.verifySteps(["doActionButton", "web_search_read"]);
});

test("click on a button in a list view on second page", async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(`web_search_read (offset: ${kwargs.offset})`);
    });
    mockService("action", {
        doActionButton: (action) => {
            expect.step("doActionButton");
            action.onClose();
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list limit="3">
                <field name="foo"/>
                <button string="a button" name="button_action" icon="fa-car" type="object"/>
            </list>
        `,
    });

    expect(".o_data_row").toHaveCount(3);

    await pagerNext();
    expect(".o_data_row").toHaveCount(1);

    await contains(".o_data_row .o_list_button button").click();
    expect(".o_data_row").toHaveCount(1);

    expect.verifySteps([
        "web_search_read (offset: 0)",
        "web_search_read (offset: 3)",
        "doActionButton",
        "web_search_read (offset: 3)",
    ]);
});

test(`invisible attrs in readonly and editable list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <button string="a button" name="button_action" icon="fa-car" type="object" invisible="id == 1"/>
                <field name="int_field"/>
                <field name="qux"/>
                <field name="foo" invisible="id == 1"/>
            </list>
        `,
    });
    expect(`.o_field_cell:eq(2)`).toHaveInnerHTML("");
    expect(`.o_data_cell.o_list_button:eq(0)`).toHaveInnerHTML(
        `<div class="d-flex flex-wrap gap-1"></div>`
    );

    // edit first row
    await contains(`.o_field_cell`).click();
    expect(`.o_field_cell:eq(2)`).toHaveInnerHTML("");
    expect(`.o_data_cell.o_list_button:eq(0)`).toHaveInnerHTML(
        `<div class="d-flex flex-wrap gap-1"></div>`
    );

    await contains(`.o_list_button_discard:not(.dropdown-item)`).click();
    // click on the invisible field's cell to edit first row
    await contains(`.o_field_cell[name=foo]`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
});

test(`monetary fields are properly rendered`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="id"/>
                <field name="amount"/>
                <field name="currency_id" column_invisible="1"/>
            </list>
        `,
    });
    expect(`tbody tr:eq(0) td`).toHaveCount(3, {
        message: "currency_id column should not be in the table",
    });
    expect(`tbody .o_data_row:eq(0) .o_data_cell:nth-child(3)`).toHaveText("1,200.00 €", {
        message: "currency_id column should not be in the table",
    });
    expect(`tbody .o_data_row:eq(1) .o_data_cell:nth-child(3)`).toHaveText("$ 500.00", {
        message: "currency_id column should not be in the table",
    });
});

test(`simple list with date and datetime`, async () => {
    mockTimeZone(+2);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="date"/><field name="datetime"/></list>`,
    });
    expect(`.o_data_row .o_data_cell:eq(0)`).toHaveText("01/25/2017", {
        message: "should have formatted the date",
    });
    expect(`.o_data_row .o_data_cell:eq(1)`).toHaveText("12/12/2016 12:55:05", {
        message: "should have formatted the datetime",
    });
});

test(`edit a row by clicking on a readonly field`, async () => {
    Foo._fields.foo = fields.Char({ readonly: true });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="int_field"/></list>`,
    });

    // edit the first row
    await contains(`.o_field_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row", {
        message: "first row should be selected",
    });
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_readonly_modifier");
    expect(`.o_selected_row .o_field_widget[name=foo] span`).toHaveText("yop", {
        message: "a widget should have been rendered for readonly fields",
    });
    expect(`.o_selected_row .o_field_widget[name=int_field] input`).toHaveCount(1, {
        message: "'int_field' should be editable",
    });

    // click again on readonly cell of first line: nothing should have changed
    await contains(`.o_field_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_readonly_modifier");
    expect(`.o_selected_row .o_field_widget[name=int_field] input`).toHaveCount(1, {
        message: "'int_field' should be editable",
    });
});

test(`list view with nested groups`, async () => {
    Foo._records.push({ id: 5, foo: "blip", int_field: -7, m2o: 1 });
    Foo._records.push({ id: 6, foo: "blip", int_field: 5, m2o: 2 });

    onRpc("web_read_group", ({ kwargs }) => {
        if (kwargs.groupby[0] === "foo") {
            // nested read_group
            // called twice (once when opening the group, once when sorting)
            expect(kwargs.domain).toEqual([["m2o", "=", 1]], {
                message: "nested read_group should be called with correct domain",
            });
        }
        expect.step("web_read_group");
    });
    onRpc("web_search_read", ({ kwargs }) => {
        // called twice (once when opening the group, once when sorting)
        expect(kwargs.domain).toEqual(
            [
                ["foo", "=", "blip"],
                ["m2o", "=", 1],
            ],
            { message: "nested web_search_read should be called with correct domain" }
        );
        expect.step("web_search_read");
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="id"/><field name="int_field"/></list>`,
        groupBy: ["m2o", "foo"],
        selectRecord(resId, options) {
            expect.step(`switch to form - resId: ${resId}`);
        },
    });
    expect.verifySteps(["web_read_group"]);

    // basic rendering tests
    expect(`.o_group_header`).toHaveCount(2);
    expect(queryAllTexts(`.o_group_name`)).toEqual(["Value 1 (4)", "Value 2 (2)"]);
    expect(`.o_group_name .fa-caret-right`).toHaveCount(2);
    expect(`.o_group_header:eq(0) span`).toHaveStyle({ "--o-list-group-level": "0" });
    expect(queryAllTexts(`.o_group_header .o_list_number`)).toEqual(["13", "16", "8", "14"]);

    // open the first group
    await contains(`.o_group_header:eq(0)`).click();
    expect.verifySteps(["web_read_group"]);
    expect(queryAllTexts(`.o_group_name`)).toEqual([
        "Value 1 (4)",
        "blip (2)",
        "gnap (1)",
        "yop (1)",
        "Value 2 (2)",
    ]);
    expect(`.o_group_name:eq(0) .fa-caret-down`).toHaveCount(1);
    expect(`.o_group_header:eq(1) span`).toHaveStyle({ "--o-list-group-level": "1" });
    expect(queryAllTexts(`.o_group_header .o_list_number`)).toEqual([
        "13",
        "16",
        "9",
        "-11",
        "3",
        "17",
        "1",
        "10",
        "8",
        "14",
    ]);

    // open subgroup
    await contains(`.o_group_header:eq(1)`).click();
    expect.verifySteps(["web_search_read"]);
    expect(`.o_group_header`).toHaveCount(5);
    expect(`.o_data_row`).toHaveCount(2);
    expect(queryAllTexts(`.o_data_row .o_data_cell`)).toEqual(["4", "-4", "5", "-7"]);

    // open a record (should trigger event 'open_record')
    await contains(`.o_data_row .o_data_cell`).click();
    expect.verifySteps([`switch to form - resId: 4`]);

    // sort by int_field (ASC) and check that open groups are still open
    await contains(`.o_list_view thead [data-name='int_field']`).click();
    expect.verifySteps(["web_read_group", "web_read_group", "web_search_read"]);
    expect(`.o_group_header`).toHaveCount(5);
    expect(`.o_data_row`).toHaveCount(2);
    expect(queryAllTexts(`.o_data_row .o_data_cell`)).toEqual(["5", "-7", "4", "-4"]);

    // close first level group
    await contains(`.o_group_header:eq(1)`).click();
    expect.verifySteps([]);
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_group_name .fa-caret-right`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(0);
});

test(`grouped list on selection field at level 2`, async () => {
    Foo._fields.priority = fields.Selection({
        selection: [
            [1, "Low"],
            [2, "Medium"],
            [3, "High"],
        ],
        default: 1,
    });
    Foo._records.push({
        id: 5,
        foo: "blip",
        int_field: -7,
        m2o: 1,
        priority: 2,
    });
    Foo._records.push({
        id: 6,
        foo: "blip",
        int_field: 5,
        m2o: 1,
        priority: 3,
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="id"/><field name="int_field"/></list>`,
        groupBy: ["m2o", "priority"],
    });
    expect(`.o_group_header`).toHaveCount(2, { message: "should contain 2 groups at first level" });

    // open the first group
    await contains(`.o_group_header`).click();
    expect(`.o_group_header`).toHaveCount(5, {
        message: "should contain 2 groups at first level and 3 groups at second level",
    });
    expect(queryAllTexts(`.o_group_header .o_group_name`)).toEqual([
        "Value 1 (5)",
        "Low (3)",
        "Medium (1)",
        "High (1)",
        "Value 2 (1)",
    ]);
});

test(`grouped list with a pager in a group`, async () => {
    Foo._records[3].bar = true;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
        limit: 3,
    });
    const headerHeight = queryFirst(`.o_group_header`).offsetHeight;
    // basic rendering checks
    await contains(`.o_group_header`).click();
    expect(queryFirst(`.o_group_header`).offsetHeight).toBe(headerHeight, {
        message: "height of group header shouldn't have changed",
    });
    expect(`.o_group_header th nav`).toHaveClass("o_pager", {
        message: "last cell of open group header should have classname 'o_pager'",
    });
    expect(`.o_group_header .o_pager .o_pager_value`).toHaveText("1-3");
    expect(`.o_data_row`).toHaveCount(3);

    // go to next page
    await contains(`.o_group_header .o_pager button.o_pager_next`).click();
    expect(`.o_group_header .o_pager .o_pager_value`).toHaveText("4-4");
    expect(`.o_data_row`).toHaveCount(1);
});

test(`edition: create new line, then discard`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="bar"/></list>`,
    });
    expect(`tr.o_data_row`).toHaveCount(4, { message: "should have 4 records" });
    expect(`.o_list_button_add`).toHaveCount(1);
    expect(`.o_list_button_discard`).toHaveCount(0);
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);

    await contains(`.o_list_button_add`).click();
    expect(`.o_list_button_add`).toHaveCount(0);
    expect(`.o_list_button_discard`).toHaveCount(1);
    expect(`.o_list_record_selector input:enabled`).toHaveCount(0);

    await contains(`.o_list_button_discard:not(.dropdown-item)`).click();
    expect(`tr.o_data_row`).toHaveCount(4, { message: "should still have 4 records" });
    expect(`.o_list_button_add`).toHaveCount(1);
    expect(`.o_list_button_discard`).toHaveCount(0);
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);
});

test(`invisible attrs on fields are re-evaluated on field change`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo" invisible="bar"/>
                <field name="bar"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["", "", "", "blip"]);

    // Make first line editable
    await contains(`.o_field_cell`).click();
    expect(`.o_selected_row .o_list_char .o_field_widget[name=foo]`).toHaveCount(0);

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_list_char .o_field_widget[name=foo]`).toHaveCount(1);
    expect(`.o_list_char input`).toHaveValue("yop");
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["", "", "", "blip"]);

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_list_char .o_field_widget[name=foo]`).toHaveCount(0);
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["", "", "", "blip"]);

    // Reswitch the field to visible and save the row
    await contains(`.o_field_widget[name=bar] input`).click();
    await contains(`.o_list_button_save`).click();
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["yop", "", "", "blip"]);
});

test(`readonly attrs on fields are re-evaluated on field change`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo" readonly="bar"/>
                <field name="bar"/>
            </list>
        `,
    });

    // Make first line editable
    await contains(`.o_field_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_selected_row .o_field_widget[name=foo] span`).toHaveCount(1);
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_field_widget[name=foo] input`).toHaveCount(1);
    expect(`.o_selected_row .o_field_widget[name=foo]`).not.toHaveClass("o_readonly_modifier");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_field_widget[name=foo] span`).toHaveCount(1);
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_field_widget[name=foo] input`).toHaveCount(1);
    expect(`.o_selected_row .o_field_widget[name=foo]`).not.toHaveClass("o_readonly_modifier");

    // Click outside to leave edition mode and make first line editable again
    await contains(`.o_control_panel`).click();
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`.o_field_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_selected_row .o_field_widget[name=foo] input`).toHaveCount(1);
    expect(`.o_selected_row .o_field_widget[name=foo]`).not.toHaveClass("o_readonly_modifier");
});

test(`required attrs on fields are re-evaluated on field change`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo" required="bar"/>
                <field name="bar"/>
            </list>
        `,
    });

    // Make first line editable
    await contains(`.o_field_cell`).click();
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_required_modifier");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_field_widget[name=foo]`).not.toHaveClass("o_required_modifier");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_required_modifier");

    // Reswitch the field to required and save the row and make first line editable again
    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_selected_row .o_field_widget[name=foo]`).not.toHaveClass("o_required_modifier");

    await contains(`.o_list_button_save`).click();
    await contains(`.o_field_cell`).click();
    expect(`.o_selected_row .o_field_widget[name=foo]`).not.toHaveClass("o_required_modifier");
});

test(`modifiers of other x2many rows a re-evaluated when a subrecord is updated`, async () => {
    // In an x2many, a change on a subrecord might trigger an onchange on the x2many that
    // updates other sub-records than the edited one. For that reason, modifiers must be
    // re-evaluated.
    Foo._onChanges = {
        o2m(record) {
            record.o2m = [
                [1, 1, { display_name: "Value 1", stage: "open" }],
                [1, 2, { display_name: "Value 2", stage: "draft" }],
            ];
        },
    };
    Foo._records[0].o2m = [1, 2];
    Bar._fields.stage = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["open", "Open"],
        ],
    });
    Bar._records[0].stage = "draft";
    Bar._records[1].stage = "open";

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <field name="o2m">
                    <list editable="top">
                        <field name="display_name" invisible="stage == 'open'"/>
                        <field name="stage"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect(queryAllTexts(`.o_field_widget[name=o2m] .o_data_row .o_data_cell:first-child`)).toEqual(
        ["Value 1", ""]
    );

    // Make a change in the list to trigger the onchange
    await contains(`.o_field_widget[name=o2m] .o_data_row .o_data_cell:eq(1)`).click();
    await contains(`.o_field_widget[name=o2m] .o_data_row [name=stage] select`).select(`"open"`);
    expect(queryAllTexts(`.o_field_widget[name=o2m] .o_data_row .o_data_cell:first-child`)).toEqual(
        ["", "Value 2"]
    );
    expect(`.o_data_row:eq(1)`).toHaveText("Value 2 Draft", {
        message: "the onchange should have been applied",
    });
});

test(`leaving unvalid rows in edition`, async () => {
    let warnings = 0;
    mockService("notification", {
        add(message, { type }) {
            if (type === "danger") {
                warnings++;
            }
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo" required="1"/>
                <field name="bar"/>
            </list>
        `,
    });

    // Start first line edition
    await contains(`.o_data_cell`).click();

    // Remove required foo field value
    await contains(`.o_selected_row .o_field_widget[name=foo] input`).edit("", { confirm: false });

    // Try starting other line edition
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row", {
        message: "first line should still be in edition as invalid",
    });
    expect(`.o_selected_row`).toHaveCount(1, { message: "no other line should be in edition" });
    expect(`.o_data_row:eq(0) .o_field_invalid input`).toHaveCount(1, {
        message: "the required field should be marked as invalid",
    });
    expect(warnings).toBe(1, { message: "a warning should have been displayed" });
});

test(`pressing enter on last line of editable list view`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
    expect(`tr.o_data_row`).toHaveCount(4);

    // click on 3rd line
    await contains(`tr.o_data_row:eq(2) .o_field_cell[name=foo]`).click();
    expect(`tr.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row [name=foo] input`).toBeFocused();

    // press enter in input
    await press("Enter");
    await animationFrame();
    expect(`tr.o_data_row:eq(3)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row [name=foo] input`).toBeFocused();

    // press enter on last row
    await press("Enter");
    await animationFrame();
    expect(`tr.o_data_row`).toHaveCount(5);
    expect(`tr.o_data_row:eq(4)`).toHaveClass("o_selected_row");
    expect.verifySteps(["onchange"]);
});

test(`pressing tab on last cell of editable list view`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="int_field"/></list>`,
    });
    await contains(`.o_data_row:eq(3) .o_data_cell`).click();
    expect(`[name=foo] input`).toBeFocused();

    //it will not create a new line unless a modification is made
    await contains(`[name=foo] input`).edit("blip-changed", { confirm: "tab" });
    expect(`[name=int_field] input`).toBeFocused();
    await press("Tab");
    await animationFrame();
    expect(`tr.o_data_row:eq(4)`).toHaveClass("o_selected_row", {
        message: "5th row should be selected",
    });

    await contains(`[name=foo] input`).edit("blip-changed", { confirm: false });
    expect(`[name=foo] input`).toBeFocused();
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        "web_save",
        "onchange",
    ]);
});

test(`navigation with tab and read completes after default_get`, async () => {
    stepAllNetworkCalls();
    const onchangePromise = new Deferred();
    const readPromise = new Deferred();
    onRpc("onchange", () => onchangePromise);
    onRpc("web_save", () => readPromise);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="int_field"/></list>`,
    });
    await contains(`.o_data_row:eq(3) .o_data_cell`).click();
    await contains(`.o_selected_row [name='int_field'] input`).edit("1234");

    onchangePromise.resolve();
    await animationFrame();
    expect(`tbody tr.o_data_row`).toHaveCount(4, { message: "should have 4 data rows" });

    readPromise.resolve();
    await animationFrame();
    expect(`tbody tr.o_data_row`).toHaveCount(5, { message: "should have 5 data rows" });
    expect(`td:contains(1,234)`).toHaveCount(1, { message: "should have a cell with new value" });

    // we trigger a tab to move to the second cell in the current row. this
    // operation requires that this.currentRow is properly set in the
    // list editable renderer.
    await press("Tab");
    await animationFrame();
    expect(`tr.o_data_row:eq(4)`).toHaveClass("o_selected_row", {
        message: "5th row should be selected",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        "web_save",
        "onchange",
    ]);
});

test(`display toolbar`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
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
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts(`.o-dropdown--menu .dropdown-item`)).toEqual([
        "Export",
        "Duplicate",
        "Delete",
        "Action event",
    ]);
});

test(`execute ActionMenus actions`, async () => {
    stepAllNetworkCalls();

    mockService("action", {
        doAction(id, { additionalContext, onClose }) {
            expect.step({ action_id: id, context: additionalContext });
            onClose(); // simulate closing of target new action's dialog
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        info: {
            actionMenus: {
                action: [
                    {
                        id: 44,
                        name: "Custom Action",
                        target: "new",
                    },
                ],
                print: [],
            },
        },
        actionMenus: {},
    });

    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);
    // select all records
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(5);
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Action");

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        {
            action_id: 44,
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                active_id: 1,
                active_ids: [1, 2, 3, 4],
                active_model: "foo",
                active_domain: [],
            },
        },
        "web_search_read",
    ]);
});

test(`execute ActionMenus actions with correct params (single page)`, async () => {
    mockService("action", {
        doAction(id, { additionalContext }) {
            expect.step({ action_id: id, context: additionalContext });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
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
            </search>
        `,
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);

    // select all records
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(5);
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Action");

    // unselect first record (will unselect the thead checkbox as well)
    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(3);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Action");

    // add a domain and select first two records (need to unselect records first)
    await contains(`thead .o_list_record_selector input`).click(); // select all
    await contains(`thead .o_list_record_selector input`).click(); // unselect all
    await toggleSearchBarMenu();
    await toggleMenuItem("bar");
    expect(`.o_data_row`).toHaveCount(3);
    expect(`.o_list_record_selector input:checked`).toHaveCount(0);

    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(2);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Action");
    expect.verifySteps([
        {
            action_id: 44,
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                active_id: 1,
                active_ids: [1, 2, 3, 4],
                active_model: "foo",
                active_domain: [],
            },
        },
        {
            action_id: 44,
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                active_id: 2,
                active_ids: [2, 3, 4],
                active_model: "foo",
                active_domain: [],
            },
        },
        {
            action_id: 44,
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                active_id: 1,
                active_ids: [1, 2],
                active_model: "foo",
                active_domain: [["bar", "=", true]],
            },
        },
    ]);
});

test(`execute ActionMenus actions with correct params (multi pages)`, async () => {
    mockService("action", {
        doAction(id, { additionalContext }) {
            expect.step({ action_id: id, context: additionalContext });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/></list>`,
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
            </search>
        `,
    });
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(2);

    // select all records
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(3);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Action");

    // select all domain
    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(3);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Action");

    // add a domain (need to unselect records first)
    await contains(`thead .o_list_record_selector input`).click();
    await toggleSearchBarMenu();
    await toggleMenuItem("bar");
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);

    // select all domain
    await contains(`thead .o_list_record_selector input`).click();
    await contains(`.o_list_selection_box .o_list_select_domain`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(3);
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Custom Action");
    expect.verifySteps([
        {
            action_id: 44,
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                active_id: 1,
                active_ids: [1, 2],
                active_model: "foo",
                active_domain: [],
            },
        },
        {
            action_id: 44,
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                active_id: 1,
                active_ids: [1, 2, 3, 4],
                active_model: "foo",
                active_domain: [],
            },
        },
        {
            action_id: 44,
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                active_id: 1,
                active_ids: [1, 2, 3],
                active_model: "foo",
                active_domain: [["bar", "=", true]],
            },
        },
    ]);
});

test(`edit list line after line deletion`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="int_field"/></list>`,
    });
    await contains(`.o_data_row:eq(2) .o_data_cell`).click();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    await contains(`.o_list_button_discard`).click();
    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await contains(`.o_list_button_discard`).click();
    expect(`.o_selected_row`).toHaveCount(0, { message: "no row should be selected" });

    await contains(`.o_data_row:eq(2) .o_data_cell`).click();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row`).toHaveCount(1, { message: "no other row should be selected" });
});

test(`pressing TAB in editable list with several fields`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    await contains(`.o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) .o_data_cell:eq(0) input`).toBeFocused();

    // Press 'Tab' -> should go to next cell (still in first row)
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) .o_data_cell:eq(1) input`).toBeFocused();

    // Press 'Tab' -> should go to next line (first cell)
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) .o_data_cell:eq(0) input`).toBeFocused();
});

test(`pressing SHIFT-TAB in editable list with several fields`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) .o_data_cell:eq(0) input`).toBeFocused();

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) .o_data_cell:eq(1) input`).toBeFocused();

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) .o_data_cell:eq(0) input`).toBeFocused();
});

test(`navigation with tab and readonly field (no modification)`, async () => {
    // This test makes sure that if we have 2 cells in a row, the first in
    // edit mode, and the second one readonly, then if we press TAB when the
    // focus is on the first, then the focus skip the readonly cells and
    // directly goes to the next line instead.
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field" readonly="1"/>
            </list>
        `,
    });

    // Pass the first row in edition.
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Pressing Tab should skip the readonly field and directly go to the next row.
    await press("Tab");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    // We do it again.
    await press("Tab");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();
});

test(`navigation with tab and readonly field (with modification)`, async () => {
    // This test makes sure that if we have 2 cells in a row, the first in
    // edit mode, and the second one readonly, then if we press TAB when the
    // focus is on the first, then the focus skips the readonly cells and
    // directly goes to the next line instead.
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field" readonly="1"/>
            </list>
        `,
    });

    // Pass the first row in edition.
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Modity the cell content, validate with tab
    await contains(`.o_data_row:eq(0) [name=foo] input`).edit("blip-changed", { confirm: "tab" });
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    // Press tab again.
    await press("Tab");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();
});

test(`navigation with tab on a list with create="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" create="0">
                <field name="foo"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4, { message: "the list should contain 4 rows" });

    await contains(`.o_data_row:eq(2) .o_data_cell`).click();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row", {
        message: "third row should be in edition",
    });

    // Fill the cell and press tab
    await contains(`.o_selected_row .o_data_cell input`).edit("11", { confirm: "tab" });
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row", {
        message: "fourth row should be in edition",
    });

    // Press 'Tab' -> should go back to first line as the create action isn't available
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row", {
        message: "first row should be in edition",
    });
});

test(`navigation with tab on a one2many list with create="0"`, async () => {
    Foo._records[0].o2m = [1, 2];
    Bar._fields.name = fields.Char();

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="o2m">
                        <list editable="bottom" create="0">
                            <field name="name"/>
                        </list>
                    </field>
                    <field name="int_field"/>
                </sheet>
            </form>
        `,
        resId: 1,
        mode: "edit",
    });
    expect(`.o_field_widget[name=o2m] .o_data_row`).toHaveCount(2);

    await contains(`.o_field_widget[name=o2m] .o_data_row:eq(0) .o_data_cell[name=name]`).click();
    expect(`.o_field_widget[name=o2m] .o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_selected_row [name=name] input`).toBeFocused();

    // Press 'Tab' -> should go to next line
    await press("Tab");
    await animationFrame();
    expect(`.o_field_widget[name=o2m] .o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_selected_row [name=name] input`).toBeFocused();

    // Pressing 'Tab' -> should use default behavior and thus get out of
    // the one to many and go to the next field of the form
    await press("Tab");
    await animationFrame();
    expect(`.o_field_widget[name=int_field] input`).toBeFocused();
});

test(`edition, then navigation with tab (with a readonly field)`, async () => {
    // This test makes sure that if we have 2 cells in a row, the first in
    // edit mode, and the second one readonly, then if we edit and press TAB,
    // (before debounce), the save operation is properly done (before
    // selecting the next row)
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field" readonly="1"/>
            </list>
        `,
    });

    // click on first dataRow and press TAB
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_selected_row [name='foo'] input`).edit("new value");
    await press("Tab");
    await animationFrame();
    expect(`tbody tr:eq(0) td:contains(new value)`).toHaveCount(1, {
        message: "should have the new value visible in dom",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        "web_save",
    ]);
});

test(`edition, then navigation with tab (with a readonly field and onchange)`, async () => {
    // This test makes sure that if we have a read-only cell in a row, in
    // case the keyboard navigation move over it and there a unsaved changes
    // (which will trigger an onchange), the focus of the next activable
    // field will not crash
    Bar._fields.o2m = fields.One2many({
        relation: "foo",
    });
    Bar._onChanges = {
        o2m() {},
    };
    Bar._records[0].o2m = [1, 4];

    onRpc("onchange", ({ model }) => {
        expect.step(`onchange:${model}`);
    });

    await mountView({
        resModel: "bar",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="display_name"/>
                    <field name="o2m">
                        <list editable="bottom">
                            <field name="foo"/>
                            <field name="date" readonly="1"/>
                            <field name="int_field"/>
                        </list>
                    </field>
                </group>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_data_cell`).click();
    expect(`.o_data_cell[name=foo] input`).toBeFocused();

    await contains(`.o_data_cell[name=foo] input`).edit("new value", { confirm: "tab" });
    expect(`.o_data_cell[name=int_field] input`).toBeFocused();
    expect.verifySteps(["onchange:bar"]);
});

test(`pressing SHIFT-TAB in editable list with a readonly field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field" readonly="1"/>
                <field name="qux"/>
            </list>
        `,
    });
    await contains(`.o_data_row:eq(1) [name=qux]`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=qux] input`).toBeFocused();

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();
});

test(`pressing SHIFT-TAB in editable list with a readonly field in first column`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="int_field" readonly="1"/>
                <field name="foo"/>
                <field name="qux"/>
            </list>
        `,
    });
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row [name=qux] input`).toBeFocused();
});

test(`pressing SHIFT-TAB in editable list with a readonly field in last column`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="int_field"/>
                <field name="foo"/>
                <field name="qux" readonly="1"/>
            </list>
        `,
    });
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=int_field] input`).toBeFocused();

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row [name=foo] input`).toBeFocused();
});

test(`skip invisible fields when navigating list view with TAB`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="bar" column_invisible="1"/>
                <field name="int_field"/>
            </list>
        `,
        resId: 1,
    });
    await contains(`.o_data_row:eq(0) .o_field_cell[name=foo]`).click();
    expect(`.o_data_row:eq(0) .o_field_cell[name=foo] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) .o_field_cell[name=int_field] input`).toBeFocused();
});

test(`skip buttons when navigating list view with TAB (end)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <button name="kikou" string="Kikou" type="object"/>
            </list>
        `,
        resId: 1,
    });
    await contains(`.o_data_row:eq(2) [name=foo]`).click();
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(3) [name=foo] input`).toBeFocused();
});

test(`skip buttons when navigating list view with TAB (middle)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <button name="kikou" string="Kikou" type="object"/>
                <field name="foo"/>
                <button name="kikou" string="Kikou" type="object"/>
                <field name="int_field"/>
            </list>
        `,
        resId: 1,
    });
    await contains(`.o_data_row:eq(2) [name=foo]`).click();
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(2) [name=int_field] input`).toBeFocused();
});

test(`navigation: not moving down with keydown`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
    });
    await contains(`.o_field_cell[name=foo]`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await press("arrowdown");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
});

test(`navigation: moving right with keydown from text field does not move the focus`, async () => {
    Foo._fields.foo = fields.Text();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
    });
    await contains(`.o_field_cell[name=foo]`).click();
    expect(`.o_field_widget[name=foo] textarea`).toBeFocused();
    const textarea = queryOne(".o_field_widget[name=foo] textarea");
    expect(textarea.selectionStart).toBe(0);
    expect(textarea.selectionEnd).toBe(3);

    await press("arrowright");
    await animationFrame();
    expect(`.o_field_widget[name=foo] textarea`).toBeFocused();
    expect(textarea.selectionStart).toBe(3);
    expect(textarea.selectionEnd).toBe(3);

    await press("arrowright");
    await animationFrame();
    expect(`.o_field_widget[name=foo] textarea`).toBeFocused();
    expect(textarea.selectionStart).toBe(3);
    expect(textarea.selectionEnd).toBe(3);
});

test(`discarding changes in a row properly updates the rendering`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    expect(`.o_field_cell:eq(0)`).toHaveText("yop", { message: "first cell should contain 'yop'" });

    await contains(`.o_field_cell`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("hello", { confirm: false });
    await contains(`.o_list_button_discard:not(.dropdown-item)`).click();
    expect(`.modal`).toHaveCount(0, { message: "should be no modal to ask for discard" });
    expect(`.o_field_cell:eq(0)`).toHaveText("yop", {
        message: "first cell should still contain 'yop'",
    });
});

test(`numbers in list are right-aligned`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="qux"/>
                <field name="amount" widget="monetary"/>
                <field name="currency_id" column_invisible="1"/>
            </list>
        `,
    });

    const nbCellRight = [...queryAll(`.o_data_row:eq(0) > .o_data_cell`)].filter(
        (el) => window.getComputedStyle(el).textAlign === "right"
    ).length;
    expect(nbCellRight).toBe(2, { message: "there should be two right-aligned cells" });

    await contains(`.o_data_cell`).click();
    const nbInputRight = [...queryAll(`.o_data_row:eq(0) > .o_data_cell input`)].filter(
        (el) => window.getComputedStyle(el).textAlign === "right"
    ).length;
    expect(nbInputRight).toBe(2, { message: "there should be two right-aligned input" });
});

test(`grouped list with another grouped list parent, click unfold`, async () => {
    Bar._fields.cornichon = fields.Char();
    const rec = Bar._records[0];
    // create records to have the search more button
    const newRecs = [];
    for (let i = 0; i < 8; i++) {
        newRecs.push({ ...rec, id: i + 1, cornichon: "extra fin" });
    }
    Bar._records = newRecs;
    Bar._views = {
        list: `<list><field name="cornichon"/></list>`,
        search: `
            <search>
                <filter context="{'group_by': 'cornichon'}" string="cornichon"/>
            </search>
        `,
    };

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="m2o"/></list>`,
        searchViewArch: `
            <search>
                <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("bar");
    await toggleMenuItem("bar");

    await contains(`.o_data_cell`).click();
    await contains(`.o_field_widget[name=m2o] input`).click();
    await contains(`.o-autocomplete--dropdown-item:contains(Search More...)`).click();
    expect(`.modal-content`).toHaveCount(1);
    expect(`.modal-content .o_group_name`).toHaveCount(0, { message: "list in modal not grouped" });

    await contains(`.modal .o_searchview_dropdown_toggler`).click();
    await toggleMenuItem("cornichon");
    await contains(`.o_group_header`).click();
    expect(`.modal-content .o_group_open`).toHaveCount(1);
});

test(`field values are escaped`, async () => {
    const value = "<script>throw Error();</script>";

    Foo._records[0].foo = value;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    expect(`.o_data_cell:eq(0)`).toHaveText(value, {
        message: "value should have been escaped",
    });
});

test(`pressing ESC discard the current line changes`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    await contains(`.o_list_button_add`).click();
    expect(`tr.o_data_row`).toHaveCount(5, { message: "should currently adding a 5th data row" });

    await press("escape");
    await animationFrame();
    expect(`tr.o_data_row`).toHaveCount(4, { message: "should have only 4 data row after escape" });
    expect(`tr.o_data_row.o_selected_row`).toHaveCount(0, {
        message: "no rows should be selected",
    });
    expect(`.o_list_button_save`).toHaveCount(0, { message: "should not have a save button" });
});

test(`pressing ESC discard the current line changes (with required)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo" required="1"/></list>`,
    });
    await contains(`.o_list_button_add`).click();
    expect(`tr.o_data_row`).toHaveCount(5, { message: "should currently adding a 5th data row" });

    await press("escape");
    await animationFrame();
    expect(`tr.o_data_row`).toHaveCount(4, { message: "should have only 4 data row after escape" });
    expect(`tr.o_data_row.o_selected_row`).toHaveCount(0, {
        message: "no rows should be selected",
    });
    expect(`.o_list_button_save`).toHaveCount(0, { message: "should not have a save button" });
});

test(`field with password attribute`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo" password="True"/></list>`,
    });
    expect(queryAllTexts(`.o_data_row .o_data_cell`)).toEqual(["***", "****", "****", "****"]);
});

test(`list with handle widget`, async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(`web_search_read: order: ${kwargs.order}`);
    });
    onRpc("/web/dataset/resequence", async (request) => {
        const { params } = await request.json();
        expect.step("resequence");
        expect(params.offset).toBe(9, {
            message: "should write the sequence starting from the lowest current one",
        });
        expect(params.field).toBe("int_field", {
            message: "should write the right field as sequence",
        });
        expect(params.ids).toEqual([3, 2, 1], {
            message: "should write the sequence in correct order",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="int_field" widget="handle"/>
                <field name="amount" widget="float" digits="[5,0]"/>
            </list>
        `,
    });
    expect.verifySteps(["web_search_read: order: int_field ASC, id ASC"]);
    expect(`.o_data_row:eq(0) [name='amount']`).toHaveText("0", {
        message: "default fourth record should have amount 0",
    });
    expect(`.o_data_row:eq(1) [name='amount']`).toHaveText("500", {
        message: "default second record should have amount 500",
    });
    expect(`.o_data_row:eq(2) [name='amount']`).toHaveText("1,200", {
        message: "default first record should have amount 1,200",
    });
    expect(`.o_data_row:eq(3) [name='amount']`).toHaveText("300", {
        message: "default third record should have amount 300",
    });

    // Drag and drop the fourth line in second position
    await contains(`tbody tr:eq(3) .o_handle_cell`).dragAndDrop(queryFirst(`tbody tr:eq(1)`));
    expect.verifySteps(["resequence"]);
    expect(`.o_data_row:eq(0) [name='amount']`).toHaveText("0", {
        message: "new second record should have amount 0",
    });
    expect(`.o_data_row:eq(1) [name='amount']`).toHaveText("300", {
        message: "new fourth record should have amount 300",
    });
    expect(`.o_data_row:eq(2) [name='amount']`).toHaveText("500", {
        message: "new third record should have amount 500",
    });
    expect(`.o_data_row:eq(3) [name='amount']`).toHaveText("1,200", {
        message: "new first record should have amount 1,200",
    });
});

test(`result of consecutive resequences is correctly sorted`, async () => {
    // we want the data to be minimal to have a minimal test
    class MyFoo extends models.Model {
        int_field = fields.Integer();

        _records = [
            { id: 1, int_field: 11 },
            { id: 2, int_field: 12 },
            { id: 3, int_field: 13 },
            { id: 4, int_field: 14 },
        ];
    }
    defineModels([MyFoo]);

    let moves = 0;
    const context = {
        lang: "en",
        tz: "taht",
        uid: 7,
        allowed_company_ids: [1],
    };
    onRpc("/web/dataset/resequence", async (request) => {
        expect.step("resequence");
        const { params } = await request.json();
        if (moves === 0) {
            expect(params).toEqual({
                context,
                model: "my.foo",
                ids: [4, 3],
                offset: 13,
                field: "int_field",
            });
        }
        if (moves === 1) {
            expect(params).toEqual({
                context,
                model: "my.foo",
                ids: [4, 2],
                offset: 12,
                field: "int_field",
            });
        }
        if (moves === 2) {
            expect(params).toEqual({
                context,
                model: "my.foo",
                ids: [2, 4],
                offset: 12,
                field: "int_field",
            });
        }
        if (moves === 3) {
            expect(params).toEqual({
                context,
                model: "my.foo",
                ids: [4, 2],
                offset: 12,
                field: "int_field",
            });
        }
        moves += 1;
    });

    await mountView({
        resModel: "my.foo",
        type: "list",
        arch: `
            <list>
                <field name="int_field" widget="handle"/>
                <field name="id"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody tr td[name=id]`)).toEqual(["1", "2", "3", "4"], {
        message: "default should be sorted by id",
    });

    await contains(`.o_list_view tbody tr:eq(3) .o_handle_cell`).dragAndDrop(
        ".o_list_view tbody tr:eq(2)"
    );
    expect.verifySteps(["resequence"]);
    expect(queryAllTexts(`tbody tr td[name=id]`)).toEqual(["1", "2", "4", "3"], {
        message: "the int_field (sequence) should have been correctly updated",
    });

    await contains(`.o_list_view tbody tr:eq(2) .o_handle_cell`).dragAndDrop(
        ".o_list_view tbody tr:eq(1)"
    );
    expect.verifySteps(["resequence"]);
    expect(queryAllTexts(`tbody tr td[name=id]`)).toEqual(["1", "4", "2", "3"], {
        message: "the int_field (sequence) should have been correctly updated",
    });

    await contains(`.o_list_view tbody tr:eq(1) .o_handle_cell`).dragAndDrop(
        ".o_list_view tbody tr:eq(2)"
    );
    expect.verifySteps(["resequence"]);
    expect(queryAllTexts(`tbody tr td[name=id]`)).toEqual(["1", "2", "4", "3"], {
        message: "the int_field (sequence) should have been correctly updated",
    });

    await contains(`.o_list_view tbody tr:eq(2) .o_handle_cell`).dragAndDrop(
        ".o_list_view tbody tr:eq(1)"
    );
    expect.verifySteps(["resequence"]);
    expect(queryAllTexts(`tbody tr td[name=id]`)).toEqual(["1", "4", "2", "3"], {
        message: "the int_field (sequence) should have been correctly updated",
    });
});

test("resequence with NULL values", async () => {
    mockService("action", {
        doActionButton(params) {
            params.onClose();
        },
    });
    // we want the data to be minimal to have a minimal test
    class MyFoo extends models.Model {
        int_field = fields.Integer();

        _records = [
            { id: 1, int_field: 1 },
            { id: 2 },
            { id: 3, int_field: 3 },
            { id: 4, int_field: 2 },
        ];
    }
    defineModels([MyFoo]);

    const serverValues = {
        1: 1,
        2: false,
        3: 3,
        4: 2,
    };

    onRpc("web_search_read", function ({ parent }) {
        const res = parent();
        const getServerValue = (record) =>
            serverValues[record.id] === false ? Number.MAX_SAFE_INTEGER : serverValues[record.id];

        // when sorted, NULL values are last
        res.records.sort((a, b) => getServerValue(a) - getServerValue(b));
        return res;
    });

    onRpc("/web/dataset/resequence", async (request) => {
        const { params } = await request.json();
        for (let i = 0; i < params.ids.length; i++) {
            serverValues[params.ids[i]] = i;
        }
    });

    await mountView({
        type: "list",
        resModel: "my.foo",
        arch: `<list default_order="int_field">
                <field name="int_field" widget="handle"/>
                <field name="id"/>
                <button name="reload" class="reload" string="Confirm" type="object"/>
            </list>`,
    });

    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["1", "4", "3", "2"]);

    await contains("tbody tr:nth-child(4) .o_handle_cell").dragAndDrop("tbody tr:nth-child(3)");
    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["1", "4", "2", "3"]);

    await contains("button.reload").click();
    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["1", "4", "2", "3"]);
});

test("resequence with only NULL values", async () => {
    mockService("action", {
        doActionButton(params) {
            params.onClose();
        },
    });
    // we want the data to be minimal to have a minimal test
    class MyFoo extends models.Model {
        int_field = fields.Integer();

        _records = [{ id: 1 }, { id: 2 }, { id: 3 }];
    }
    defineModels([MyFoo]);

    const serverValues = {
        1: false,
        2: false,
        3: false,
    };

    onRpc("web_search_read", function ({ parent }) {
        const res = parent();
        const getServerValue = (record) =>
            serverValues[record.id] === false ? Number.MAX_SAFE_INTEGER : serverValues[record.id];

        // when sorted, NULL values are last
        res.records.sort((a, b) => getServerValue(a) - getServerValue(b));
        return res;
    });

    onRpc("/web/dataset/resequence", async (request) => {
        const { params } = await request.json();
        for (let i = 0; i < params.ids.length; i++) {
            serverValues[params.ids[i]] = i;
        }
    });

    await mountView({
        type: "list",
        resModel: "my.foo",
        arch: `<list default_order="int_field">
                <field name="int_field" widget="handle"/>
                <field name="id"/>
                <button name="reload" class="reload" string="Confirm" type="object"/>
            </list>`,
    });

    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["1", "2", "3"]);

    await contains("tbody tr:nth-child(3) .o_handle_cell").dragAndDrop("tbody tr:nth-child(2)");
    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["1", "3", "2"]);

    await contains("button.reload").click();
    expect(queryAllTexts(".o_field_cell[name=id]")).toEqual(["1", "3", "2"]);
});

test(`editable list with handle widget`, async () => {
    // resequence makes sense on a sequence field, not on arbitrary fields
    Foo._records[0].int_field = 0;
    Foo._records[1].int_field = 1;
    Foo._records[2].int_field = 2;
    Foo._records[3].int_field = 3;

    onRpc("/web/dataset/resequence", async (request) => {
        expect.step("resequence");
        const { params } = await request.json();
        expect(params.offset).toBe(1, {
            message: "should write the sequence starting from the lowest current one",
        });
        expect(params.field).toBe("int_field", {
            message: "should write the right field as sequence",
        });
        expect(params.ids).toEqual([4, 2, 3], {
            message: "should write the sequence in correct order",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" default_order="int_field">
                <field name="int_field" widget="handle"/>
                <field name="amount" widget="float" digits="[5,0]"/>
            </list>
        `,
    });
    expect(`tbody tr:eq(0) td:last`).toHaveText("1,200", {
        message: "default first record should have amount 1,200",
    });
    expect(`tbody tr:eq(1) td:last`).toHaveText("500", {
        message: "default second record should have amount 500",
    });
    expect(`tbody tr:eq(2) td:last`).toHaveText("300", {
        message: "default third record should have amount 300",
    });
    expect(`tbody tr:eq(3) td:last`).toHaveText("0", {
        message: "default fourth record should have amount 0",
    });

    // Drag and drop the fourth line in second position
    await contains(`tbody tr:eq(3) .o_handle_cell`).dragAndDrop(queryFirst(`tbody tr:eq(1)`));
    expect.verifySteps(["resequence"]);
    expect(`tbody tr:eq(0) td:last`).toHaveText("1,200", {
        message: "new first record should have amount 1,200",
    });
    expect(`tbody tr:eq(1) td:last`).toHaveText("0", {
        message: "new second record should have amount 0",
    });
    expect(`tbody tr:eq(2) td:last`).toHaveText("500", {
        message: "new third record should have amount 500",
    });
    expect(`tbody tr:eq(3) td:last`).toHaveText("300", {
        message: "new fourth record should have amount 300",
    });

    await contains(`tbody tr:eq(1) div[name='amount']`).click();
    expect(`tbody tr:eq(1) td:last input`).toHaveValue("0", {
        message: "the edited record should be the good one",
    });
});

test(`editable target, handle widget locks and unlocks on sort`, async () => {
    // resequence makes sense on a sequence field, not on arbitrary fields
    Foo._records[0].int_field = 0;
    Foo._records[1].int_field = 1;
    Foo._records[2].int_field = 2;
    Foo._records[3].int_field = 3;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" default_order="int_field">
                <field name="int_field" widget="handle"/>
                <field name="amount" widget="float"/>
            </list>
        `,
    });
    expect(queryAllTexts(`tbody div[name=amount]`)).toEqual(
        ["1,200.00", "500.00", "300.00", "0.00"],
        {
            message: "default should be sorted by int_field",
        }
    );

    // Drag and drop the fourth line in second position
    await contains(`tbody tr:eq(3) .o_row_handle`).dragAndDrop(`tbody tr:eq(1)`);
    // Handle should be unlocked at this point
    expect(queryAllTexts(`tbody div[name=amount]`)).toEqual(
        ["1,200.00", "0.00", "500.00", "300.00"],
        {
            message: "drag and drop should have succeeded, as the handle is unlocked",
        }
    );

    // Sorting by a field different for int_field should lock the handle
    await contains(`.o_column_sortable:eq(1)`).click();
    expect(queryAllTexts(`tbody div[name=amount]`)).toEqual(
        ["0.00", "300.00", "500.00", "1,200.00"],
        {
            message: "should have been sorted by amount",
        }
    );

    // Drag and drop the fourth line in second position (not)
    await contains(`tbody tr:eq(3) .o_row_handle`).dragAndDrop(`tbody tr:eq(1)`);
    expect(queryAllTexts(`tbody div[name=amount]`)).toEqual(
        ["0.00", "300.00", "500.00", "1,200.00"],
        {
            message: "drag and drop should have failed as the handle is locked",
        }
    );

    // Sorting by int_field should unlock the handle
    await contains(`.o_column_sortable`).click();
    expect(queryAllTexts(`tbody div[name=amount]`)).toEqual(
        ["1,200.00", "0.00", "500.00", "300.00"],
        {
            message: "records should be ordered as per the previous resequence",
        }
    );

    // Drag and drop the fourth line in second position
    await contains(`tbody tr:eq(3) .o_row_handle`).dragAndDrop(`tbody tr:eq(1)`);
    expect(queryAllTexts(`tbody div[name=amount]`)).toEqual(
        ["1,200.00", "300.00", "0.00", "500.00"],
        {
            message: "drag and drop should have worked as the handle is unlocked",
        }
    );
});

test(`editable list with handle widget with slow network`, async () => {
    // resequence makes sense on a sequence field, not on arbitrary fields
    Foo._records[0].int_field = 0;
    Foo._records[1].int_field = 1;
    Foo._records[2].int_field = 2;
    Foo._records[3].int_field = 3;

    const deferred = new Deferred();
    onRpc("/web/dataset/resequence", async (request) => {
        expect.step("resequence");
        const { params } = await request.json();
        expect(params.offset).toBe(1, {
            message: "should write the sequence starting from the lowest current one",
        });
        expect(params.field).toBe("int_field", {
            message: "should write the right field as sequence",
        });
        expect(params.ids).toEqual([4, 2, 3], {
            message: "should write the sequence in correct order",
        });
        await deferred;
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="int_field" widget="handle"/>
                <field name="amount" widget="float" digits="[5,0]"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_data_cell[name=amount]`)).toEqual(["1,200", "500", "300", "0"]);

    // drag and drop the fourth line in second position
    await contains(`tbody tr:eq(3) .o_handle_cell`).dragAndDrop(`tbody tr:eq(1)`);
    expect.verifySteps(["resequence"]);

    // edit moved row before the end of resequence
    await contains(`tbody tr:eq(3) .o_field_widget[name='amount']`).click();
    await animationFrame();
    expect(`tbody tr:eq(3) td:eq(2) input`).toHaveCount(0, {
        message: "shouldn't edit the line before resequence",
    });

    deferred.resolve();
    await animationFrame();
    expect(`tbody tr:eq(3) td:eq(2) input`).toHaveCount(1, {
        message: "should edit the line after resequence",
    });
    expect(`tbody tr:eq(3) td:eq(2) input`).toHaveValue("300", {
        message: "fourth record should have amount 300",
    });

    await contains(`.o_data_row [name='amount'] input`).edit("301", { confirm: false });
    await contains(`tbody tr:eq(0) .o_field_widget[name='amount']`).click();
    await contains(`.o_list_button_save`).click();
    expect(queryAllTexts(`.o_data_cell[name=amount]`)).toEqual(["1,200", "0", "500", "301"]);

    await contains(`tbody tr:eq(3) .o_field_widget[name='amount']`).click();
    expect(`tbody tr:eq(3) td:eq(2) input`).toHaveValue("301", {
        message: "fourth record should have amount 301",
    });
});

test(`multiple clicks on Add do not create invalid rows`, async () => {
    Foo._onChanges = {
        m2o() {},
    };

    const deferred = new Deferred();
    onRpc("onchange", () => deferred);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="m2o" required="1"/></list>`,
    });
    expect(`.o_data_row`).toHaveCount(4, { message: "should contain 4 records" });

    // click on Add and delay the onchange (check that the button is correctly disabled)
    await contains(`.o_list_button_add`).click();
    expect(`.o_list_button_add`).toHaveProperty("disabled", true);

    deferred.resolve();
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5, { message: "only one record should have been created" });
});

test(`reference field rendering`, async () => {
    Foo._records.push({
        id: 5,
        reference: "res.currency,2",
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="reference"/></list>`,
    });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["Value 1", "USD", "EUR", "", "EUR"]);
});

test(`reference field batched in grouped list`, async () => {
    Foo._records = [
        // group 1
        { id: 1, foo: "1", reference: "bar,1" },
        { id: 2, foo: "1", reference: "bar,2" },
        { id: 3, foo: "1", reference: "res.currency,1" },
        //group 2
        { id: 4, foo: "2", reference: "bar,2" },
        { id: 5, foo: "2", reference: "bar,3" },
    ];

    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list expand="1">
                <field name="foo" column_invisible="1"/>
                <field name="reference"/>
            </list>
        `,
        groupBy: ["foo"],
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
    ]);
    expect(`.o_group_header`).toHaveCount(2);
    expect(queryAllTexts(`.o_data_cell`)).toEqual([
        "Value 1",
        "Value 2",
        "USD",
        "Value 2",
        "Value 3",
    ]);
});

test(`multi edit in view grouped by field not in view`, async () => {
    Foo._records = [
        // group 1
        { id: 1, foo: "1", m2o: 1 },
        { id: 3, foo: "2", m2o: 1 },
        //group 2
        { id: 2, foo: "1", m2o: 2 },
        { id: 4, foo: "2", m2o: 2 },
        // group 3
        { id: 5, foo: "2", m2o: 3 },
    ];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="1" multi_edit="1"><field name="foo"/></list>`,
        groupBy: ["m2o"],
    });

    // Select items from the first group
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_list_char`).click();
    await contains(`.o_data_row [name=foo] input`).edit("test");
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .modal-footer .btn-primary`).click();
    expect(`.modal`).toHaveCount(0);
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["test", "test", "1", "2", "2"]);
});

test(`multi edit reference field batched in grouped list`, async () => {
    Foo._records = [
        // group 1
        { id: 1, foo: "1", reference: "bar,1" },
        { id: 2, foo: "1", reference: "bar,2" },
        //group 2
        { id: 3, foo: "2", reference: "res.currency,1" },
        { id: 4, foo: "2", reference: "bar,2" },
        { id: 5, foo: "2", reference: "bar,3" },
    ];

    stepAllNetworkCalls();
    onRpc("write", ({ args }) => {
        expect(args).toEqual([[1, 2, 3], { bar: true }]);
    });

    // Field boolean_toggle just to simplify the test flow
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list expand="1" multi_edit="1">
                <field name="foo" column_invisible="1"/>
                <field name="bar" widget="boolean_toggle"/>
                <field name="reference"/>
            </list>
        `,
        groupBy: ["foo"],
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
    ]);
    await contains(`.o_data_row .o_list_record_selector input:eq(0)`).click();
    await contains(`.o_data_row .o_list_record_selector input:eq(1)`).click();
    await contains(`.o_data_row .o_list_record_selector input:eq(2)`).click();
    await contains(`.o_data_row .o_field_boolean input`).click();
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .modal-footer .btn-primary`).click();
    expect(`.modal`).toHaveCount(0);
    expect.verifySteps(["write", "web_read"]);
    expect(`.o_group_header`).toHaveCount(2);
    expect(queryAllTexts(`.o_data_cell[name=reference]`)).toEqual([
        "Value 1",
        "Value 2",
        "USD",
        "Value 2",
        "Value 3",
    ]);
});

test(`multi edit field with daterange widget`, async () => {
    mockTimeZone(+6);

    class Daterange extends models.Model {
        date_start = fields.Date();
        date_end = fields.Date();

        _records = [
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
        ];
    }
    defineModels([Daterange]);

    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args).toEqual([[1, 2], { date_start: "2017-01-16", date_end: "2017-02-12" }]);
    });

    await mountView({
        resModel: "daterange",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="date_start" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </list>
        `,
    });
    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_data_row .o_data_cell`).click(); // edit first row
    await contains(`.o_data_row .o_data_cell .o_field_daterange input`).click();

    // change dates range
    await contains(getPickerCell("16").at(0)).click();
    await contains(getPickerCell("12").at(1)).click();
    expect(getPickerApplyButton()).not.toHaveAttribute("disabled");

    // Apply the changes
    await contains(getPickerApplyButton()).click();
    expect(`.modal`).toHaveCount(1, {
        message: "The confirm dialog should appear to confirm the multi edition.",
    });
    expect(queryAllTexts(`.modal-body .o_modal_changes td`)).toEqual([
        "Field:",
        "Date start",
        "Update to:",
        "01/16/2017\n02/12/2017",
        "Field:",
        "Date end",
        "Update to:",
        "02/12/2017",
    ]);

    // Valid the confirm dialog
    await contains(`.modal .btn-primary`).click();
    expect(`.modal`).toHaveCount(0);
    expect.verifySteps(["write"]);
});

test(`multi edit field with daterange widget (edition without using the picker)`, async () => {
    mockTimeZone(+6);

    class Daterange extends models.Model {
        date_start = fields.Date();
        date_end = fields.Date();

        _records = [
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
        ];
    }
    defineModels([Daterange]);

    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args).toEqual([[1, 2], { date_start: "2016-04-01" }]);
    });

    await mountView({
        resModel: "daterange",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="date_start" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </list>
        `,
    });

    // Test manually edit the date without using the daterange picker
    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_data_row .o_data_cell`).click(); // edit first row

    // Change the date in the first datetime
    await contains(
        `.o_data_row .o_data_cell .o_field_daterange[name='date_start'] input[data-field='date_start']`
    ).edit("2016-04-01 11:00:00", { confirm: "enter" });
    expect(`.modal`).toHaveCount(1, {
        message: "The confirm dialog should appear to confirm the multi edition.",
    });
    expect(queryAllTexts(`.modal-body .o_modal_changes td`)).toEqual([
        "Field:",
        "Date start",
        "Update to:",
        "04/01/2016\n01/26/2017",
    ]);

    // Valid the confirm dialog
    await contains(`.modal .btn-primary`).click();
    expect(`.modal`).toHaveCount(0);
    expect.verifySteps(["write"]);
});

test(`list daterange with start date and empty end date`, async () => {
    Foo._fields.date_end = fields.Date();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_data_row:eq(0) .o_field_widget[name=date] span`)).toEqual([
        "01/25/2017",
        "",
    ]);
});

test(`list daterange with empty start date and end date`, async () => {
    Foo._fields.date_end = fields.Date();
    Foo._records[0].date_end = Foo._records[0].date;
    Foo._records[0].date = false;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_data_row:eq(0) .o_field_widget[name=date] span`)).toEqual([
        "",
        "01/25/2017",
    ]);
});

test(`editable list view: contexts are correctly sent`, async () => {
    serverState.userContext = { someKey: "some value" };

    onRpc(({ method, kwargs }) => {
        if (method === "web_search_read" || method === "web_save") {
            expect.step(method);
            const context = kwargs.context;
            expect(context.active_field).toBe(2, { message: "context should be correct" });
            expect(context.someKey).toBe("some value", {
                message: "context should be correct",
            });
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
        context: { active_field: 2 },
    });
    expect.verifySteps(["web_search_read"]);

    await contains(`.o_data_cell`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("abc", { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`editable list view: contexts with multiple edit`, async () => {
    serverState.userContext = { someKey: "some value" };

    onRpc(({ method, kwargs }) => {
        if (method === "web_read" || method === "write") {
            expect.step(method);
            const context = kwargs.context;
            expect(context.active_field).toBe(2, { message: "context should be correct" });
            expect(context.someKey).toBe("some value", {
                message: "context should be correct",
            });
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list multi_edit="1"><field name="foo"/></list>`,
        context: { active_field: 2 },
    });
    // Uses the main selector to select all lines.
    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_data_row .o_data_cell`).click();

    // Edits first record then confirms changes.
    await contains(`.o_data_row [name=foo] input`).edit("legion");
    await contains(`.modal-dialog button.btn-primary`).click();
    expect.verifySteps(["write", "web_read"]);
});

test(`editable list view: single edition with selected records`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" multi_edit="1"><field name="foo"/></list>`,
    });

    // Select first record
    await contains(`.o_data_row .o_list_record_selector input`).click();

    // Edit the second
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    await contains(`.o_data_cell input`).edit("oui", { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "oui", "gnap", "blip"]);
});

test(`editable list view: non dirty record with required fields`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo" required="1"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(1);

    // do not change anything and then click outside should discard record
    await contains(`.o_list_view`).click();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(1);

    // do not change anything and then click save button should not allow to discard record
    await contains(`.o_list_button_save`).click();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(1);

    // selecting some other row should discard non dirty record
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_selected_row`).toHaveCount(1);

    // click somewhere else to discard currently selected row
    await contains(`.o_list_view`).click();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(1);

    // do not change anything and press Enter key should not allow to discard record
    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);

    // discard row and create new record and keep required field empty and click anywhere
    await contains(`.o_list_button_discard:not(.dropdown-item)`).click();
    await contains(`.o_list_button_add`).click();
    expect(`.o_selected_row`).toHaveCount(1, { message: "row should be selected" });

    await contains(`.o_selected_row [name=int_field] input`).edit("123", { confirm: false });
    await contains(`.o_list_view`).click();
    expect(`.o_selected_row`).toHaveCount(1, { message: "row should still be in edition" });
});

test(`editable list view: multi edition`, async () => {
    stepAllNetworkCalls();
    onRpc("write", ({ args }) => {
        expect(args).toEqual([[1, 2], { int_field: 666 }], {
            message: "should write on multi records",
        });
    });
    onRpc("web_read", ({ args, kwargs }) => {
        if (args[0].length !== 1) {
            expect.step("conditional web_read");
            expect(args).toEqual([[1, 2]], { message: "should batch the read" });
            expect(kwargs.specification).toEqual({ foo: {}, int_field: {} });
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();

    // edit a line without modifying a field
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await contains(`.o_list_view`).click();
    expect(`.o_selected_row`).toHaveCount(0);

    // create a record and edit its value
    await contains(`.o_list_button_add`).click();
    expect.verifySteps(["onchange"]);

    await contains(`.o_selected_row [name=int_field] input`).edit("123", { confirm: false });
    expect(`.modal`).toHaveCount(0);

    await contains(`.o_list_button_save`).click();
    expect.verifySteps(["web_save"]);

    // edit a field
    await contains(`.o_data_row:eq(0) [name=int_field]`).click();
    await contains(`.o_data_row:eq(0) [name=int_field] input`).edit("666");
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .btn.btn-secondary`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(2);
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["yop", "10"]);
    expect(`.o_data_row:eq(0) .o_data_cell[name=int_field]`).toBeFocused();

    await contains(`.o_data_row:eq(0) .o_data_cell:eq(1)`).click();
    await contains(`.o_data_row [name=int_field] input`).edit("666");
    expect(queryOne(".modal-body").innerText.includes("those 2 records")).toBe(true, {
        message: "the number of records should be correctly displayed",
    });

    await contains(`.modal .btn-primary`).click();
    expect(`.o_data_cell input.o_field_widget`).toHaveCount(0, {
        message: "no field should be editable anymore",
    });
    // discard selection
    await contains(`.o_list_unselect_all`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(0, {
        message: "no record should be selected anymore",
    });
    expect.verifySteps(["write", "web_read", "conditional web_read"]);
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["yop", "666"], {
        message: "the first row should be updated",
    });
    expect(queryAllTexts(`.o_data_row:eq(1) .o_data_cell`)).toEqual(["blip", "666"], {
        message: "the second row should be updated",
    });
    expect(`.o_data_cell input.o_field_widget`).toHaveCount(0, {
        message: "no field should be editable anymore",
    });
});

test(`editable list view: multi edit a field with string attr`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo" string="Custom Label"/>
                <field name="int_field"/>
            </list>
        `,
    });

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();

    // edit foo
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    await contains(`.o_data_row [name=foo] input`).edit("new value");
    expect(`.modal`).toHaveCount(1);
    expect(queryAllTexts(`.modal-body .o_modal_changes td`)).toEqual([
        "Field:",
        "Custom Label",
        "Update to:",
        "new value",
    ]);
});

test(`create in multi editable list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
        createRecord() {
            expect.step("createRecord");
        },
    });

    // click on CREATE (should trigger a switch_view)
    await contains(`.o_list_button_add`).click();
    expect.verifySteps(["createRecord"]);
});

test(`editable list view: multi edition cannot call onchanges`, async () => {
    Foo._onChanges = {
        foo(record) {
            record.int_field = record.foo.length;
        },
    };

    stepAllNetworkCalls();
    onRpc("write", ({ args }) => {
        for (const id of args[0]) {
            const record = Foo._records.find((r) => r.id === id);
            record.int_field = args[1].foo.length;
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    // select and edit a single record
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    await contains(`.o_data_row [name=foo] input`).edit("hi");
    expect(`.modal`).toHaveCount(0);
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["hi", "2"]);
    expect(queryAllTexts(`.o_data_row:eq(1) .o_data_cell`)).toEqual(["blip", "9"]);
    expect.verifySteps(["write", "web_read"]);
    // select the second record (the first one is still selected)
    expect(`.o_list_record_selector input:checked`).toHaveCount(1, {
        message: "Record should be still selected",
    });

    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    // edit foo, first row
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    await contains(`.o_data_row [name=foo] input`).edit("hello");
    expect(`.modal`).toHaveCount(1); // save dialog

    await contains(`.modal .btn-primary`).click();
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["hello", "5"]);
    expect(queryAllTexts(`.o_data_row:eq(1) .o_data_cell`)).toEqual(["hello", "5"]);
    // should not perform the onchange in multi edition
    expect.verifySteps(["write", "web_read"]);
});

test.todo(`editable list view: multi edition error and cancellation handling`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo" required="1"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();

    // edit a line and cancel
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    expect(`.o_list_record_selector input:enabled`).toHaveCount(0);
    await contains(`.o_selected_row [name=foo] input`).edit("abc");
    await contains(`.modal .btn.btn-secondary`).click();
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["yop", "10"], {
        message: "first cell should have discarded any change",
    });
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);

    // edit a line with an invalid format type
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(1)`).click();
    expect(`.o_list_record_selector input:enabled`).toHaveCount(0);

    await contains(`.o_selected_row [name=int_field] input`).edit("hahaha", { confirm: "blur" });
    expect(`.modal`).toHaveCount(1, { message: "there should be an opened modal" });

    await contains(`.modal .btn-primary`).click();
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["yop", "10"], {
        message: "changes should be discarded",
    });
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);

    // edit a line with an invalid value
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    expect(`.o_list_record_selector input:enabled`).toHaveCount(0);

    await contains(`.o_selected_row [name=foo] input`).edit("", { confirm: false });
    await contains(`.o_control_panel`).click();
    expect(`.modal`).toHaveCount(1, { message: "there should be an opened modal" });

    await contains(`.modal .btn-primary`).click();
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["yop", "10"], {
        message: "changes should be discarded",
    });
    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);
});

test(`multi edition: many2many_tags in many2many field`, async () => {
    for (let i = 4; i <= 10; i++) {
        Bar._records.push({ id: i, name: "Value" + i });
    }
    Bar._views = {
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
    };

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list multi_edit="1"><field name="m2m" widget="many2many_tags"/></list>`,
    });

    expect(`.o_list_record_selector input:enabled`).toHaveCount(5);

    // select two records and enter edit mode
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    await contains(`.o_field_widget[name=m2m] input`).click();
    await contains(`.o-autocomplete--dropdown-item:contains(Search More...)`).click();
    expect(`.modal`).toHaveCount(1, { message: "should have open the modal" });

    await contains(`.modal .o_data_row:eq(2) .o_field_cell`).click();
    expect(`.modal [role='alert']`).toHaveCount(1, {
        message: "should have open the confirmation modal",
    });
    expect(`.modal .o_field_many2many_tags .badge`).toHaveCount(3);
    expect(`.modal .o_field_many2many_tags .badge:eq(2)`).toHaveText("Value 3", {
        message: "should have display_name in badge",
    });
});

test(`multi edition: many2many field in grouped list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["m2m"],
    });
    await contains(`.o_group_header:eq(1)`).click();
    await contains(`.o_group_header:eq(2)`).click(); // open Value 2 group
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(1)`).click();
    await contains(`.o_field_widget[name=m2m] input`).click();
    await contains(`.o-autocomplete--dropdown-item:contains(Value 3)`).click();
    expect(`.o_data_row:eq(0) .o_data_cell:eq(1)`).toHaveText("Value 1\nValue 2\nValue 3", {
        message: "should have a right value in many2many field",
    });
    expect(`.o_data_row:eq(2) .o_data_cell:eq(1)`).toHaveText("Value 1\nValue 2\nValue 3", {
        message: "should have same value in many2many field on all other records with same res_id",
    });
});

test(`editable list view: multi edition of many2one: set same value`, async () => {
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args).toEqual([[1, 2, 3, 4], { m2o: 2 }], {
            message: "should force write value on all selected records",
        });
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="m2o"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_list_many2one`)).toEqual(["Value 1", "Value 2", "Value 1", "Value 1"]);

    // select all records (the first one has value 1 for m2o)
    await contains(`.o_list_record_selector input`).click();

    // set m2o to 1 in first record
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_data_row [name=m2o] input`).fill("Value 2", { confirm: false });
    await runAllTimers();
    await contains(`.o-autocomplete--dropdown-item:contains(Value 2)`).click();
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .modal-footer .btn-primary`).click();
    expect(queryAllTexts(`.o_list_many2one`)).toEqual(["Value 2", "Value 2", "Value 2", "Value 2"]);
    expect.verifySteps(["write"]);
});

test(`editable list view: clicking on "Discard changes" in multi edition`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" multi_edit="1">
                <field name="foo"/>
            </list>
        `,
    });

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).check();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).check();
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    await contains(`.o_data_row [name=foo] input`).edit("oof", { confirm: "blur" });

    await clickModalButton({ text: "Cancel" });

    expect(`.modal`).toHaveCount(0, { message: "should not open modal" });
    expect(`.o_data_row:eq(0) .o_data_cell:eq(0)`).toHaveText("yop");
});

test(`discard has to wait for changes in each field in multi edit`, async () => {
    const def = new Deferred();

    class CustomField extends Component {
        static template = xml`<input t-ref="input" t-att-value="value" t-on-blur="onBlur" t-on-input="onInput"/>`;
        static props = {
            ...standardFieldProps,
        };

        setup() {
            this.input = useRef("input");
            useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
                detail.proms.push(this.updateValue())
            );
        }

        get value() {
            return this.props.record.data[this.props.name];
        }

        async updateValue() {
            if (!this.isDirty) {
                return;
            }
            const value = this.input.el.value;
            await def;
            await this.props.record.update({ [this.props.name]: `update value: ${value}` });
        }

        onBlur() {
            return this.updateValue();
        }

        onInput() {
            this.isDirty = true;
            this.props.record.model.bus.trigger("FIELD_IS_DIRTY", true);
        }
    }
    registry.category("fields").add("custom", { component: CustomField });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" multi_edit="1">
                <field name="foo" widget="custom"/>
            </list>
        `,
    });

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell`).click();
    await contains(`.o_data_row .o_data_cell input`).edit("oof", { confirm: false });
    await contains(`.o_list_button_discard`).click();
    expect(`.modal`).toHaveCount(0);
    expect(`.o_data_row:eq(0) .o_data_cell input`).toHaveValue("oof");

    def.resolve();
    await animationFrame();
    expect(`.modal`).toHaveCount(0);
    expect(`.o_data_row:eq(0) .o_data_cell input`).toHaveValue("yop");
});

test(`editable list view: mousedown on "Discard", mouseup somewhere else (no multi-edit)`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
            </list>
        `,
    });

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    await contains(`.o_data_row [name=foo] input`).edit("oof", { confirm: false });
    await pointerDown(`.o_list_button_discard`);
    await pointerUp(".o_control_panel");
    await animationFrame();
    expect(`.modal`).toHaveCount(0, { message: "should not open modal" });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["oof", "blip", "gnap", "blip"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        "web_save",
    ]);
});

test(`multi edit list view: mousedown on "Discard" with invalid field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`.o_data_row:eq(0) .o_data_cell`).toHaveText("10");

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();

    // edit the numeric field with an invalid value
    await contains(`.o_data_row:eq(0) .o_data_cell`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell input`).edit("oof", { confirm: false });

    // mousedown on Discard and then mouseup also on Discard
    await contains(`.o_list_button_discard`).click();
    expect(`.o_dialog`).toHaveCount(0, { message: "should not display an invalid field dialog" });
    expect(`.o_data_row:eq(0) .o_data_cell`).toHaveText("10");

    // edit again with an invalid value
    await contains(`.o_data_row:eq(0) .o_data_cell`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell input`).edit("oof2", { confirm: false });

    // mousedown on Discard (simulate a mousemove) and mouseup somewhere else
    await pointerDown(".o_list_button_discard");
    await animationFrame();
    expect(`.o_dialog`).toHaveCount(0, { message: "should not display an invalid field dialog" });

    // FIXME: Hoot incorrectly triggers"change" events *after* the blur instead of
    // *before*, causing the internals of the list controller/renderer to dispatch
    // 2 dialogs. We have to catch and stop that "change" event to prevent this.
    getFixture().addEventListener("change", (ev) => ev.stopPropagation(), {
        capture: true,
        once: true,
    });
    await pointerUp(".o_control_panel");
    await animationFrame();
    expect(`.o_dialog`).toHaveCount(1, { message: "should display an invalid field dialog" });

    await contains(`.o_dialog .modal-footer .btn-primary`).click(); // click OK
    expect(`.o_data_row:eq(0) .o_data_cell`).toHaveText("10");
});

test(`editable list view (multi edition): mousedown on 'Discard', but mouseup somewhere else`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list multi_edit="1"><field name="foo"/></list>`,
    });

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell`).click();
    await contains(`.o_data_row [name=foo] input`).fill("oof", { confirm: false });
    await pointerDown(".o_list_button_discard");
    await animationFrame();
    await pointerUp(".o_control_panel");
    await animationFrame();
    expect(`.modal-header`).toHaveText("Confirmation", {
        message: "Modal should ask to save changes",
    });
});

test(`editable list view (multi edition): writable fields in readonly (force save)`, async () => {
    stepAllNetworkCalls();
    onRpc("write", ({ args }) => {
        expect(args).toEqual([[1, 3], { bar: false }]);
    });

    // boolean toogle widget allows for writing on the record even in readonly mode
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="bar" widget="boolean_toggle"/>
            </list>
        `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(2) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_boolean_toggle input`).click();
    expect(`.modal-header`).toHaveText("Confirmation");

    await contains(`.modal .btn-primary`).click();
    expect.verifySteps(["write", "web_read"]);
});

test(`editable list view: multi edition with readonly modifiers`, async () => {
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args).toEqual([[1, 2], { int_field: 666 }], {
            message: "should only write on the valid records",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="id"/>
                <field name="foo"/>
                <field name="int_field" readonly="id > 2"/>
            </list>
        `,
    });
    // select all records
    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_data_row .o_data_cell:eq(1)`).click();
    await contains(`.o_data_row [name=int_field] input`).edit("666");

    expect(`.modal-body`).toHaveText(`Among the 4 selected records, 2 are valid for this update.
Are you sure you want to perform the following update on those 2 records?

Field: Int field
Update to: 666`);
    expect(queryOne(".modal .o_modal_changes .o_field_widget").parentNode.style.pointerEvents).toBe(
        "none",
        { message: "pointer events should be deactivated on the demo widget" }
    );

    await contains(`.modal .btn-primary`).click();
    expect.verifySteps(["write"]);
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["1", "yop", "666"], {
        message: "the first row should be updated",
    });
    expect(queryAllTexts(`.o_data_row:eq(1) .o_data_cell`)).toEqual(["2", "blip", "666"], {
        message: "the second row should be updated",
    });
});

test(`editable list view: multi edition when the domain is selected`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1" limit="2">
                <field name="id"/>
                <field name="int_field"/>
            </list>
        `,
    });

    // select all records, and then select all domain
    await contains(`.o_list_record_selector input`).click();
    await contains(`.o_list_selection_box .o_list_select_domain`).click();

    // edit a field
    await contains(`.o_data_row .o_data_cell:eq(1)`).click();
    await contains(`.o_data_row [name=int_field] input`).edit("666");
    expect(`.modal-body`).toHaveText(
        /This update will only consider the records of the current page./
    );
});

test(`editable list view: many2one with readonly modifier`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="m2o" readonly="1"/>
                <field name="foo"/>
            </list>
        `,
    });

    // edit a field
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_data_row:eq(0) .o_data_cell:eq(0) div[name=m2o] a`).toHaveCount(1);
    expect(`.o_data_row .o_data_cell:eq(1) input`).toBeFocused({
        message: "focus should go to the char input",
    });
});

test(`editable list view: multi edition server error handling`, async () => {
    expect.errors(1);

    onRpc("write", () => {
        throw makeServerError();
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list multi_edit="1"><field name="foo" required="1"/></list>`,
    });

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();

    // edit a line and confirm
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    await contains(`.o_selected_row [name=foo] input`).edit("abc");
    await contains(`.o_list_view`).click();
    await contains(`.modal .btn-primary`).click();
    // Server error: if there was a crash manager, there would be an open error at this point...
    expect(`.o_data_row:eq(0) .o_data_cell`).toHaveText("yop", {
        message: "first cell should have discarded any change",
    });
    expect(`.o_data_row:eq(1) .o_data_cell`).toHaveText("blip", {
        message: "second selected record should not have changed",
    });
    expect(`.o_data_cell input.o_field_widget`).toHaveCount(0, {
        message: "no field should be editable anymore",
    });
});

test(`editable readonly list view: navigation`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
        selectRecord(resId) {
            expect.step(`resId: ${resId}`);
        },
    });
    expect(`.o_searchview_input`).toBeFocused();

    // ArrowDown two times must get to the checkbox selector of first data row
    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeFocused();

    // select the second record
    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(1) .o_list_record_selector input`).toBeFocused();
    expect(`.o_data_row:eq(1) .o_list_record_selector input`).not.toBeChecked();

    await press("space");
    await animationFrame();
    expect(`.o_data_row:eq(1) .o_list_record_selector input`).toBeFocused();
    expect(`.o_data_row:eq(1) .o_list_record_selector input`).toBeChecked();

    // select the fourth record
    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).toBeFocused();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).not.toBeChecked();

    await press("space");
    await animationFrame();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).toBeFocused();
    expect(`.o_data_row:eq(3) .o_list_record_selector input`).toBeChecked();

    // toggle a row mode
    await press("ArrowUp");
    await press("ArrowUp");
    await press("ArrowRight");
    await animationFrame();
    expect(`.o_data_row:eq(1) [name=foo]`).toBeFocused();

    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    // Keyboard navigation only interracts with selected elements
    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(3) [name=foo] input`).toBeFocused();

    await press("Tab"); // go to 4th row int_field
    await press("Tab"); // go to 2nd row foo field
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    await press("Tab"); // go to 2nd row int_field
    await press("Tab"); // go to 4th row foo field
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(3) [name=foo] input`).toBeFocused();

    await press("Shift+Tab"); // go to 2nd row int_field
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=int_field] input`).toBeFocused();

    await press("Shift+Tab"); // go to 2nd row foo field
    await press("Shift+Tab"); // go to 4th row int_field field
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(3) [name=int_field] input`).toBeFocused();

    // Clicking on an unselected row while a row is being edited will leave the edition
    await contains(`.o_data_row:eq(2) [name=foo]`).click();
    expect(`.o_selected_row`).toHaveCount(0);

    // Clicking on an unselected record while no row is being edited will open the record
    expect.verifySteps([]);
    await contains(`.o_data_row:eq(2) [name=foo]`).click();
    expect.verifySteps([`resId: 3`]);
});

test(`editable list view: multi edition: edit and validate last row`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);
    await contains(`.o_list_view .o_list_record_selector input`).click();

    await contains(`.o_data_row:eq(-1) [name=int_field]`).click();
    await contains(`.o_data_row:eq(-1) [name=int_field] input`).fill("7", { confirm: "Enter" });
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .btn-primary`).click();
    expect(`.o_data_row`).toHaveCount(4);
});

test(`editable readonly list view: navigation in grouped list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list multi_edit="1"><field name="foo"/></list>`,
        groupBy: ["bar"],
        selectRecord(resId) {
            expect.step(`resId: ${resId}`);
        },
    });

    // Open both groups
    expect(`.o_group_header`).toHaveCount(2);
    await contains(`.o_group_header:eq(0)`).click();
    await contains(`.o_group_header:eq(1)`).click();

    // select 2 records
    expect(`.o_data_row`).toHaveCount(4);
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(2) .o_list_record_selector input`).click();

    // toggle a row mode
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Keyboard navigation only interracts with selected elements
    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();

    // Click on a non selected row
    await contains(`.o_data_row:eq(3) [name=foo]`).click();
    expect(`.o_selected_row`).toHaveCount(0);

    // Click again should select the clicked record
    await contains(`.o_data_row:eq(3) [name=foo]`).click();
    expect.verifySteps(["resId: 3"]);
});

test.todo(
    `editable readonly list view: single edition does not behave like a multi-edition`,
    async () => {
        await mountView({
            resModel: "foo",
            type: "list",
            arch: `<list multi_edit="1"><field name="foo" required="1"/></list>`,
        });

        // select a record
        await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
        // edit a field (invalid input)
        await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
        await clear({ confirm: "blur" });
        await animationFrame();
        expect(`.modal`).toHaveCount(1, { message: "should have a modal (invalid fields)" });

        await contains(`.modal button.btn`).click();
        // edit a field
        await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
        await contains(`.o_data_row [name=foo] input`).edit("bar");
        expect(`.modal`).toHaveCount(0, { message: "should not have a modal" });
        expect(`.o_data_row:eq(0) .o_data_cell`).toHaveText("bar", {
            message: "the first row should be updated",
        });
    }
);

test(`non editable list view: multi edition`, async () => {
    stepAllNetworkCalls();
    onRpc("write", ({ args }) => {
        expect(args).toEqual([[1, 2], { int_field: 666 }], {
            message: "should write on multi records",
        });
    });
    onRpc("web_read", ({ args, kwargs }) => {
        if (args[0].length !== 1) {
            expect.step("conditional web_read");
            expect(args).toEqual([[1, 2]], { message: "should batch the read" });
            expect(kwargs.specification).toEqual({ foo: {}, int_field: {} });
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    // select two records
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();

    // edit a field
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(1)`).click();
    await contains(`.o_data_row [name=int_field] input`).edit("666");
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    expect(`.modal`).toHaveCount(1, { message: "modal appears when switching cells" });

    await contains(`.modal .btn-secondary`).click();
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["yop", "10"], {
        message: "changes have been discarded and row is back to readonly",
    });

    await contains(`.o_data_row:eq(0) .o_data_cell:eq(1)`).click();
    await contains(`.o_data_row [name=int_field] input`).edit("666");
    expect(`.modal`).toHaveCount(1, { message: "there should be an opened modal" });
    expect(queryOne(".modal").innerText.includes("those 2 records")).toBe(true, {
        message: "the number of records should be correctly displayed",
    });

    await contains(`.modal .btn-primary`).click();
    expect.verifySteps(["write", "web_read", "conditional web_read"]);
    expect(queryAllTexts(`.o_data_row:eq(0) .o_data_cell`)).toEqual(["yop", "666"], {
        message: "the first row should be updated",
    });
    expect(queryAllTexts(`.o_data_row:eq(1) .o_data_cell`)).toEqual(["blip", "666"], {
        message: "the second row should be updated",
    });
    expect(`.o_data_cell input.o_field_widget`).toHaveCount(0, {
        message: "no field should be editable anymore",
    });
});

test(`editable list view: m2m tags in grouped list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" multi_edit="1">
                <field name="bar"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        groupBy: ["bar"],
    });

    // Opens first group
    await contains(`.o_group_header:eq(1)`).click();
    expect(queryAllTexts(`td.o_many2many_tags_cell`)).toEqual([
        "Value 1\nValue 2",
        "Value 1\nValue 2\nValue 3",
        "",
    ]);

    await contains(`thead .o_list_record_selector input`).click();
    await contains(`.o_data_row .o_field_many2many_tags`).click();
    await contains(`.o_selected_row .o_field_many2many_tags .o_delete`).click();
    await contains(`.modal .btn-primary`).click();
    expect(queryAllTexts(`td.o_many2many_tags_cell`)).toEqual(["Value 2", "Value 2\nValue 3", ""]);
});

test(`editable list: edit many2one from external link`, async () => {
    Bar._views = {
        form: `<form><field name="name"/></form>`,
    };

    onRpc("get_formview_id", () => false);

    await mountViewInDialog({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" multi_edit="1"><field name="m2o"/></list>`,
    });
    expect(`.o_dialog .o_list_view`).toHaveCount(1);
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`thead .o_list_record_selector input`).click();
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1, { message: "in edit mode" });

    await contains(`.o_external_button`).click();
    // Clicking somewhere on the form dialog should not close it
    // and should not leave edit mode
    expect(`.modal[role='dialog']`).toHaveCount(2);

    await contains(`.modal[role='dialog']`).click();
    expect(`.modal[role='dialog']`).toHaveCount(2);
    expect(`.o_selected_row`).toHaveCount(1, { message: "in edit mode" });

    // Change the M2O value in the Form dialog (will open a confirmation dialog)
    await contains(`.modal:eq(1) input`).edit("OOF");
    await contains(`.modal:eq(1) .o_form_button_save`).click();
    expect(`.modal[role='dialog']`).toHaveCount(3);
    expect(`.modal:eq(2) .o_field_widget[name=m2o]`).toHaveText("OOF", {
        message: "Value of the m2o should be updated in the confirmation dialog",
    });

    // Close the confirmation dialog
    await contains(`.modal:eq(2) .btn-primary`).click();
    expect(`.o_data_cell:eq(0)`).toHaveText("OOF", {
        message: "Value of the m2o should be updated in the list",
    });
});

test(`editable list with fields with readonly modifier`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="bar"/>
                <field name="foo" readonly="bar"/>
                <field name="m2o" readonly="not bar"/>
                <field name="int_field"/>
            </list>
        `,
    });

    await contains(`.o_list_button_add`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_selected_row .o_field_boolean input`).not.toBeChecked();
    expect(`.o_selected_row .o_field_char`).not.toHaveClass("o_readonly_modifier");
    expect(`.o_selected_row .o_field_many2one`).toHaveClass("o_readonly_modifier");

    await contains(`.o_selected_row .o_field_boolean input`).click();
    expect(`.o_selected_row .o_field_boolean input`).toBeChecked();
    expect(`.o_selected_row .o_field_char`).toHaveClass("o_readonly_modifier");
    expect(`.o_selected_row .o_field_many2one`).not.toHaveClass("o_readonly_modifier");

    await contains(`.o_selected_row .o_field_many2one`).click();
    expect(`.o_selected_row .o_field_many2one input`).toBeFocused();
});

test(`editable form alongside html field: click out to unselect the row`, async () => {
    Bar._fields.name = fields.Char();

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <field name="text" widget="html"/>
                <field name="o2m">
                    <list editable="bottom">
                        <field name="name"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(`.o_data_row`).toHaveCount(0);

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_data_row`).toHaveClass("o_selected_row");

    await contains(`[name=o2m] .o_field_x2many .o_selected_row [name=name] input`).edit(
        "new value"
    );
    // click outside to unselect the row
    await contains(`.o_form_view`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_data_row`).not.toHaveClass("o_selected_row");
});

test(`list grouped by date:month`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="date"/></list>`,
        groupBy: ["date:month"],
    });
    expect(queryAllTexts(`.o_group_header`)).toEqual(["January 2017 (1)", "None (3)"], {
        message: "the group names should be correct",
    });
});

test(`grouped list edition with boolean_favorite widget`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({ bar: false }, { message: "should write the correct value" });
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="bar" widget="boolean_favorite"/></list>`,
        groupBy: ["m2o"],
    });

    await contains(`.o_group_header`).click();
    expect(`.o_data_row:eq(0) .fa-star`).toHaveCount(1, {
        message: "boolean value of the first record should be true",
    });

    await contains(".o_data_row:eq(0) .fa-star", { visible: false }).click();
    expect.verifySteps(["web_save"]);
    expect(`.o_data_row:eq(0) .fa-star-o`).toHaveCount(1, {
        message: "boolean value of the first record should have been updated",
    });
});

test(`grouped list view, indentation for empty group`, async () => {
    Foo._fields.priority = fields.Selection({
        selection: [
            [1, "Low"],
            [2, "Medium"],
            [3, "High"],
        ],
        default: 1,
    });
    Foo._records.push({
        id: 5,
        foo: "blip",
        int_field: -7,
        m2o: 1,
        priority: 2,
    });
    Foo._records.push({
        id: 6,
        foo: "blip",
        int_field: 5,
        m2o: 1,
        priority: 3,
    });

    onRpc("web_read_group", ({ kwargs }) => {
        // Override of the read_group to display the row even if there is no record in it,
        // to mock the behavihour of some fields e.g stage_id on the sale order.
        if (kwargs.groupby[0] === "m2o") {
            return {
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
            };
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="id"/></list>`,
        groupBy: ["priority", "m2o"],
    });

    // open the first group
    await contains(`.o_group_header`).click();
    expect(`tr:nth-child(1) th.o_group_name .fa`).toHaveCount(1, {
        message: "There should be an element creating the indentation for the subgroup.",
    });
    expect(`tr:nth-child(1) th.o_group_name span`).toHaveStyle(
        { "--o-list-group-level": "0" },
        {
            message:
                "The element creating the indentation should have a group level to use for margin css calculation.",
        }
    );
});

test(`use the limit attribute in arch`, async () => {
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.limit).toBe(2, {
            message: "should use the correct limit value",
        });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/></list>`,
    });
    expect.verifySteps(["web_search_read"]);
    expect(getPagerValue()).toEqual([1, 2]);
    expect(getPagerLimit()).toBe(4);
    expect(`.o_data_row`).toHaveCount(2, { message: "should display 2 data rows" });
});

test(`concurrent reloads finishing in inverse order`, async () => {
    let blockSearchRead = false;
    const deferred = new Deferred();
    onRpc("web_search_read", () => {
        if (blockSearchRead) {
            return deferred;
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        searchViewArch: `
            <search>
                <filter name="yop" domain="[('foo', '=', 'yop')]"/>
            </search>
        `,
    });
    expect(`.o_list_view .o_data_row`).toHaveCount(4, {
        message: "list view should contain 4 records",
    });

    // reload with a domain (this request is blocked)
    blockSearchRead = true;
    // list.reload({ domain: [["foo", "=", "yop"]] });
    await toggleSearchBarMenu();
    await toggleMenuItem("yop");
    expect(`.o_list_view .o_data_row`).toHaveCount(4, {
        message: "list view should still contain 4 records (search_read being blocked)",
    });

    // reload without the domain
    blockSearchRead = false;
    await toggleMenuItem("yop");
    expect(`.o_list_view .o_data_row`).toHaveCount(4, {
        message: "list view should still contain 4 records",
    });

    // unblock the RPC
    deferred.resolve();
    await animationFrame();
    expect(`.o_list_view .o_data_row`).toHaveCount(4, {
        message: "list view should still contain 4 records",
    });
});

test(`list view move to previous page when all records from last page deleted`, async () => {
    let checkSearchRead = false;
    onRpc("web_search_read", ({ kwargs }) => {
        if (checkSearchRead) {
            expect.step(`web_search_read (limit: ${kwargs.limit}, offset: ${kwargs.offset})`);
        }
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="3"><field name="display_name"/></list>`,
        actionMenus: {},
    });
    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(4);

    // move to next page
    await pagerNext();
    expect(getPagerValue()).toEqual([4, 4]);
    expect(getPagerLimit()).toBe(4);

    // delete a record
    await contains(`tbody .o_data_row td.o_list_record_selector input`).click();
    checkSearchRead = true;

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await contains(`.o-dropdown--menu .o_menu_item:contains(Delete)`).click();
    await contains(`.modal button.btn-primary`).click();
    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(3);
    expect.verifySteps([
        "web_search_read (limit: 3, offset: 3)",
        "web_search_read (limit: 3, offset: 0)",
    ]);
});

test(`grouped list view move to previous page of group when all records from last page deleted`, async () => {
    let checkSearchRead = false;
    onRpc("web_search_read", ({ kwargs }) => {
        if (checkSearchRead) {
            expect.step(`web_search_read (limit: ${kwargs.limit}, offset: ${kwargs.offset})`);
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="display_name"/></list>`,
        actionMenus: {},
        groupBy: ["m2o"],
    });
    expect(`th:contains(Value 1 (3))`).toHaveCount(1, {
        message: "Value 1 should contain 3 records",
    });
    expect(`th:contains(Value 2 (1))`).toHaveCount(1, {
        message: "Value 2 should contain 1 record",
    });

    await contains(`.o_group_header:eq(0)`).click();
    expect(getPagerValue(queryFirst(`.o_group_header`))).toEqual([1, 2]);
    expect(getPagerLimit(queryFirst(`.o_group_header`))).toBe(3);

    // move to next page
    await pagerNext(queryFirst(`.o_group_header`));
    expect(getPagerValue(queryFirst(`.o_group_header`))).toEqual([3, 3]);
    expect(getPagerLimit(queryFirst(`.o_group_header`))).toBe(3);

    // delete a record
    await contains(`.o_data_row .o_list_record_selector input`).click();
    checkSearchRead = true;
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await contains(`.dropdown-item:contains(Delete)`).click();
    await contains(`.modal .btn-primary`).click();
    expect(`th.o_group_name:eq(0) .o_pager_counter`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(2);
    expect.verifySteps([
        "web_search_read (limit: 2, offset: 2)",
        "web_search_read (limit: 2, offset: 0)",
    ]);
});

test(`grouped list view move to next page when all records from the current page deleted`, async () => {
    Foo._records = [1, 2, 3, 4, 5, 6]
        .map((i) => ({
            id: i,
            foo: `yop${i}`,
            m2o: 1,
        }))
        .concat([{ id: 7, foo: "blip", m2o: 2 }]);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/></list>`,
        actionMenus: {},
        groupBy: ["m2o"],
    });
    expect(`tr.o_group_header:eq(0) th:eq(0)`).toHaveText("Value 1 (6)");
    expect(`tr.o_group_header:eq(1) th:eq(0)`).toHaveText("Value 2 (1)");

    const firstGroup = queryFirst(`tr.o_group_header:eq(0)`);
    await contains(firstGroup).click();
    expect(getPagerValue(firstGroup)).toEqual([1, 2]);
    expect(getPagerLimit(firstGroup)).toBe(6);

    // delete all records from current page
    await contains(`thead .o_list_record_selector input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await contains(`.dropdown-item:contains(Delete)`).click();
    await contains(`.modal .btn-primary`).click();
    expect(`.o_group_header:eq(0) .o_group_name`).toHaveText(`Value 1 (4)\n1-2 / 4`);
    expect(queryAllTexts(`.o_data_row`)).toEqual(["yop3", "yop4"]);
});

test(`list view move to previous page when all records from last page archive/unarchived`, async () => {
    // add active field on foo model and make all records active
    Foo._fields.active = fields.Boolean({ default: true });

    onRpc("/web/dataset/call_kw/foo/action_archive", () => {
        Foo._records[3].active = false;
        return {};
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="3"><field name="display_name"/></list>`,
        actionMenus: {},
    });
    expect(`.o_pager_counter`).toHaveText("1-3 / 4", {
        message: "should have 2 pages and current page should be first page",
    });
    expect(`tbody td.o_list_record_selector`).toHaveCount(3, {
        message: "should have 3 records",
    });

    // move to next page
    await contains(`.o_pager_next`).click();
    expect(`.o_pager_counter`).toHaveText("4-4 / 4", {
        message: "should be on second page",
    });
    expect(`tbody td.o_list_record_selector`).toHaveCount(1, {
        message: "should have 1 records",
    });
    expect(`.o_control_panel_actions .o_cp_action_menus`).toHaveCount(0, {
        message: "sidebar should not be available",
    });

    await contains(`tbody .o_data_row:eq(0) td.o_list_record_selector:eq(0) input`).click();
    expect(`.o_control_panel_actions .o_cp_action_menus`).toHaveCount(1, {
        message: "sidebar should be available",
    });

    // archive all records of current page
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1, { message: "a confirm modal should be displayed" });

    await contains(`.modal-footer .btn-primary`).click();
    expect(`tbody td.o_list_record_selector`).toHaveCount(3, {
        message: "should have 3 records",
    });
    expect(queryFirst(`.o_pager_counter`)).toHaveText("1-3 / 3", {
        message: "should have 1 page only",
    });
});

test(`list should ask to scroll to top on page changes`, async () => {
    // add records to be able to scroll
    for (let i = 5; i < 55; i++) {
        Foo._records.push({ id: i, foo: "foo" });
    }
    patchWithCleanup(ListController.prototype, {
        onPageChangeScroll() {
            super.onPageChangeScroll(...arguments);
            expect.step("scroll");
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="3"><field name="display_name"/></list>`,
    });
    // switch pages (should ask to scroll)
    await pagerNext();
    await pagerPrevious();
    // should ask to scroll when switching pages
    expect.verifySteps(["scroll", "scroll"]);

    // change the limit (should not ask to scroll)
    await contains(`.o_pager_value`).click();
    await contains(`.o_pager_value`).edit("1-25");
    await animationFrame();
    expect(getPagerValue()).toEqual([1, 25]);
    // should not ask to scroll when changing the limit
    expect.verifySteps([]);

    await contains(".o_list_renderer").scroll({ top: 250 });
    expect(".o_list_renderer").toHaveProperty("scrollTop", 250);

    // switch pages again (should still ask to scroll)
    await pagerNext();
    // this is still working after a limit change
    expect.verifySteps(["scroll"]);
    // Should effectively reset the scroll position
    expect(".o_list_renderer").toHaveProperty("scrollTop", 0);
});

test(`list with handle field, override default_get, bottom when inline`, async () => {
    Foo._fields.int_field = fields.Integer({ default: 10 });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" default_order="int_field">
                <field name="int_field" widget="handle"/>
                <field name="foo"/>
            </list>
        `,
    });
    // starting condition
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual(["blip", "blip", "yop", "gnap"]);

    // click add a new line
    // save the record
    // check line is at the correct place
    await contains(`.o_list_button_add`).click();
    await contains(`[name=foo] input`).edit("ninja", { confirm: false });
    await contains(`.o_list_button_save`).click();
    await contains(`.o_list_button_add`).click();
    expect(queryAllTexts(`.o_data_cell.o_list_char`)).toEqual([
        "blip",
        "blip",
        "yop",
        "gnap",
        "ninja",
        "",
    ]);
});

test(`create record on list with modifiers depending on id`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="id" column_invisible="1"/>
                <field name="foo" readonly="id"/>
                <field name="int_field" invisible="id"/>
            </list>
        `,
    });
    // add a new record
    await contains(`.o_list_button_add`).click();
    // modifiers should be evaluted to false
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_selected_row [name=foo].o_field_widget`).not.toHaveClass("o_readonly_modifier");
    expect(`.o_selected_row div[name=int_field]`).toHaveCount(1);

    // set a value and save
    await contains(`.o_selected_row [name=foo] input`).edit("some value");
    await contains(`.o_list_button_save`).click();
    // int_field should not be displayed
    expect(`.o_data_row .o_data_cell:eq(1)`).toHaveText("");

    // edit again the just created record
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    // modifiers should be evaluated to true
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_readonly_modifier");
    expect(`.o_selected_row div[name=int_field]`).toHaveCount(0);
});

test(`readonly boolean in editable list is readonly`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="bar" readonly="foo != 'yop'"/>
            </list>
        `,
    });
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(1) [name=bar] input`).not.toBeEnabled();
    expect(`.o_data_row:eq(1) [name=bar] input`).toBeChecked();

    await contains(`.o_data_row:eq(1) [name=bar] div`).click();
    expect(`.o_data_row:eq(1) [name=bar] input`).toBeChecked();
    expect(`.o_data_row:eq(1) input[type=text]`).toBeFocused();

    // clicking on enabled checkbox with active row toggles check mark
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(0)`).click();
    expect(`.o_data_row:eq(0) [name=bar] input`).toBeEnabled();
    expect(`.o_data_row:eq(0) [name=bar] input`).toBeChecked();

    await contains(`.o_data_row:eq(0) div[name=bar] div`).click();
    expect(`.o_data_row:eq(0) [name=bar] input`).not.toBeChecked();
    expect(`.o_data_row:eq(0) [name=bar] input[type=checkbox]`).toBeFocused();
});

test(`grouped list with groups_limit attribute`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list groups_limit="3"><field name="foo"/></list>`,
        groupBy: ["int_field"],
    });
    expect(`.o_group_header`).toHaveCount(3); // page 1
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_pager`).toHaveCount(1); // has a pager

    await pagerNext(); // switch to page 2
    expect(`.o_group_header`).toHaveCount(1); // page 2
    expect(`.o_data_row`).toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // read_group page 1
        "has_group",
        "web_read_group", // read_group page 2
    ]);
});

test(`ungrouped list with groups_limit attribute, then group`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list groups_limit="3"><field name="foo"/></list>`,
        searchViewArch: `
            <search>
                <filter name="int_field" string="GroupBy IntField" context="{'group_by': 'int_field'}"/>
            </search>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);

    // add a custom group in searchview groupby
    await toggleSearchBarMenu();
    await toggleMenuItem("GroupBy IntField");
    expect(`.o_group_header`).toHaveCount(3);
    expect(`.o_pager_value`).toHaveText("1-3", {
        message: "pager should be correct",
    });
    expect(`.o_pager_limit`).toHaveText("4");
});

test(`grouped list with groups_limit attribute, then ungroup`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list groups_limit="3"><field name="foo"/></list>`,
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
    expect(`.o_group_header`).toHaveCount(3);
    expect(`.o_pager_value`).toHaveText("1-3", {
        message: "pager should be correct",
    });
    expect(`.o_pager_limit`).toHaveText("4");

    // remove groupby
    await removeFacet("GroupBy IntField");
    expect(`.o_data_row`).toHaveCount(4);
});

test(`multi level grouped list with groups_limit attribute`, async () => {
    for (let i = 50; i < 55; i++) {
        Foo._records.push({ id: i, foo: "foo", int_field: i });
    }
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list groups_limit="3"><field name="foo"/></list>`,
        groupBy: ["foo", "int_field"],
    });
    expect(`.o_group_header`).toHaveCount(3);
    expect(`.o_pager_value`).toHaveText("1-3", {
        message: "pager should be correct",
    });
    expect(`.o_pager_limit`).toHaveText("4");
    expect(queryAllTexts(`.o_group_header`)).toEqual(["blip (2)", "foo (5)", "gnap (1)"]);

    // open foo group
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_group_header`).toHaveCount(6);
    expect(queryAllTexts(`.o_group_header`)).toEqual([
        "blip (2)",
        "foo (5)\n1-3 / 5",
        "50 (1)",
        "51 (1)",
        "52 (1)",
        "gnap (1)",
    ]);
});

test(`grouped list with expand attribute`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="1"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(4);
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["blip", "yop", "blip", "gnap"]);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
    ]);
});

test(`grouped list with dynamic expand attribute (eval true)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="context.get('expand', False)"><field name="foo"/></list>`,
        groupBy: ["bar"],
        context: {
            expand: true,
        },
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(4);
});

test(`grouped list with dynamic expand attribute (eval false)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="context.get('expand', False)"><field name="foo"/></list>`,
        groupBy: ["bar"],
        context: {
            expand: false,
        },
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(0);
});

test(`grouped list (two levels) with expand attribute`, async () => {
    stepAllNetworkCalls();

    // the expand attribute only opens the first level groups
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="1"><field name="foo"/></list>`,
        groupBy: ["bar", "int_field"],
    });
    expect(`.o_group_header`).toHaveCount(6);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group", // global
        "has_group",
        "web_read_group", // first group
        "web_read_group", // second group
    ]);
});

test(`grouped lists with expand attribute and a lot of groups`, async () => {
    for (let i = 0; i < 15; i++) {
        Foo._records.push({ foo: "record " + i, int_field: i });
    }

    onRpc("web_read_group", () => {
        expect.step("web_read_group");
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list expand="1"><field name="foo"/></list>`,
        groupBy: ["int_field"],
    });
    expect(`.o_group_header`).toHaveCount(10); // page 1
    expect(`.o_data_row`).toHaveCount(10); // two groups contains two records
    expect(`.o_pager`).toHaveCount(1); // has a pager
    expect(queryAllTexts(`.o_group_name`)).toEqual([
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
    ]);

    await pagerNext(); // switch to page 2
    expect(`.o_group_header`).toHaveCount(7); // page 2
    expect(`.o_data_row`).toHaveCount(9); // two groups contains two records
    expect(queryAllTexts(`.o_group_name`)).toEqual([
        "9 (2)",
        "10 (2)",
        "11 (1)",
        "12 (1)",
        "13 (1)",
        "14 (1)",
        "17 (1)",
    ]);
    expect.verifySteps([
        "web_read_group", // read_group page 1
        "web_read_group", // read_group page 2
    ]);
});

test(`add filter in a grouped list with a pager`, async () => {
    defineActions([
        {
            id: 11,
            name: "Action 11",
            res_model: "foo",
            views: [[3, "list"]],
            search_view_id: [9, "search"],
            context: { group_by: ["int_field"] },
        },
    ]);

    Foo._views = {
        "list,3": `<list groups_limit="3"><field name="foo"/></list>`,
        "search,9": `
            <search>
                <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
            </search>
        `,
    };

    onRpc("web_read_group", ({ kwargs }) => {
        expect.step({ domain: kwargs.domain, offset: kwargs.offset });
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(11);
    expect(`.o_list_view`).toHaveCount(1);
    expect(getPagerValue()).toEqual([1, 3]);
    expect(`.o_group_header`).toHaveCount(3); // page 1

    await pagerNext();
    expect(getPagerValue()).toEqual([4, 4]);
    expect(`.o_group_header`).toHaveCount(1); // page 2

    // toggle a filter -> there should be only one group left (on page 1)
    await toggleSearchBarMenu();
    await toggleMenuItem("Not Bar");
    expect(getPagerValue()).toEqual([1, 1]);
    expect(`.o_group_header`).toHaveCount(1); // page 1
    expect.verifySteps([
        { domain: [], offset: 0 },
        { domain: [], offset: 3 },
        { domain: [["bar", "=", false]], offset: 0 },
    ]);
});

test(`grouped list: have a group with pager, then apply filter`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="2"><field name="foo"/></list>`,
        searchViewArch: `
            <search>
                <filter name="Some Filter" domain="[('foo', '=', 'gnap')]"/>
            </search>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_group_header`).toHaveCount(2);

    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_group_header .o_pager:first`).toHaveText("1-2 / 3");

    await contains(`.o_group_header .o_pager_next`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_group_header .o_pager:first`).toHaveText("3-3 / 3");

    await toggleSearchBarMenu();
    await toggleMenuItem("Some Filter");
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_group_header`).toHaveCount(1);
    expect(`.o_group_header .o_pager`).toHaveCount(0);
});

test(`editable grouped lists`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="bar"/></list>`,
        searchViewArch: `
            <search>
                <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
            </search>
        `,
    });
    await toggleSearchBarMenu();
    await toggleMenuItem("bar");
    await contains(`.o_group_header`).click();
    // enter edition (grouped case)
    await contains(`.o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    // click on the body should leave the edition
    await contains(`.o_list_view`).click();
    expect(`.o_selected_row`).toHaveCount(0);

    // reload without groupBy
    await toggleSearchBarMenu();
    await toggleMenuItem("bar");

    // enter edition (ungrouped case)
    await contains(`.o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    // click on the body should leave the edition
    await contains(`.o_list_view`).click();
    expect(`.o_selected_row`).toHaveCount(0);
});

test(`grouped lists are editable (ungrouped first)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="bar"/></list>`,
        searchViewArch: `
            <search>
                <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
            </search>
        `,
    });
    // enter edition (ungrouped case)
    await contains(`.o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    // reload with a groupby
    await toggleSearchBarMenu();
    await toggleMenuItem("bar");

    // open first group
    await contains(`.o_group_header`).click();

    // enter edition (grouped case)
    await contains(`.o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);
});

test(`char field edition in editable grouped list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click();
    await contains(`.o_data_cell`).click();
    await contains(`.o_selected_row .o_data_cell [name=foo] input`).edit("pla");
    await contains(`.o_list_button_save`).click();
    expect(Foo._records[3].foo).toBe("pla", {
        message: "the edition should have been properly saved",
    });
    expect(`.o_data_row:eq(0):contains(pla)`).toHaveCount(1);
});

test(`control panel buttons in editable grouped list views`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="bar"/></list>`,
        searchViewArch: `
            <search>
                <filter name="bar" string="bar" context="{'group_by': 'bar'}"/>
            </search>
        `,
    });
    expect(`.o_list_button_add`).toHaveCount(1);

    // reload with a groupby
    await toggleSearchBarMenu();
    await toggleMenuItem("bar");
    expect(`.o_list_button_add`).toHaveCount(1);

    // reload without groupby
    await toggleMenuItem("bar");
    expect(`.o_list_button_add`).toHaveCount(1);
});

test(`control panel buttons in multi editable grouped list views`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["foo"],
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    expect(`.o_data_row`).toHaveCount(0, { message: "all groups should be closed" });
    expect(`.o_list_button_add`).toHaveCount(1, {
        message: "should have a visible Create button",
    });

    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(2, { message: "first group should be opened" });
    expect(`.o_list_button_add`).toHaveCount(1, {
        message: "should have a visible Create button",
    });

    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_data_row:eq(0) .o_list_record_selector input:enabled`).toHaveCount(1, {
        message: "should have selected first record",
    });
    expect(`.o_list_button_add`).toHaveCount(1, {
        message: "should have a visible Create button",
    });

    await contains(`.o_group_header:eq(-1)`).click();
    expect(`.o_data_row`).toHaveCount(3, { message: "two groups should be opened" });
    expect(`.o_list_button_add`).toHaveCount(1, {
        message: "should have a visible Create button",
    });
});

test(`edit a line and discard it in grouped editable`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="int_field"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header:nth-child(2)`).click();
    await contains(`.o_data_row:nth-child(5) .o_data_cell:nth-child(2)`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:nth-child(5)`).toHaveClass("o_selected_row");

    await contains(`.o_list_button_discard`).click();
    await contains(`.o_data_row:nth-child(3) .o_data_cell:nth-child(2)`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:nth-child(3)`).toHaveClass("o_selected_row");

    await contains(`.o_list_button_discard`).click();
    expect(`.o_selected_row`).toHaveCount(0);

    await contains(`.o_data_row:nth-child(5) .o_data_cell:nth-child(2)`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:nth-child(5)`).toHaveClass("o_selected_row");
});

test(`add and discard a record in a multi-level grouped list view`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo" required="1"/></list>`,
        groupBy: ["foo", "bar"],
    });
    // unfold first subgroup
    await contains(`.o_group_header`).click();
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_group_header:eq(0)`).toHaveClass("o_group_open");
    expect(`.o_group_header:eq(1)`).toHaveClass("o_group_open");
    expect(`.o_data_row`).toHaveCount(1);

    // add a record to first subgroup
    await contains(`.o_group_field_row_add a`).click();
    expect(`.o_data_row`).toHaveCount(2);

    // discard
    await contains(`.o_list_button_discard`).click();
    expect(`.o_data_row`).toHaveCount(1);
});

test(`pressing ESC in editable grouped list should discard the current line changes`, async () => {
    // This test is wrong, there's a bug in list view when pressing "Escape".
    // The row becomes readonly but the value is not reset.

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header:eq(1)`).click();
    expect(`tr.o_data_row`).toHaveCount(3);

    await contains(`.o_data_cell`).click();
    // update foo field of edited row
    await contains(`.o_data_cell [name=foo] input`).edit("new_value", { confirm: false });
    expect(`.o_data_cell [name=foo] input`).toBeFocused();

    // discard by pressing ESC
    await press("Escape");
    await animationFrame();
    expect(`.modal`).toHaveCount(0);
    expect(`tbody tr td:contains(yop)`).toHaveCount(1);
    expect(`tr.o_data_row`).toHaveCount(3);
    expect(`tr.o_data_row.o_selected_row`).toHaveCount(0);
    expect(`.o_list_button_save`).not.toBeVisible();
});

test(`pressing TAB in editable="bottom" grouped list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    // open two groups
    await contains(`.o_group_header:eq(0)`).click();
    expect(`.o_data_row`).toHaveCount(1, { message: "first group contains 1 row" });

    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4, { message: "second group contains 3 rows" });

    await contains(`.o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go to first line of second group
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go to next line (still in second group)
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go to next line (still in second group)
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go back to first line of first group
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
});

test(`pressing TAB in editable="top" grouped list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
            </list>
        `,
        groupBy: ["bar"],
    });

    // open two groups
    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(1);

    await contains(`.o_group_header:eq(-1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row");
});

test(`pressing TAB in editable grouped list with create=0`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom" create="0"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });

    // open two groups
    await contains(`.o_group_header:eq(0)`).click();
    expect(`.o_data_row`).toHaveCount(1, { message: "first group contains 1 rows" });

    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4, { message: "first group contains 3 row" });

    await contains(`.o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go to the second group
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go to next line (still in second group)
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go to next line (still in second group)
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row");

    // Press 'Tab' -> should go back to first line of first group
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
});

test(`pressing SHIFT-TAB in editable="bottom" grouped list`, async () => {
    Foo._records[2].bar = false;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo" required="1"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(2);

    await contains(`.o_group_header:eq(-1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    // navigate inside a group
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1)`).not.toHaveClass("o_selected_row");

    // navigate between groups
    await contains(`.o_data_row:eq(2) .o_data_cell`).click();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
});

test(`pressing SHIFT-TAB in editable="top" grouped list`, async () => {
    Foo._records[2].bar = false;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo" required="1"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(2);

    await contains(`.o_group_header:eq(-1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    // navigate inside a group
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1)`).not.toHaveClass("o_selected_row");

    // navigate between groups
    await contains(`.o_data_row:eq(2) .o_data_cell`).click();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
});

test(`pressing SHIFT-TAB in editable grouped list with create="0"`, async () => {
    Foo._records[2].bar = false;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" create="0">
                <field name="foo" required="1"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click();
    expect(`.o_data_row`).toHaveCount(2);

    await contains(`.o_group_header:eq(-1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    // navigate inside a group
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1)`).not.toHaveClass("o_selected_row");

    // navigate between groups
    await contains(`.o_data_row:eq(2) .o_data_cell`).click();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    await press("shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
});

test.todo(`editing then pressing TAB in editable grouped list`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });

    // open two groups
    await contains(`.o_group_header:eq(0)`).click();
    expect(`.o_data_row`).toHaveCount(1, { message: "first group contains 1 rows" });

    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4, { message: "first group contains 3 row" });

    // select and edit last row of first group
    await contains(`.o_data_row:eq(0) .o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await edit("new value", { confirm: false });
    await press("tab");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    // fill foo field for the new record and press 'tab' -> should create another record
    // FIXME: input field hook calls update, but in a mutex -> .dirty is not set when we call applyCellKeydownEditModeGroup
    await edit("new record", { confirm: false });
    await press("tab");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    // leave this new row empty and press tab -> should discard the new record and move to the
    // next group
    await press("tab");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
        "web_save",
        "onchange",
        "web_save",
        "onchange",
    ]);
});

test(`editing then pressing TAB (with a readonly field) in grouped list`, async () => {
    Foo._records[0].bar = false;

    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field" readonly="1"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click();
    await contains(`.o_data_row [name=foo]`).click();
    await contains(`.o_selected_row [name=foo] input`).edit("new value", { confirm: "tab" });
    expect(`.o_data_row:eq(0) [name=foo]`).toHaveText("new value");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_save",
    ]);
});

test(`pressing ENTER in editable="bottom" grouped list view`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header:eq(0)`).click(); // open first group
    await contains(`.o_group_header:eq(1)`).click(); // open second group
    expect(`tr.o_data_row`).toHaveCount(4);

    await contains(`.o_data_row:eq(2) .o_data_cell`).click();
    expect(`tr.o_data_row:eq(2)`).toHaveClass("o_selected_row");

    // press enter in input should move to next record
    await press("Enter");
    await animationFrame();
    expect(`tr.o_data_row:eq(3)`).toHaveClass("o_selected_row");
    expect(`tr.o_data_row:eq(2)`).not.toHaveClass("o_selected_row");

    // press enter on last row should create a new record
    await press("Enter");
    await animationFrame();
    expect(`tr.o_data_row`).toHaveCount(5);
    expect(`tr.o_data_row:eq(4)`).toHaveClass("o_selected_row");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
        "onchange",
    ]);
});

test(`pressing ENTER in editable="top" grouped list view`, async () => {
    Foo._records[2].bar = false;

    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click();
    await contains(`.o_group_header:eq(-1)`).click();
    expect(`tr.o_data_row`).toHaveCount(4);

    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await press("Enter");
    await animationFrame();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    await press("Enter");
    await animationFrame();
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
        "web_search_read",
        "web_search_read",
    ]);
});

test(`pressing ENTER in editable grouped list view with create=0`, async () => {
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom" create="0"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
    ]);

    // Open group headers
    await contains(`.o_group_header:eq(0)`).click();
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_selected_row`).toHaveCount(0);
    expect.verifySteps(["web_search_read", "web_search_read"]);

    // Click on first data row
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Press enter in input should move to next record, even if record is in another group
    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    // Press enter in input should move to next record
    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(2)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();

    // Once again
    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(3)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(3) [name=foo] input`).toBeFocused();

    // Once again on the last data row should cycle to the first data row
    await press("Enter");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();
    expect.verifySteps([]);
});

test(`cell-level keyboard navigation in non-editable list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo" required="1"/></list>`,
        selectRecord(resId) {
            expect.step(`resId: ${resId}`);
        },
    });
    expect(`.o_searchview_input`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`thead .o_list_record_selector input`).toBeFocused();

    await press("ArrowUp");
    await animationFrame();
    expect(`.o_searchview_input`).toBeFocused();

    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(`tbody tr:eq(0) .o_list_record_selector input`).toBeFocused();

    await press("ArrowRight");
    await animationFrame();
    expect(`tbody tr:eq(0) .o_field_cell[name=foo]`).toBeFocused();
    expect(`tbody tr:eq(0) .o_field_cell[name=foo]`).toHaveText("yop");

    await press("ArrowRight");
    await animationFrame();
    expect(`tbody tr:eq(0) .o_field_cell[name=foo]`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`tbody tr:eq(1) .o_field_cell[name=foo]`).toBeFocused();
    expect(`tbody tr:eq(1) .o_field_cell[name=foo]`).toHaveText("blip");

    await press("ArrowDown");
    await animationFrame();
    expect(`tbody tr:eq(2) .o_field_cell[name=foo]`).toBeFocused();
    expect(`tbody tr:eq(2) .o_field_cell[name=foo]`).toHaveText("gnap");

    await press("ArrowDown");
    await animationFrame();
    expect(`tbody tr:eq(3) .o_field_cell[name=foo]`).toBeFocused();
    expect(`tbody tr:eq(3) .o_field_cell[name=foo]`).toHaveText("blip");

    await press("ArrowDown");
    await animationFrame();
    expect(`tbody tr:eq(3) .o_field_cell[name=foo]`).toBeFocused();
    expect(`tbody tr:eq(3) .o_field_cell[name=foo]`).toHaveText("blip");

    await press("ArrowRight");
    await animationFrame();
    expect(`tbody tr:eq(3) .o_field_cell[name=foo]`).toBeFocused();
    expect(`tbody tr:eq(3) .o_field_cell[name=foo]`).toHaveText("blip");

    await press("ArrowLeft");
    await animationFrame();
    expect(`tbody tr:eq(3) .o_list_record_selector input`).toBeFocused();

    await press("ArrowLeft");
    await animationFrame();
    expect(`tbody tr:eq(3) .o_list_record_selector input`).toBeFocused();

    await press("ArrowUp");
    await press("ArrowRight");
    await animationFrame();
    expect(`tbody tr:eq(2) .o_field_cell[name=foo]`).toBeFocused();
    expect(`tbody tr:eq(2) .o_field_cell[name=foo]`).toHaveText("gnap");

    await press("Enter");
    await animationFrame();
    expect.verifySteps(["resId: 3"]);
});

test(`keyboard navigation from last cell in editable list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    // Click on last cell
    await contains(`.o_data_row:eq(-1) [name=int_field]`).click();
    expect(`.o_data_row:eq(-1) [name=int_field] input`).toBeFocused();

    // Tab should focus the first field of first row
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Shift+Tab should focus back the last field of last row
    await press("Shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(-1) [name=int_field] input`).toBeFocused();
    // Enter should add a new row at the bottom
    expect(`.o_data_row`).toHaveCount(4);

    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(-1) [name=foo] input`).toBeFocused();

    // Enter should discard the edited row as it is pristine + get to first row
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Click on last cell
    await contains(`.o_data_row:eq(-1) [name=int_field]`).click();
    expect(`.o_data_row:eq(-1) [name=int_field] input`).toBeFocused();

    // Enter should add a new row at the bottom
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);

    // Edit the row and press enter: should add a new row
    await contains(`.o_data_row:eq(-1) [name=foo] input`).edit("blork", { confirm: "enter" });
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_data_row:eq(-1) [name=foo] input`).toBeFocused();

    // Escape should discard the added row as it is pristine + view should go into readonly mode
    await press("Escape");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(0);
});

test(`keyboard navigation from last cell in editable grouped list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_group_header`).toHaveCount(2);

    // Open first and second groups
    await contains(`.o_group_header:eq(0)`).click();
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    // Click on last cell
    await contains(`.o_data_row:eq(3) [name=int_field]`).click();
    expect(`.o_data_row:eq(3) [name=int_field] input`).toBeFocused();

    // Tab should focus the first field of first data row
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Shift+Tab should focus back the last field of last row
    await press("Shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(3) [name=int_field] input`).toBeFocused();

    // Enter should add a new row at the bottom
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(4) [name=foo] input`).toBeFocused();

    // Enter should discard the edited row as it is pristine + get to first row
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Click on last cell
    await contains(`.o_data_row:eq(3) [name=int_field]`).click();
    expect(`.o_data_row:eq(3) [name=int_field] input`).toBeFocused();

    // Enter should add a new row at the bottom
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(4) [name=foo] input`).toBeFocused();

    // Edit the row and press enter: should add a new row
    await contains(`.o_data_row:eq(4) [name=foo] input`).edit("blork", { confirm: "enter" });
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_data_row:eq(5) [name=foo] input`).toBeFocused();

    // Escape should discard the added row as it is pristine + view should go into readonly mode
    await press("Escape");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(0);

    // Click on last data row of first group
    expect(`.o_group_header:eq(0)`).toHaveText("No (1)\n -4");
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Enter should add a new row in the first group
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_group_header:eq(0)`).toHaveText("No (2)\n -4");

    // Enter should discard the edited row as it is pristine + get to next data row
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_group_header:eq(0)`).toHaveText("No (1)\n -4");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    // Shift+Tab should focus back the last field of first row
    await press("Shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=int_field] input`).toBeFocused();

    // Enter should add a new row in the first group
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_group_header:eq(0)`).toHaveText("No (2)\n -4");

    // Edit the row and press enter: should add a new row
    await contains(`.o_data_row:eq(1) [name=foo] input`).edit("zzapp", { confirm: "enter" });
    expect(`.o_data_row`).toHaveCount(7);
    expect(`.o_group_header:eq(0)`).toHaveText("No (3)\n -4");
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();
});

test(`keyboard navigation from last cell in multi-edit list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
        groupBy: ["bar"],
    });
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_group_header`).toHaveCount(2);

    // Open first and second groups
    await contains(`.o_group_header:eq(0)`).click();
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    // Click on last cell
    await contains(`.o_data_row:eq(3) [name=int_field]`).click();
    expect(`.o_data_row:eq(3) [name=int_field] input`).toBeFocused();

    // Tab should focus the first field of first data row
    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Shift+Tab should focus back the last field of last row
    await press("Shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(3) [name=int_field] input`).toBeFocused();

    // Enter should add a new row at the bottom
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(4) [name=foo] input`).toBeFocused();

    // Enter should discard the edited row as it is pristine + get to first row
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Click on last cell
    await contains(`.o_data_row:eq(3) [name=int_field]`).click();
    expect(`.o_data_row:eq(3) [name=int_field] input`).toBeFocused();

    // Enter should add a new row at the bottom
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(4) [name=foo] input`).toBeFocused();

    // Edit the row and press enter: should add a new row
    await contains(`.o_data_row:eq(4) [name=foo] input`).edit("blork", { confirm: "enter" });
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_data_row:eq(5) [name=foo] input`).toBeFocused();

    // Escape should discard the added row as it is pristine + view should go into readonly mode
    await press("Escape");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_selected_row`).toHaveCount(0);
    expect(`.o_group_header:eq(0)`).toHaveText("No (1)\n -4");

    // Click on last data row of first group
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    // Enter should add a new row in the first group
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_group_header:eq(0)`).toHaveText("No (2)\n -4");

    // Enter should discard the edited row as it is pristine + get to next data row
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_group_header:eq(0)`).toHaveText("No (1)\n -4");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    // Shift+Tab should focus back the last field of first row
    await press("Shift+Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=int_field] input`).toBeFocused();

    // Enter should add a new row in the first group
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(6);
    expect(`.o_group_header:eq(0)`).toHaveText("No (2)\n -4");

    // Edit the row and press enter: should add a new row
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();
    await contains(`.o_data_row:eq(1) [name=foo] input`).edit("zzapp", { confirm: "enter" });
    expect(`.o_data_row`).toHaveCount(7);
    expect(`.o_group_header:eq(0)`).toHaveText("No (3)\n -4");
    expect(`.o_data_row:eq(2) [name=foo] input`).toBeFocused();
});

test(`keyboard navigation with date range`, async () => {
    Foo._fields.date_end = fields.Date();
    Foo._records[0].date_end = "2017-01-26";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
                <field name="int_field"/>
            </list>
        `,
    });
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    const [startDateInput, endDateInput] = queryAll(`.o_data_row:eq(0) [name=date] input`);
    expect(startDateInput).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(endDateInput).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=int_field] input`).toBeFocused();
});

test(`keyboard navigation with Many2One field`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="m2o"/>
                <field name="int_field"/>
            </list>
        `,
    });
    await contains(`.o_data_row:eq(0) [name=foo]`).click();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=m2o] input`).toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=int_field] input`).toBeFocused();
});

test(`multi-edit records with ENTER does not crash`, async () => {
    const deferred = new Deferred();
    onRpc("write", () => deferred);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list multi_edit="1">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });

    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(2) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_data_cell[name=int_field]`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1) [name=int_field] input`).toBeFocused();

    await contains(`.o_data_row:eq(1) [name=int_field] input`).edit("234", { confirm: "enter" });
    expect(`.o_dialog`).toHaveCount(1); // confirmation dialog

    await contains(`.o_dialog .modal-footer .btn-primary`).click();
    deferred.resolve();
    await animationFrame();
    expect(queryAllTexts(`.o_data_cell.o_list_number`)).toEqual(["10", "234", "234", "-4"]);
    expect(`.o_dialog`).toHaveCount(0); // no more confirmation dialog, no error dialog
});

test(`editable grouped list: adding a second record pass the first in readonly`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
            </list>`,
        groupBy: ["bar"],
    });

    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_group_header`).toHaveCount(2);

    // Open first and second groups
    await contains(`.o_group_header:eq(0)`).click();
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_group_header:eq(0)`).toHaveText("No (1)");
    expect(`.o_group_header:eq(1)`).toHaveText("Yes (3)");

    // add a row in first group
    await contains(`.o_group_field_row_add:eq(0) a`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_group_header:eq(0)`).toHaveText("No (2)");
    expect(`.o_data_row:eq(1) [name=foo] input`).toBeFocused();

    // add a row in second group
    await contains(`.o_group_field_row_add:eq(1) a`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_group_header:eq(1)`).toHaveText("Yes (4)");
    expect(`.o_group_header:eq(0)`).toHaveText("No (1)");
    expect(`.o_data_row:eq(4) [name=foo] input`).toBeFocused();
});

test(`removing a groupby while adding a line from list`, async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `
            <list multi_edit="1" editable="bottom">
                <field name="display_name"/>
                <field name="foo"/>
            </list>`,
        searchViewArch: `
            <search>
                <field name="foo"/>
                <group expand="1" string="Group By">
                    <filter name="groupby_foo" context="{'group_by': 'foo'}"/>
                </group>
            </search>`,
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");

    // expand group
    await contains(`th.o_group_name`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    await contains(`td.o_group_field_row_add a`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    await contains(`.o_searchview_facet .o_facet_remove`).click();
    expect(`.o_selected_row`).toHaveCount(0);
});

test.todo(`cell-level keyboard navigation in editable grouped list`, async () => {
    Foo._records[0].bar = false;
    Foo._records[1].bar = false;
    Foo._records[2].bar = false;
    Foo._records[3].bar = true;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo" required="1"/>
            </list>
        `,
        groupBy: ["bar"],
    });

    await contains(`.o_group_name`).click();
    await contains(`.o_data_row:eq(1) [name=foo]`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    await contains(`.o_data_row:eq(1) [name=foo] input`).click();
    await edit("blipbloup", { confirm: false });
    await press("escape");
    await animationFrame();
    expect(`.modal`).toHaveCount(0);
    expect(`.o_data_row:eq(1)`).not.toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(1) [name=foo]`).toBeFocused();
    expect(`.o_data_row:eq(1) [name=foo]`).toHaveText("blip");

    await press("ArrowLeft");
    await animationFrame();
    expect(`.o_data_row:eq(1) input[type=checkbox]`).toBeFocused();

    await press("ArrowUp");
    await press("ArrowRight");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=foo]`).toBeFocused();

    await press("Enter");
    await animationFrame();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");

    await edit("Zipadeedoodah", { confirm: "enter" });
    await animationFrame();
    expect(`.o_data_row:eq(0)`).not.toHaveClass("o_selected_row");
    expect(`.o_data_row:eq(0) [name=foo]`).toHaveText("Zipadeedoodah");
    expect(`.o_data_row:eq(1) [name=foo]`).toBeFocused();
    expect(`.o_data_row:eq(1) [name=foo]`).toHaveText("blip");

    await press("ArrowUp");
    await press("ArrowRight");
    await animationFrame();
    expect(`.o_data_row:eq(1) [name=foo]`).toBeFocused();
    expect(`.o_data_row:eq(1) [name=foo]`).toHaveText("blip");

    await press("ArrowDown");
    await press("ArrowLeft");
    await animationFrame();
    expect(`.o_data_row:eq(1) [name=foo]`).toBeFocused();
    expect(`.o_data_row:eq(1) [name=foo]`).toHaveText("blip");

    await press("Escape");
    await animationFrame();
    expect(`.o_data_row:eq(1) td[name=foo]`).toBeFocused();

    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(`.o_group_field_row_add a`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_group_name:eq(1)`).toBeFocused();
    expect(`.o_data_row`).toHaveCount(3);

    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(4);
    expect(`.o_group_name:eq(1)`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(3) [name=foo]`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_group_field_row_add:eq(1) a`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_group_field_row_add:eq(1) a`).toBeFocused();

    // default Enter on a A tag
    await press("Enter");
    await animationFrame();
    await contains(`.o_group_field_row_add a:eq(1)`).click();
    expect(`.o_data_row:eq(4) [name=foo] input`).toBeFocused();

    await contains(`.o_data_row:eq(4) [name=foo] input`).edit("cheateur arrete de cheater", {
        confirm: "Enter",
    });
    expect(`.o_data_row`).toHaveCount(6);

    await press("Escape");
    await animationFrame();
    expect(`.o_group_field_row_add:eq(1) a`).toBeFocused();

    // come back to the top
    for (let i = 0; i < 9; i++) {
        await press("ArrowUp");
    }
    await animationFrame();
    expect(`thead th:eq(1)`).toBeFocused();

    await press("ArrowLeft");
    await animationFrame();
    expect(`thead th.o_list_record_selector input`).toBeFocused();

    await press("ArrowDown");
    await press("ArrowDown");
    await press("ArrowRight");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=foo] input`).toBeFocused();

    await press("ArrowUp");
    await animationFrame();
    expect(`.o_group_header:eq(0) .o_group_name`).toBeFocused();
    expect(`.o_data_row`).toHaveCount(5);

    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_group_header:eq(0) .o_group_name`).toBeFocused();

    await press("ArrowRight");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_group_header:eq(0) .o_group_name`).toBeFocused();

    await press("ArrowRight");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_group_header:eq(0) .o_group_name`).toBeFocused();

    await press("ArrowLeft");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_group_header:eq(0) .o_group_name`).toBeFocused();

    await press("ArrowLeft");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_group_header:eq(0) .o_group_name`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_group_header:eq(1) .o_group_name`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=foo]`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_data_row:eq(1) [name=foo]`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_group_field_row_add a`).toBeFocused();

    await press("ArrowUp");
    await animationFrame();
    expect(`.o_data_row:eq(1) [name=foo]`).toBeFocused();

    await press("ArrowUp");
    await animationFrame();
    expect(`.o_data_row:eq(0) [name=foo]`).toBeFocused();
});

test(`execute group header button with keyboard navigation`, async () => {
    mockService("action", {
        doActionButton: ({ name }) => {
            expect.step(name);
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <groupby name="m2o">
                    <button type="object" name="some_method" string="Do this"/>
                </groupby>
            </list>
        `,
        groupBy: ["m2o"],
    });
    expect(`.o_data_row`).toHaveCount(0);

    // focus create button as a starting point
    expect(`.o_list_button_add`).toHaveCount(1);

    queryFirst(`.o_list_button_add`).focus();
    expect(`.o_list_button_add`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`thead th.o_list_record_selector input`).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(`.o_group_header:nth-child(1) .o_group_name`).toBeFocused();

    // unfold first group
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(3);
    expect(`.o_group_header:nth-child(1) .o_group_name`).toBeFocused();

    // move to first record of opened group
    await press("ArrowDown");
    await animationFrame();
    expect(`tbody .o_data_row:eq(0) td[name=foo]`).toBeFocused();

    // move back to the group header
    await press("ArrowUp");
    await animationFrame();
    expect(`.o_group_header:nth-child(1) .o_group_name`).toBeFocused();

    // fold the group
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_group_header:nth-child(1) .o_group_name`).toBeFocused();

    // unfold the group
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(3);
    expect(`.o_group_header:nth-child(1) .o_group_name`).toBeFocused();

    // tab to the group header button
    await press("Tab");
    await animationFrame();
    expect(`.o_group_header .o_group_buttons button:eq(0)`).toBeFocused();

    // click on the button by pressing enter
    expect.verifySteps([]);
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(3);
    expect.verifySteps(["some_method"]);
});

test(`add a new row in grouped editable="top" list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo" required="1"/></list>`,
        groupBy: ["bar"],
    });

    await contains(`.o_group_header`).click(); // open group "No"
    await contains(`.o_group_field_row_add a`).click(); // add a new row
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(`.o_selected_row [name=foo] input`).toBeFocused({
        message: "The first input of the line should have the focus",
    });
    expect(`.o_data_row`).toHaveCount(2);

    await contains(`.o_list_button_discard`).click();
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_group_field_row_add a:eq(1)`).click(); // create row in second group "Yes"
    expect(`.o_group_name:eq(1)`).toHaveText("Yes (4)", {
        message: "group should have correct name and count",
    });
    expect(`.o_data_row`).toHaveCount(5);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");

    await contains(`.o_selected_row [name=foo] input`).edit("pla", { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(`.o_data_row`).toHaveCount(5);
});

test(`add a new row in grouped editable="bottom" list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo" required="1"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click(); // open group "No"
    await contains(`.o_group_field_row_add a`).click(); // add a new row
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(`.o_data_row`).toHaveCount(2);

    await contains(`.o_list_button_discard`).click();
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_group_field_row_add a:eq(1)`).click(); // create row in second group "Yes"
    expect(`.o_data_row:eq(4)`).toHaveClass("o_selected_row");

    await contains(`.o_selected_row [name=foo] input`).edit("pla", { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(`.o_data_row`).toHaveCount(5);
});

test("editable grouped list: fold group with edited row", async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: '<list editable="top"><field name="foo"/></list>',
        groupBy: ["bar"],
    });

    await contains(".o_group_header").click();
    expect(".o_data_row .o_data_cell").toHaveText("blip");
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_selected_row [name=foo] input").edit("some change");
    await contains(".o_group_header").click();
    await contains(".o_group_header").click();
    expect(".o_data_row .o_data_cell").toHaveText("some change");
});

test("editable grouped list: add row with edited row", async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: '<list editable="bottom"><field name="foo"/></list>',
        groupBy: ["bar"],
    });

    await contains(".o_group_header").click();
    expect(".o_data_row").toHaveCount(1);
    await contains(".o_data_row .o_data_cell").click();
    await contains(".o_selected_row [name=foo] input").edit("some change");
    await contains(".o_group_field_row_add a").click();
    expect(".o_data_row").toHaveCount(2);
    expect(".o_data_row:first .o_data_cell").toHaveText("some change");
});

test(`add and discard a line through keyboard navigation without crashing`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo" required="1"/></list>`,
        groupBy: ["bar"],
    });

    // open the last group
    await contains(`.o_group_header:eq(-1)`).click();
    expect(`.o_data_row`).toHaveCount(3);

    // Can trigger ENTER on "Add a line" link ?
    expect(`.o_group_field_row_add a`).toHaveCount(1);

    queryFirst(`.o_group_field_row_add a`).focus();
    expect(`.o_group_field_row_add a`).toBeFocused();
    await press("Enter");
    await animationFrame();
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_list_button_discard`).click();
    // At this point, a crash manager should appear if no proper link targetting
    expect(`.o_data_row`).toHaveCount(3);
});

test(`discard an invalid row in a list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo" required="1"/></list>`,
    });

    await contains(`.o_data_cell`).click();
    expect(`.o_field_invalid`).toHaveCount(0);
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`[name=foo] input`).edit("");
    await contains(`.o_list_view`).click();
    expect(`.o_field_invalid`).toHaveCount(1);
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`[name=foo] input`).toHaveValue("");

    await contains(`.o_list_button_discard`).click();
    expect(`.o_field_invalid`).toHaveCount(0);
    expect(`.o_selected_row`).toHaveCount(0);
    expect(`[name='foo']:eq(0)`).toHaveText("yop");
});

test(`editable grouped list with create="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" create="0"><field name="foo" required="1"/></list>`,
        groupBy: ["bar"],
    });

    await contains(`.o_group_header`).click(); // open group
    expect(`.o_group_field_row_add a`).toHaveCount(0, {
        message: "Add a line should not be available in readonly",
    });
});

test(`add a new row in (selection) grouped editable list`, async () => {
    Foo._fields.priority = fields.Selection({
        selection: [
            [1, "Low"],
            [2, "Medium"],
            [3, "High"],
        ],
        default: 1,
    });
    Foo._records.push({
        id: 5,
        foo: "blip",
        int_field: -7,
        m2o: 1,
        priority: 2,
    });
    Foo._records.push({
        id: 6,
        foo: "blip",
        int_field: 5,
        m2o: 1,
        priority: 3,
    });

    onRpc("onchange", ({ kwargs }) => expect.step(kwargs.context.default_priority.toString()));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="priority"/>
                <field name="m2o"/>
            </list>
        `,
        groupBy: ["priority"],
    });
    await contains(`.o_group_header`).click(); // open group
    await contains(`.o_group_field_row_add a`).click(); // add a new row
    await contains(`[name=foo] input`).edit("xyz", { confirm: false }); // make record dirty
    await contains(`.o_list_view`).click(); // unselect row
    expect.verifySteps(["1"]);
    expect(`.o_data_row .o_data_cell:eq(1)`).toHaveText("Low", {
        message: "should have a column name with a value from the groupby",
    });

    await contains(`.o_group_header:eq(1)`).click();
    await contains(`.o_group_field_row_add a:eq(1)`).click(); // create row in second group
    await contains(`.o_list_view`).click(); // unselect row
    expect(`.o_data_row:eq(5) .o_data_cell:eq(1)`).toHaveText("Medium", {
        message: "should have a column name with a value from the groupby",
    });
    expect.verifySteps(["2"]);
});

test(`add a new row in (m2o) grouped editable list`, async () => {
    onRpc("onchange", ({ kwargs }) => {
        expect.step(kwargs.context.default_m2o.toString());
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="m2o"/>
            </list>
        `,
        groupBy: ["m2o"],
    });
    await contains(`.o_group_header`).click(); // open group
    await contains(`.o_group_field_row_add a`).click(); // add a new row
    await contains(`.o_list_view`).click(); // unselect row
    expect(`.o_data_row:eq(0) .o_data_cell:eq(1)`).toHaveText("Value 1", {
        message: "should have a column name with a value from the groupby",
    });
    expect.verifySteps(["1"]);

    await contains(`.o_group_header:eq(1)`).click();
    await contains(`.o_group_field_row_add a:eq(1)`).click(); // create row in second group
    await contains(`.o_list_view`).click(); // unselect row
    expect(`.o_data_row:eq(3) .o_data_cell:eq(1)`).toHaveText("Value 2", {
        message: "should have a column name with a value from the groupby",
    });
    expect.verifySteps(["2"]);
});

test(`list view with optional fields rendering`, async () => {
    defineParams({ lang_parameters: { direction: "ltr" } });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
                <field name="amount"/>
                <field name="reference" optional="hide"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(4, {
        message: "should have 4 th, 1 for selector, 2 for columns and 1 for optional columns",
    });
    expect(`tfoot td`).toHaveCount(4, {
        message: "should have 4 td, 1 for selector, 2 for columns and 1 for optional columns",
    });
    expect(`table .o_optional_columns_dropdown`).toHaveCount(1, {
        message: "should have the optional columns dropdown toggle inside the table",
    });
    expect(`table > thead > tr > th:eq(-1) .o_optional_columns_dropdown`).toHaveCount(1, {
        message: "The optional fields toggler is in the last header column",
    });

    // optional fields
    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(`.o-dropdown--menu span.dropdown-item`).toHaveCount(2, {
        message: "dropdown have 2 optional field foo with checked and bar with unchecked",
    });

    // enable optional field
    await contains(`.o-dropdown--menu span.dropdown-item:eq(0)`).click();
    // 5 th (1 for checkbox, 3 for columns, 1 for optional columns)
    expect(`th`).toHaveCount(5, { message: "should have 5 th" });
    expect(`tfoot td`).toHaveCount(5, { message: "should have 5 td" });
    expect(`th[data-name=m2o]`).toHaveCount(1);
    expect(queryAllTexts(`.o-dropdown--menu span.dropdown-item`)).toEqual(["M2o", "Reference"]);
    expect(`.o-dropdown--menu span.dropdown-item [name=m2o]`).toBeChecked();

    await contains(`.o-dropdown--menu span.dropdown-item [name=m2o]`).click();
    // 4 th (1 for checkbox, 2 for columns, 1 for optional columns)
    expect(`th`).toHaveCount(4, { message: "should have 4 th" });
    expect(`tfoot td`).toHaveCount(4, { message: "should have 4 td" });
    expect(`th[data-name=m2o]`).toHaveCount(0);
    expect(`.o-dropdown--menu span.dropdown-item [name=m2o]`).not.toBeChecked();
});

test(`list view with optional fields rendering in RTL mode`, async () => {
    defineParams({
        lang_parameters: {
            direction: "rtl",
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
                <field name="amount"/>
                <field name="reference" optional="hide"/>
            </list>
        `,
    });
    expect(`table .o_optional_columns_dropdown`).toHaveCount(1, {
        message: "should have the optional columns dropdown toggle inside the table",
    });
    expect(`table > thead > tr > th:eq(-1) .o_optional_columns_dropdown`).toHaveCount(1, {
        message: "The optional fields toggler is in the last header column",
    });
});

test(`optional fields do not disappear even after listview reload`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
                <field name="amount"/>
                <field name="reference" optional="hide"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(4, {
        message: "should have 3 th, 1 for selector, 2 for columns, 1 for optional columns",
    });

    // enable optional field
    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(`.o-dropdown--menu span.dropdown-item:eq(0) input`).not.toBeChecked();

    await contains(`.o-dropdown--menu span.dropdown-item:eq(0)`).click();
    expect(`th`).toHaveCount(5, {
        message: "should have 5 th 1 for selector, 3 for columns, 1 for optional columns",
    });
    expect(`th[data-name=m2o]`).toHaveCount(1);

    await contains(`tbody .o_list_record_selector input`).click();
    expect(`.o_list_selection_box`).toHaveCount(1);

    await contains(`.o_pager_value`).click();
    await contains(`input.o_pager_value`).edit("1-4");
    expect(`.o_list_selection_box`).toHaveCount(0);
    expect(`th`).toHaveCount(5, {
        message:
            "should have 5 th 1 for selector, 3 for columns, 1 for optional columns ever after listview reload",
    });
    expect(`th[data-name=m2o]`).toHaveCount(1);

    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(`.o-dropdown--menu span.dropdown-item:eq(0) input`).toBeChecked();
});

test(`optional fields is shown only if enabled`, async () => {
    defineActions([
        {
            id: 1,
            name: "Currency Action 1",
            res_model: "foo",
            views: [[1, "list"]],
        },
    ]);

    Foo._views = {
        "list,1": `
            <list>
                <field name="currency_id" optional="show"/>
                <field name="display_name" optional="show"/>
            </list>
        `,
        search: `<search/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`th`).toHaveCount(4, {
        message: "should have 4 th, 1 for selector, 2 for columns, 1 for optional columns",
    });

    // disable optional field
    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    await contains(`.o-dropdown--menu span.dropdown-item:eq(0)`).click();
    expect(`th`).toHaveCount(3, {
        message: "should have 3 th, 1 for selector, 1 for columns, 1 for optional columns",
    });

    await getService("action").doAction(1);
    expect(`th`).toHaveCount(3, {
        message:
            "should have 3 th, 1 for selector, 1 for columns, 1 for optional columns ever after listview reload",
    });
});

test(`selection is kept when optional fields are toggled`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(3);

    // select a record
    await contains(`.o_data_row .o_list_record_selector input`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(1);

    // add an optional field
    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    await contains(`.o-dropdown--menu span.dropdown-item:eq(0) label`).click();
    expect(`th`).toHaveCount(4);
    expect(`.o_list_record_selector input:checked`).toHaveCount(1);

    // select all records
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_record_selector input:checked`).toHaveCount(5);

    // remove an optional field
    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    await contains(`.o-dropdown--menu span.dropdown-item:eq(0) label`).click();
    expect(`th`).toHaveCount(3);
    expect(`.o_list_record_selector input:checked`).toHaveCount(5);
});

test(`list view with optional fields and async rendering`, async () => {
    const deferred = new Deferred();
    const charField = registry.category("fields").get("char");
    class AsyncCharField extends charField.component {
        setup() {
            super.setup();
            onWillStart(() => {
                expect.step("onWillStart");
                return deferred;
            });
        }
    }
    registry.category("fields").add("asyncwidget", { component: AsyncCharField });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="m2o"/>
                <field name="foo" widget="asyncwidget" optional="hide"/>
            </list>
        `,
    });
    expect(`th`).toHaveCount(3);
    expect(`.o_optional_columns_dropdown .show`).toHaveCount(0);

    // add an optional field (we click on the label on purpose, as it will trigger
    // a second event on the input)
    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(`.o_optional_columns_dropdown .show`).toHaveCount(1);
    expect(`.o-dropdown--menu input:checked`).toHaveCount(0);

    await contains(`.o-dropdown--menu span.dropdown-item:eq(0) label`).click();
    expect(`th`).toHaveCount(3);
    expect(`.o_optional_columns_dropdown .show`).toHaveCount(1);
    expect(`.o-dropdown--menu input:checked`).toHaveCount(1);
    expect.verifySteps(["onWillStart", "onWillStart", "onWillStart", "onWillStart"]); // 4 rows

    deferred.resolve();
    await animationFrame();
    expect(`th`).toHaveCount(4);
    expect(`.o_optional_columns_dropdown .show`).toHaveCount(1);
    expect(`.o-dropdown--menu input:checked`).toHaveCount(1);
});

test(`change the viewType of the current action`, async () => {
    defineActions([
        {
            id: 1,
            name: "Partners Action 1",
            res_model: "foo",
            views: [[1, "kanban"]],
        },
        {
            id: 2,
            name: "Partners",
            res_model: "foo",
            views: [
                [false, "list"],
                [1, "kanban"],
            ],
        },
    ]);

    Foo._views = {
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `
            <list limit="3">
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
                <field name="o2m" optional="show"/>
            </list>
        `,
        search: `<search><field name="foo" string="Foo"/></search>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);
    expect(`.o_list_view`).toHaveCount(1, { message: "should have rendered a list view" });
    expect(`th`).toHaveCount(4, {
        message: "should display 4 th (selector + 2 fields + optional columns)",
    });

    // enable optional field
    await contains(`table .o_optional_columns_dropdown_toggle`).click();
    expect(`.o-dropdown--menu span.dropdown-item [name=m2o]`).not.toBeChecked();
    expect(`.o-dropdown--menu span.dropdown-item [name=o2m]`).toBeChecked();

    await contains(`.o-dropdown--menu span.dropdown-item`).click();
    expect(`th`).toHaveCount(5, {
        message: "should display 5 th (selector + 3 fields + optional columns)",
    });
    expect(`th[data-name=m2o]`).toHaveCount(1);

    // switch to kanban view
    await contains(`.o_switch_view.o_kanban`).click();
    expect(`.o_list_view`).toHaveCount(0, { message: "should not display the list view anymore" });
    expect(`.o_kanban_view`).toHaveCount(1, { message: "should have switched to the kanban view" });

    // switch back to list view
    await contains(`.o_switch_view.o_list`).click();
    expect(`.o_kanban_view`).toHaveCount(0, {
        message: "should not display the kanban view anymoe",
    });
    expect(`.o_list_view`).toHaveCount(1, { message: "should display the list view" });
    expect(`th`).toHaveCount(5, { message: "should display 5 th" });
    expect(`th[data-name=m2o]`).toHaveCount(1);
    expect(`th[data-name=o2m]`).toHaveCount(1);

    // disable optional field
    await contains(`table .o_optional_columns_dropdown_toggle`).click();
    expect(`.o-dropdown--menu span.dropdown-item [name=m2o]`).toBeChecked();
    expect(`.o-dropdown--menu span.dropdown-item [name=o2m]`).toBeChecked();

    await contains(`.o-dropdown--menu span.dropdown-item input:eq(1)`).click();
    expect(`.o-dropdown--menu span.dropdown-item [name=m2o]`).toBeChecked();
    expect(`.o-dropdown--menu span.dropdown-item [name=o2m]`).not.toBeChecked();
    expect(`th`).toHaveCount(4, { message: "should display 4 th" });

    await getService("action").doAction(1);
    expect(`.o_list_view`).toHaveCount(0, { message: "should not display the list view anymore" });
    expect(`.o_kanban_view`).toHaveCount(1, { message: "should have switched to the kanban view" });

    await getService("action").doAction(2);
    expect(`.o_kanban_view`).toHaveCount(0, { message: "should not havethe kanban view anymoe" });
    expect(`.o_list_view`).toHaveCount(1, { message: "should display the list view" });

    await contains(`table .o_optional_columns_dropdown_toggle`).click();
    expect(`th`).toHaveCount(4, { message: "should display 4 th" });
    expect(`.o-dropdown--menu span.dropdown-item [name=m2o]`).toBeChecked();
    expect(`.o-dropdown--menu span.dropdown-item [name=o2m]`).not.toBeChecked();
});

test(`list view with optional fields rendering and local storage mock`, async () => {
    let forceLocalStorage = true;
    patchWithCleanup(localStorage, {
        getItem(key) {
            if (key.startsWith("optional_fields")) {
                expect.step(["getItem", key]);
                if (forceLocalStorage) {
                    return "m2o";
                }
            }
            return super.getItem(...arguments);
        },
        setItem(key, value) {
            if (key.startsWith("optional_fields")) {
                expect.step(["setItem " + key, value]);
            }
            super.setItem(...arguments);
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
                <field name="reference" optional="show"/>
            </list>
        `,
        viewId: 42,
    });

    const localStorageKey = "optional_fields,foo,list,42,foo,m2o,reference";
    expect.verifySteps([["getItem", localStorageKey]]);
    expect(`th`).toHaveCount(4, {
        message: "should have 4 th, 1 for selector, 2 for columns, 1 for optional columns",
    });
    expect(`th[data-name=m2o]`).toHaveCount(1);
    expect(`th[data-name=reference]`).toHaveCount(0);

    // optional fields
    await contains(`table .o_optional_columns_dropdown button`).click();
    expect(`.o-dropdown--menu span.dropdown-item`).toHaveCount(2, {
        message: "dropdown have 2 optional fields",
    });

    forceLocalStorage = false;
    // enable optional field
    await contains(`.o-dropdown--menu span.dropdown-item:eq(1) input`).click();
    // Only a setItem since the list view maintains its own internal state of toggled
    // optional columns.
    expect.verifySteps([
        [`setItem ${localStorageKey}`, ["m2o", "reference"]],
        ["getItem", "optional_fields,foo,list,42,foo,m2o,reference"],
    ]);
    // 5 th (1 for checkbox, 3 for columns, 1 for optional columns)
    expect(`th`).toHaveCount(5, { message: "should have 5 th" });
    expect(`th[data-name=m2o]`).toHaveCount(1);
    expect(`th[data-name=reference]`).toHaveCount(1);
});

test(`list view with optional fields from local storage being the empty array`, async () => {
    patchWithCleanup(localStorage, {
        getItem(key) {
            if (key.startsWith("optional_fields")) {
                expect.step(["getItem", key]);
            }
            return super.getItem(...arguments);
        },
        setItem(key, value) {
            if (key.startsWith("optional_fields")) {
                expect.step(["setItem " + key, value]);
            }
            super.setItem(...arguments);
        },
    });

    const verifyHeaders = (namedHeaders) => {
        // const headers = [...queryAll(`.o_list_table thead th`)];
        expect(`.o_list_table thead th`).toHaveCount(namedHeaders.length + 2);
        expect(`.o_list_table thead th:eq(0)`).toHaveClass("o_list_record_selector");
        expect(`.o_list_table thead th:last`).toHaveClass("o_list_actions_header");
        for (let i = 0; i < namedHeaders.length; i++) {
            expect(`.o_list_table thead th:eq(${i + 1})`).toHaveAttribute(
                "data-name",
                namedHeaders[i],
                { message: `header at index ${i} is ${namedHeaders[i - 1]}` }
            );
        }
    };

    defineActions([
        {
            id: 1,
            name: "Action 1",
            res_model: "foo",
            views: [[42, "list"]],
            search_view_id: [1, "search"],
        },
    ]);

    Foo._views = {
        "search,1": `<search/>`,
        "list,42": `
            <list>
                <field name="foo"/>
                <field name="m2o" optional="hide"/>
                <field name="reference" optional="show"/>
            </list>
        `,
    };

    const localStorageKey = "optional_fields,foo,list,42,foo,m2o,reference";
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    // verify initialization
    expect.verifySteps([["getItem", localStorageKey]]);
    verifyHeaders(["foo", "reference"]);
    // open optional columns headers dropdown
    await contains(`table .o_optional_columns_dropdown button`).click();
    expect(`.o-dropdown--menu span.dropdown-item`).toHaveCount(2, {
        message: "dropdown has 2 optional column headers",
    });
    // disable optional field "reference" (no optional column enabled)
    await contains(`.o-dropdown--menu span.dropdown-item input:eq(1)`).click();
    expect.verifySteps([
        [`setItem ${localStorageKey}`, []],
        ["getItem", "optional_fields,foo,list,42,foo,m2o,reference"],
    ]);
    verifyHeaders(["foo"]);
    // mount again to ensure that active optional columns will not be reset while empty
    await getService("action").doAction(1);
    expect.verifySteps([["getItem", localStorageKey]]);
    verifyHeaders(["foo"]);
});

test(`quickcreate in a many2one in a list`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="m2o"/></list>`,
    });
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_data_row .o_data_cell input`).edit("aaa", { confirm: false });
    await runAllTimers();
    await press("tab");
    await animationFrame();
    expect(`.o_data_cell:eq(0)`).toHaveText("aaa");
});

test(`float field render with digits attribute on listview`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="qux" digits="[12,6]"/></list>`,
    });
    expect(`td.o_list_number:eq(0)`).toHaveText("0.400000", {
        message: "should contain 6 digits decimal precision",
    });
});

test(`enter edition in editable list with multi_edit = 0`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" multi_edit="0"><field name="int_field"/></list>`,
    });

    // click on int_field cell of first row
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_selected_row .o_field_widget[name=int_field] input`).toBeFocused();
});

test(`enter edition in editable list with multi_edit = 1`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" multi_edit="1">
                <field name="int_field"/>
            </list>
        `,
    });

    // click on int_field cell of first row
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_selected_row .o_field_widget[name=int_field] input:eq(0)`).toBeFocused();
});

test.todo(`continue creating new lines in editable=top on keyboard nav`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="int_field"/></list>`,
    });

    const initialRowCount = queryAll(`.o_data_cell[name=int_field]`).length;

    // click on int_field cell of first row
    await contains(`.o_list_button_add`).click();
    await contains(`.o_data_cell[name=int_field] input`).edit("1", { confirm: "tab" });
    await contains(`.o_data_cell[name=int_field] input`).edit("2", { confirm: "enter" });

    // 3 new rows: the two created ("1" and "2", and a new still in edit mode)
    expect(`.o_data_cell[name=int_field]`).toHaveCount(initialRowCount + 3);
});

test(`Date in evaluation context works with date field`, async () => {
    mockDate("1997-01-09 12:00:00");

    Foo._fields.birthday = fields.Date();
    Foo._records[0].birthday = "1997-01-08";
    Foo._records[1].birthday = "1997-01-09";
    Foo._records[2].birthday = "1997-01-10";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="birthday" decoration-danger="birthday > today"/>
            </list>
        `,
    });
    expect(`.o_data_row .text-danger`).toHaveCount(1);
});

test(`Datetime in evaluation context works with datetime field`, async () => {
    mockDate("1997-01-09 12:00:00");

    /**
     * Returns "1997-01-DD HH:MM:00" with D, H and M holding current UTC values
     * from patched date + (deltaMinutes) minutes.
     * This is done to allow testing from any timezone since UTC values are
     * calculated with the offset of the current browser.
     */
    function dateStringDelta(deltaMinutes) {
        return luxon.DateTime.now().plus({ minutes: deltaMinutes }).toSQL({ includeZone: false });
    }

    // "datetime" field may collide with "datetime" object in context
    Foo._fields.birthday = fields.Datetime();
    Foo._records[0].birthday = dateStringDelta(-120);
    Foo._records[1].birthday = dateStringDelta(0);
    Foo._records[2].birthday = dateStringDelta(+120);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="birthday" decoration-danger="birthday > now"/>
            </list>
        `,
    });
    expect(`.o_data_row .text-danger`).toHaveCount(1);
});

test(`Auto save: add a record and leave action`, async () => {
    defineActions([
        {
            id: 1,
            name: "Action 1",
            res_model: "foo",
            views: [[2, "list"]],
            search_view_id: [1, "search"],
        },
        {
            id: 2,
            name: "Action 2",
            res_model: "foo",
            views: [[3, "list"]],
            search_view_id: [1, "search"],
        },
    ]);
    Foo._views = {
        "search,1": `<search/>`,
        "list,2": `<list editable="top"><field name="foo"/></list>`,
        "list,3": `<list editable="top"><field name="foo"/></list>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap", "blip"]);
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_list_button_add`).click();
    await contains(`.o_data_cell [name=foo] input`).edit("test");
    // change action and come back
    await getService("action").doAction(2);
    await getService("action").doAction(1, { clearBreadcrumbs: true });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap", "blip", "test"]);
    expect(`.o_data_row`).toHaveCount(5);
});

test(`Auto save: create a new record without modifying it and leave action`, async () => {
    Foo._fields.foo = fields.Char({ required: true });

    defineActions([
        {
            id: 1,
            name: "Action 1",
            res_model: "foo",
            views: [[2, "list"]],
            search_view_id: [1, "search"],
        },
        {
            id: 2,
            name: "Action 2",
            res_model: "foo",
            views: [[3, "list"]],
            search_view_id: [1, "search"],
        },
    ]);
    Foo._views = {
        "search,1": `<search/>`,
        "list,2": `<list editable="top"><field name="foo"/></list>`,
        "list,3": `<list editable="top"><field name="foo"/></list>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap", "blip"]);
    expect(`.o_data_row`).toHaveCount(4);

    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row`).toHaveCount(5);

    // change action and come back
    await getService("action").doAction(2);
    await getService("action").doAction(1, { clearBreadcrumbs: true });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap", "blip"]);
    expect(`.o_data_row`).toHaveCount(4);
});

test(`Auto save: modify a record and leave action`, async () => {
    defineActions([
        {
            id: 1,
            name: "Action 1",
            res_model: "foo",
            views: [[2, "list"]],
            search_view_id: [1, "search"],
        },
        {
            id: 2,
            name: "Action 2",
            res_model: "foo",
            views: [[3, "list"]],
            search_view_id: [1, "search"],
        },
    ]);
    Foo._views = {
        "search,1": `<search/>`,
        "list,2": `<list editable="top"><field name="foo"/></list>`,
        "list,3": `<list editable="top"><field name="foo"/></list>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap", "blip"]);

    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell [name=foo] input`).edit("test");
    // change action and come back
    await getService("action").doAction(2);
    await getService("action").doAction(1, { clearBreadcrumbs: true });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["test", "blip", "gnap", "blip"]);
});

test(`Auto save: modify a record and leave action (reject)`, async () => {
    defineActions([
        {
            id: 1,
            name: "Action 1",
            res_model: "foo",
            views: [[2, "list"]],
            search_view_id: [1, "search"],
        },
        {
            id: 2,
            name: "Action 2",
            res_model: "foo",
            views: [[3, "list"]],
            search_view_id: [1, "search"],
        },
    ]);
    Foo._views = {
        "search,1": `<search/>`,
        "list,2": `<list editable="top"><field name="foo" required="1"/></list>`,
        "list,3": `<list editable="top"><field name="foo"/></list>`,
    };

    mockService("notification", {
        add(message, options) {
            expect.step(options.title.toString());
            expect.step(message.toString());
        },
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap", "blip"]);

    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell [name=foo] input`).edit("", { confirm: false });
    getService("action").doAction(2);
    await animationFrame();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["", "blip", "gnap", "blip"]);
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_field_invalid");
    expect(`.o_data_row`).toHaveCount(4);
    expect.verifySteps(["Invalid fields: ", "<ul><li>Foo</li></ul>"]);
});

test(`Auto save: add a record and change page`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" limit="3">
                <field name="foo"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap"]);

    await contains(`.o_list_button_add`).click();
    await contains(`.o_data_cell [name=foo] input`).edit("test", { confirm: false });
    await pagerNext();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["blip", "test"]);

    await pagerPrevious();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap"]);
});

test(`Auto save: modify a record and change page`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" limit="3">
                <field name="foo"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap"]);

    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell input`).edit("test");
    await pagerNext();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["blip"]);

    await pagerPrevious();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["test", "blip", "gnap"]);
});

test(`Auto save: modify a record and change page (reject)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top" limit="3">
                <field name="foo" required="1"/>
            </list>
        `,
    });
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["yop", "blip", "gnap"]);

    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell input`).edit("", { confirm: false });
    await pagerNext();
    expect(`.o_selected_row .o_field_widget[name=foo]`).toHaveClass("o_field_invalid");
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["", "blip", "gnap"]);
});

test(`Auto save: save on closing tab/browser`, async () => {
    onRpc("foo", "web_save", ({ args }) => {
        expect.step("save"); // should be called
        expect(args).toEqual([[1], { foo: "test" }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell [name=foo] input`).edit("test");

    const [event] = await unload();
    await animationFrame();
    expect(event.defaultPrevented).toBe(false);
    expect.verifySteps(["save"]);
});

test(`Auto save: save on closing tab/browser (pending changes)`, async () => {
    onRpc("foo", "web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { foo: "test" }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell [name=foo] input`).edit("test", { confirm: false });

    await unload();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test(`Auto save: save on closing tab/browser (invalid field)`, async () => {
    onRpc("foo", "web_save", () => {
        expect.step("save"); // should not be called
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo" required="1"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell [name=foo] input`).edit("");

    const [event] = await unload();
    await animationFrame();
    // should not save because of invalid field
    expect.verifySteps([]);
    expect(event.defaultPrevented).toBe(true);
});

test(`Auto save: save on closing tab/browser (onchanges + pending changes)`, async () => {
    Foo._onChanges = {
        int_field(record) {
            record.foo = `${record.int_field}`;
        },
    };

    const deferred = new Deferred();
    onRpc("foo", "onchange", () => deferred);
    onRpc("foo", "web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { int_field: 2021 }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell [name="int_field"] input`).edit("2021", { confirm: "blur" });

    await unload();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test(`Auto save: save on closing tab/browser (onchanges)`, async () => {
    Foo._onChanges = {
        int_field(record) {
            record.foo = `${record.int_field}`;
        },
    };

    const deferred = new Deferred();
    onRpc("foo", "onchange", () => deferred);
    onRpc("foo", "web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { foo: "test", int_field: 2021 }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell [name="int_field"] input`).edit("2021", { confirm: false });
    await contains(`.o_data_cell [name="foo"] input`).edit("test", { confirm: "blur" });

    await unload();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test(`edition, then navigation with tab (with a readonly re-evaluated field and onchange)`, async () => {
    // This test makes sure that if we have a cell in a row that will become
    // read-only after editing another cell, in case the keyboard navigation
    // move over it before it becomes read-only and there are unsaved changes
    // (which will trigger an onchange), the focus of the next activable
    // field will not crash
    Bar._onChanges = {
        o2m() {},
    };
    Bar._fields.o2m = fields.One2many({ relation: "foo" });
    Bar._records[0].o2m = [1, 4];

    onRpc("onchange", ({ model }) => {
        expect.step(`onchange:${model}`);
    });

    await mountView({
        resModel: "bar",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="display_name"/>
                    <field name="o2m">
                        <list editable="bottom">
                            <field name="foo"/>
                            <field name="date" readonly="foo != 'yop'"/>
                            <field name="int_field"/>
                        </list>
                    </field>
                </group>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_data_cell`).click();
    expect(`.o_data_cell[name=foo] input`).toBeFocused();

    await contains(`.o_data_cell[name=foo] input`).edit("new value", { confirm: "tab" });
    expect(`.o_data_cell[name=date] input`).toHaveCount(0);
    expect.verifySteps(["onchange:bar"]);
});

test(`selecting a row after another one containing a table within an html field should be the correct one`, async () => {
    Foo._fields.html = fields.Html();
    Foo._records[0].html = `
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
        </table>
    `;

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" multi_edit="1"><field name="html"/></list>`,
    });
    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_list_table > tbody > tr:eq(1)`).toHaveClass("o_selected_row");
});

test(`archive/unarchive not available on active readonly models`, async () => {
    Foo._fields.active = fields.Boolean({ default: true, readonly: true });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="3"><field name="display_name"/></list>`,
        actionMenus: {},
    });
    await contains(`tbody .o_data_row td.o_list_record_selector input`).click();
    expect(`.o_cp_action_menus`).toHaveCount(1, { message: "sidebar should be available" });

    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click();
    expect(`a:contains(Archive)`).toHaveCount(0, {
        message: "Archive action should not be available",
    });
});

test(`open groups are kept when leaving and coming back`, async () => {
    Foo._views = {
        list: `<list><field name="foo"/></list>`,
        search: `<search/>`,
        form: `<form/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
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
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_group_open`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(0);

    // unfold the second group
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_group_open`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(3);

    // open a record and go back
    await contains(`.o_data_cell`).click();
    expect(`.o_form_view`).toHaveCount(1);

    await contains(`.breadcrumb-item a`).click();
    expect(`.o_group_open`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(3);
});

test(`open groups are kept when leaving and coming back (grouped by date)`, async () => {
    Foo._fields.date = fields.Date({ default: "2022-10-10" });
    Foo._views = {
        list: `<list><field name="foo"/></list>`,
        search: `<search/>`,
        form: `<form/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
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
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_group_open`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(0);

    // unfold the second group
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_group_open`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(3);

    // open a record and go back
    await contains(`.o_data_cell`).click();
    expect(`.o_form_view`).toHaveCount(1);

    await contains(`.breadcrumb-item a`).click();
    expect(`.o_group_open`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(3);
});

test(`go to the next page after leaving and coming back to a grouped list view`, async () => {
    Foo._views = {
        list: `<list groups_limit="1"><field name="foo"/></list>`,
        form: `<form/>`,
        search: `<search/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
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
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_group_header`).toHaveCount(1);
    expect(`.o_group_header`).toHaveText("No (1)");

    // unfold the second group
    await contains(`.o_group_header`).click();
    expect(`.o_group_open`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(1);

    // open a record and go back
    await contains(`.o_data_cell`).click();
    expect(`.o_form_view`).toHaveCount(1);

    await contains(`.breadcrumb-item a`).click();
    expect(`.o_group_header`).toHaveCount(1);
    expect(`.o_group_header`).toHaveText("No (1)");

    await pagerNext();
    expect(`.o_group_header`).toHaveCount(1);
    expect(`.o_group_header`).toHaveText("Yes (3)");
});

test(`keep order after grouping`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        searchViewArch: `
            <search>
                <filter name="group_by_foo" string="Foo" context="{'group_by':'foo'}"/>
            </search>
        `,
    });
    expect(queryAllTexts`.o_data_row td[name=foo]`).toEqual(["yop", "blip", "gnap", "blip"]);

    // Descending order on Bar
    await contains(`th.o_column_sortable[data-name=foo]`).click();
    await contains(`th.o_column_sortable[data-name=foo]`).click();
    expect(queryAllTexts`.o_data_row td[name=foo]`).toEqual(["yop", "gnap", "blip", "blip"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");
    expect(queryAllTexts`.o_group_name`).toEqual(["yop (1)", "gnap (1)", "blip (2)"]);

    await toggleMenuItem("Foo");
    expect(queryAllTexts`.o_data_row td[name=foo]`).toEqual(["yop", "gnap", "blip", "blip"]);
});

test(`editable list header click should unselect record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_data_cell input`).edit("someInput", { confirm: false });
    await contains(`thead th:eq(1)`).click();
    await press("down");
    await animationFrame();
    expect(`.o_selected_row`).toHaveCount(0);
});

test(`editable list group header click should unselect record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header`).click();
    await contains(`.o_group_header:not(.o_group_open)`).click();
    await contains(`.o_data_cell`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_data_cell input`).edit("someInput", { confirm: false });
    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_selected_row`).toHaveCount(0);
});

test(`fieldDependencies support for fields`, async () => {
    Foo._records = [{ id: 1, int_field: 2 }];

    registry.category("fields").add("custom_field", {
        component: class CustomField extends Component {
            static template = xml`<span t-esc="props.record.data.int_field"/>`;
            static props = ["*"];
        },
        fieldDependencies: [{ name: "int_field", type: "integer" }],
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo" widget="custom_field"/></list>`,
    });
    expect(`[name=foo] span:eq(0)`).toHaveText("2");
});

test(`fieldDependencies support for fields: dependence on a relational field`, async () => {
    registry.category("fields").add("custom_field", {
        component: class CustomField extends Component {
            static template = xml`<span t-esc="props.record.data.m2o[0]"/>`;
            static props = ["*"];
        },
        fieldDependencies: [{ name: "m2o", type: "many2one", relation: "bar" }],
    });

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo" widget="custom_field"/></list>`,
    });
    expect(`[name=foo] span:eq(0)`).toHaveText("1");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test(`editable list correctly saves dirty fields `, async () => {
    Foo._records = [Foo._records[0]];

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { foo: "test" }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_data_cell input`).edit("test", { confirm: "tab" });
    expect.verifySteps(["web_save"]);
});

test(`edit a field with a slow onchange in a new row`, async () => {
    Foo._onChanges = {
        int_field() {},
    };
    Foo._records = [];

    let deferred;
    onRpc("onchange", () => deferred);
    stepAllNetworkCalls();

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="int_field"/></list>`,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    // add a new line
    await contains(`.o_list_button_add`).click();
    expect.verifySteps(["onchange"]);

    // we want to add a delay to simulate an onchange
    deferred = new Deferred();

    // write something in the field
    await contains(`[name=int_field] input`).edit("14", { confirm: false });
    expect(`[name=int_field] input`).toHaveValue("14");

    await contains(`.o_list_view`).click();
    // check that nothing changed before the onchange finished
    expect(`[name=int_field] input`).toHaveValue("14");
    expect.verifySteps(["onchange"]);

    // unlock onchange
    deferred.resolve();
    await animationFrame();

    // check the current line is added with the correct content
    expect(`.o_data_row [name=int_field]:eq(0)`).toHaveText("14");
    expect.verifySteps(["web_save"]);
});

test(`create a record with the correct context`, async () => {
    Foo._fields.text = fields.Text({ required: true });
    Foo._records = [];

    onRpc("web_save", ({ kwargs }) => {
        expect.step("web_save");
        const { context } = kwargs;
        expect(context.default_text).toBe("yop");
        expect(context.test).toBe(true);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="text"/>
            </list>
        `,
        context: {
            default_text: "yop",
            test: true,
        },
    });
    await contains(`.o_list_button_add`).click();
    await contains(`[name='foo'] input`).edit("blop", { confirm: false });
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_list_view`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    expect(queryAllTexts`.o_data_row:eq(-1) .o_data_cell`).toEqual(["blop", "yop"]);
    expect.verifySteps(["web_save"]);
});

test(`create a record with the correct context in a group`, async () => {
    Foo._fields.text = fields.Text({ required: true });

    onRpc("web_save", ({ kwargs }) => {
        expect.step("web_save");
        const { context } = kwargs;
        expect(context.default_bar).toBe(true);
        expect(context.default_text).toBe("yop");
        expect(context.test).toBe(true);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="text"/>
            </list>
        `,
        groupBy: ["bar"],
        context: {
            default_text: "yop",
            test: true,
        },
    });
    await contains(`.o_group_name:eq(1)`).click();
    await contains(`.o_group_field_row_add a`).click();
    await contains(`[name='foo'] input`).edit("blop", { confirm: false });
    expect(`.o_selected_row`).toHaveCount(1);

    await contains(`.o_list_view`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    expect(queryAllTexts`.o_data_row:eq(-1) .o_data_cell`).toEqual(["blop", "yop"]);
    expect.verifySteps(["web_save"]);
});

test(`classNames given to a field are set on the right field directly`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field class="d-flex align-items-center" name="int_field" widget="progressbar" options="{'editable': true}"/>
                <field class="d-none" name="bar"/>
            </list>
        `,
    });
    expect(`.o_field_cell:eq(2)`).not.toHaveClass("d-flex align-items-center", {
        message: "classnames are not set on the first cell",
    });
    expect(`.o_field_progressbar`).toHaveClass("d-flex align-items-center", {
        message: "classnames are set on the corresponding field div directly",
    });
    expect(`.o_field_cell:eq(3)`).toHaveClass("d-none", {
        message: "classnames are set on the second cell",
    });
});

test(`use a filter_domain in a list view`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="m2o"/></list>`,
        searchViewArch: `
            <search>
                <field name="m2o" filter_domain="[('m2o', 'child_of', raw_value)]"/>
            </search>
        `,
        context: {
            search_default_m2o: 1,
        },
    });
    expect(`.o_data_row`).toHaveCount(3);
});

test(`Formatted group operator`, async () => {
    Foo._records[0].qux = 0.4;
    Foo._records[1].qux = 0.2;
    Foo._records[2].qux = 0.01;
    Foo._records[3].qux = 0.48;
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="qux" widget="percentage"/></list>`,
        groupBy: ["bar"],
    });
    expect(`td.o_list_number:eq(0)`).toHaveText("48%");
    expect(`td.o_list_number:eq(1)`).toHaveText("61%");
});

test(`Formatted group operator with digit precision on the field definition`, async () => {
    Foo._fields.qux = fields.Float({ digits: [16, 3] });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="qux"/></list>`,
        groupBy: ["bar"],
    });
    expect(`td.o_list_number:eq(0)`).toHaveText("9.000");
    expect(`td.o_list_number:eq(1)`).toHaveText("10.400");
});

test(`list view does not crash when clicked button cell`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><button name="a" type="object" icon="fa-car"/></list>`,
    });
    expect(`.o_data_row:eq(0) td.o_list_button`).toHaveCount(1);
    await contains(`.o_data_row:eq(0) td.o_list_button`).click();
});

test(`group by going to next page then back to first`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list groups_limit="1"><field name="foo"/><field name="bar"/></list>`,
        groupBy: ["bar"],
    });
    expect([...getPagerValue(), getPagerLimit()]).toEqual([1, 2]);

    await pagerNext();
    expect([...getPagerValue(), getPagerLimit()]).toEqual([2, 2]);

    await pagerPrevious();
    expect([...getPagerValue(), getPagerLimit()]).toEqual([1, 2]);
});

test(`sort on a non sortable field with allow_order option`, async () => {
    Foo._records = [{ bar: true }, { bar: false }, { bar: true }];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="bar" options="{ 'allow_order': true }"/></list>`,
    });
    expect(queryAllProperties(`[name=bar] input`, "checked")).toEqual([true, false, true]);
    expect(`th[data-name=bar]`).toHaveClass("o_column_sortable");
    expect(`th[data-name=bar]`).not.toHaveClass("table-active");

    await contains(`th[data-name=bar]`).click();
    expect(queryAllProperties(`[name=bar] input`, "checked")).toEqual([false, true, true]);
    expect(`th[data-name=bar]`).toHaveClass("o_column_sortable");
    expect(`th[data-name=bar]`).toHaveClass("table-active");
    expect(`th[data-name=bar] i`).toHaveClass("fa-angle-up");
});

test(`sort rows in a grouped list view`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="int_field"/></list>`,
        groupBy: ["bar"],
    });
    await contains(`.o_group_header:eq(1)`).click();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["10", "9", "17"]);
    expect(`th[data-name=int_field]`).toHaveClass("o_column_sortable");

    await contains(`th[data-name=int_field]`).click();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["9", "10", "17"]);
    expect(`th[data-name=int_field]`).toHaveClass("o_column_sortable");
    expect(`th[data-name=int_field] i`).toHaveClass("fa-angle-up");
});

test(`have some records, then go to next page in pager then group by some field: at least one group should be visible`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
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
    expect(`tbody .o_data_row`).toHaveCount(2);
    expect(queryAllTexts(`tbody .o_data_row`)).toEqual(["yop", "blip"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");
    expect(`tbody .o_group_header`).toHaveCount(2);
    expect(queryAllTexts(`tbody .o_group_header`)).toEqual(["No (1)", "Yes (3)"]);

    await removeFacet("Bar");
    expect(`tbody .o_data_row`).toHaveCount(2);
    expect(queryAllTexts(`tbody .o_data_row`)).toEqual(["yop", "blip"]);

    await pagerNext();
    expect(`tbody .o_data_row`).toHaveCount(2);
    expect(queryAllTexts(`tbody .o_data_row`)).toEqual(["gnap", "blip"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");
    expect(`tbody .o_group_header`).toHaveCount(2);
    expect(queryAllTexts(`tbody .o_group_header`)).toEqual(["No (1)", "Yes (3)"]);
});

test(`optional field selection do not unselect current row`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="text" optional="hide"/>
                <field name="foo" optional="show"/>
                <field name="bar" optional="hide"/>
            </list>
        `,
    });
    await contains(`.o_list_button_add`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`div[name=foo] input`).toBeFocused();

    await contains(`table .o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    // input loses focus when we open dropdown but gets it back when an item is toggled.
    expect(`div[name=foo] input`).not.toBeFocused();

    await contains(`.o-dropdown--menu span.dropdown-item:eq(2) label`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`div[name=foo] input`).toBeFocused();
    expect(`.o_selected_row div[name=bar]`).toHaveCount(1);

    await contains(`.o-dropdown--menu span.dropdown-item:eq(0) label`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    // This below would be better if it still focused foo, but it is an acceptable tradeoff.
    expect(`div[name=text] textarea`).toBeFocused();
    expect(`.o_selected_row div[name=text]`).toHaveCount(1);
});

test(`view widgets are rendered in list view`, async () => {
    class TestWidget extends Component {
        static template = xml`<div class="test_widget" t-esc="props.record.data.bar"/>`;
        static props = ["*"];
    }
    registry.category("view_widgets").add("test_widget", { component: TestWidget });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="bar" column_invisible="1"/>
                <widget name="test_widget"/>
            </list>
        `,
    });
    expect(`td .test_widget`).toHaveCount(4, {
        message: "there should be one widget (inside td) per record",
    });
    expect(queryAllTexts`.test_widget`).toEqual(["true", "true", "true", "false"]);
});

test(`edit a record then select another record with a throw error when saving`, async () => {
    expect.errors(1);

    onRpc("web_save", () => {
        throw makeServerError({ message: "Can't write" });
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="foo"/></list>`,
    });
    await contains(`.o_data_cell:eq(1)`).click();
    await contains(`[name=foo] input`).edit("plop", { confirm: false });
    expect(`[name=foo] input`).toHaveCount(1);

    await contains(`.o_data_cell:eq(0)`).click();
    await animationFrame();
    expect(`.o_error_dialog`).toHaveCount(1);

    await contains(`.o_error_dialog .btn-primary.o-default-button`).click();
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
});

test(`no highlight of a (sortable) column without label`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list default_order="foo">
                <field name="foo" nolabel="1"/>
                <field name="bar"/>
            </list>
        `,
    });
    expect(`thead th[data-name=foo]`).toHaveCount(1);
    expect(`thead th[data-name=foo]`).not.toHaveClass("table-active");
});

test(`highlight of a (sortable) column with label`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list default_order="foo">
                <field name="foo"/>
            </list>
        `,
    });
    expect(`thead th[data-name=foo]`).toHaveCount(1);
    expect(`thead th[data-name=foo]`).toHaveClass("table-active");
});

test(`Search more in a many2one`, async () => {
    Bar._views = {
        list: `<list><field name="display_name"/></list>`,
        search: `<search/>`,
    };

    patchWithCleanup(Many2XAutocomplete.defaultProps, {
        searchLimit: 1,
    });

    onRpc("web_read", ({ args }) => expect.step(`web_read ${args[0]}`));
    onRpc("web_save", ({ args }) => expect.step(`web_save ${args[0]}`));

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom"><field name="m2o"/></list>`,
    });
    expect(queryAllTexts`.o_data_row td[name=m2o]`).toEqual([
        "Value 1",
        "Value 2",
        "Value 1",
        "Value 1",
    ]);

    await contains(`.o_data_row:eq(0) td.o_list_many2one`).click();
    await selectFieldDropdownItem("m2o", "Search More...");
    expect.verifySteps([]);

    await contains(`.modal .o_data_row:eq(2) td[name=display_name]`).click();
    expect.verifySteps(["web_read 3"]);

    await contains(`.o_list_button_save`).click();
    expect(queryAllTexts`.o_data_row td[name=m2o]`).toEqual([
        "Value 3",
        "Value 2",
        "Value 1",
        "Value 1",
    ]);
    expect.verifySteps(["web_save 1"]);
});

test(`view's context is passed down as evalContext`, async () => {
    onRpc("name_search", ({ kwargs }) => {
        expect.step(`name_search`);
        expect(kwargs.args).toEqual([["someField", "=", "some_value"]]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o" domain="[['someField', '=', context.get('default_global_key', 'nope')]]"/>
            </list>
        `,
        context: {
            default_global_key: "some_value",
        },
    });
    await contains(`.o_data_row:eq(0) td.o_list_many2one`).click();
    await contains(`.o_field_many2one_selection .o-autocomplete--input`).click();
    expect.verifySteps(["name_search"]);
});

test(`list view with default_group_by`, async () => {
    let readGroupCount = 0;
    onRpc("web_read_group", ({ kwargs }) => {
        readGroupCount++;
        expect.step(`web_read_group${readGroupCount}`);
        switch (readGroupCount) {
            case 1:
                return expect(kwargs.groupby).toEqual(["bar"]);
            case 2:
                return expect(kwargs.groupby).toEqual(["m2m"]);
            case 3:
                return expect(kwargs.groupby).toEqual(["bar"]);
        }
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list default_group_by="bar">
                <field name="bar"/>
            </list>
        `,
    });
    expect(`.o_list_renderer table`).toHaveClass("o_list_table_grouped");
    expect(`.o_group_header`).toHaveCount(2);
    expect.verifySteps(["web_read_group1"]);

    await selectGroup("m2m");
    expect(`.o_group_header`).toHaveCount(4);
    expect.verifySteps(["web_read_group2"]);

    await toggleMenuItem("M2m");
    expect(`.o_group_header`).toHaveCount(2);
    expect.verifySteps(["web_read_group3"]);
});

test(`ungrouped list, apply filter, decrease limit`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="4"><field name="foo"/></list>`,
        searchViewArch: `
            <search>
                <filter name="my_filter" string="My Filter" domain="[('id', '>', 1)]"/>
            </search>
        `,
    });
    expect(`.o_data_row`).toHaveCount(4);

    // apply the filter to trigger a reload of datapoints
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");
    expect(`.o_data_row`).toHaveCount(3);

    // edit the pager with a smaller limit
    await contains(`.o_pager_value`).click();
    await contains(`.o_pager_value`).edit("1-2");
    expect(`.o_data_row`).toHaveCount(2);
});

test(`Properties: char`, async () => {
    const definition = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: "CHAR" };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: "TEST" }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_char']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_char']`).toHaveText("Property char");
    expect(`.o_field_cell.o_char_cell`).toHaveCount(3);
    expect(`.o_field_cell.o_char_cell`).toHaveText("CHAR");

    await contains(`.o_field_cell.o_char_cell`).click();
    await contains(`.o_field_cell.o_char_cell input`).edit("TEST", { confirm: false });
    expect(`.o_field_cell.o_char_cell input`).toHaveValue("TEST");

    await contains(`[name='m2o']`).click();
    expect(`.o_field_cell.o_char_cell input`).toHaveValue("TEST");

    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_char_cell:eq(0)`).toHaveText("TEST");
    expect.verifySteps(["web_save"]);
});

test(`Properties: boolean`, async () => {
    const definition = {
        type: "boolean",
        name: "property_boolean",
        string: "Property boolean",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: true };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: false }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_boolean']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_boolean']`).toHaveText(
        "Property boolean"
    );
    expect(`.o_field_cell.o_boolean_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_boolean_cell`).click();
    await contains(`.o_field_cell.o_boolean_cell input`).click();
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_boolean_cell input`).not.toBeChecked();
    expect.verifySteps(["web_save"]);
});

test(`Properties: integer`, async () => {
    const definition = {
        type: "integer",
        name: "property_integer",
        string: "Property integer",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: 123 };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: 321 }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_integer']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_integer']`).toHaveText(
        "Property integer"
    );
    expect(`.o_field_cell.o_integer_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_integer_cell`).click();
    await contains(`.o_field_cell.o_integer_cell input`).edit(321, { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_integer_cell:eq(0)`).toHaveText("321");
    expect(`.o_list_footer .o_list_number`).toHaveText("567", {
        message:
            "First property is 321, second is zero because it has a different parent and the 2 others are 123 so the total should be 321 + 123 * 2 = 567",
    });
    expect.verifySteps(["web_save"]);
});

test(`Properties: float`, async () => {
    const definition = {
        type: "float",
        name: "property_float",
        string: "Property float",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: record.id === 4 ? false : 123.45 };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: 3.21 }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_float']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_float']`).toHaveText(
        "Property float"
    );
    expect(`.o_field_cell.o_float_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_float_cell`).click();
    await contains(`.o_field_cell.o_float_cell input`).edit(3.21, { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_float_cell:eq(0)`).toHaveText("3.21");
    expect(`.o_list_footer .o_list_number`).toHaveText("126.66", {
        message:
            "First property is 3.21, second is zero because it has a different parent the other is 123.45 and the last one zero because it is false so the total should be 3.21 + 123.45 = 126.66",
    });
    expect.verifySteps(["web_save"]);
});

test(`Properties: date`, async () => {
    const definition = {
        type: "date",
        name: "property_date",
        string: "Property date",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: "2022-12-12" };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: "2022-12-19" }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_date']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_date']`).toHaveText("Property date");
    expect(`.o_field_cell.o_date_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_date_cell`).click();
    await contains(`.o_field_date input`).click();
    await contains(getPickerCell("19")).click();
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_date_cell:eq(0)`).toHaveText("12/19/2022");
    expect.verifySteps(["web_save"]);
});

test(`Properties: datetime`, async () => {
    mockTimeZone(0);

    const definition = {
        type: "datetime",
        name: "property_datetime",
        string: "Property datetime",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: "2022-12-12 12:12:00" };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([
            [1],
            { properties: [{ ...definition, value: "2022-12-19 12:12:00" }] },
        ]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_datetime']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_datetime']`).toHaveText(
        "Property datetime"
    );
    expect(`.o_field_cell.o_datetime_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_datetime_cell`).click();
    await contains(`.o_field_datetime input`).click();
    await contains(getPickerCell("19")).click();
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_datetime_cell:eq(0)`).toHaveText("12/19/2022 12:12:00");
    expect.verifySteps(["web_save"]);
});

test(`Properties: selection`, async () => {
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
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: "b" };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: "a" }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_selection']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_selection']`).toHaveText(
        "Property selection"
    );
    expect(`.o_field_cell.o_selection_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_selection_cell`).click();
    await contains(`.o_field_cell.o_selection_cell select`).select(`"a"`);
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_selection_cell:eq(0)`).toHaveText("A");
    expect.verifySteps(["web_save"]);
});

test(`Properties: tags`, async () => {
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
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: ["a", "c"] };
        }
    }

    let expectedValue = null;
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: expectedValue }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_tags']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_tags']`).toHaveText("Property tags");
    expect(`.o_field_cell.o_property_tags_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_property_tags_cell`).click();
    await contains(`.o_field_cell.o_property_tags_cell .o_delete`).click();
    expectedValue = ["c"];
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_property_tags_cell:eq(0)`).toHaveText("C");
    expect.verifySteps(["web_save"]);

    await contains(`.o_field_cell.o_property_tags_cell`).click();
    await selectFieldDropdownItem(`properties.property_tags`, "B");
    expectedValue = ["c", "b"];
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_property_tags_cell:eq(0)`).toHaveText("B\nC");
    expect.verifySteps(["web_save"]);
});

test(`Properties: many2one`, async () => {
    const definition = {
        type: "many2one",
        name: "property_many2one",
        string: "Property many2one",
        comodel: "res.currency",
        domain: "[]",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: [1, "USD"] };
        }
    }

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args).toEqual([[1], { properties: [{ ...definition, value: [2, "EUR"] }] }]);
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_many2one']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_many2one']`).toHaveText(
        "Property many2one"
    );
    expect(`.o_field_cell.o_many2one_cell`).toHaveCount(3);

    await contains(`.o_field_cell.o_many2one_cell`).click();
    await selectFieldDropdownItem(`properties.property_many2one`, "EUR");
    await contains(`.o_list_button_save`).click();
    expect(`.o_field_cell.o_many2one_cell:eq(0)`).toHaveText("EUR");
    expect.verifySteps(["web_save"]);
});

test(`Properties: many2many`, async () => {
    const definition = {
        type: "many2many",
        name: "property_many2many",
        string: "Property many2many",
        comodel: "res.currency",
        domain: "[]",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: [[1, "USD"]] };
        }
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type='checkbox']`).click();
    expect(`.o_list_renderer th[data-name='properties.property_many2many']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_many2many']`).toHaveText(
        "Property many2many"
    );
    expect(`.o_field_cell.o_many2many_tags_cell`).toHaveCount(3);
});

test(`multiple sources of properties definitions`, async () => {
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
    Bar._records[0].definitions = [definition0];
    Bar._records[1].definitions = [definition1];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition0.name]: "0" };
        } else if (record.m2o === 2) {
            record.properties = { [definition1.name]: true };
        }
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown--menu input[type=checkbox]:eq(0)`).click();
    await contains(`.o-dropdown--menu input[type=checkbox]:eq(1)`).click();
    expect(`.o_list_renderer th[data-name='properties.property_char']`).toHaveCount(1);
    expect(`.o_field_cell.o_char_cell`).toHaveCount(3);
    expect(`.o_list_renderer th[data-name='properties.property_boolean']`).toHaveCount(1);
    expect(`.o_field_cell.o_boolean_cell`).toHaveCount(1);
});

test(`toggle properties`, async () => {
    const definition0 = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    const definition1 = {
        type: "separator",
        name: "property_separator",
        string: "Group 1",
    };
    const definition2 = {
        type: "boolean",
        name: "property_boolean",
        string: "Property boolean",
    };
    Bar._records[0].definitions = [definition0];
    Bar._records[1].definitions = [definition1, definition2];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition0.name]: "0" };
        } else if (record.m2o === 2) {
            record.properties = {
                [definition1.name]: false,
                [definition2.name]: true,
            };
        }
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(`.o_optional_columns_dropdown_toggle`).click();
    expect(`.o-dropdown--menu input[type='checkbox']`).toHaveCount(2);

    await contains(`.o-dropdown--menu input[type='checkbox']:eq(0)`).click();
    expect(`.o_list_renderer th[data-name='properties.property_char']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_boolean']`).toHaveCount(0);

    await contains(`.o-dropdown--menu input[type='checkbox']:eq(1)`).click();
    expect(`.o_list_renderer th[data-name='properties.property_char']`).toHaveCount(1);
    expect(`.o_list_renderer th[data-name='properties.property_boolean']`).toHaveCount(1);

    await contains(`.o-dropdown--menu input[type='checkbox']:eq(0)`).click();
    expect(`.o_list_renderer th[data-name='properties.property_char']`).toHaveCount(0);
    expect(`.o_list_renderer th[data-name='properties.property_boolean']`).toHaveCount(1);

    await contains(`.o-dropdown--menu input[type='checkbox']:eq(1)`).click();
    expect(`.o_list_renderer th[data-name='properties.property_char']`).toHaveCount(0);
    expect(`.o_list_renderer th[data-name='properties.property_boolean']`).toHaveCount(0);
});

test(`properties: optional show/hide (no config in local storage)`, async () => {
    const definition = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: "0" };
        }
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    expect(`.o_list_table thead th`).toHaveCount(3);
    expect(`.o_list_table thead th.o_list_record_selector`).toHaveCount(1);
    expect(`.o_list_table thead th[data-name=m2o]`).toHaveCount(1);
    expect(`.o_list_table thead th.o_list_actions_header`).toHaveCount(1);
});

test(`properties: optional show/hide (config from local storage)`, async () => {
    const definition = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: "0" };
        }
    }

    localStorage.setItem(
        "optional_fields,foo,list,123456789,m2o,properties",
        "properties.property_char"
    );

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    expect(`.o_list_table thead th`).toHaveCount(4);
    expect(`.o_list_table thead th.o_list_record_selector`).toHaveCount(1);
    expect(`.o_list_table thead th[data-name=m2o]`).toHaveCount(1);
    expect(`.o_list_table thead th[data-name='properties.property_char']`).toHaveCount(1);
    expect(`.o_list_table thead th.o_list_actions_header`).toHaveCount(1);
});

test(`properties: optional show/hide (at reload, config from local storage)`, async () => {
    const definition = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: "0" };
        }
    }

    localStorage.setItem(
        "optional_fields,foo,list,123456789,m2o,properties",
        "properties.property_char"
    );

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
        groupBy: ["m2o"],
    });

    // list is grouped, no record displayed
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(0);
    expect(`.o_list_table thead th`).toHaveCount(2);
    expect(`.o_list_table thead th.o_list_record_selector`).toHaveCount(1);
    expect(`.o_list_table thead th[data-name=m2o]`).toHaveCount(1);

    await contains(`.o_group_header`).click(); // open group Value 1
    expect(`.o_data_row`).toHaveCount(3);
    expect(`.o_list_table thead th`).toHaveCount(4);
    expect(`.o_list_table thead th.o_list_record_selector`).toHaveCount(1);
    expect(`.o_list_table thead th[data-name=m2o]`).toHaveCount(1);
    expect(`.o_list_table thead th[data-name='properties.property_char']`).toHaveCount(1);
    expect(`.o_list_table thead th.o_list_actions_header`).toHaveCount(1);
});

test(`reload properties definitions when domain change`, async () => {
    const definition0 = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition0];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition0.name]: "AA" };
        }
    }

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
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
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await toggleSearchBarMenu();
    await toggleMenuItem("only one");
    expect.verifySteps(["web_search_read"]);
});

test(`do not reload properties definitions when page change`, async () => {
    const definition0 = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition0];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition0.name]: "0" };
        }
    }

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom" limit="2">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);

    await pagerNext();
    expect.verifySteps(["web_search_read"]);
});

test(`load properties definitions only once when grouped`, async () => {
    const definition0 = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition0];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition0.name]: "0" };
        }
    }

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
        groupBy: ["m2o"],
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read_group",
        "has_group",
    ]);

    await contains(`.o_group_header`).click();
    expect.verifySteps(["web_search_read"]);
});

test(`Invisible Properties`, async () => {
    const definition = {
        type: "integer",
        name: "property_integer",
        string: "Property integer",
    };
    Bar._records[0].definitions = [definition];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition.name]: 123 };
        }
    }

    stepAllNetworkCalls();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties" column_invisible="1"/>
            </list>
        `,
    });
    expect(`.o_optional_columns_dropdown_toggle`).toHaveCount(0);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test(`header buttons in list view`, async () => {
    onRpc("/web/dataset/call_button/*", async (request) => {
        const { params } = await request.json();
        expect.step(params.method);
        return true;
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button name="a" type="object" string="Confirm" confirm="Are you sure?"/>
                </header>
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
    });
    await contains(`.o_data_row .o_list_record_selector input`).click();
    await contains(`.o_control_panel_actions button[name="a"]`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal-body`).toHaveText("Are you sure?");

    await contains(`.modal footer button.btn-primary`).click();
    expect.verifySteps(["a"]);
});

test(`restore orderBy from state when using default order`, async () => {
    defineActions([
        {
            id: 1,
            name: "Foo",
            res_model: "foo",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    Foo._views = {
        list: `
            <list default_order="foo">
                <field name="foo"/>
                <field name="amount"/>
            </list>
        `,
        form: `
            <form>
                <field name="amount"/>
                <field name="foo"/>
            </form>
        `,
        search: `<search/>`,
    };

    onRpc("web_search_read", ({ kwargs }) => expect.step(`order:${kwargs.order}`));
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(`th[data-name=amount]`).click(); // order by amount
    await contains(`.o_data_row .o_data_cell`).click(); // switch to the form view
    await contains(`.breadcrumb-item`).click(); // go back to the list view
    expect.verifySteps([
        "order:foo ASC", // initial list view
        "order:amount ASC, foo ASC", // order by amount
        "order:amount ASC, foo ASC", // go back to the list view, it should still be ordered by amount
    ]);
});

test(`x2many onchange, check result`, async () => {
    const deferred = new Deferred();
    Foo._onChanges = {
        m2m() {},
    };

    onRpc("onchange", async () => {
        expect.step("onchange");
        await deferred;
        return { value: { m2o: [3, "Value 3"] } };
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2m" widget="many2many_tags"/>
                <field name="m2o"/>
            </list>
        `,
    });
    expect(`.o_data_cell.o_many2many_tags_cell:eq(0)`).toHaveText("Value 1\nValue 2");
    expect(`.o_data_cell.o_list_many2one:eq(0)`).toHaveText("Value 1");

    await contains(`.o_data_cell.o_many2many_tags_cell:eq(0)`).click();
    await selectFieldDropdownItem("m2m", "Value 3");
    expect.verifySteps(["onchange"]);

    await contains(`.o_list_button_save`).click();
    deferred.resolve();
    await animationFrame();
    expect(`.o_data_cell.o_many2many_tags_cell:eq(0)`).toHaveText("Value 1\nValue 2\nValue 3");
    expect(`.o_data_cell.o_list_many2one:eq(0)`).toHaveText("Value 3", {
        message: "onchange result should be applied",
    });
});

test(`list view: prevent record selection when editable list in edit mode`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top"><field name="foo"/></list>`,
    });

    //  When we try to select new record in edit mode
    await contains(`.o_control_panel_main_buttons .o_list_button_add`).click();
    await contains(`.o_data_row .o_list_record_selector`).click();
    expect(`.o_data_row .o_list_record_selector input[type="checkbox"]`).not.toBeChecked();

    //  When we try to select all records in edit mode
    await contains(`th.o_list_record_selector.o_list_controller`).click();
    expect(`.o_list_controller input[type="checkbox"]`).not.toBeChecked();
});

test(`context keys not passed down the stack and not to fields`, async () => {
    defineActions([
        {
            id: 1,
            name: "Foo",
            res_model: "foo",
            views: [[false, "list"]],
            context: {
                list_view_ref: "foo_view_ref",
                search_default_bar: true,
            },
        },
    ]);

    Foo._views = {
        "list,foo_view_ref": `
            <list default_order="foo" editable="top">
                <field name="m2m" widget="many2many_tags"/>
            </list>
        `,
        search: `<search/>`,
    };
    Bar._views = {
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
    };

    Bar._records = [];
    for (let i = 1; i < 50; i++) {
        Bar._records.push({ id: i, name: `Value ${i}` });
    }

    onRpc(["foo", "bar"], "*", ({ model, method, kwargs }) => {
        expect.step({ model, method, context: kwargs.context });
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect.verifySteps([
        {
            model: "foo",
            method: "get_views",
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                list_view_ref: "foo_view_ref",
            },
        },
        {
            model: "foo",
            method: "web_search_read",
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                bin_size: true,
                list_view_ref: "foo_view_ref",
                current_company_id: 1,
            },
        },
    ]);

    await contains(`.o_data_row .o_data_cell:eq(1)`).click();
    await contains(`.o_selected_row .o_field_many2many_tags input`).click();
    await runAllTimers();
    expect.verifySteps([
        {
            model: "bar",
            method: "name_search",
            context: { lang: "en", tz: "taht", uid: 7, allowed_company_ids: [1] },
        },
    ]);

    await contains(
        `.o_selected_row .o_field_many2many_tags .dropdown-item:contains(Search More...)`
    ).click();
    expect.verifySteps([
        {
            model: "bar",
            method: "get_views",
            context: { lang: "en", tz: "taht", uid: 7, allowed_company_ids: [1] },
        },
        {
            model: "bar",
            method: "web_search_read",
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
                bin_size: true,
                current_company_id: 1,
            },
        },
    ]);
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .modal-header .modal-title`).toHaveText("Search: M2m");
});

test(`search nested many2one field with early option selection`, async () => {
    class Parent extends models.Model {
        foo = fields.One2many({ relation: "foo" });
    }
    defineModels([Parent]);

    const deferred = new Deferred();
    onRpc("name_search", () => deferred);

    await mountView({
        resModel: "parent",
        type: "form",
        arch: `
            <form>
                <field name="foo">
                    <list editable="bottom">
                        <field name="m2o"/>
                    </list>
                </field>
            </form>
        `,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();

    await edit("alu", { confirm: false });
    await runAllTimers();

    await edit("alue", { confirm: false });
    await press("enter");
    await runAllTimers();

    deferred.resolve();
    await animationFrame();
    expect(`.o_field_widget input`).toBeFocused();
    expect(`.o_field_widget input`).toHaveValue("Value 1");
});

test(`monetary field display for rtl languages`, async () => {
    defineParams({ lang_parameters: { direction: "rtl" } });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/><field name="amount"/></list>`,
    });
    expect(`thead th:eq(2) .o_list_number_th`).toHaveCount(1, {
        message: "header cells of monetary fields should have o_list_number_th class",
    });
    expect(`thead th:eq(2)`).toHaveStyle(
        { "text-align": "right" },
        {
            message: "header cells of monetary fields should be right alined",
        }
    );
    expect(`tbody tr:eq(0) td:eq(2)`).toHaveStyle(
        { "text-align": "right" },
        {
            message: "Monetary cells should be right alined",
        }
    );
    expect(`tbody tr:eq(0) td:eq(2)`).toHaveStyle(
        { direction: "ltr" },
        {
            message: "Monetary cells should have ltr direction",
        }
    );
});

test(`add record in editable list view with sample data`, async () => {
    Foo._records = [];

    let deferred = null;
    onRpc("web_search_read", () => deferred);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list sample="1" editable="top"><field name="int_field"/></list>`,
        noContentHelp: "click to add a record",
    });
    expect(`.o_view_sample_data`).toHaveCount(1);
    expect(`.o_view_nocontent`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);

    deferred = new Deferred();
    await contains(`.o_list_button_add`).click();
    expect(`.o_view_sample_data`).toHaveCount(1);
    expect(`.o_view_nocontent`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(10);

    deferred.resolve();
    await animationFrame();
    expect(`.o_view_sample_data`).toHaveCount(0);
    expect(`.o_view_nocontent`).toHaveCount(0);
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_data_row.o_selected_row`).toHaveCount(1);
});

test(`Adding new record in list view with open form view button`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="top" open_form_view="1"><field name="foo"/></list>`,
        selectRecord(resId, options) {
            expect.step(`switch to form - resId: ${resId} activeIds: ${options.activeIds}`);
        },
    });

    await contains(`.o_list_button_add`).click();
    expect(`td.o_list_record_open_form_view`).toHaveCount(5, {
        message: "button to open form view should be present on each row",
    });

    await contains(`.o_field_widget[name=foo] input`).edit("new", { confirm: false });
    await contains(`td.o_list_record_open_form_view`).click();
    expect.verifySteps(["switch to form - resId: 5 activeIds: 5,1,2,3,4"]);
});

test(`onchange should only be called once after pressing enter on a field`, async () => {
    Foo._onChanges.foo = (record) => {
        if (record.foo) {
            record.int_field = 1;
        }
    };

    onRpc("onchange", () => expect.step("onchange"));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="top">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });
    await contains(`.o_data_cell`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("1", { confirm: "enter" });
    // There should only be one onchange call
    expect.verifySteps(["onchange"]);
});

test(`list: remove a record from sorted recordlist`, async () => {
    Foo._records = [{ id: 1, o2m: [1, 2, 3, 4, 5, 6] }];
    Bar._fields.name = fields.Char();
    Bar._fields.city = fields.Boolean({ default: false, sortable: false });
    Bar._records = [
        { id: 1, name: "a", city: true },
        { id: 2, name: "b" },
        { id: 3, name: "c" },
        { id: 4, name: "d" },
        { id: 5, name: "e" },
        { id: 6, name: "f", city: true },
    ];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="o2m">
                        <list limit="2">
                            <field name="name" required="not city"/>
                            <field name="city"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
        mode: "edit",
    });
    // 3 th (1 for delete button, 2 for columns)
    expect(`th`).toHaveCount(3, { message: "should have 2 columns and delete buttons" });
    expect(`tbody tr.o_data_row`).toHaveCount(2, { message: "should have 2 rows" });
    expect(`th.o_column_sortable`).toHaveCount(1, { message: "should have 1 sortable column" });
    expect(queryAllTexts`.o_data_cell[name="name"]`).toEqual(["a", "b"]);

    // sort by name desc
    await contains(`th.o_column_sortable[data-name=name]`).click();
    await contains(`th.o_column_sortable[data-name=name]`).click();
    expect(queryAllTexts`.o_data_cell[name="name"]`).toEqual(["f", "e"]);

    // remove second record
    await contains(`.o_list_record_remove:eq(1)`).click();
    expect(queryAllTexts`.o_data_cell[name="name"]`).toEqual(["f", "d"]);
    expect(`.o_list_view .o_pager_counter`).toHaveText("1-2 / 5");
});

test("Pass context when duplicating data in list view", async () => {
    onRpc("copy", ({ kwargs }) => {
        expect(kwargs.context.ctx_key).toBe("ctx_val");
        expect.step("copy");
    });
    await mountView({
        type: "list",
        resModel: "res.partner",
        actionMenus: {},
        arch: `
            <list>
                <field name="name" />
            </list>`,
        context: { ctx_key: "ctx_val" },
    });
    await contains(`.o_data_row .o_list_record_selector input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await toggleMenuItem("Duplicate");
    expect.verifySteps(["copy"]);
});

test(`properties do not disappear after domain change`, async () => {
    const definition0 = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    Bar._records[0].definitions = [definition0];
    for (const record of Foo._records) {
        if (record.m2o === 1) {
            record.properties = { [definition0.name]: "AA" };
        }
    }

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="m2o"/>
                <field name="properties"/>
            </list>
        `,
        searchViewArch: `
            <search>
                <filter name="properties_filter" string="My filter" domain="[['properties.property_char', '=', 'AA']]"/>
                <group>
                    <!-- important -->
                    <filter name="properties_groupby" string="My groupby" context="{'group_by':'properties'}"/>
                </group>
            </search>
        `,
    });

    await contains(`.o_optional_columns_dropdown_toggle`).click();
    await contains(`.o-dropdown-item input[type="checkbox"]`).click();
    expect(`.o_list_renderer th[data-name="properties.property_char"]`).toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("My filter");
    expect(`.o_list_renderer th[data-name="properties.property_char"]`).toHaveCount(1);

    await toggleMenuItem("My filter");
    expect(`.o_list_renderer th[data-name="properties.property_char"]`).toHaveCount(1);
});

test("two pages, go page 2, record deleted meanwhile", async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list limit="3">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });

    expect(".o_data_row").toHaveCount(3);
    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(4);

    Foo._records.splice(3);
    await pagerNext();
    expect(".o_data_row").toHaveCount(3);
    expect(getPagerValue()).toEqual([1, 3]);
    expect(getPagerLimit()).toBe(3);
});

test("two pages, go page 2, record deleted meanwhile (grouped case)", async () => {
    for (let i = 0; i < 4; i++) {
        Foo._records[i].bar = true;
    }
    await mountView({
        resModel: "foo",
        type: "list",
        groupBy: ["bar"],
        arch: `<list limit="3">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    });

    expect(".o_group_header").toHaveCount(1);
    expect(".o_data_row").toHaveCount(0);

    await contains(".o_group_header").click();
    expect(".o_data_row").toHaveCount(3);
    expect(getPagerValue(queryFirst(".o_group_header"))).toEqual([1, 3]);
    expect(getPagerLimit(queryFirst(".o_group_header"))).toBe(4);

    Foo._records.splice(3);
    await pagerNext(queryFirst(".o_group_header"));
    expect(".o_data_row").toHaveCount(3);
    expect(".o_group_header .o_pager").toHaveCount(0);
});

test("select records range with shift click on several page", async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
        <list limit="3">
            <field name="foo"/>
            <field name="int_field"/>
        </list>`,
    });

    await contains(`.o_data_row .o_list_record_selector input:eq(0)`).click();
    expect(`.o_data_row:eq(0) .o_list_record_selector input`).toBeChecked();

    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(0);
    expect(`.o_list_selection_box`).toHaveText("1\nselected");
    expect(`.o_data_row .o_list_record_selector input:checked`).toHaveCount(1);
    // click the pager next button
    await contains(".o_pager_next").click();
    // shift click the first record of the second page
    await contains(`.o_data_row .o_list_record_selector input`).click({ shiftKey: true });
    expect(`.o_list_selection_box`).toHaveText("1\nselected\n Select all 4");
});

test("open record, with invalid record in list", async () => {
    // in this scenario, the record is already invalid in db, so we should be allowed to
    // leave it
    Foo._records[0].foo = false;
    Foo._views = {
        form: `<form><field name="foo"/><field name="int_field"/></form>`,
        list: `<list><field name="foo" required="1"/><field name="int_field"/></list>`,
        search: `<search/>`,
    };

    mockService("notification", {
        add() {
            throw new Error("should not display a notification");
        },
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });

    await contains(".o_data_cell").click();

    expect(".o_form_view").toHaveCount(1);
});
