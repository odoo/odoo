/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { session } from "@web/session";
import { tooltipService } from "../../src/core/tooltip/tooltip_service";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import {
    addRow,
    click,
    clickDiscard,
    clickEdit,
    clickSave,
    editInput,
    editSelect,
    getFixture,
    getNodesTextContent,
    legacyExtraNextTick,
    makeDeferred,
    mouseEnter,
    nextTick,
    patchTimeZone,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerEvents,
} from "../helpers/utils";
import {
    getButtons,
    getFacetTexts,
    getPagerLimit,
    getPagerValue,
    groupByMenu,
    pagerNext,
    pagerPrevious,
    toggleActionMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenuItem,
} from "../search/helpers";
import { createWebClient, doAction } from "../webclient/helpers";
import { makeView, setupViewRegistries } from "./helpers";

const { markup, onWillStart } = owl;

const serviceRegistry = registry.category("services");

let serverData;
let target;

// WOWL remove after adapting tests
let testUtils,
    Widget,
    widgetRegistry,
    widgetRegistryOwl,
    ListView,
    ListRenderer,
    core,
    _t,
    clickFirst,
    BasicModel,
    RamStorage,
    AbstractStorageService,
    loadState,
    patch,
    unpatch,
    ControlPanel,
    ListController;

async function reloadListView(target) {
    await click(target, "input.o_searchview_input");
    await triggerEvent(target, "input.o_searchview_input", "keydown", { key: "Enter" });
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
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "res_currency",
                            default: 1,
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
                            currency_id: 2,
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                            reference: "bar,1",
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
                        },
                    ],
                },
                bar: {
                    fields: {},
                    records: [
                        { id: 1, display_name: "Value 1" },
                        { id: 2, display_name: "Value 2" },
                        { id: 3, display_name: "Value 3" },
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
                "ir.translation": {
                    fields: {
                        lang_code: { type: "char" },
                        src: { type: "char" },
                        value: { type: "char" },
                        res_id: { type: "integer" },
                        name: { type: "char" },
                        lang: { type: "char" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 1,
                            value: "",
                            lang_code: "en_US",
                            lang: "en_US",
                            name: "foo,foo",
                        },
                        {
                            id: 100,
                            res_id: 1,
                            value: "",
                            lang_code: "fr_BE",
                            lang: "fr_BE",
                            name: "foo,foo",
                        },
                    ],
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
        assert.expect(9);

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

        assert.strictEqual(
            $(target).find("thead th:nth(2)").css("text-align"),
            "right",
            "header cells of integer fields should be right aligned"
        );
        assert.strictEqual(
            $(target).find("tbody tr:first td:nth(2)").css("text-align"),
            "right",
            "integer cells should be right aligned"
        );

        assert.isVisible(target.querySelector(".o_list_button_add"));
        assert.isNotVisible(target.querySelector(".o_list_button_save"));
        assert.isNotVisible(target.querySelector(".o_list_button_discard"));
    });

    QUnit.test('list with create="0"', async function (assert) {
        assert.expect(1);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree create="0"><field name="foo"/></tree>',
        });

        assert.containsNone(target, ".o_list_button_add", "should not have the 'Create' button");
    });

    QUnit.test('list with delete="0"', async function (assert) {
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            actionMenus: {},
            arch: '<tree delete="0"><field name="foo"/></tree>',
        });

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
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

    QUnit.test(
        "export feature in list for users not in base.group_allow_export",
        async function (assert) {
            assert.expect(5);

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
                ["Delete"],
                "action menu should not contain the Export button"
            );
        }
    );

    QUnit.test("list with export button", async function (assert) {
        assert.expect(5);

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

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
        assert.ok(
            target.querySelectorAll("tbody td.o_list_record_selector").length,
            "should have at least one record"
        );
        assert.containsOnce(target, "div.o_control_panel .o_cp_buttons .o_list_export_xlsx");

        await click(target.querySelector("tbody td.o_list_record_selector input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        await toggleActionMenu(target);
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".o_control_panel .o_cp_action_menus .o_menu_item")
            ),
            ["Export", "Delete"],
            "action menu should have Export button"
        );
    });

    QUnit.test("export button in list view", async function (assert) {
        assert.expect(5);

        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.isVisible(target.querySelector(".o_list_export_xlsx"));

        await click(target.querySelector("tbody td.o_list_record_selector input"));
        assert.isNotVisible(target.querySelector(".o_list_export_xlsx"));
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");

        await click(target.querySelector("tbody td.o_list_record_selector input"));
        assert.isVisible(target.querySelector(".o_list_export_xlsx"));
    });

    QUnit.test("export button in empty list view", async function (assert) {
        const records = serverData.models.foo.records;

        serverData.models.foo.records = [];

        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.isNotVisible(target.querySelector(".o_list_export_xlsx"));

        serverData.models.foo.records = records;
        await reloadListView(target);
        assert.isVisible(target.querySelector(".o_list_export_xlsx"));
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
        assert.expect(2);

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

    QUnit.test("list view with adjacent buttons and invisible field", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" invisible="1"/>
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
        assert.containsN(target.querySelector(".o_data_row:first-child"), "td.o_list_button", 2);
    });

    QUnit.test(
        "list view with adjacent buttons and invisible field (modifier)",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree>
                    <button name="a" type="object" icon="fa-car"/>
                    <field name="foo" attrs="{'invisible': [['foo', '=', 'blip']]}"/>
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
        assert.expect(2);

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
            3,
            "adjacent buttons in the arch must be grouped in a single column"
        );
        assert.containsN(target.querySelector(".o_data_row:first-child"), "td.o_list_button", 2);
    });

    QUnit.test("list view with adjacent buttons with invisible modifier", async function (assert) {
        assert.expect(6);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <button name="x" type="object" icon="fa-star" attrs="{'invisible': [['foo', '=', 'blip']]}"/>
                    <button name="y" type="object" icon="fa-refresh" attrs="{'invisible': [['foo', '=', 'yop']]}"/>
                    <button name="z" type="object" icon="fa-exclamation" attrs="{'invisible': [['foo', '=', 'gnap']]}"/>
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
        assert.expect(5);

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

    QUnit.test("list view: action button in controlPanel basic rendering", async function (assert) {
        assert.expect(11);

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
        let cpButtons = getButtons(target);
        assert.containsNone(cpButtons[0], 'button[name="x"]');
        assert.containsNone(cpButtons[0], ".o_list_selection_box");
        assert.containsNone(cpButtons[0], 'button[name="y"]');

        await click(
            target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        cpButtons = getButtons(target);
        assert.containsOnce(cpButtons[0], 'button[name="x"]');
        assert.hasClass(cpButtons[0].querySelector('button[name="x"]'), "btn btn-secondary");
        assert.containsOnce(cpButtons[0], ".o_list_selection_box");
        assert.strictEqual(
            cpButtons[0].querySelector('button[name="x"]').nextElementSibling,
            cpButtons[0].querySelector(".o_list_selection_box")
        );
        assert.containsNone(cpButtons[0], 'button[name="y"]');

        await click(
            target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
        );
        cpButtons = getButtons(target);
        assert.containsNone(cpButtons[0], 'button[name="x"]');
        assert.containsNone(cpButtons[0], ".o_list_selection_box");
        assert.containsNone(cpButtons[0], 'button[name="y"]');
    });

    QUnit.test(
        "list view: action button executes action on click: buttons are disabled and re-enabled",
        async function (assert) {
            assert.expect(3);

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
            const cpButtons = getButtons(target);
            assert.ok(
                Array.from(cpButtons[0].querySelectorAll("button")).every((btn) => !btn.disabled)
            );

            await click(cpButtons[0].querySelector('button[name="x"]'));
            assert.ok(
                Array.from(cpButtons[0].querySelectorAll("button")).every((btn) => btn.disabled)
            );

            executeActionDef.resolve();
            await nextTick();
            assert.ok(
                Array.from(cpButtons[0].querySelectorAll("button")).every((btn) => !btn.disabled)
            );
        }
    );

    QUnit.test(
        "list view: buttons handler is called once on double click",
        async function (assert) {
            assert.expect(3);

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
                    assert.strictEqual(JSON.stringify(context), "{}");
                },
            });
            await click(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
            );
            const cpButtons = getButtons(target);
            await click(cpButtons[0].querySelector('button[name="x"]'));
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

                    assert.strictEqual(JSON.stringify(context), "{}");
                    assert.strictEqual(resModel, "foo");
                    assert.deepEqual([...resIds], [1, 2, 3, 4]);
                },
            });
            await click(
                target.querySelector('.o_data_row .o_list_record_selector input[type="checkbox"]')
            );
            const cpButtons = getButtons(target);

            await click(cpButtons[0].querySelector(".o_list_select_domain"));
            assert.verifySteps([]);

            await click(cpButtons[0].querySelector('button[name="x"]'));
            assert.verifySteps(["search", "execute_action"]);
        }
    );

    QUnit.test("column names (noLabel, label, string and default)", async function (assert) {
        assert.expect(1);

        const fieldRegistry = registry.category("fields");
        const CharField = fieldRegistry.get("char");

        class NoLabelCharField extends CharField {}
        NoLabelCharField.noLabel = true;
        fieldRegistry.add("nolabel_char", NoLabelCharField);

        class LabelCharField extends CharField {}
        LabelCharField.displayName = "Some static label";
        fieldRegistry.add("label_char", LabelCharField);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="display_name" widget="nolabel_char"/>
                    <field name="foo" widget="label_char"/>
                    <field name="int_field" string="My custom label"/>
                    <field name="text"/>
                </tree>`,
        });

        const columnLabels = [...target.querySelectorAll("thead th")].map((th) => th.textContent);
        assert.deepEqual(columnLabels, [
            "",
            "",
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

        assert.containsOnce(target, ".o_list_button_add");
        assert.containsNone(target, ".o_list_button_save");
        assert.containsNone(target, ".o_list_button_discard");

        await click(target.querySelector(".o_field_cell"));

        assert.containsNone(target, ".o_list_button_add");
        assert.containsOnce(target, ".o_list_button_save");
        assert.containsOnce(target, ".o_list_button_discard");
        assert.containsNone(target, ".o_list_record_selector input:enabled");

        await click(target.querySelector(".o_list_button_save"));

        assert.containsOnce(target, ".o_list_button_add");
        assert.containsNone(target, ".o_list_button_save");
        assert.containsNone(target, ".o_list_button_discard");
        assert.containsN(target, ".o_list_record_selector input:enabled", 5);
    });

    QUnit.skipWOWL("editable rendering with handle and no data", async function (assert) {
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
        assert.expect(1);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" + '<field name="foo"/>' + '<field name="bar" invisible="1"/>' + "</tree>",
        });

        // 1 th for checkbox, 1 for 1 visible column
        assert.containsN(target, "th", 2, "should have 2 th");
    });

    QUnit.test("boolean field has no title (data-tooltip)", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="bar"/></tree>',
        });
        assert.equal($(target).find("tbody tr:first td:eq(1)").attr("data-tooltip"), "");
    });

    QUnit.test("field with nolabel has no title", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo" nolabel="1"/></tree>',
        });
        assert.strictEqual($(target).find("thead tr:first th:eq(1)").text(), "");
    });

    QUnit.test("field titles are not escaped", async function (assert) {
        assert.expect(2);

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
                    <field name="bar" attrs="{'invisible': [('id','=', 1)]}"/>
                    <field name="int_field"/>
                </tree>`,
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsN(target, ".o_data_row td", 16); // 4 cells per row
        assert.strictEqual(target.querySelectorAll(".o_data_row td")[2].innerHTML, "");
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
                        <field name="m2o" invisible="1"/>
                    </tree>`,
                mockRPC: function (route) {
                    assert.step(route.split("/").pop());
                },
            });

            await click(target.querySelector(".o_list_button_add"));
            assert.verifySteps(
                ["get_views", "web_search_read", "onchange"],
                "no nameget should be done"
            );
        }
    );

    QUnit.skipWOWL(
        "editable list datetimepicker destroy widget (edition)",
        async function (assert) {
            assert.expect(7);
            var eventPromise = testUtils.makeTestPromise();

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top">' + '<field name="date"/>' + "</tree>",
            });
            $(target).findel.on({
                "show.datetimepicker": async function () {
                    assert.containsOnce(target, ".o_selected_row");
                    assert.containsOnce($("body"), ".bootstrap-datetimepicker-widget");

                    await testUtils.fields.triggerKeydown(
                        $(target).find(".o_datepicker_input"),
                        "escape"
                    );

                    assert.containsOnce(target, ".o_selected_row");
                    assert.containsNone($("body"), ".bootstrap-datetimepicker-widget");

                    await testUtils.fields.triggerKeydown($(document.activeElement), "escape");

                    assert.containsNone(target, ".o_selected_row");

                    eventPromise.resolve();
                },
            });

            assert.containsN(target, ".o_data_row", 4);
            assert.containsNone(target, ".o_selected_row");

            await click($(target).find(".o_data_cell:first"));
            await testUtils.dom.openDatepicker($(target).find(".o_datepicker"));

            await eventPromise;
        }
    );

    QUnit.skipWOWL(
        "editable list datetimepicker destroy widget (new line)",
        async function (assert) {
            assert.expect(10);
            var eventPromise = testUtils.makeTestPromise();

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top">' + '<field name="date"/>' + "</tree>",
            });
            $(target).findel.on({
                "show.datetimepicker": async function () {
                    assert.containsOnce($("body"), ".bootstrap-datetimepicker-widget");
                    assert.containsN(target, ".o_data_row", 5);
                    assert.containsOnce(target, ".o_selected_row");

                    await testUtils.fields.triggerKeydown(
                        $(target).find(".o_datepicker_input"),
                        "escape"
                    );

                    assert.containsNone($("body"), ".bootstrap-datetimepicker-widget");
                    assert.containsN(target, ".o_data_row", 5);
                    assert.containsOnce(target, ".o_selected_row");

                    await testUtils.fields.triggerKeydown($(document.activeElement), "escape");

                    assert.containsN(target, ".o_data_row", 4);
                    assert.containsNone(target, ".o_selected_row");

                    eventPromise.resolve();
                },
            });
            assert.equal($(target).find(".o_data_row").length, 4, "There should be 4 rows");

            assert.equal(
                $(target).find(".o_selected_row").length,
                0,
                "No row should be in edit mode"
            );

            await click(target.querySelector(".o_list_button_add"));
            await testUtils.dom.openDatepicker($(target).find(".o_datepicker"));

            await eventPromise;
        }
    );

    QUnit.test("at least 4 rows are rendered, even if less data", async function (assert) {
        assert.expect(1);

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
            assert.expect(7);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="bar"/></tree>',
                domain: [["bar", "=", true]],
            });
            assert.containsN(target, ".o_data_row", 3);
            assert.containsN(target, "tbody tr", 4);

            await click(target.querySelector(".o_list_button_add"));
            assert.containsN(target, ".o_data_row", 4);
            assert.hasClass(target.querySelector("tbody tr"), "o_selected_row");

            await click(target.querySelector(".o_list_button_discard"));
            assert.containsN(target, ".o_data_row", 3);
            assert.containsN(target, "tbody tr", 4);
            assert.hasClass(target.querySelector("tbody tr"), "o_data_row");
        }
    );

    QUnit.test("basic grouped list rendering", async function (assert) {
        assert.expect(4);

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
        assert.expect(5);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" +
                '<field name="int_field" widget="handle"/>' +
                '<field name="foo"/>' +
                '<field name="bar"/>' +
                "</tree>",
            groupBy: ["bar"],
        });

        assert.strictEqual($(target).find("th:contains(Foo)").length, 1, "should contain Foo");
        assert.strictEqual($(target).find("th:contains(Bar)").length, 1, "should contain Bar");
        assert.containsN(target, "tr.o_group_header", 2, "should have 2 .o_group_header");
        assert.containsN(target, "th.o_group_name", 2, "should have 2 .o_group_name");
        assert.containsNone(
            target,
            "th:contains(int_field)",
            "Should not have int_field in grouped list"
        );
    });

    QUnit.test("basic grouped list rendering 1 col without selector", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
            groupBy: ["bar"],
            hasSelectors: false,
        });

        assert.containsOnce(target.querySelector(".o_group_header"), "th");
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "1");
    });

    QUnit.test("basic grouped list rendering 1 col with selector", async function (assert) {
        assert.expect(2);

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
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
            hasSelectors: false,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "1");
    });

    QUnit.test("basic grouped list rendering 3 cols without selector", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree ><field name="foo"/><field name="bar"/><field name="text"/></tree>',
            groupBy: ["bar"],
            hasSelectors: false,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "2");
    });

    QUnit.test("basic grouped list rendering 2 col with selector", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ["bar"],
            hasSelectors: true,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "2");
    });

    QUnit.test("basic grouped list rendering 3 cols with selector", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree ><field name="foo"/><field name="bar"/><field name="text"/></tree>',
            groupBy: ["bar"],
            hasSelectors: true,
        });

        assert.containsN(target.querySelector(".o_group_header"), "th", 2);
        assert.strictEqual(target.querySelector(".o_group_header th").getAttribute("colspan"), "3");
    });

    QUnit.test(
        "basic grouped list rendering 7 cols with aggregates and selector",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    "<tree>" +
                    '<field name="datetime"/>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum1"/>' +
                    '<field name="bar"/>' +
                    '<field name="qux" sum="Sum2"/>' +
                    '<field name="date"/>' +
                    '<field name="text"/>' +
                    "</tree>",
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

    QUnit.test("basic grouped list rendering with groupby m2m field", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree>
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
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree>
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

    QUnit.test("deletion of record is disabled when groupby m2m field", async function (assert) {
        assert.expect(5);

        serviceRegistry.add(
            "user",
            makeFakeUserService(() => false),
            { force: true }
        );

        serverData.models.foo.fields.m2m.sortable = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree>
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

        // unselect group by m2m
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "M2M field");
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus .dropdown");
        await click(target, "div.o_control_panel .o_cp_action_menus .dropdown button");
        assert.deepEqual(
            [...target.querySelectorAll(".o_cp_action_menus .o_menu_item")].map(
                (el) => el.innerText
            ),
            ["Delete"]
        );
    });

    QUnit.skipWOWL(
        "editing a record should change same record in other groups when grouped by m2m field",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `<tree editable="bottom">
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

    QUnit.skipWOWL(
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
                arch: `<tree>
                    <field name="foo"/>
                    <field name="priority" widget="priority"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
                groupBy: ["m2m"],
                domain: [["m2o", "=", 1]],
                mockRPC: function (route, args) {
                    if (args.method === "write") {
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
        assert.expect(1);
        // Equivalent to saving a custom filter

        serverData.models.foo.fields.foo.sortable = true;
        serverData.models.foo.fields.date.sortable = true;

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: "<tree>" + '<field name="foo"/>' + '<field name="date"/>' + "</tree>",
        });

        // Descending order on Foo
        await click($(target).find('th.o_column_sortable:contains("Foo")')[0]);
        await click($(target).find('th.o_column_sortable:contains("Foo")')[0]);

        // Ascending order on Date
        await click($(target).find('th.o_column_sortable:contains("Date")')[0]);

        assert.deepEqual(
            list.model.root.orderBy,
            [
                {
                    name: "date",
                    asc: true,
                },
                {
                    name: "foo",
                    asc: false,
                },
            ],
            "the list should have the right orderedBy"
        );
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
            arch: "<tree>" + '<field name="foo"/>' + '<field name="date"/>' + "</tree>",
            mockRPC: function (route, args) {
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

        await toggleFavoriteMenu(target);
        await toggleMenuItem(target, "My second favorite");
    });

    QUnit.test("many2one field rendering", async function (assert) {
        assert.expect(1);

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

    QUnit.test("grouped list view, with 1 open group", async function (assert) {
        assert.expect(8);

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
        class ListViewCustom extends listView.Controller {
            openRecord(record) {
                assert.step("openRecord");
                assert.strictEqual(record.resId, 2);
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

        serverData.models.foo.fields.foo.sortable = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
        });

        await click(target.querySelector("tr:nth-child(2) td:not(.o_list_record_selector)"));
        await groupByMenu(target, "foo");

        assert.containsN(target, "tr.o_group_header", 3, "list should be grouped");
        await click(target.querySelector("th.o_group_name"));

        click(target.querySelector("tr:not(.o_group_header) td:not(.o_list_record_selector)"));
        assert.verifySteps(["openRecord", "openRecord"]);
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
    });

    QUnit.test("editable list view: line with no active element", async function (assert) {
        assert.expect(3);

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
            mockRPC: function (route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], {
                        o2m: [
                            [1, 1, { grosminet: false }],
                            [4, 2, false],
                        ],
                    });
                }
            },
        });
        await clickEdit(target);

        const cells = target.querySelectorAll(".o_data_cell");
        assert.containsOnce(cells[0], ".o_readonly_modifier");
        assert.hasClass(cells[1], "o_boolean_toggle_cell");

        await click(cells[0]);
        await click(cells[1], ".o_boolean_toggle input");
        await clickSave(target);
    });

    QUnit.skipWOWL(
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
                arch:
                    "<form>" +
                    '<field name="o2m">' +
                    '<tree editable="top">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="titi"/>' +
                    "</tree>" +
                    "</field>" +
                    "</form>",
            });
            await clickEdit(target);
            await addRow(target);
            await click(
                [...target.querySelectorAll(".o_data_row")].pop().querySelector("td.o_list_char")
            );
            // This test ensure that they aren't traceback when clicking on the last row.
            assert.containsN(target, ".o_data_row", 2, "list should have exactly 2 rows");
        }
    );

    QUnit.skipWOWL("edit field in editable field without editing the row", async function (assert) {
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
                if (args.method === "write") {
                    assert.step("write: " + args.args[1].bar);
                }
            },
        });

        // toggle the boolean value of the first row without editing the row
        assert.ok(target.querySelector(".o_data_row .o_boolean_toggle input").checked);
        assert.containsNone(target, ".o_selected_row");
        await click(target.querySelector(".o_data_row .o_boolean_toggle input"));
        assert.notOk(target.querySelector(".o_data_row .o_boolean_toggle input").checked);
        assert.containsNone(target, ".o_selected_row");
        assert.verifySteps(["write: false"]);

        // toggle the boolean value after switching the row in edition
        assert.containsNone(target, ".o_selected_row");
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");
        await click(target.querySelector(".o_selected_row .o_boolean_toggle"));
        assert.containsOnce(target, ".o_selected_row");
        assert.verifySteps([]);

        // save
        await clickSave(target);
        assert.containsNone(target, ".o_selected_row");
        assert.verifySteps(["write: true"]);
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

        await click(target.querySelector(".o_list_button_add"));

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

        await click(target.querySelector(".o_list_button_discard"));

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
            assert.expect(3);

            serverData.models.foo.fields.foo.sortable = true;

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo"/></tree>',
                mockRPC: function (route, args) {
                    if (args.method === "write") {
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

            assert.hasClass(
                target.querySelector(".o_data_row"),
                "o_selected_row",
                "first row should still be in edition"
            );

            await click(target.querySelector(".o_list_button_save"));
            assert.containsNone(target, ".o_list_button_save");
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
            await click(target.querySelector(".o_list_button_add"));

            assert.containsNone(target, ".o_list_button_add");
            assert.containsOnce(target, ".o_list_button_save");

            await toggleGroupByMenu(target);
            await toggleMenuItem(target, "candle");

            assert.containsNone(
                target,
                ".o_list_button_add",
                "Create not available as list is grouped"
            );
            assert.containsNone(
                target,
                ".o_list_button_save",
                "Save not available as no row in edition"
            );
        }
    );

    QUnit.test("list view not groupable", async function (assert) {
        assert.expect(2);

        serverData.views = {
            "foo,false,search": `
                <search>
                    <filter context="{'group_by': 'foo'}" name="foo"/>
                </search>
            `,
        };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="display_name"/>
                    <field name="foo"/>
                </tree>
            `,
            mockRPC: function (route, args) {
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
        assert.expect(11);

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

        await click(tbody_selector);
        assert.strictEqual(list.model.root.selection.length, 0, "no record should be selected");
        assert.notOk(tbody_selector.checked, "selection checkbox should be checked");

        // head checkbox click
        await click(thead_selector);
        assert.strictEqual(list.model.root.selection.length, 4, "all records should be selected");
        assert.containsN(
            target,
            "tbody .o_list_record_selector input:checked",
            target.querySelectorAll("tbody tr").length,
            "all selection checkboxes should be checked"
        );

        await click(thead_selector);
        assert.strictEqual(list.model.root.selection.length, 0, "no records should be selected");
        assert.containsNone(
            target,
            "tbody .o_list_record_selector input:checked",
            "no selection checkbox should be checked"
        );
    });

    QUnit.test(
        "Row selection checkbox can be toggled by clicking on the cell",
        async function (assert) {
            assert.expect(9);

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
        assert.expect(6);

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
        assert.expect(11);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");

        // select a record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "1 selected"
        );

        // select all records of first page
        await click(target.querySelector("thead .o_list_record_selector input"));
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "4 selected"
        );

        // unselect a record
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[1]);
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "3 selected"
        );
    });

    QUnit.test("selection box is properly displayed (multi pages)", async function (assert) {
        assert.expect(10);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="3"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 3);
        assert.containsNone(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");

        // select a record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.containsNone(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "1 selected"
        );

        // select all records of first page
        await click(target.querySelector("thead .o_list_record_selector input"));
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.containsOnce(target.querySelector(".o_list_selection_box"), ".o_list_select_domain");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.replace(/\s+/g, " ").trim(),
            "3 selected Select all 4"
        );

        // select all domain
        await click(target.querySelector(".o_list_selection_box .o_list_select_domain"));
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.strictEqual(
            target.querySelector(".o_list_selection_box").textContent.trim(),
            "All 4 selected"
        );
    });

    QUnit.test("selection box is displayed after header buttons", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree>
                    <header>
                         <button name="x" type="object" class="plaf" string="plaf"/>
                         <button name="y" type="object" class="plouf" string="plouf"/>
                    </header>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
        });

        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone($(target).find(".o_cp_buttons"), ".o_list_selection_box");

        // select a record
        await click(target, ".o_data_row:first-child .o_list_record_selector input");
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        const lastElement = target.querySelector(".o_cp_buttons .o_list_buttons").lastElementChild;
        assert.strictEqual(
            lastElement,
            target.querySelector(".o_cp_buttons .o_list_selection_box"),
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
            target.querySelector(".o_cp_buttons"),
            ".o_list_selection_box",
            "list selection box should not be displayed"
        );

        // select all records
        await click(target.querySelector(".o_list_record_selector input"));
        assert.containsOnce(
            target.querySelector(".o_cp_buttons"),
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
            target.querySelector(".o_cp_buttons"),
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
        assert.expect(8);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" +
                '<field name="foo"/>' +
                '<field name="int_field" sum="Sum"/>' +
                "</tree>",
        });

        assert.containsNone(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.strictEqual(
            $(target).find("tfoot td:nth(2)").text(),
            "32",
            "total should be 32 (no record selected)"
        );

        // select first record
        var firstRowSelector = target.querySelector("tbody .o_list_record_selector input");
        await click(firstRowSelector);
        assert.ok(firstRowSelector.checked, "first row should be selected");
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.strictEqual(
            $(target).find("tfoot td:nth(2)").text(),
            "10",
            "total should be 10 (first record selected)"
        );

        await reloadListView(target);
        firstRowSelector = target.querySelector("tbody .o_list_record_selector input");
        assert.notOk(firstRowSelector.checked, "first row should no longer be selected");
        assert.containsNone(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
        assert.strictEqual(
            $(target).find("tfoot td:nth(2)").text(),
            "32",
            "total should be 32 (no more record selected)"
        );
    });

    QUnit.test("selection is kept on render without reload", async function (assert) {
        assert.expect(10);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["foo"],
            actionMenus: {},
            arch:
                "<tree>" +
                '<field name="foo"/>' +
                '<field name="int_field" sum="Sum"/>' +
                "</tree>",
        });

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsNone(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");

        // open blip grouping and check all lines
        await click($(target).find('.o_group_header:contains("blip (2)")')[0]);
        await click(target.querySelector(".o_data_row input"));
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");

        // open yop grouping and verify blip are still checked
        await click($(target).find('.o_group_header:contains("yop (1)")')[0]);
        assert.containsOnce(
            target,
            ".o_data_row input:checked",
            "opening a grouping does not uncheck others"
        );
        assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsOnce(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");

        // close and open blip grouping and verify blip are unchecked
        await click($(target).find('.o_group_header:contains("blip (2)")')[0]);
        await click($(target).find('.o_group_header:contains("blip (2)")')[0]);
        assert.containsNone(
            target,
            ".o_data_row input:checked",
            "opening and closing a grouping uncheck its elements"
        );
        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
        assert.containsNone(target.querySelector(".o_cp_buttons"), ".o_list_selection_box");
    });

    QUnit.skipWOWL("aggregates are computed correctly", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field" sum="Sum"/></tree>',
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('id', '=', 0)]"/>
                </search>`,
        });
        const tbodySelectors = target.querySelectorAll("tbody .o_list_record_selector input");
        const theadSelector = target.querySelector("thead .o_list_record_selector input");

        assert.strictEqual(target.querySelectorAll("tfoot td")[2].innerText, "32");

        await click(tbodySelectors[0]);
        await click(tbodySelectors[3]);
        assert.strictEqual(target.querySelectorAll("tfoot td")[2].innerText, "6");

        await click(theadSelector);
        assert.strictEqual(target.querySelectorAll("tfoot td")[2].innerText, "32");

        // Let's update the view to dislay NO records
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");
        assert.strictEqual(
            target.querySelectorAll("tfoot td")[2].innerText,
            "",
            "No records, so no total."
        );
    });

    QUnit.test("aggregates are computed correctly in grouped lists", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["m2o"],
            arch:
                '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
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

    QUnit.test(
        "hide aggregated value in grouped lists when no data provided by RPC call",
        async function (assert) {
            assert.expect(1);

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
            target.querySelector('td[data-tooltip="Sum"]').innerText,
            "32",
            "current total should be 32"
        );

        await click(target.querySelector("tr.o_data_row td.o_data_cell"));
        await editInput(target, "td.o_data_cell input", "15");

        assert.strictEqual(
            target.querySelector('td[data-tooltip="Sum"]').innerText,
            "37",
            "current total should be 37"
        );
    });

    QUnit.test("aggregates are formatted according to field widget", async function (assert) {
        assert.expect(1);

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

    // Will change TASK-ID 2822174
    QUnit.skipWOWL(
        "aggregates digits can be set with digits field attribute",
        async function (assert) {
            assert.expect(2);

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
                "2000.000",
                "aggregates monetary use digits attribute if available"
            );
        }
    );

    QUnit.test("groups can be sorted on aggregates", async function (assert) {
        assert.expect(10);
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["foo"],
            arch:
                '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
            mockRPC: function (route, args) {
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

    QUnit.test("groups cannot be sorted on non-aggregable fields", async function (assert) {
        assert.expect(8);
        serverData.models.foo.fields.sort_field = {
            string: "sortable_field",
            type: "sting",
            sortable: true,
            default: "value",
        };
        _.each(serverData.models.records, function (elem) {
            elem.sort_field = "value" + elem.id;
        });
        serverData.models.foo.fields.foo.sortable = true;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            groupBy: ["foo"],
            arch:
                '<tree editable="bottom"><field name="foo" /><field name="int_field"/><field name="sort_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === "web_read_group") {
                    assert.step(args.kwargs.orderby || "default order");
                }
            },
        });
        assert.verifySteps(["default order"]);
        //we cannot sort by sort_field since it doesn't have a group_operator
        await click(target.querySelectorAll(".o_column_sortable")[2]);
        assert.verifySteps([]);
        //we can sort by int_field since it has a group_operator
        await click(target.querySelectorAll(".o_column_sortable")[1]);
        assert.verifySteps(["int_field ASC"]);
        //we keep previous order
        await click(target.querySelectorAll(".o_column_sortable")[2]);
        assert.verifySteps([]);
        //we can sort on foo since we are groupped by foo + previous order
        await click(target.querySelectorAll(".o_column_sortable")[0]);
        assert.verifySteps(["foo ASC, int_field ASC"]);
    });

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

    QUnit.skipWOWL("column width should not change when switching mode", async function (assert) {
        assert.expect(4);

        // Warning: this test is css dependant
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="top">' +
                '<field name="foo"/>' +
                '<field name="int_field" readonly="1"/>' +
                '<field name="m2o"/>' +
                '<field name="m2m" widget="many2many_tags"/>' +
                "</tree>",
        });

        var startWidths = _.pluck($(target).find("thead th"), "offsetWidth");
        var startWidth = $(target).find("table").addBack("table").width();

        // start edition of first row
        await click($(target).find("td:not(.o_list_record_selector)").first());

        var editionWidths = _.pluck($(target).find("thead th"), "offsetWidth");
        var editionWidth = $(target).find("table").addBack("table").width();

        // leave edition
        await click(target.querySelector(".o_list_button_save"));

        var readonlyWidths = _.pluck($(target).find("thead th"), "offsetWidth");
        var readonlyWidth = $(target).find("table").addBack("table").width();

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

    QUnit.skipWOWL(
        "column widths should depend on the content when there is data",
        async function (assert) {
            assert.expect(1);

            serverData.models.foo.records[0].foo = "Some very very long value for a char field";

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="top">' +
                    '<field name="bar"/>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                    '<field name="date"/>' +
                    '<field name="datetime"/>' +
                    "</tree>",
                viewOptions: {
                    limit: 2,
                },
            });
            var widthPage1 = $(target).find(`th[data-name=foo]`)[0].offsetWidth;

            await testUtils.controlPanel.pagerNext(target);

            var widthPage2 = $(target).find(`th[data-name=foo]`)[0].offsetWidth;
            assert.ok(
                widthPage1 > widthPage2,
                "column widths should be computed dynamically according to the content"
            );
        }
    );

    QUnit.skipWOWL(
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
                arch:
                    '<tree editable="top">' +
                    '<field name="bar"/>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                    '<field name="date"/>' +
                    '<field name="datetime"/>' +
                    '<field name="amount"/>' +
                    '<field name="currency_id" width="25px"/>' +
                    "</tree>",
            });

            assert.containsNone(
                target,
                ".o_resize",
                "There shouldn't be any resize handle if no data"
            );
            assertions.forEach((a) => {
                assert.strictEqual(
                    $(target).find(`th[data-name="${a.field}"]`)[0].offsetWidth,
                    a.expected,
                    `Field ${a.type} should have a fixed width of ${a.expected} pixels`
                );
            });
            assert.strictEqual(
                $(target).find('th[data-name="foo"]')[0].style.width,
                "100%",
                "Char field should occupy the remaining space"
            );
            assert.strictEqual(
                $(target).find('th[data-name="currency_id"]')[0].offsetWidth,
                25,
                "Currency field should have a fixed width of 25px (see arch)"
            );
        }
    );

    QUnit.skipWOWL(
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
            const form = await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                viewOptions: { mode: "edit" },
                arch: `<form>
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

            assert.isNotVisible(form.$(".o_field_one2many"));

            await click(form.$(".nav-item:last-child .nav-link"));

            assert.isVisible(form.$(".o_field_one2many"));

            assert.containsNone(
                form,
                ".o_field_one2many .o_resize",
                "There shouldn't be any resize handle if no data"
            );
            assertions.forEach((a) => {
                assert.strictEqual(
                    form.$(`.o_field_one2many th[data-name="${a.field}"]`)[0].offsetWidth,
                    a.expected,
                    `Field ${a.type} should have a fixed width of ${a.expected} pixels`
                );
            });
            assert.strictEqual(
                form.$('.o_field_one2many th[data-name="foo"]')[0].style.width,
                "100%",
                "Char field should occupy the remaining space"
            );
            assert.strictEqual(
                form.$('th[data-name="currency_id"]')[0].offsetWidth,
                25,
                "Currency field should have a fixed width of 25px (see arch)"
            );
            assert.strictEqual(
                form.el.querySelector(".o_list_record_remove_header").style.width,
                "32px"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "empty editable list with the handle widget and no content help",
        async function (assert) {
            assert.expect(4);

            // no records for the foo model
            serverData.models.foo.records = [];

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `<tree editable="bottom">
                    <field name="int_field" widget="handle" />
                    <field name="foo" />
                </tree>`,
                viewOptions: {
                    action: {
                        help: '<p class="hello">click to add a foo</p>',
                    },
                },
            });

            // as help is being provided in the action, table won't be rendered until a record exists
            assert.containsNone(
                target,
                ".o_list_table",
                " there should not be any records in the view."
            );
            assert.containsOnce(target, ".o_view_nocontent", "should have no content help");

            // click on create button
            await click(target.querySelector(".o_list_button_add"));
            const handleWidgetMinWidth = "33px";
            const handleWidgetHeader = $(target).find("thead > tr > th.o_handle_cell");
            assert.strictEqual(
                handleWidgetHeader.css("min-width"),
                handleWidgetMinWidth,
                "While creating first record, min-width should be applied to handle widget."
            );

            // creating one record
            await editInput($(target).find("tr.o_selected_row input[name='foo']"), "test_foo");
            await click($(target).find(".o_list_button_save"));
            assert.strictEqual(
                handleWidgetHeader.css("min-width"),
                handleWidgetMinWidth,
                "After creation of the first record, min-width of the handle widget should remain as it is"
            );
        }
    );

    QUnit.skipWOWL("editable list: overflowing table", async function (assert) {
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

    QUnit.skipWOWL("editable list: overflowing table (3 columns)", async function (assert) {
        assert.expect(4);

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
            model: "bar",
            type: "list",
        });

        assert.strictEqual($(target).find("table").width(), $(target).find(".o_list_view").width());
        const largeCells = $(target).find(".o_data_cell.large");
        assert.strictEqual(largeCells[0].offsetWidth, largeCells[1].offsetWidth);
        assert.strictEqual(largeCells[1].offsetWidth, largeCells[2].offsetWidth);
        assert.ok(
            $(target).find(".o_data_cell:not(.large)")[0].offsetWidth < largeCells[0].offsetWidth
        );
    });

    QUnit.skipWOWL(
        "editable list: list view in an initially unselected notebook page",
        async function (assert) {
            assert.expect(5);

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
            const form = await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                viewOptions: { mode: "edit" },
                arch:
                    "<form>" +
                    "<sheet>" +
                    "<notebook>" +
                    '<page string="Page1"></page>' +
                    '<page string="Page2">' +
                    '<field name="o2m">' +
                    '<tree editable="bottom">' +
                    '<field name="titi"/>' +
                    '<field name="grosminet"/>' +
                    "</tree>" +
                    "</field>" +
                    "</page>" +
                    "</notebook>" +
                    "</sheet>" +
                    "</form>",
            });

            const [titi, grosminet] = form.el.querySelectorAll(".tab-pane:last-child th");
            const one2many = form.el.querySelector(".o_field_one2many");

            assert.isNotVisible(one2many, "One2many field should be hidden");
            assert.strictEqual(titi.style.width, "", "width of small char should not be set yet");
            assert.strictEqual(
                grosminet.style.width,
                "",
                "width of large char should also not be set"
            );

            await click(form.el.querySelector(".nav-item:last-child .nav-link"));

            assert.isVisible(one2many, "One2many field should be visible");
            assert.ok(
                titi.style.width.split("px")[0] > 80 && grosminet.style.width.split("px")[0] > 700,
                "list has been correctly frozen after being visible"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "editable list: list view hidden by an invisible modifier",
        async function (assert) {
            assert.expect(5);

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
            var form = await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                resId: 1,
                viewOptions: { mode: "edit" },
                arch:
                    "<form>" +
                    "<sheet>" +
                    '<field name="bar"/>' +
                    "<field name=\"o2m\" attrs=\"{'invisible': [('bar', '=', True)]}\">" +
                    '<tree editable="bottom">' +
                    '<field name="titi"/>' +
                    '<field name="grosminet"/>' +
                    "</tree>" +
                    "</field>" +
                    "</sheet>" +
                    "</form>",
            });

            const [titi, grosminet] = form.el.querySelectorAll("th");
            const one2many = form.el.querySelector(".o_field_one2many");

            assert.isNotVisible(one2many, "One2many field should be hidden");
            assert.strictEqual(titi.style.width, "", "width of small char should not be set yet");
            assert.strictEqual(
                grosminet.style.width,
                "",
                "width of large char should also not be set"
            );

            await click(form.el.querySelector(".o_field_boolean input"));

            assert.isVisible(one2many, "One2many field should be visible");
            assert.ok(
                titi.style.width.split("px")[0] > 80 && grosminet.style.width.split("px")[0] > 700,
                "list has been correctly frozen after being visible"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL("editable list: updating list state while invisible", async function (assert) {
        assert.expect(2);

        serverData.models.foo.onchanges = {
            bar: function (obj) {
                obj.o2m = [[5], [0, null, { display_name: "Whatever" }]];
            },
        };
        var form = await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            viewOptions: { mode: "edit" },
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="bar"/>' +
                "<notebook>" +
                '<page string="Page 1"></page>' +
                '<page string="Page 2">' +
                '<field name="o2m">' +
                '<tree editable="bottom">' +
                '<field name="display_name"/>' +
                "</tree>" +
                "</field>" +
                "</page>" +
                "</notebook>" +
                "</sheet>" +
                "</form>",
        });

        await click(form.$(".o_field_boolean input"));

        assert.strictEqual(
            form.el.querySelector("th").style.width,
            "",
            "Column header should be initially unfrozen"
        );

        await click(form.$(".nav-item:last() .nav-link"));

        assert.notEqual(
            form.el.querySelector("th").style.width,
            "",
            "Column header should have been frozen"
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "empty list: state with nameless and stringless buttons",
        async function (assert) {
            assert.expect(2);

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
                [...target.querySelectorAll("th")].find((el) => el.textContent === "Foo").style
                    .width,
                "50%",
                "Field column should be frozen"
            );
            assert.strictEqual(
                target.querySelector("th:last-child").style.width,
                "50%",
                "Buttons column should be frozen"
            );
        }
    );

    QUnit.skipWOWL("editable list: unnamed columns cannot be resized", async function (assert) {
        assert.expect(2);

        serverData.models.foo.records = [{ id: 1, o2m: [1] }];
        serverData.models.bar.records = [{ id: 1, display_name: "Oui" }];
        var form = await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            resId: 1,
            viewOptions: { mode: "edit" },
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="o2m">' +
                '<tree editable="top">' +
                '<field name="display_name"/>' +
                '<button name="the_button" icon="fa-heart"/>' +
                "</tree>" +
                "</field>" +
                "</sheet>" +
                "</form>",
        });

        const [charTh, buttonTh] = form.$(".o_field_one2many th");
        const thRect = charTh.getBoundingClientRect();
        const resizeRect = charTh.getElementsByClassName("o_resize")[0].getBoundingClientRect();

        assert.strictEqual(
            thRect.x + thRect.width,
            resizeRect.x + resizeRect.width,
            "First resize handle should be attached at the end of the first header"
        );
        assert.containsNone(
            buttonTh,
            ".o_resize",
            "Columns without name should not have a resize handle"
        );

        form.destroy();
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

            await click(target.querySelector(".o_list_button_add"));
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
                arch: `<tree editable="top">
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
        assert.expect(1);

        serverData.models.foo.records = []; // the width heuristic only applies when there are no records
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="top">
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
        assert.expect(2);

        serverData.models.foo.records = []; // in this scenario, we start with no records
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="top">
                    <field name="datetime"/>
                    <field name="text"/>
                </tree>`,
        });

        var width = target.querySelectorAll('th[data-name="datetime"]')[0].offsetWidth;

        await click(target.querySelector(".o_list_button_add"));

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(
            target.querySelectorAll('th[data-name="datetime"]')[0].offsetWidth,
            width
        );
    });

    QUnit.test("column widths are kept when editing a record", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree editable="bottom">
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
            arch: `<tree editable="bottom">
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
            arch: `<tree editable="bottom">
                        <field name="datetime"/>
                        <field name="text"/>
                    </tree>`,
        });

        const initialTextWidth = target.querySelectorAll('th[data-name="text"]')[0].offsetWidth;
        const selectorWidth = target.querySelectorAll("th.o_list_record_selector")[0].offsetWidth;

        // simulate a window resize
        target.style.width = target.getBoundingClientRect().width / 2 + "px";

        const postResizeTextWidth = target.querySelectorAll('th[data-name="text"]')[0].offsetWidth;
        const postResizeSelectorWidth = target.querySelectorAll("th.o_list_record_selector")[0]
            .offsetWidth;
        assert.ok(postResizeTextWidth < initialTextWidth);
        assert.strictEqual(selectorWidth, postResizeSelectorWidth);
    });

    QUnit.skipWOWL(
        "columns with an absolute width are never narrower than that width",
        async function (assert) {
            assert.expect(2);

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
                arch:
                    '<tree editable="bottom">' +
                    '<field name="datetime"/>' +
                    '<field name="int_field" width="200px"/>' +
                    '<field name="text"/>' +
                    "</tree>",
            });

            assert.strictEqual($(target).find('th[data-name="datetime"]')[0].offsetWidth, 146);
            assert.strictEqual($(target).find('th[data-name="int_field"]')[0].offsetWidth, 200);
        }
    );

    QUnit.skipWOWL("list view with data: text columns are not crushed", async function (assert) {
        assert.expect(2);

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

        assert.strictEqual(
            fooWidth,
            textWidth,
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
        assert.expect(1);

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

    QUnit.skipWOWL("button columns in a list view don't have a max width", async function (assert) {
        assert.expect(2);

        testUtils.mock.patch(ListRenderer, {
            RESIZE_DELAY: 0,
        });

        // set a long foo value s.t. the column can be squeezed
        serverData.models.foo.records[0].foo = "Lorem ipsum dolor sit amet";
        await makeView({
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
        $(target).findel.width("300px");
        core.bus.trigger("resize");
        await testUtils.nextTick();

        assert.strictEqual(
            $(target).find("th:nth(1)").css("max-width"),
            "92px",
            "max-width should be set on column foo to the minimum column width (92px)"
        );
        assert.strictEqual(
            $(target).find("th:nth(2)").css("max-width"),
            "100%",
            "no max-width should be harcoded on the buttons column"
        );

        testUtils.mock.unpatch(ListRenderer);
    });

    QUnit.skipWOWL("column widths are kept when editing multiple records", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree multi_edit="1">' +
                '<field name="datetime"/>' +
                '<field name="text"/>' +
                "</tree>",
        });

        var width = $(target).find('th[data-name="datetime"]')[0].offsetWidth;

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
        await editInput($(target).find(".o_field_widget[name=text]"), longVal);
        assert.containsOnce(document.body, ".modal");
        await click(target, ".modal .btn-primary");

        assert.containsNone(target, ".o_selected_row");
        assert.strictEqual($(target).find('th[data-name="datetime"]')[0].offsetWidth, width);
    });

    QUnit.skipWOWL(
        "row height and width should not change when switching mode",
        async function (assert) {
            // Warning: this test is css dependant
            assert.expect(5);

            var multiLang = _t.database.multi_lang;
            _t.database.multi_lang = true;

            serverData.models.foo.fields.foo.translate = true;
            serverData.models.foo.fields.boolean = { type: "boolean", string: "Bool" };
            var currencies = {};
            _.each(serverData.models.res_currency.records, function (currency) {
                currencies[currency.id] = currency;
            });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="top">' +
                    '<field name="foo" required="1"/>' +
                    '<field name="int_field" readonly="1"/>' +
                    '<field name="boolean"/>' +
                    '<field name="date"/>' +
                    '<field name="text"/>' +
                    '<field name="amount"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                    '<field name="m2o"/>' +
                    '<field name="m2m" widget="many2many_tags"/>' +
                    "</tree>",
                session: {
                    currencies: currencies,
                },
            });

            // the width is hardcoded to make sure we have the same condition
            // between debug mode and non debug mode
            $(target).findel.width("1200px");
            var startHeight = $(target).find(".o_data_row:first").outerHeight();
            var startWidth = $(target).find(".o_data_row:first").outerWidth();

            // start edition of first row
            await click(
                $(target).find(".o_data_row:first > td:not(.o_list_record_selector)").first()
            );
            assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
            var editionHeight = $(target).find(".o_data_row:first").outerHeight();
            var editionWidth = $(target).find(".o_data_row:first").outerWidth();

            // leave edition
            await click(target.querySelector(".o_list_button_save"));
            var readonlyHeight = $(target).find(".o_data_row:first").outerHeight();
            var readonlyWidth = $(target).find(".o_data_row:first").outerWidth();

            assert.strictEqual(startHeight, editionHeight);
            assert.strictEqual(startHeight, readonlyHeight);
            assert.strictEqual(startWidth, editionWidth);
            assert.strictEqual(startWidth, readonlyWidth);

            _t.database.multi_lang = multiLang;
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
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_button" && args.method === "translate_fields") {
                    return Promise.resolve({
                        domain: [],
                        context: { search_default_name: "foo,foo" },
                    });
                }
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([
                        ["en_US", "English"],
                        ["fr_BE", "Frenglish"],
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
        assert.expect(2);

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

    QUnit.test("deleting one record", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            actionMenus: {},
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
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

        assert.containsN(target, "tbody td.o_list_record_selector", 3, "should have 3 records");
    });

    QUnit.test(
        "deleting record which throws UserError should close confirmation dialog",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                actionMenus: {},
                arch: '<tree><field name="foo"/></tree>',
                mockRPC: function (route, args) {
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
            mockRPC: function (route, args) {
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

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
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

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [["bar", "=", true]],
            mockRPC: function (route, args) {
                if (args.method === "unlink") {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
            },
            actionMenus: {},
        });
        patchWithCleanup(session, {
            active_ids_limit: 4,
        });
        patchWithCleanup(list.env.services.notification, {
            add: () => {
                assert.step("notify");
            },
        });

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
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

    QUnit.test("archiving one record", async function (assert) {
        assert.expect(13);

        // add active field on foo model and make all records active
        serverData.models.foo.fields.active = { string: "Active", type: "boolean", default: true };

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            actionMenus: {},
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
            },
        });

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
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
            mockRPC: function (route, args) {
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

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
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

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [["bar", "=", true]],
            mockRPC: function (route, args) {
                if (args.method === "action_archive") {
                    assert.deepEqual(args.args[0], [1, 2, 3, 5]);
                }
            },
            actionMenus: {},
        });

        patchWithCleanup(session, {
            active_ids_limit: 4,
        });
        patchWithCleanup(list.env.services.notification, {
            add: () => {
                assert.step("notify");
            },
        });

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
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
        assert.expect(6);

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

        assert.containsNone(target, ".o_cp_action_menus", "sidebar should be invisible");
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
            mockRPC: function (route, args) {
                if (args.method === "web_search_read") {
                    assert.strictEqual(args.kwargs.limit, 80, "default limit should be 80 in List");
                }
            },
        });

        assert.containsOnce(target, "div.o_control_panel .o_cp_pager .o_pager");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Bar");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "2");
    });

    QUnit.test("can sort records when clicking on header", async function (assert) {
        assert.expect(9);

        serverData.models.foo.fields.foo.sortable = true;

        var nbSearchRead = 0;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            mockRPC: function (route) {
                if (route === "/web/dataset/call_kw/foo/web_search_read") {
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
        assert.expect(6);

        serverData.models.foo.fields.foo.sortable = true;

        let nbSearchRead = 0;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo" nolabel="1"/><field name="int_field"/></tree>',
            mockRPC: function (route) {
                if (route === "/web/dataset/call_kw/foo/web_search_read") {
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
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/foo/web_search_read") {
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
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/foo/web_search_read") {
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

        await clickEdit(target);
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

        await clickEdit(target);
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
                name: { string: "Name", type: "char", sortable: true },
            };

            var ids = [];
            for (var i = 0; i < 45; i++) {
                var id = 4 + i;
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
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: "<tree>" + '<field name="m2m"/>' + "</tree>",
            mockRPC: function (route, args) {
                assert.step(args.method);
            },
        });
        assert.verifySteps(["get_views", "web_search_read"], "should have done 1 web_search_read");
        assert.ok(
            $(target).find("td:contains(3 records)").length,
            "should have a td with correct formatted value"
        );
    });

    QUnit.test("display a tooltip on a field", async function (assert) {
        patchWithCleanup(odoo, {
            debug: false,
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree>
                    <field name="foo"/>
                    <field name="bar" widget="toggle_button"/>
                </tree>`,
        });

        await mouseEnter(target.querySelector("th[data-name=foo]"));
        await nextTick(); // GES: see next nextTick comment
        assert.strictEqual(
            target.querySelectorAll(".o-tooltip .o-tooltip--string").length,
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
            target.querySelectorAll(".o-tooltip .o-tooltip--string").length,
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
            ["Widget:Button (toggle_button)"],
            "widget description should be correct"
        );
    });

    QUnit.test("support row decoration", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree decoration-info="int_field > 5">' +
                '<field name="foo"/><field name="int_field"/>' +
                "</tree>",
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

        await click(target.querySelector(".o_list_button_add"));
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
        assert.expect(3);

        serverData.models.foo.records[0].datetime = "2017-02-27 12:51:35";

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree
                    decoration-info="datetime == '2017-02-27 12:51:35'"
                    decoration-danger="datetime &gt; '2017-02-27 12:51:35' AND datetime &lt; '2017-02-27 10:51:35'"
                >
                    <field name="datetime"/>
                    <field name="int_field"/>
                </tree>
            `,
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

    QUnit.test("support field decoration", async function (assert) {
        assert.expect(3);

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

        assert.containsN(target, "tbody tr", 4, "should have 4 rows");
        assert.containsN(target, "tbody td .text-danger", 3);
        assert.containsNone(target, "tbody td.o_list_number.text-danger");
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

            await toggleFilterMenu(target);
            await toggleMenuItem(target, "Empty List");
            assert.containsOnce(target, ".o_view_nocontent");

            await click(target, ".o_view_nocontent");
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
            noContentHelp: markup('<p class="hello">click to add a partner</p>'),
        });
        assert.containsOnce(target, ".o_view_nocontent", "should display the no content helper");
        assert.containsNone(target, ".o_list_view table", "should not have a table in the dom");
        assert.deepEqual(
            [...target.querySelectorAll(".o_view_nocontent p.hello")].map((el) => el.textContent),
            ["click to add a partner"]
        );

        serverData.models.foo.records = records;
        await reloadListView(target);

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "should not display the no content helper"
        );
        assert.containsOnce(target, ".o_list_view table", "should have a table in the dom");
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
            noContentHelp: markup('<p class="hello">click to add a partner</p>'),
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
        assert.containsOnce(target, ".o_nocontent_help .hello");

        // Check list sample data
        const firstRow = target.querySelector(".o_data_row");
        const cells = firstRow.querySelectorAll(":scope > .o_data_cell");
        assert.strictEqual(
            cells[0].innerText.trim(),
            "",
            "Char field should yield an empty element"
        );
        assert.containsOnce(cells[1], ".custom-checkbox", "Boolean field has been instantiated");
        assert.notOk(isNaN(cells[2].innerText.trim()), "Intger value is a number");
        assert.ok(cells[3].innerText.trim(), "Many2one field is a string");

        const firstM2MTag = cells[4].querySelector(":scope span.o_tag_badge_text").innerText.trim();
        assert.ok(firstM2MTag.length > 0, "Many2many contains at least one string tag");

        assert.ok(
            /\d{2}\/\d{2}\/\d{4}/.test(cells[5].innerText.trim()),
            "Date field should have the right format"
        );
        assert.ok(
            /\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}/.test(cells[6].innerText.trim()),
            "Datetime field should have the right format"
        );

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "empty");
        await toggleMenuItem(target, "False Domain");
        assert.doesNotHaveClass(
            target.querySelector(".o_list_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsNone(target, ".o_list_table");
        assert.containsOnce(target, ".o_nocontent_help .hello");

        await toggleMenuItem(target, "False Domain");
        await toggleMenuItem(target, "True Domain");
        assert.doesNotHaveClass(
            target.querySelector(".o_list_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 4);
        assert.containsNone(target, ".o_nocontent_help .hello");
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
            help: markup('<p class="hello">click to add a partner</p>'),
        });
        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 10);
        assert.containsOnce(target, ".o_nocontent_help .hello");

        const textContent = target.querySelector(".o_list_view").textContent;
        await click(target, ".o_cp_switch_buttons .o_list");
        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_list_table");
        assert.containsN(target, ".o_data_row", 10);
        assert.containsOnce(target, ".o_nocontent_help .hello");
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
        assert.hasClass(target.querySelectorAll(".o_data_row"), "o_sample_data_disabled");
        assert.containsN(target, "th", 2, "should have 2 th, 1 for selector and 1 for foo");
        assert.containsOnce(target, "table .o_optional_columns_dropdown");

        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");

        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");

        assert.hasClass(target.querySelector(".o_list_view .o_content"), "o_view_sample_data");
        assert.ok(target.querySelectorAll(".o_data_row").length > 0);
        assert.hasClass(target.querySelector(".o_data_row"), "o_sample_data_disabled");
        assert.containsN(target, "th", 3);
    });

    QUnit.skipWOWL("empty list with sample data: keyboard navigation", async function (assert) {
        await makeView({
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
        assert.hasClass(target.querySelector(".o_data_row"), "o_sample_data_disabled");
        assert.hasClass(target.querySelector(".o_list_table > tfoot"), "o_sample_data_disabled");
        assert.hasClass(
            target.querySelector(".o_list_table > thead .o_list_record_selector"),
            "o_sample_data_disabled"
        );
        assert.containsNone(target.querySelector(".o_list_renderer"), 'input:not([tabindex="-1"])');

        // From search bar
        assert.hasClass(document.activeElement, "o_searchview_input");

        await testUtils.fields.triggerKeydown(document.activeElement, "down");

        assert.hasClass(document.activeElement, "o_searchview_input");

        // From 'Create' button
        document.querySelector(".btn.o_list_button_add").focus();

        assert.hasClass(document.activeElement, "o_list_button_add");

        await testUtils.fields.triggerKeydown(document.activeElement, "down");

        assert.hasClass(document.activeElement, "o_list_button_add");

        await testUtils.fields.triggerKeydown(document.activeElement, "tab");

        assert.containsNone(document.body, ".o-tooltip--string");

        // From column header
        target.querySelector(':scope th[data-name="foo"]').focus();

        assert.ok(document.activeElement.dataset.name === "foo");

        await testUtils.fields.triggerKeydown(document.activeElement, "down");

        assert.ok(document.activeElement.dataset.name === "foo");
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

        await toggleFilterMenu(target);
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
            assert.containsNone(target, ".o_list_table");
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
            await click(target.querySelector(".btn.o_list_button_add"));
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsOnce(target, ".o_data_row");

            // Discard temporary record
            await click(target.querySelector(".btn.o_list_button_discard"));

            // Final state: there should be no table, but the no content helper
            assert.doesNotHaveClass(
                target.querySelector(".o_list_view .o_content"),
                "o_view_sample_data"
            );
            assert.containsNone(target, ".o_list_table");
            assert.containsOnce(target, ".o_nocontent_help");
        }
    );

    QUnit.test(
        "empty editable list with sample data: create and delete record",
        async function (assert) {
            assert.expect(13);

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
            await click(target.querySelector(".btn.o_list_button_add"));
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
            assert.containsNone(target, ".o_list_table");
            assert.containsOnce(target, ".o_nocontent_help");
        }
    );

    QUnit.test("groupby node with a button", async function (assert) {
        assert.expect(17);

        serverData.models.foo.fields.currency_id.sortable = true;
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                '<button string="Button 1" type="object" name="button_method"/>' +
                "</groupby>" +
                "</tree>",
            mockRPC: function (route, args) {
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
        assert.expect(15);
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree>
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <field name="position"/>
                        <button string="Button 1" type="object" name="button_method" attrs='{"invisible": [("position", "=", "after")]}'/>
                    </groupby>
                </tree>`,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === "read" && args.model === "res_currency") {
                    assert.deepEqual(args.args, [[1, 2], ["position"]]);
                }
            },
            groupBy: ["currency_id"],
        });

        assert.verifySteps(["get_views", "web_read_group", "read"]);
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
                        <button string="Button 1" type="object" name="button_method" attrs='{"invisible": [("m2o", "=", false)]}'/>
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

            assert.verifySteps(["get_views", "web_read_group", "read"]);
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
                        <button string="Button 1" type="object" name="button_method" attrs='{"invisible": [("position", "=", "after")]}'/>
                    </groupby>
                </tree>`,
            groupBy: ["currency_id"],
        });

        assert.containsOnce(target, ".o_group_header button");

        await reloadListView(target);
        assert.containsOnce(target, ".o_group_header button");
    });

    QUnit.skipWOWL("editable list view with groupby node and modifiers", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree expand="1" editable="bottom">
                    <field name="foo"/>
                    <groupby name="currency_id">
                        <field name="position"/>
                        <button string="Button 1" type="object" name="button_method" attrs='{"invisible": [("position", "=", "after")]}'/>
                    </groupby>
                </tree>`,
            groupBy: ["currency_id"],
        });

        assert.doesNotHaveClass(
            $(target).find(".o_data_row:first"),
            "o_selected_row",
            "first row should be in readonly mode"
        );

        await click($(target).find(".o_data_row:first .o_data_cell"));
        assert.hasClass(
            $(target).find(".o_data_row:first"),
            "o_selected_row",
            "the row should be in edit mode"
        );

        await testUtils.fields.triggerKeydown($(document.activeElement), "escape");
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
            arch: `<tree editable="bottom" expand="1">
                    <field name="foo"/>
                    <field name="currency_id"/>
                    <groupby name="currency_id">
                        <field name="position" invisible="1"/>
                    </groupby>
                </tree>`,
            groupBy: ["currency_id"],
            mockRPC: function (route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(
                        args.args[3],
                        {
                            foo: "1",
                            currency_id: "",
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
                if (args.method === "create") {
                    assert.step("create");
                }
            },
        });

        assert.containsOnce(
            target,
            ".o_view_nocontent",
            "should have a no content helper displayed"
        );
        assert.containsNone(
            target,
            "div.table-responsive",
            "should not have a div.table-responsive"
        );
        assert.containsNone(target, "table", "should not have rendered a table");

        await click(target.querySelector(".o_list_button_add"));
        assert.containsNone(
            target,
            ".o_view_nocontent",
            "should not have a no content helper displayed"
        );
        assert.containsOnce(target, "table", "should have rendered a table");
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
            true,
            "buttons should be disabled while the record is not yet created"
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
        assert.verifySteps(["create"]);
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
        });

        await click(target.querySelector(".o_list_button_add"));

        assert.containsOnce(
            target,
            "table button i.o_button_icon.fa-phone",
            "should have rendered a button"
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
        assert.containsOnce(target, ".o_list_button_discard");

        await click(target.querySelector(".o_list_button_discard"));

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
                if (args.method === "create") {
                    assert.step("create");
                }
            },
        });

        await click(target.querySelector(".o_list_button_add"));
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        await click(target.querySelector(".o_list_renderer"));
        assert.verifySteps(["create"]);

        await click(target.querySelector(".o_list_button_add"));
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        await click(target.querySelector("tfoot"));
        assert.verifySteps(["create"]);

        await click(target.querySelector(".o_list_button_add"));
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        await click(target.querySelectorAll("tbody tr")[2].querySelector(".o_data_cell"));
        assert.verifySteps(["create"]);
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
            mockRPC: function (route) {
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
                    <button string="a button" name="button_action" icon="fa-car" type="object" attrs="{'invisible': [('id','=', 1)]}"/>
                    <field name="int_field"/>
                    <field name="qux"/>
                    <field name="foo" attrs="{'invisible': [('id','=', 1)]}"/>
                </tree>`,
        });

        assert.strictEqual(target.querySelectorAll(".o_field_cell")[2].innerHTML, "");
        assert.strictEqual(target.querySelector(".o_data_cell.o_list_button").innerHTML, "");

        // edit first row
        await click(target.querySelector(".o_field_cell"));
        assert.strictEqual(target.querySelectorAll(".o_field_cell")[2].innerHTML, "");
        assert.strictEqual(target.querySelector(".o_data_cell.o_list_button").innerHTML, "");

        await click(target.querySelector(".o_list_button_discard"));

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
                    <field name="currency_id" invisible="1"/>
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
        assert.expect(9);

        serverData.models.foo.fields.foo.readonly = true;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.containsN(target, ".o_field_widget[name=foo].o_readonly_modifier", 4);

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

    QUnit.skipWOWL("list view with nested groups", async function (assert) {
        assert.expect(42);

        serverData.models.foo.records.push({ id: 5, foo: "blip", int_field: -7, m2o: 1 });
        serverData.models.foo.records.push({ id: 6, foo: "blip", int_field: 5, m2o: 2 });

        var nbRPCs = { readGroup: 0, searchRead: 0 };
        var envIDs = []; // the ids that should be in the environment during this test

        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ["m2o", "foo"],
            mockRPC: function (route, args) {
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
                } else if (route === "/web/dataset/search_read") {
                    // called twice (once when opening the group, once when sorting)
                    assert.deepEqual(
                        args.domain,
                        [
                            ["foo", "=", "blip"],
                            ["m2o", "=", 1],
                        ],
                        "nested search_read should be called with correct domain"
                    );
                    nbRPCs.searchRead++;
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(
                        event.data.res_id,
                        4,
                        "'switch_view' event has been triggered"
                    );
                },
            },
        });

        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        // basic rendering tests
        assert.containsOnce(target, "tbody", "there should be 1 tbody");
        assert.containsN(target, ".o_group_header", 2, "should contain 2 groups at first level");
        assert.strictEqual(
            $(target).find(".o_group_name:first").text(),
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
            $(target).find(".o_group_name:first span").css("padding-left"),
            "2px",
            "groups of level 1 should have a 2px padding-left"
        );
        assert.strictEqual(
            $(target).find(".o_group_header:first td:last").text(),
            "16",
            "group aggregates are correctly displayed"
        );

        // open the first group
        nbRPCs = { readGroup: 0, searchRead: 0 };
        await click($(target).find(".o_group_header:first"));
        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        var $openGroup = $(target).find("tbody:nth(1)");
        assert.strictEqual(
            $(target).find(".o_group_name:first").text(),
            "Value 1 (4)",
            "group should have correct name and count (of records, not inner subgroups)"
        );
        assert.containsN(target, "tbody", 3, "there should be 3 tbodys");
        assert.containsOnce(
            target,
            ".o_group_name:first .fa-caret-down",
            "the carret of open groups should be down"
        );
        assert.strictEqual(
            $openGroup.find(".o_group_header").length,
            3,
            "open group should contain 3 groups"
        );
        assert.strictEqual(
            $openGroup.find(".o_group_name:nth(2)").text(),
            "blip (2)",
            "group should have correct name and count"
        );
        assert.strictEqual(
            $openGroup.find(".o_group_name:nth(2) span").css("padding-left"),
            "22px",
            "groups of level 2 should have a 22px padding-left"
        );
        assert.strictEqual(
            $openGroup.find(".o_group_header:nth(2) td:last").text(),
            "-11",
            "inner group aggregates are correctly displayed"
        );

        // open subgroup
        nbRPCs = { readGroup: 0, searchRead: 0 };
        envIDs = [4, 5]; // the opened subgroup contains these two records
        await click($openGroup.find(".o_group_header:nth(2)"));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        var $openSubGroup = $(target).find("tbody:nth(2)");
        assert.containsN(target, "tbody", 4, "there should be 4 tbodys");
        assert.strictEqual(
            $openSubGroup.find(".o_data_row").length,
            2,
            "open subgroup should contain 2 data rows"
        );
        assert.strictEqual(
            $openSubGroup.find(".o_data_row:first td:last").text(),
            "-4",
            "first record in open subgroup should be res_id 4 (with int_field -4)"
        );

        // open a record (should trigger event 'open_record')
        await click($openSubGroup.find(".o_data_row:first"));

        // sort by int_field (ASC) and check that open groups are still open
        nbRPCs = { readGroup: 0, searchRead: 0 };
        envIDs = [5, 4]; // order of the records changed
        await click($(target).find("thead th:last"));
        assert.strictEqual(nbRPCs.readGroup, 2, "should have done two read_groups");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        $openSubGroup = $(target).find("tbody:nth(2)");
        assert.containsN(target, "tbody", 4, "there should be 4 tbodys");
        assert.strictEqual(
            $openSubGroup.find(".o_data_row").length,
            2,
            "open subgroup should contain 2 data rows"
        );
        assert.strictEqual(
            $openSubGroup.find(".o_data_row:first td:last").text(),
            "-7",
            "first record in open subgroup should be res_id 5 (with int_field -7)"
        );

        // close first level group
        nbRPCs = { readGroup: 0, searchRead: 0 };
        envIDs = []; // the group being closed, there is no more record in the environment
        await click($(target).find(".o_group_header:nth(1)"));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        assert.containsOnce(target, "tbody", "there should be 1 tbody");
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
        assert.expect(6);
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
            target.querySelector(".o_group_header th > nav"),
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
        assert.containsOnce(target, ".o_list_button_add");
        assert.containsNone(target, ".o_list_button_discard");
        assert.containsN(target, ".o_list_record_selector input:enabled", 5);
        await click(target.querySelector(".o_list_button_add"));
        assert.containsNone(target, ".o_list_button_add");
        assert.containsOnce(target, ".o_list_button_discard");
        assert.containsNone(target, ".o_list_record_selector input:enabled");
        await click(target.querySelector(".o_list_button_discard"));
        assert.containsN(target, "tr.o_data_row", 4, "should still have 4 records");
        assert.containsOnce(target, ".o_list_button_add");
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
                        <field name="foo" attrs="{'invisible': [['bar', '=', True]]}"/>
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
            await click(target.querySelector(".o_list_button_save"));

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
                        <field name="foo" attrs="{'readonly': [['bar', '=', True]]}"/>
                        <field name="bar"/>
                    </tree>`,
            });

            assert.containsN(target, "tbody td .o_readonly_modifier", 3);

            // Make first line editable
            await click(target.querySelector(".o_field_cell"));
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] span");

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] input");
            assert.containsN(target, "tbody td .o_readonly_modifier", 2);

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] span");
            assert.containsN(target, "tbody td .o_readonly_modifier", 3);

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.containsOnce(target, ".o_selected_row .o_field_widget[name=foo] input");
            assert.containsN(target, "tbody td .o_readonly_modifier", 2);

            // Click outside to leave edition mode
            await click(target);
            assert.containsN(target, "tbody td .o_readonly_modifier", 2);
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
                        <field name="foo" attrs="{'required': [['bar', '=', True]]}"/>
                        <field name="bar"/>
                    </tree>`,
            });

            assert.containsN(target, "tbody td .o_required_modifier", 3);

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
            assert.containsN(target, "tbody td .o_required_modifier", 2);

            await click(target.querySelector(".o_field_widget[name=bar] input"));
            assert.hasClass(
                target.querySelector(".o_selected_row .o_field_widget[name=foo]"),
                "o_required_modifier"
            );
            assert.containsN(target, "tbody td .o_required_modifier", 3);

            // Reswitch the field to required and save the row
            await click(target.querySelector(".o_field_widget[name=bar] input"));
            await click(target.querySelector(".o_list_button_save"));

            assert.containsN(target, "tbody td .o_required_modifier", 2);
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
                        [5],
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
                arch: `<form>
                    <field name="o2m">
                        <tree editable="top">
                            <field name="display_name" attrs="{'invisible': [('stage', '=', 'open')]}"/>
                            <field name="stage"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
            });
            await clickEdit(target);
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
        assert.expect(4);

        var warnings = 0;
        const list = await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="bottom">' +
                '<field name="foo" required="1"/>' +
                '<field name="bar"/>' +
                "</tree>",
        });
        patchWithCleanup(list.env.services.notification, {
            add: (message, { type }) => {
                if (type === "danger") {
                    warnings++;
                }
            },
        });

        // Start first line edition
        const rows = target.querySelectorAll(".o_data_row");
        const firstRowFoo = rows[0].querySelector(".o_data_cell [name=foo]");
        await click(firstRowFoo);

        // Remove required foo field value
        await editInput(firstRowFoo, "input", "");

        // Try starting other line edition
        const secondRowFoo = rows[1].querySelector(".o_data_cell [name=foo]");
        await click(secondRowFoo);
        assert.hasClass(
            rows[0],
            "o_selected_row",
            "first line should still be in edition as invalid"
        );
        assert.containsOnce(target, ".o_selected_row", "no other line should be in edition");
        assert.containsOnce(
            rows[0],
            ".o_field_invalid input",
            "the required field should be marked as invalid"
        );
        assert.strictEqual(warnings, 1, "a warning should have been displayed");
    });

    QUnit.skipWOWL("open a virtual id", async function (assert) {
        assert.expect(1);

        const list = await makeView({
            type: "list",
            resModel: "event",
            serverData,
            arch: '<tree><field name="name"/></tree>',
        });
        patchWithCleanup(list.env.services.action, {
            switchView: async (event) => {
                assert.deepEqual(
                    _.pick(event.data, "mode", "model", "res_id", "view_type"),
                    {
                        mode: "readonly",
                        model: "event",
                        res_id: "2-20170808020000",
                        view_type: "form",
                    },
                    "should trigger a switch_view event to the form view for the record virtual id"
                );
            },
        });
        await click(target.querySelector(".o_data_row .o_data_cell"));
    });

    QUnit.skipWOWL("pressing enter on last line of editable list view", async function (assert) {
        assert.expect(7);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        // click on 3rd line
        await click($(target).find("td:contains(gnap)"));
        assert.hasClass(
            $(target).find("tr.o_data_row:eq(2)"),
            "o_selected_row",
            "3rd row should be selected"
        );

        // press enter in input
        await testUtils.fields.triggerKeydown(
            $(target).find('tr.o_selected_row input[name="foo"]'),
            "enter"
        );
        assert.hasClass(
            $(target).find("tr.o_data_row:eq(3)"),
            "o_selected_row",
            "4rd row should be selected"
        );
        assert.doesNotHaveClass(
            $(target).find("tr.o_data_row:eq(2)"),
            "o_selected_row",
            "3rd row should no longer be selected"
        );

        // press enter on last row
        await testUtils.fields.triggerKeydown(
            $(target).find('tr.o_selected_row input[name="foo"]'),
            "enter"
        );
        assert.containsN(target, "tr.o_data_row", 5, "should have created a 5th row");

        assert.verifySteps(["/web/dataset/search_read", "/web/dataset/call_kw/foo/onchange"]);
    });

    QUnit.skipWOWL("pressing tab on last cell of editable list view", async function (assert) {
        assert.expect(9);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        await click($(target).find("td:contains(blip)").last());
        assert.strictEqual(
            document.activeElement.name,
            "foo",
            "focus should be on an input with name = foo"
        );

        //it will not create a new line unless a modification is made
        document.activeElement.value = "blip-changed";
        $(document.activeElement).trigger({ type: "change" });

        await testUtils.fields.triggerKeydown(
            $(target).find('tr.o_selected_row input[name="foo"]'),
            "tab"
        );
        assert.strictEqual(
            document.activeElement.name,
            "int_field",
            "focus should be on an input with name = int_field"
        );

        await testUtils.fields.triggerKeydown(
            $(target).find('tr.o_selected_row input[name="foo"]'),
            "tab"
        );
        assert.hasClass(
            $(target).find("tr.o_data_row:eq(4)"),
            "o_selected_row",
            "5th row should be selected"
        );
        assert.strictEqual(
            document.activeElement.name,
            "foo",
            "focus should be on an input with name = foo"
        );

        assert.verifySteps([
            "/web/dataset/search_read",
            "/web/dataset/call_kw/foo/write",
            "/web/dataset/call_kw/foo/read",
            "/web/dataset/call_kw/foo/onchange",
        ]);
    });

    QUnit.skipWOWL(
        "navigation with tab and read completes after default_get",
        async function (assert) {
            assert.expect(8);

            var onchangeGetPromise = testUtils.makeTestPromise();
            var readPromise = testUtils.makeTestPromise();

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
                mockRPC: function (route, args) {
                    if (args.method) {
                        assert.step(args.method);
                    }
                    var result = this._super.apply(this, arguments);
                    if (args.method === "read") {
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

            await click($(target).find("td:contains(-4)").last());

            await editInput($(target).find('tr.o_selected_row input[name="int_field"]'), "1234");
            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="int_field"]'),
                "tab"
            );

            onchangeGetPromise.resolve();
            assert.containsN(target, "tbody tr.o_data_row", 4, "should have 4 data rows");

            readPromise.resolve();
            await testUtils.nextTick();
            assert.containsN(target, "tbody tr.o_data_row", 5, "should have 5 data rows");
            assert.strictEqual(
                $(target).find("td:contains(1234)").length,
                1,
                "should have a cell with new value"
            );

            // we trigger a tab to move to the second cell in the current row. this
            // operation requires that this.currentRow is properly set in the
            // list editable renderer.
            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "tab"
            );
            assert.hasClass(
                $(target).find("tr.o_data_row:eq(4)"),
                "o_selected_row",
                "5th row should be selected"
            );

            assert.verifySteps(["write", "read", "onchange"]);
        }
    );

    QUnit.skipWOWL("display toolbar", async function (assert) {
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
                            name: "Action partner",
                        },
                    ],
                },
            },
        });

        assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");

        await click(target.querySelector(".o_list_record_selector input"));

        await toggleActionMenu(target);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_cp_action_menus .dropdown-item")),
            ["Delete", "Action event"]
        );
    });

    QUnit.skipWOWL(
        "execute ActionMenus actions with correct params (single page)",
        async function (assert) {
            assert.expect(12);

            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree><field name="foo"/></tree>',
                toolbar: {
                    action: [
                        {
                            id: 44,
                            name: "Custom Action",
                            type: "ir.actions.server",
                        },
                    ],
                    print: [],
                },
                mockRPC: function (route, args) {
                    if (route === "/web/action/load") {
                        assert.step(JSON.stringify(args));
                        return Promise.resolve({});
                    }
                    return this._super(...arguments);
                },
                actionMenus: {},
            });

            assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");

            assert.containsN(target, ".o_data_row", 4);

            // select all records
            await click($(target).find("thead .o_list_record_selector input"));
            assert.containsN(target, ".o_list_record_selector input:checked", 5);

            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // unselect first record (will unselect the thead checkbox as well)
            await click($(target).find("tbody .o_list_record_selector:first input"));
            assert.containsN(target, ".o_list_record_selector input:checked", 3);
            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // add a domain and select first two records
            await list.reload({ domain: [["bar", "=", true]] });
            assert.containsN(target, ".o_data_row", 3);
            assert.containsNone(target, ".o_list_record_selector input:checked");

            await click($(target).find("tbody .o_list_record_selector:nth(0) input"));
            await click($(target).find("tbody .o_list_record_selector:nth(1) input"));
            assert.containsN(target, ".o_list_record_selector input:checked", 2);

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            assert.verifySteps([
                '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2,3,4],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"active_id":2,"active_ids":[2,3,4],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2],"active_model":"foo","active_domain":[["bar","=",true]]}}',
            ]);
        }
    );

    QUnit.skipWOWL(
        "execute ActionMenus actions with correct params (multi pages)",
        async function (assert) {
            assert.expect(13);

            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="2"><field name="foo"/></tree>',
                toolbar: {
                    action: [
                        {
                            id: 44,
                            name: "Custom Action",
                            type: "ir.actions.server",
                        },
                    ],
                    print: [],
                },
                mockRPC: function (route, args) {
                    if (route === "/web/action/load") {
                        assert.step(JSON.stringify(args));
                        return Promise.resolve({});
                    }
                    return this._super(...arguments);
                },
                actionMenus: {},
            });

            assert.containsNone(target, "div.o_control_panel .o_cp_action_menus");
            assert.containsN(target, ".o_data_row", 2);

            // select all records
            await click($(target).find("thead .o_list_record_selector input"));
            assert.containsN(target, ".o_list_record_selector input:checked", 3);
            assert.containsOnce(target, ".o_list_selection_box .o_list_select_domain");
            assert.containsOnce(target, "div.o_control_panel .o_cp_action_menus");

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // select all domain
            await click($(target).find(".o_list_selection_box .o_list_select_domain"));
            assert.containsN(target, ".o_list_record_selector input:checked", 3);

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            // add a domain
            await list.reload({ domain: [["bar", "=", true]] });
            assert.containsNone(target, ".o_list_selection_box .o_list_select_domain");

            // select all domain
            await click($(target).find("thead .o_list_record_selector input"));
            await click($(target).find(".o_list_selection_box .o_list_select_domain"));
            assert.containsN(target, ".o_list_record_selector input:checked", 3);
            assert.containsNone(target, ".o_list_selection_box .o_list_select_domain");

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Custom Action");

            assert.verifySteps([
                '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2,3,4],"active_model":"foo","active_domain":[]}}',
                '{"action_id":44,"context":{"active_id":1,"active_ids":[1,2,3],"active_model":"foo","active_domain":[["bar","=",true]]}}',
            ]);
        }
    );

    QUnit.skipWOWL("edit list line after line deletion", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        await click($(target).find(".o_data_row:nth(2) > td:not(.o_list_record_selector)").first());
        assert.ok(
            $(target).find(".o_data_row:nth(2)").is(".o_selected_row"),
            "third row should be in edition"
        );
        await click(target.querySelector(".o_list_button_discard"));
        await click(target.querySelector(".o_list_button_add"));
        assert.ok(
            $(target).find(".o_data_row:nth(0)").is(".o_selected_row"),
            "first row should be in edition (creation)"
        );
        await click(target.querySelector(".o_list_button_discard"));
        assert.containsNone(target, ".o_selected_row", "no row should be selected");
        await click($(target).find(".o_data_row:nth(2) > td:not(.o_list_record_selector)").first());
        assert.ok(
            $(target).find(".o_data_row:nth(2)").is(".o_selected_row"),
            "third row should be in edition"
        );
        assert.containsOnce(target, ".o_selected_row", "no other row should be selected");
    });

    QUnit.skipWOWL(
        "pressing TAB in editable list with several fields [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(6);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                    "</tree>",
            });

            await click($(target).find(".o_data_cell:first"));
            assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:first .o_data_cell:first input")[0]
            );

            // // Press 'Tab' -> should go to next cell (still in first row)
            await testUtils.fields.triggerKeydown(
                $(target).find('.o_selected_row input[name="foo"]'),
                "tab"
            );
            assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:first .o_data_cell:last input")[0]
            );

            // // Press 'Tab' -> should go to next line (first cell)
            await testUtils.fields.triggerKeydown(
                $(target).find('.o_selected_row input[name="int_field"]'),
                "tab"
            );
            assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(1) .o_data_cell:first input")[0]
            );
        }
    );

    QUnit.skipWOWL(
        "pressing SHIFT-TAB in editable list with several fields [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(6);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                    "</tree>",
            });

            await click($(target).find(".o_data_row:nth(2) .o_data_cell:nth(1)"));
            assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(2) .o_data_cell:last input")[0]
            );

            // Press 'shift-Tab' -> should go to previous line (last cell)
            $(target)
                .find("tr.o_selected_row input")
                .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
            await testUtils.nextTick();
            assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(2) .o_data_cell:first input")[0]
            );

            // Press 'shift-Tab' -> should go to previous cell
            $(target)
                .find("tr.o_selected_row input")
                .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
            await testUtils.nextTick();
            assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(1) .o_data_cell:last input")[0]
            );
        }
    );

    QUnit.skipWOWL(
        "navigation with tab and readonly field (no modification)",
        async function (assert) {
            // This test makes sure that if we have 2 cells in a row, the first in
            // edit mode, and the second one readonly, then if we press TAB when the
            // focus is on the first, then the focus skip the readonly cells and
            // directly goes to the next line instead.
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
            });

            // click on first td and press TAB
            await click($(target).find("td:contains(yop)").last());

            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "tab"
            );

            assert.hasClass(
                $(target).find("tr.o_data_row:eq(1)"),
                "o_selected_row",
                "2nd row should be selected"
            );

            // we do it again. This was broken because the this.currentRow variable
            // was not properly set, and the second TAB could cause a crash.
            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "tab"
            );
            assert.hasClass(
                $(target).find("tr.o_data_row:eq(2)"),
                "o_selected_row",
                "3rd row should be selected"
            );
        }
    );

    QUnit.skipWOWL(
        "navigation with tab and readonly field (with modification)",
        async function (assert) {
            // This test makes sure that if we have 2 cells in a row, the first in
            // edit mode, and the second one readonly, then if we press TAB when the
            // focus is on the first, then the focus skips the readonly cells and
            // directly goes to the next line instead.
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
            });

            // click on first td and press TAB
            await click($(target).find("td:contains(yop)"));

            //modity the cell content
            testUtils.fields.editAndTrigger($(document.activeElement), "blip-changed", ["change"]);

            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "tab"
            );

            assert.hasClass(
                $(target).find("tr.o_data_row:eq(1)"),
                "o_selected_row",
                "2nd row should be selected"
            );

            // we do it again. This was broken because the this.currentRow variable
            // was not properly set, and the second TAB could cause a crash.
            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "tab"
            );
            assert.hasClass(
                $(target).find("tr.o_data_row:eq(2)"),
                "o_selected_row",
                "3rd row should be selected"
            );
        }
    );

    QUnit.skipWOWL('navigation with tab on a list with create="0"', async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="bottom" create="0">' + '<field name="display_name"/>' + "</tree>",
        });

        assert.containsN(target, ".o_data_row", 4, "the list should contain 4 rows");

        await click($(target).find(".o_data_row:nth(2) .o_data_cell:first"));
        assert.hasClass(
            $(target).find(".o_data_row:nth(2)"),
            "o_selected_row",
            "third row should be in edition"
        );

        // Press 'Tab' -> should go to next line
        // add a value in the cell because the Tab on an empty first cell would activate the next widget in the view
        await editInput($(target).find(".o_selected_row input").eq(1), 11);
        await testUtils.fields.triggerKeydown(
            $(target).find('.o_selected_row input[name="display_name"]'),
            "tab"
        );
        assert.hasClass(
            $(target).find(".o_data_row:nth(3)"),
            "o_selected_row",
            "fourth row should be in edition"
        );

        // Press 'Tab' -> should go back to first line as the create action isn't available
        await editInput($(target).find(".o_selected_row input").eq(1), 11);
        await testUtils.fields.triggerKeydown(
            $(target).find('.o_selected_row input[name="display_name"]'),
            "tab"
        );
        assert.hasClass(
            $(target).find(".o_data_row:first"),
            "o_selected_row",
            "first row should be in edition"
        );
    });

    QUnit.skipWOWL(
        'navigation with tab on a one2many list with create="0"',
        async function (assert) {
            assert.expect(4);

            serverData.models.foo.records[0].o2m = [1, 2];
            var form = await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                arch:
                    "<form><sheet>" +
                    '<field name="o2m">' +
                    '<tree editable="bottom" create="0">' +
                    '<field name="display_name"/>' +
                    "</tree>" +
                    "</field>" +
                    '<field name="foo"/>' +
                    "</sheet></form>",
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.containsN(
                form,
                ".o_field_widget[name=o2m] .o_data_row",
                2,
                "there should be two records in the many2many"
            );

            await click(form.$(".o_field_widget[name=o2m] .o_data_cell:first"));
            assert.hasClass(
                form.$(".o_field_widget[name=o2m] .o_data_row:first"),
                "o_selected_row",
                "first row should be in edition"
            );

            // Press 'Tab' -> should go to next line
            await testUtils.fields.triggerKeydown(
                form.$(".o_field_widget[name=o2m] .o_selected_row input"),
                "tab"
            );
            await testUtils.nextTick(); // wait for discard
            assert.hasClass(
                form.$(".o_field_widget[name=o2m] .o_data_row:nth(1)"),
                "o_selected_row",
                "second row should be in edition"
            );

            // Press 'Tab' -> should get out of the one to many and go to the next field of the form
            await testUtils.fields.triggerKeydown(
                form.$(".o_field_widget[name=o2m] .o_selected_row input"),
                "tab"
            );
            // use of owlCompatibilityExtraNextTick because the x2many control panel is updated twice
            await testUtils.owlCompatibilityExtraNextTick();
            assert.strictEqual(
                document.activeElement,
                form.$('input[name="foo"]')[0],
                "the next field should be selected"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "edition, then navigation with tab (with a readonly field)",
        async function (assert) {
            // This test makes sure that if we have 2 cells in a row, the first in
            // edit mode, and the second one readonly, then if we edit and press TAB,
            // (before debounce), the save operation is properly done (before
            // selecting the next row)
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
                mockRPC: function (route, args) {
                    if (args.method) {
                        assert.step(args.method);
                    }
                    return this._super.apply(this, arguments);
                },
                fieldDebounce: 1,
            });

            // click on first td and press TAB
            await click($(target).find("td:contains(yop)"));
            await testUtils.fields.editSelect(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "new value"
            );
            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "tab"
            );

            assert.strictEqual(
                $(target).find("tbody tr:first td:contains(new value)").length,
                1,
                "should have the new value visible in dom"
            );
            assert.verifySteps(["write", "read"]);
        }
    );

    QUnit.skipWOWL(
        "edition, then navigation with tab (with a readonly field and onchange)",
        async function (assert) {
            // This test makes sure that if we have a read-only cell in a row, in
            // case the keyboard navigation move over it and there a unsaved changes
            // (which will trigger an onchange), the focus of the next activable
            // field will not crash
            assert.expect(4);

            serverData.models.bar.onchanges = {
                o2m: function () {},
            };
            serverData.models.bar.fields.o2m = {
                string: "O2M field",
                type: "one2many",
                relation: "foo",
            };
            serverData.models.bar.records[0].o2m = [1, 4];

            var form = await makeView({
                type: "form",
                model: "bar",
                resId: 1,
                serverData,
                arch:
                    "<form>" +
                    "<group>" +
                    '<field name="display_name"/>' +
                    '<field name="o2m">' +
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="date" readonly="1"/>' +
                    '<field name="int_field"/>' +
                    "</tree>" +
                    "</field>" +
                    "</group>" +
                    "</form>",
                mockRPC: function (route, args) {
                    if (args.method === "onchange") {
                        assert.step(args.method + ":" + args.model);
                    }
                    return this._super.apply(this, arguments);
                },
                fieldDebounce: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            var jq_evspecial_focus_trigger = $.event.special.focus.trigger;
            // As KeyboardEvent will be triggered by JS and not from the
            // User-Agent itself, the focus event will not trigger default
            // action (event not being trusted), we need to manually trigger
            // 'change' event on the currently focused element
            $.event.special.focus.trigger = function () {
                if (this !== document.activeElement && this.focus) {
                    var activeElement = document.activeElement;
                    this.focus();
                    $(activeElement).trigger("change");
                }
            };

            // editable target, click on first td and press TAB
            await click(form.$(".o_data_cell:contains(yop)"));
            assert.strictEqual(
                document.activeElement,
                form.$('tr.o_selected_row input[name="foo"]')[0],
                "focus should be on an input with name = foo"
            );
            await editInput(form.$('tr.o_selected_row input[name="foo"]'), "new value");
            var tabEvent = $.Event("keydown", { which: $.ui.keyCode.TAB });
            await testUtils.dom.triggerEvents(form.$('tr.o_selected_row input[name="foo"]'), [
                tabEvent,
            ]);
            assert.strictEqual(
                document.activeElement,
                form.$('tr.o_selected_row input[name="int_field"]')[0],
                "focus should be on an input with name = int_field"
            );

            // Restore origin jQuery special trigger for 'focus'
            $.event.special.focus.trigger = jq_evspecial_focus_trigger;

            assert.verifySteps(["onchange:bar"], "onchange method should have been called");
            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "pressing SHIFT-TAB in editable list with a readonly field [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field" readonly="1"/>' +
                    '<field name="qux"/>' +
                    "</tree>",
            });

            // start on 'qux', line 3
            await click($(target).find(".o_data_row:nth(2) .o_data_cell:nth(2)"));
            assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(2) .o_data_cell input[name=qux]")[0]
            );

            // Press 'shift-Tab' -> should go to first cell (same line)
            $(document.activeElement).trigger({
                type: "keydown",
                which: $.ui.keyCode.TAB,
                shiftKey: true,
            });
            await testUtils.nextTick();
            assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(2) .o_data_cell input[name=foo]")[0]
            );
        }
    );

    QUnit.skipWOWL(
        "pressing SHIFT-TAB in editable list with a readonly field in first column [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="int_field" readonly="1"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                    "</tree>",
            });

            // start on 'foo', line 3
            await click($(target).find(".o_data_row:nth(2) .o_data_cell:nth(1)"));
            assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(2) .o_data_cell input[name=foo]")[0]
            );

            // Press 'shift-Tab' -> should go to previous line (last cell)
            $(document.activeElement).trigger({
                type: "keydown",
                which: $.ui.keyCode.TAB,
                shiftKey: true,
            });
            await testUtils.nextTick();
            assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(1) .o_data_cell input[name=qux]")[0]
            );
        }
    );

    QUnit.skipWOWL(
        "pressing SHIFT-TAB in editable list with a readonly field in last column [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux" readonly="1"/>' +
                    "</tree>",
            });

            // start on 'int_field', line 3
            await click($(target).find(".o_data_row:nth(2) .o_data_cell:first"));
            assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(2) .o_data_cell input[name=int_field]")[0]
            );

            // Press 'shift-Tab' -> should go to previous line ('foo' field)
            $(document.activeElement).trigger({
                type: "keydown",
                which: $.ui.keyCode.TAB,
                shiftKey: true,
            });
            await testUtils.nextTick();
            assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");
            assert.strictEqual(
                document.activeElement,
                $(target).find(".o_data_row:nth(1) .o_data_cell input[name=foo]")[0]
            );
        }
    );

    QUnit.skipWOWL(
        "skip invisible fields when navigating list view with TAB",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar" invisible="1"/>' +
                    '<field name="int_field"/>' +
                    "</tree>",
                resId: 1,
            });

            await click($(target).find("td:contains(gnap)"));
            assert.strictEqual(
                $(target).find('input[name="foo"]')[0],
                document.activeElement,
                "foo should be focused"
            );
            await testUtils.fields.triggerKeydown($(target).find('input[name="foo"]'), "tab");
            assert.strictEqual(
                $(target).find('input[name="int_field"]')[0],
                document.activeElement,
                "int_field should be focused"
            );
        }
    );

    QUnit.skipWOWL(
        "skip buttons when navigating list view with TAB (end)",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="kikou" string="Kikou" type="object"/>' +
                    "</tree>",
                resId: 1,
            });

            await click($(target).find("tbody tr:eq(2) td:eq(1)"));
            assert.strictEqual(
                $(target).find('tbody tr:eq(2) input[name="foo"]')[0],
                document.activeElement,
                "foo should be focused"
            );
            await testUtils.fields.triggerKeydown(
                $(target).find('tbody tr:eq(2) input[name="foo"]'),
                "tab"
            );
            assert.strictEqual(
                $(target).find('tbody tr:eq(3) input[name="foo"]')[0],
                document.activeElement,
                "next line should be selected"
            );
        }
    );

    QUnit.skipWOWL(
        "skip buttons when navigating list view with TAB (middle)",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    // Adding a button column makes conversions between column and field position trickier
                    '<button name="kikou" string="Kikou" type="object"/>' +
                    '<field name="foo"/>' +
                    '<button name="kikou" string="Kikou" type="object"/>' +
                    '<field name="int_field"/>' +
                    "</tree>",
                resId: 1,
            });

            await click($(target).find("tbody tr:eq(2) td:eq(2)"));
            assert.strictEqual(
                $(target).find('tbody tr:eq(2) input[name="foo"]')[0],
                document.activeElement,
                "foo should be focused"
            );
            await testUtils.fields.triggerKeydown(
                $(target).find('tbody tr:eq(2) input[name="foo"]'),
                "tab"
            );
            assert.strictEqual(
                $(target).find('tbody tr:eq(2) input[name="int_field"]')[0],
                document.activeElement,
                "int_field should be focused"
            );
        }
    );

    QUnit.skipWOWL("navigation: not moving down with keydown", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
        });

        await click($(target).find("td:contains(yop)"));
        assert.hasClass(
            $(target).find("tr.o_data_row:eq(0)"),
            "o_selected_row",
            "1st row should be selected"
        );
        await testUtils.fields.triggerKeydown(
            $(target).find('tr.o_selected_row input[name="foo"]'),
            "down"
        );
        assert.hasClass(
            $(target).find("tr.o_data_row:eq(0)"),
            "o_selected_row",
            "1st row should still be selected"
        );
    });

    QUnit.skipWOWL(
        "navigation: moving right with keydown from text field does not move the focus",
        async function (assert) {
            assert.expect(6);

            serverData.models.foo.fields.foo.type = "text";
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    "</tree>",
            });

            await click($(target).find("td:contains(yop)"));
            var textarea = $(target).find('textarea[name="foo"]')[0];
            assert.strictEqual(document.activeElement, textarea, "textarea should be focused");
            assert.strictEqual(
                textarea.selectionStart,
                0,
                "textarea selection start should be at the beginning"
            );
            assert.strictEqual(
                textarea.selectionEnd,
                3,
                "textarea selection end should be at the end"
            );
            textarea.selectionStart = 3; // Simulate browser keyboard right behavior (unselect)
            assert.strictEqual(
                document.activeElement,
                textarea,
                "textarea should still be focused"
            );
            assert.ok(
                textarea.selectionStart === 3 && textarea.selectionEnd === 3,
                "textarea value ('yop') should not be selected and cursor should be at the end"
            );
            await testUtils.fields.triggerKeydown($(textarea), "right");
            assert.strictEqual(
                document.activeElement,
                $(target).find('textarea[name="foo"]')[0],
                "next field (checkbox) should now be focused"
            );
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
            await click(target.querySelector(".o_list_button_discard"));
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
                    <field name="currency_id" invisible="1"/>
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

    QUnit.skipWOWL(
        "grouped list with another grouped list parent, click unfold",
        async function (assert) {
            assert.expect(3);
            serverData.models.bar.fields = {
                cornichon: { string: "cornichon", type: "char" },
            };

            var rec = serverData.models.bar.records[0];
            // create records to have the search more button
            var newRecs = [];
            for (var i = 0; i < 8; i++) {
                var newRec = _.extend({}, rec);
                newRec.id = 1 + i;
                newRec.cornichon = "extra fin";
                newRecs.push(newRec);
            }
            serverData.models.bar.records = newRecs;

            const list = await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo"/><field name="m2o"/></tree>',
                groupBy: ["bar"],
                archs: {
                    "bar,false,list": '<tree><field name="cornichon"/></tree>',
                    "bar,false,search":
                        "<search><filter context=\"{'group_by': 'cornichon'}\" string=\"cornichon\"/></search>",
                },
            });

            await list.update({ groupBy: [] });

            await clickFirst($(target).find(".o_data_cell"));

            await testUtils.fields.many2one.searchAndClickItem("m2o", { item: "Search More" });

            assert.containsOnce($("body"), ".modal-content");

            assert.containsNone(
                $("body"),
                ".modal-content .o_group_name",
                "list in modal not grouped"
            );

            await click($("body .modal-content button:contains(Group By)"));

            await click($("body .modal-content .o_menu_item:contains(cornichon)"));

            await click($("body .modal-content .o_group_header"));

            assert.containsOnce($("body"), ".modal-content .o_group_open");
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

    QUnit.skipWOWL("pressing ESC discard the current line changes", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        await click(target.querySelector(".o_list_button_add"));
        assert.containsN(target, "tr.o_data_row", 5, "should currently adding a 5th data row");

        await testUtils.fields.triggerKeydown($(target).find('input[name="foo"]'), "escape");
        assert.containsN(target, "tr.o_data_row", 4, "should have only 4 data row after escape");
        assert.containsNone(target, "tr.o_data_row.o_selected_row", "no rows should be selected");
        assert.ok(
            !target.querySelector(".o_list_button_save").is(":visible"),
            "should not have a visible save button"
        );
    });

    QUnit.skipWOWL(
        "pressing ESC discard the current line changes (with required)",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            });

            await click(target.querySelector(".o_list_button_add"));
            assert.containsN(target, "tr.o_data_row", 5, "should currently adding a 5th data row");

            await testUtils.fields.triggerKeydown($(target).find('input[name="foo"]'), "escape");
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
            assert.ok(
                !target.querySelector(".o_list_button_save").is(":visible"),
                "should not have a visible save button"
            );
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

    QUnit.skipWOWL("list with handle widget", async function (assert) {
        assert.expect(11);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" +
                '<field name="int_field" widget="handle"/>' +
                '<field name="amount" widget="float" digits="[5,0]"/>' +
                "</tree>",
            mockRPC: function (route, args) {
                if (route === "/web/dataset/resequence") {
                    assert.strictEqual(
                        args.offset,
                        -4,
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
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
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
        await testUtils.dom.dragAndDrop(
            $(target).find(".ui-sortable-handle").eq(3),
            $(target).find("tbody tr").first(),
            { position: "bottom" }
        );

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
    });

    QUnit.skipWOWL(
        "result of consecutive resequences is correctly sorted",
        async function (assert) {
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
            var moves = 0;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    "<tree>" +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="id"/>' +
                    "</tree>",
                mockRPC: function (route, args) {
                    if (route === "/web/dataset/resequence") {
                        if (moves === 0) {
                            assert.deepEqual(args, {
                                context: {},
                                model: "foo",
                                ids: [4, 3],
                                offset: 13,
                                field: "int_field",
                            });
                        }
                        if (moves === 1) {
                            assert.deepEqual(args, {
                                context: {},
                                model: "foo",
                                ids: [4, 2],
                                offset: 12,
                                field: "int_field",
                            });
                        }
                        if (moves === 2) {
                            assert.deepEqual(args, {
                                context: {},
                                model: "foo",
                                ids: [2, 4],
                                offset: 12,
                                field: "int_field",
                            });
                        }
                        if (moves === 3) {
                            assert.deepEqual(args, {
                                context: {},
                                model: "foo",
                                ids: [4, 2],
                                offset: 12,
                                field: "int_field",
                            });
                        }
                        moves += 1;
                    }
                    return this._super.apply(this, arguments);
                },
            });
            assert.strictEqual(
                $(target).find("tbody tr td.o_list_number").text(),
                "1234",
                "default should be sorted by id"
            );
            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(3),
                $(target).find("tbody tr").eq(2),
                { position: "top" }
            );
            assert.strictEqual(
                $(target).find("tbody tr td.o_list_number").text(),
                "1243",
                "the int_field (sequence) should have been correctly updated"
            );

            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(2),
                $(target).find("tbody tr").eq(1),
                { position: "top" }
            );
            assert.deepEqual(
                $(target).find("tbody tr td.o_list_number").text(),
                "1423",
                "the int_field (sequence) should have been correctly updated"
            );

            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(1),
                $(target).find("tbody tr").eq(3),
                { position: "top" }
            );
            assert.deepEqual(
                $(target).find("tbody tr td.o_list_number").text(),
                "1243",
                "the int_field (sequence) should have been correctly updated"
            );

            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(2),
                $(target).find("tbody tr").eq(1),
                { position: "top" }
            );
            assert.deepEqual(
                $(target).find("tbody tr td.o_list_number").text(),
                "1423",
                "the int_field (sequence) should have been correctly updated"
            );
        }
    );

    QUnit.skipWOWL("editable list with handle widget", async function (assert) {
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
            arch:
                '<tree editable="top" default_order="int_field">' +
                '<field name="int_field" widget="handle"/>' +
                '<field name="amount" widget="float" digits="[5,0]"/>' +
                "</tree>",
            mockRPC: function (route, args) {
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
                return this._super.apply(this, arguments);
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
        await testUtils.dom.dragAndDrop(
            $(target).find(".ui-sortable-handle").eq(3),
            $(target).find("tbody tr").first(),
            { position: "bottom" }
        );

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

        await click($(target).find("tbody tr:eq(1) td:last"));

        assert.strictEqual(
            $(target).find("tbody tr:eq(1) td:last input").val(),
            "0",
            "the edited record should be the good one"
        );
    });

    QUnit.skipWOWL(
        "editable target, handle widget locks and unlocks on sort",
        async function (assert) {
            assert.expect(6);

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
                arch:
                    '<tree editable="top" default_order="int_field">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float"/>' +
                    "</tree>",
            });

            assert.strictEqual(
                $(target).find('tbody span[name="amount"]').text(),
                "1200.00500.00300.000.00",
                "default should be sorted by int_field"
            );

            // Drag and drop the fourth line in second position
            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(3),
                $(target).find("tbody tr").first(),
                { position: "bottom" }
            );

            // Handle should be unlocked at this point
            assert.strictEqual(
                $(target).find('tbody span[name="amount"]').text(),
                "1200.000.00500.00300.00",
                "drag and drop should have succeeded, as the handle is unlocked"
            );

            // Sorting by a field different for int_field should lock the handle
            await click($(target).find(".o_column_sortable").eq(1));

            assert.strictEqual(
                $(target).find('tbody span[name="amount"]').text(),
                "0.00300.00500.001200.00",
                "should have been sorted by amount"
            );

            // Drag and drop the fourth line in second position (not)
            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(3),
                $(target).find("tbody tr").first(),
                { position: "bottom" }
            );

            assert.strictEqual(
                $(target).find('tbody span[name="amount"]').text(),
                "0.00300.00500.001200.00",
                "drag and drop should have failed as the handle is locked"
            );

            // Sorting by int_field should unlock the handle
            await click($(target).find(".o_column_sortable").eq(0));

            assert.strictEqual(
                $(target).find('tbody span[name="amount"]').text(),
                "1200.000.00500.00300.00",
                "records should be ordered as per the previous resequence"
            );

            // Drag and drop the fourth line in second position
            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(3),
                $(target).find("tbody tr").first(),
                { position: "bottom" }
            );

            assert.strictEqual(
                $(target).find('tbody span[name="amount"]').text(),
                "1200.00300.000.00500.00",
                "drag and drop should have worked as the handle is unlocked"
            );
        }
    );

    QUnit.skipWOWL("editable list with handle widget with slow network", async function (assert) {
        assert.expect(15);

        // resequence makes sense on a sequence field, not on arbitrary fields
        serverData.models.foo.records[0].int_field = 0;
        serverData.models.foo.records[1].int_field = 1;
        serverData.models.foo.records[2].int_field = 2;
        serverData.models.foo.records[3].int_field = 3;

        var prom = testUtils.makeTestPromise();

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="top">' +
                '<field name="int_field" widget="handle"/>' +
                '<field name="amount" widget="float" digits="[5,0]"/>' +
                "</tree>",
            mockRPC: function (route, args) {
                if (route === "/web/dataset/resequence") {
                    var _super = this._super.bind(this);
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
                    return prom.then(function () {
                        return _super(route, args);
                    });
                }
                return this._super.apply(this, arguments);
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

        // drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            $(target).find(".ui-sortable-handle").eq(3),
            $(target).find("tbody tr").first(),
            { position: "bottom" }
        );

        // edit moved row before the end of resequence
        await click($(target).find("tbody tr:eq(3) td:last"));
        await testUtils.nextTick();

        assert.strictEqual(
            $(target).find("tbody tr:eq(3) td:last input").length,
            0,
            "shouldn't edit the line before resequence"
        );

        prom.resolve();
        await testUtils.nextTick();

        assert.strictEqual(
            $(target).find("tbody tr:eq(3) td:last input").length,
            1,
            "should edit the line after resequence"
        );

        assert.strictEqual(
            $(target).find("tbody tr:eq(3) td:last input").val(),
            "300",
            "fourth record should have amount 300"
        );

        await editInput($(target).find("tbody tr:eq(3) td:last input"), 301);
        await click($(target).find("tbody tr:eq(0) td:last"));

        await click(target.querySelector(".o_list_button_save"));

        assert.strictEqual(
            $(target).find("tbody tr:eq(0) td:last").text(),
            "1200",
            "first record should have amount 1200"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(1) td:last").text(),
            "0",
            "second record should have amount 1"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(2) td:last").text(),
            "500",
            "third record should have amount 500"
        );
        assert.strictEqual(
            $(target).find("tbody tr:eq(3) td:last").text(),
            "301",
            "fourth record should have amount 301"
        );

        await click($(target).find("tbody tr:eq(3) td:last"));
        assert.strictEqual(
            $(target).find("tbody tr:eq(3) td:last input").val(),
            "301",
            "fourth record should have amount 301"
        );
    });

    QUnit.skipWOWL(
        "list with handle widget, create and move should keep empty lines at last",
        async function (assert) {
            // When there are less than 4 records in the table, empty lines are added
            // to have at least 4 rows. This test ensures that the empty line added
            // when a new record is discarded is correctly added on the bottom of
            // the target, even if the discarded record wasn't.
            assert.expect(11);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <tree editable="bottom">
                    <field name="int_field" widget="handle"/>
                    <field name="foo" required="1"/>
                </tree>`,
                domain: [["bar", "=", false]],
            });

            assert.containsOnce(target, ".o_data_row");
            assert.containsN(target, "tbody tr", 4);

            await click(target.querySelector(".o_list_button_add"));
            assert.containsN(target, ".o_data_row", 2);
            assert.doesNotHaveClass($(target).find(".o_data_row:first"), "o_selected_row");
            assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

            // Drag and drop the first line after creating record row
            await testUtils.dom.dragAndDrop(
                $(target).find(".ui-sortable-handle").eq(0),
                $(target).find("tbody tr.o_data_row").eq(1),
                { position: "bottom" }
            );
            assert.containsN(target, ".o_data_row", 2);
            assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
            assert.doesNotHaveClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

            await click($(target).find(".o_list_button_discard"));
            assert.containsOnce(target, ".o_data_row");
            assert.hasClass($(target).find("tbody tr:first"), "o_data_row");
            assert.containsN(target, "tbody tr", 4);
        }
    );

    QUnit.skipWOWL("multiple clicks on Add do not create invalid rows", async function (assert) {
        assert.expect(2);

        serverData.models.foo.onchanges = {
            m2o: function () {},
        };

        var prom = testUtils.makeTestPromise();
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="m2o" required="1"/></tree>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "onchange") {
                    return prom.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        assert.containsN(target, ".o_data_row", 4, "should contain 4 records");

        // click on Add twice, and delay the onchange
        click(target.querySelector(".o_list_button_add"));
        click(target.querySelector(".o_list_button_add"));

        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(target, ".o_data_row", 5, "only one record should have been created");
    });

    QUnit.skipWOWL("reference field rendering", async function (assert) {
        assert.expect(4);

        serverData.models.foo.records.push({
            id: 5,
            reference: "res_currency,2",
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="reference"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    assert.step(args.model);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(
            ["bar", "res_currency"],
            "should have done 1 name_get by model in reference values"
        );
        assert.strictEqual(
            $(target).find("tbody td:not(.o_list_record_selector)").text(),
            "Value 1USDEUREUR",
            "should have the display_name of the reference"
        );
    });

    QUnit.skipWOWL("reference field batched in grouped list", async function (assert) {
        assert.expect(8);

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
            arch: `<tree expand="1">
                       <field name="foo" invisible="1"/>
                       <field name="reference"/>
                   </tree>`,
            groupBy: ["foo"],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === "name_get") {
                    if (args.model === "bar") {
                        assert.deepEqual(args.args[0], [1, 2, 3]);
                    }
                    if (args.model === "res_currency") {
                        assert.deepEqual(args.args[0], [1]);
                    }
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.verifySteps(["web_read_group", "name_get", "name_get"]);
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
            arch: `<tree expand="1" multi_edit="1">
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

    QUnit.skipWOWL("multi edit reference field batched in grouped list", async function (assert) {
        assert.expect(18);

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
        let nameGetCount = 0;
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree expand="1" multi_edit="1">
                       <field name="foo" invisible="1"/>
                       <field name="bar" widget="boolean_toggle"/>
                       <field name="reference"/>
                   </tree>`,
            groupBy: ["foo"],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === "write") {
                    assert.deepEqual(args.args, [[1, 2, 3], { bar: true }]);
                }
                if (args.method === "name_get") {
                    if (nameGetCount === 2) {
                        assert.strictEqual(args.model, "bar");
                        assert.deepEqual(args.args[0], [1, 2]);
                    }
                    if (nameGetCount === 3) {
                        assert.strictEqual(args.model, "res_currency");
                        assert.deepEqual(args.args[0], [1]);
                    }
                    nameGetCount++;
                }
            },
        });

        assert.verifySteps(["get_views", "web_read_group", "name_get", "name_get"]);
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[0]);
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[1]);
        await click(target.querySelectorAll(".o_data_row .o_list_record_selector input")[2]);
        await click(target.querySelector(".o_data_row .o_field_boolean"));
        assert.containsOnce(target, ".modal");

        await click($(".modal .modal-footer .btn-primary"));
        assert.containsNone(target, ".modal");
        assert.verifySteps(["write", "read", "name_get", "name_get"]);
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
                    <field name="date_start" widget="daterange" options="{'related_end_date': 'date_end'}" />
                    <field name="date_end" widget="daterange" options="{'related_start_date': 'date_start'}"/>
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
        // change dates via the daterangepicker
        const datepicker = document.querySelector(`.daterangepicker[data-name="date_start"]`);
        await triggerEvent(
            datepicker,
            ".drp-calendar.left .available[data-title='r3c1']",
            "mousedown"
        );
        await triggerEvent(
            datepicker,
            ".drp-calendar.right .available[data-title='r2c0']",
            "mousedown"
        );
        const applyBtn = datepicker.querySelector(".applyBtn");
        assert.notOk(applyBtn.disabled);

        // Apply the changes
        await click(applyBtn);
        assert.containsOnce(
            target,
            ".modal",
            "The confirm dialog should appear to confirm the multi edition."
        );

        const changesTable = document.querySelector(".modal-body .o_modal_changes");
        assert.strictEqual(
            changesTable.innerText.replaceAll("\n", "").replaceAll("\t", ""),
            "Field:Date StartUpdate to:01/16/2017Field:Date EndUpdate to:02/12/2017"
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
                    <field name="date_start" widget="daterange" options="{'related_end_date': 'date_end'}" />
                    <field name="date_end" widget="daterange" options="{'related_start_date': 'date_start'}"/>
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
                ".o_data_row .o_data_cell .o_field_daterange[name='date_start'] input",
                "2021-04-01 11:00:00"
            );
            assert.containsOnce(
                target,
                ".modal",
                "The confirm dialog should appear to confirm the multi edition."
            );

            const changesTable = target.querySelector(".modal-body .o_modal_changes");
            assert.strictEqual(
                changesTable.innerText.replaceAll("\n", "").replaceAll("\t", ""),
                "Field:Date StartUpdate to:04/01/2021"
            );

            // Valid the confirm dialog
            await click(target, ".modal .btn-primary");
            assert.containsNone(target, ".modal");
        }
    );

    QUnit.test("editable list view: contexts are correctly sent", async function (assert) {
        patchWithCleanup(session.user_context, { someKey: "some value" });
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                const context = args.kwargs.context;
                assert.strictEqual(context.active_field, 2, "context should be correct");
                assert.strictEqual(context.someKey, "some value", "context should be correct");
            },
            context: { active_field: 2 },
        });

        await click(target.querySelector(".o_data_cell"));
        await editInput(target.querySelector(".o_field_widget[name=foo] input"), null, "abc");
        await click(target.querySelector(".o_list_button_save"));
    });

    QUnit.test("editable list view: contexts with multiple edit", async function (assert) {
        assert.expect(4);

        patchWithCleanup(session.user_context, { someKey: "some value" });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree multi_edit="1">' + '<field name="foo"/>' + "</tree>",
            mockRPC: function (route, args) {
                if (
                    route === "/web/dataset/call_kw/foo/write" ||
                    route === "/web/dataset/call_kw/foo/read"
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
        await click(target.querySelector(".o_list_button_save"));

        const fooFields = target.querySelectorAll(".o_data_cell .o_field_widget[name=foo]");
        assert.strictEqual(fooFields[0].innerText, "yop", "First row should remain unchanged");
        assert.strictEqual(fooFields[1].innerText, "oui", "Second row should have been updated");
    });

    // Need keynav Enter
    QUnit.skipWOWL(
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

            await click(target.querySelector(".o_list_button_add"));
            assert.containsN(target, ".o_data_row", 5);
            assert.containsOnce(target, ".o_selected_row");

            // do not change anything and then click outside should discard record
            await click(target, ".o_list_view");
            assert.containsN(target, ".o_data_row", 4);
            assert.containsNone(target, ".o_selected_row");

            await click(target.querySelector(".o_list_button_add"));
            assert.containsN(target, ".o_data_row", 5);
            assert.containsOnce(target, ".o_selected_row");

            // do not change anything and then click save button should not allow to discard record
            await click(target.querySelector(".o_list_button_save"));
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

            await click(target.querySelector(".o_list_button_add"));
            assert.containsN(target, ".o_data_row", 5);
            assert.containsOnce(target, ".o_selected_row");

            // do not change anything and press Enter key should not allow to discard record
            await testUtils.fields.triggerKeydown(
                target.querySelector('tr.o_selected_row input.o_field_widget[name="foo"]'),
                "enter"
            );
            assert.containsOnce(target, ".o_selected_row");

            // discard row and create new record and keep required field empty and click anywhere
            await click(target.querySelector(".o_list_button_discard"));
            await click(target, ".o_list_button_add");
            assert.containsOnce(target, ".o_selected_row", "row should be selected");
            await editInput(target, ".o_selected_row .o_field_widget[name=int_field]", 123);
            await click(target, ".o_list_view");
            assert.containsOnce(target, ".o_selected_row", "row should still be selected");
        }
    );

    // Neer focus datacell
    QUnit.skipWOWL("editable list view: multi edition", async function (assert) {
        assert.expect(26);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="bottom" multi_edit="1">' +
                '<field name="foo"/>' +
                '<field name="int_field"/>' +
                "</tree>",
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args,
                        [[1, 2], { int_field: 666 }],
                        "should write on multi records"
                    );
                } else if (args.method === "read") {
                    if (args.args[0].length !== 1) {
                        assert.deepEqual(
                            args.args,
                            [
                                [1, 2],
                                ["foo", "int_field"],
                            ],
                            "should batch the read"
                        );
                    }
                }
            },
        });

        assert.verifySteps(["/web/dataset/search_read"]);

        // select two records
        const rows = target.querySelectorAll(".o_data_row");
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");

        // edit a line without modifying a field
        await click(rows[0].querySelector(".o_data_cell"));
        assert.hasClass(
            $(target).find(".o_data_row:eq(0)"),
            "o_selected_row",
            "the first row should be selected"
        );
        await click(target, ".o_list_view");
        assert.containsNone(target, ".o_selected_row", "no row should be selected");

        // create a record and edit its value
        await click(target, ".o_list_button_add");
        assert.verifySteps(["onchange"]);

        await editInput(target, ".o_selected_row [name=int_field] input", 123);
        assert.containsNone(
            document.body,
            ".modal",
            "the multi edition should not be triggered during creation"
        );

        await clickSave(target);
        assert.verifySteps(["create", "read"]);

        // edit a field
        await click(rows[0].querySelector(".o_data_cell"));
        await editInput(rows[0], "[name=int_field] input", 666);
        assert.containsOnce(target, ".modal", "modal appears when switching cells");

        await click(target, ".modal .btn.btn-secondary");
        assert.containsN(
            target,
            ".o_list_record_selector input:checked",
            2,
            "Selection should remain unchanged"
        );
        assert.deepEqual(
            [...rows[0].querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["yop", "10"],
            "changes have been discarded and row is back to readonly"
        );
        assert.strictEqual(
            document.activeElement,
            rows[0].querySelectorAll(".o_data_cell")[1],
            "focus should be given to the most recently edited cell after discard"
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
        assert.verifySteps(["write", "read"]);
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
        assert.strictEqual(
            document.activeElement,
            $(target).find(".o_data_row:eq(0) .o_data_cell:eq(1)")[0],
            "focus should be given to the most recently edited cell after confirm"
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
            arch:
                '<tree multi_edit="1">' +
                '<field name="foo"/>' +
                '<field name="int_field"/>' +
                "</tree>",
            createRecord: () => {
                assert.step("createRecord");
            },
        });

        // click on CREATE (should trigger a switch_view)
        await click(target, ".o_list_button_add");
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
            arch:
                '<tree multi_edit="1">' +
                '<field name="foo"/>' +
                '<field name="int_field"/>' +
                "</tree>",
            mockRPC: function (route, args) {
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

        assert.verifySteps(["write", "read"]);

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

        assert.verifySteps(["write", "read"], "should not perform the onchange in multi edition");
    });

    QUnit.test(
        "editable list view: multi edition error and cancellation handling",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree multi_edit="1">' +
                    '<field name="foo" required="1"/>' +
                    '<field name="int_field"/>' +
                    "</tree>",
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
        assert.expect(5);

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

    // Need Update duplicate m2m record
    QUnit.skipWOWL("multi edition: many2many field in grouped list", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `<tree multi_edit="1">
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
            $(target)
                .find("tbody:eq(1) .o_data_row:first .o_data_cell:eq(1)")
                .text()
                .replace(/\s/g, ""),
            "Value1Value2Value3",
            "should have a right value in many2many field"
        );
        assert.strictEqual(
            $(target)
                .find("tbody:eq(3) .o_data_row:first .o_data_cell:eq(1)")
                .text()
                .replace(/\s/g, ""),
            "Value1Value2Value3",
            "should have same value in many2many field on all other records with same res_id"
        );
    });

    QUnit.skipWOWL(
        "editable list view: multi edition of many2one: set same value",
        async function (assert) {
            assert.expect(4);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree multi_edit="1">' +
                    '<field name="foo"/>' +
                    '<field name="m2o"/>' +
                    "</tree>",
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(
                            args.args,
                            [[1, 2, 3, 4], { m2o: 1 }],
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
            await click(target, ".o_list_record_selector input");

            // set m2o to 1 in first record
            await click(target.querySelector(".o_data_row .o_data_cell"));
            await testUtils.fields.many2one.searchAndClickItem("m2o", { search: "Value 1" });

            assert.containsOnce(document.body, ".modal");

            await click(target, ".modal .modal-footer .btn-primary");

            assert.strictEqual(
                $(target).find(".o_list_many2one").text(),
                "Value 1Value 1Value 1Value 1"
            );
        }
    );

    QUnit.test(
        'editable list view: clicking on "Discard changes" in multi edition',
        async function (assert) {
            assert.expect(2);

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

            const discardButton = target.querySelector(".o_list_button_discard");
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

            const discardButton = target.querySelector(".o_list_button_discard");
            // Simulates an actual click (event chain is: mousedown > change > blur > focus > mouseup > click)
            await triggerEvents(discardButton, null, ["mousedown"]);
            await triggerEvents(target.querySelector(".o_data_row .o_data_cell input"), null, [
                "change",
                "blur",
                "focusout",
            ]);
            await triggerEvents(discardButton, null, ["focus"]);
            await triggerEvents(document, null, ["mouseup"]);

            assert.ok(
                $(".modal").text().includes("Confirmation"),
                "Modal should ask to save changes"
            );
            await click(target, ".modal .btn-primary");
        }
    );

    QUnit.skipWOWL(
        "editable list view (multi edition): writable fields in readonly (force save)",
        async function (assert) {
            assert.expect(7);

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
            await click(rows[0].querySelector(".o_field_boolean"));

            assert.ok(
                $(".modal").text().includes("Confirmation"),
                "Modal should ask to save changes"
            );
            await click(target, ".modal .btn-primary");
            assert.verifySteps(["write", "read"]);
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
                        <field name="int_field" attrs='{"readonly": [("id", ">" , 2)]}'/>
                    </tree>`,
                mockRPC: function (route, args) {
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
                    "perform the following update on those 2 records ? Field:int_fieldUpdate to:666"
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
        assert.expect(2);

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

    QUnit.skipWOWL(
        "editable list view: multi edition server error handling",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree multi_edit="1">' + '<field name="foo" required="1"/>' + "</tree>",
                mockRPC: function (route, args) {
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
        }
    );

    QUnit.skipWOWL("editable readonly list view: navigation", async function (assert) {
        assert.expect(6);

        await makeView({
            arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            serverData,
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(
                        event.data.res_id,
                        3,
                        "'switch_view' event has been triggered"
                    );
                },
            },
            resModel: "foo",
        });

        // select 2 records
        await click($(target).find(".o_data_row:eq(1) .o_list_record_selector input"));
        await click($(target).find(".o_data_row:eq(3) .o_list_record_selector input"));

        // toggle a row mode
        await click($(target).find(".o_data_row:eq(1) .o_data_cell:eq(1)"));
        assert.hasClass(
            $(target).find(".o_data_row:eq(1)"),
            "o_selected_row",
            "the second row should be selected"
        );

        // Keyboard navigation only interracts with selected elements
        await testUtils.fields.triggerKeydown(
            $(target).find('tr.o_selected_row input.o_field_widget[name="int_field"]'),
            "enter"
        );
        assert.hasClass(
            $(target).find(".o_data_row:eq(3)"),
            "o_selected_row",
            "the fourth row should be selected"
        );

        await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
        await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
        assert.hasClass(
            $(target).find(".o_data_row:eq(1)"),
            "o_selected_row",
            "the second row should be selected again"
        );

        await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
        await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
        assert.hasClass(
            $(target).find(".o_data_row:eq(3)"),
            "o_selected_row",
            "the fourth row should be selected again"
        );

        await click($(target).find(".o_data_row:eq(2) .o_data_cell:eq(0)"));
        assert.containsNone(
            target,
            ".o_data_cell input.o_field_widget",
            "no row should be editable anymore"
        );
        // Clicking on an unselected record while no row is being edited will open the record (switch_view)
        await click($(target).find(".o_data_row:eq(2) .o_data_cell:eq(0)"));

        await click($(target).find(".o_data_row:eq(1) .o_list_record_selector input"));
        await click($(target).find(".o_data_row:eq(3) .o_list_record_selector input"));
    });

    // Need Key Nav
    QUnit.skipWOWL(
        "editable list view: multi edition: edit and validate last row",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                    </tree>`,
                // in this test, we want to accurately mock what really happens, that is, input
                // fields only trigger their changes on 'change' event, not on 'input'
                // fieldDebounce: 100000,
            });

            assert.containsN(target, ".o_data_row", 4);

            // select all records
            await click(target.querySelector(".o_list_view .o_list_record_selector input"));

            // edit last cell of last line
            await click([...target.querySelectorAll(".o_data_row .o_data_cell")].pop());
            const input = target.querySelector(".o_data_row [name=int_field] input");
            input.value = "666";
            await triggerEvent(input, null, "input");
            await triggerEvent(
                [...target.querySelectorAll(".o_data_row .o_data_cell")].pop(),
                null,
                "keydown",
                { key: "enter" }
            );

            assert.containsOnce(target, ".modal");

            await click(target, ".modal .btn-primary");
            assert.containsN(
                target,
                ".o_data_row",
                4,
                "should not create a new row as we were in multi edition"
            );
        }
    );

    QUnit.skipWOWL(
        "editable readonly list view: navigation in grouped list",
        async function (assert) {
            assert.expect(6);

            await makeView({
                arch: `
                <tree multi_edit="1">
                    <field name="foo"/>
                </tree>`,
                serverData,
                groupBy: ["bar"],
                intercepts: {
                    switch_view: function (event) {
                        assert.strictEqual(
                            event.data.res_id,
                            3,
                            "'switch_view' event has been triggered"
                        );
                    },
                },
                resModel: "foo",
            });

            // Open both groups
            const groupHeaders = target.querySelectorAll(".o_group_header");
            await click(groupHeaders[0]);
            await click(groupHeaders.pop());

            // select 2 records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[1], ".o_list_record_selector input");
            await click(rows[3], ".o_list_record_selector input");

            // toggle a row mode
            await click(rows[1].querySelector(".o_data_cell"));
            assert.hasClass(
                $(target).find(".o_data_row:eq(1)"),
                "o_selected_row",
                "the second row should be selected"
            );

            // Keyboard navigation only interracts with selected elements
            await testUtils.fields.triggerKeydown(
                $(target).find("tr.o_selected_row input.o_field_widget"),
                "enter"
            );
            assert.hasClass(
                $(target).find(".o_data_row:eq(3)"),
                "o_selected_row",
                "the fourth row should be selected"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
            assert.hasClass(
                $(target).find(".o_data_row:eq(1)"),
                "o_selected_row",
                "the second row should be selected again"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
            assert.hasClass(
                $(target).find(".o_data_row:eq(3)"),
                "o_selected_row",
                "the fourth row should be selected again"
            );

            await click($(target).find(".o_data_row:eq(2) .o_data_cell:eq(0)"));
            assert.containsNone(
                target,
                ".o_data_cell input.o_field_widget",
                "no row should be editable anymore"
            );
            await click($(target).find(".o_data_row:eq(2) .o_data_cell:eq(0)"));
        }
    );

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

    QUnit.test("editable readonly list view: multi edition", async function (assert) {
        await makeView({
            type: "list",
            arch: `<tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            serverData,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args,
                        [[1, 2], { int_field: 666 }],
                        "should write on multi records"
                    );
                } else if (args.method === "read") {
                    if (args.args[0].length !== 1) {
                        assert.deepEqual(
                            args.args,
                            [
                                [1, 2],
                                ["foo", "int_field"],
                            ],
                            "should batch the read"
                        );
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
        await click(rows[1].querySelectorAll(".o_data_cell")[0]);
        assert.containsOnce(target, ".modal", "there should be an opened modal");
        assert.ok(
            $(".modal").text().includes("those 2 records"),
            "the number of records should be correctly displayed"
        );

        await click(target, ".modal .btn-primary");
        assert.verifySteps(["write", "read"]);
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

    QUnit.skipWOWL("editable list: edit many2one from external link", async function (assert) {
        // need to implement save,... in FormViewDialog
        assert.expect(7);

        serverData.views = {
            "bar,false,form": `
                <form string="Bar">
                    <field name="display_name"/>
                </form>
            `,
        };

        await makeView({
            arch: `
                <tree editable="top" multi_edit="1">
                    <field name="m2o"/>
                </tree>
            `,
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "get_formview_id") {
                    return false;
                }
            },
            resModel: "foo",
            type: "list",
        });

        assert.containsNone(target, ".o_selected_row", "not in edit mode");
        await click(target.querySelector("thead .o_list_record_selector input"));
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_selected_row", "in edit mode");
        await click(target.querySelector(".o_external_button"));

        // Clicking somewhere on the form dialog should not close it
        // and should not leave edit mode
        assert.containsOnce(target, ".modal[role='dialog']");
        await click(target.querySelector(".modal[role='dialog']"));
        assert.containsOnce(target, ".modal[role='dialog']");
        assert.containsOnce(target, ".o_selected_row", "in edit mode");

        // Change the M2O value in the Form dialog
        await editInput(target, ".modal input", "OOF");
        await click(target.querySelector(".modal .btn-primary"));

        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=m2o]").innerText,
            "OOF",
            "Value of the m2o should be updated in the confirmation dialog"
        );

        // Close the confirmation dialog
        await click(target.querySelector(".modal .btn-primary"));

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
                    <field name="foo" attrs="{'readonly': [['bar','=',True]]}"/>
                    <field name="m2o" attrs="{'readonly': [['bar','=',False]]}"/>
                    <field name="int_field"/>
                </tree>
            `,
        });

        await click(target.querySelector(".o_list_button_add"));
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

        await click(target.querySelector(".o_selected_row .o_field_many2one input"));
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_selected_row .o_field_many2one input")
        );
    });

    QUnit.skipWOWL(
        "editable form with many2one: click out does not discard the row",
        async function (assert) {
            // WOWL Should be moved to form view tests!

            // In this test, we simulate a long click by manually triggering a mousedown and later on
            // mouseup and click events
            assert.expect(5);

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
                    </form>
                `,
            });

            assert.containsNone(target, ".o_data_row");

            await click(target.querySelector(".o_field_x2many_list_row_add > a"));
            assert.containsOnce(target, ".o_data_row");

            // focus and write something in the m2o
            await editInput(target, ".o_field_many2one input", "abcdef");
            await triggerEvent(target, "input.o_searchview_input", "keydown", { key: "ArrowUp" });

            await testUtils.nextTick();

            // then simulate a mousedown outside
            target.querySelector('.o_field_widget[name="display_name"]').focus();
            await triggerEvent(target, '.o_field_widget[name="display_name"]', "mousedown");
            await testUtils.nextTick();
            assert.containsOnce(target, ".modal", "should ask confirmation to create a record");

            // trigger the mouseup and the click
            target
                .querySelector('.o_field_widget[name="display_name"]')
                .trigger("mouseup")
                .trigger("click");
            await testUtils.nextTick();

            assert.containsOnce(target, ".modal", "modal should still be displayed");
            assert.containsOnce(target, ".o_data_row", "the row should still be there");
        }
    );

    QUnit.test(
        "editable form alongside html field: click out to unselect the row",
        async function (assert) {
            assert.expect(5);

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

    QUnit.test("grouped list edition with toggle_button widget", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="bar" widget="toggle_button"/></tree>',
            groupBy: ["m2o"],
            mockRPC: function (route, args) {
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
            ".o_data_row:first .o_toggle_button_success",
            "boolean value of the first record should be true"
        );
        await click(target.querySelector(".o_data_row .o_icon_button"));
        assert.strictEqual(
            $(target).find(".o_data_row:first .text-muted:not(.o_toggle_button_success)").length,
            1,
            "boolean button should have been updated"
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
            mockRPC: function (route, args) {
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
        assert.strictEqual(
            $(target).find("th.o_group_name").eq(1).children().length,
            1,
            "There should be an empty element creating the indentation for the subgroup."
        );
        assert.hasClass(
            $(target).find("th.o_group_name").eq(1).children().eq(0),
            "fa",
            "The first element of the row name should have the fa class"
        );
        assert.strictEqual(
            $(target).find("th.o_group_name").eq(1).children().eq(0).is("span"),
            true,
            "The first element of the row name should be a span"
        );
    });

    QUnit.skipWOWL("basic support for widgets", async function (assert) {
        // This test could be removed as soon as we drop the support of legacy widgets (see test
        // below, which is a duplicate of this one, but with an Owl Component instead).
        assert.expect(1);

        var MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                serverData.models = dataPoint.data;
            },
            start: function () {
                this.$el.text(JSON.stringify(serverData.models));
            },
        });
        widgetRegistry.add("test", MyWidget);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field"/><widget name="test"/></tree>',
        });

        assert.strictEqual(
            $(target).find(".o_widget").first().text(),
            '{"foo":"yop","int_field":10,"id":1}',
            "widget should have been instantiated"
        );

        delete widgetRegistry.map.test;
    });

    QUnit.skipWOWL("basic support for widgets (being Owl Components)", async function (assert) {
        assert.expect(1);

        class MyComponent extends owl.Component {
            get value() {
                return JSON.stringify(this.props.record.data);
            }
        }
        MyComponent.template = owl.xml`<div t-esc="value"/>`;
        widgetRegistryOwl.add("test", MyComponent);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/><field name="int_field"/><widget name="test"/></tree>',
        });

        assert.strictEqual(
            $(target).find(".o_widget").first().text(),
            '{"foo":"yop","int_field":10,"id":1}'
        );

        delete widgetRegistryOwl.map.test;
    });

    QUnit.test("use the limit attribute in arch", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
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
        await toggleFilterMenu(target);
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
        // await toggleFilterMenu(target);
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

    QUnit.skipWOWL('list view on a "noCache" model', async function (assert) {
        assert.expect(9);

        testUtils.mock.patch(BasicModel, {
            noCacheModels: BasicModel.prototype.noCacheModels.concat(["foo"]),
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top">' + '<field name="display_name"/>' + "</tree>",
            mockRPC: function (route, args) {
                if (_.contains(["create", "unlink", "write"], args.method)) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
            actionMenus: {},
        });
        core.bus.on("clear_cache", target, assert.step.bind(assert, "clear_cache"));

        // create a new record
        await click(target.querySelector(".o_list_button_add"));
        await editInput($(target).find(".o_selected_row .o_field_widget"), "some value");
        await click(target.querySelector(".o_list_button_save"));

        // edit an existing record
        await click($(target).find(".o_data_cell:first"));
        await editInput($(target).find(".o_selected_row .o_field_widget"), "new value");
        await click(target.querySelector(".o_list_button_save"));

        // delete a record
        await click($(target).find(".o_data_row:first .o_list_record_selector input"));
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");
        await click($(".modal-footer .btn-primary"));

        assert.verifySteps([
            "create",
            "clear_cache",
            "write",
            "clear_cache",
            "unlink",
            "clear_cache",
        ]);

        testUtils.mock.unpatch(BasicModel);

        assert.verifySteps(["clear_cache"]); // triggered by the test environment on destroy
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
                arch: '<tree limit="3">' + '<field name="display_name"/>' + "</tree>",
                mockRPC: function (route, args) {
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
            assert.expect(9);

            let checkSearchRead = false;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree limit="2">' + '<field name="display_name"/>' + "</tree>",
                mockRPC: function (route, args) {
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
        }
    );

    QUnit.test(
        "list view move to previous page when all records from last page archive/unarchived",
        async function (assert) {
            assert.expect(9);

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
                mockRPC: function (route) {
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
            assert.containsNone(target, ".o_cp_action_menus", "sidebar should not be available");

            await click(
                target,
                "tbody .o_data_row:first-child td.o_list_record_selector:first-child input"
            );
            assert.containsOnce(target, ".o_cp_action_menus", "sidebar should be available");

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

    QUnit.skipWOWL("list should ask to scroll to top on page changes", async function (assert) {
        assert.expect(10);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree limit="3">' + '<field name="display_name"/>' + "</tree>",
            intercepts: {
                scrollTo: function (ev) {
                    assert.strictEqual(ev.data.top, 0, "should ask to scroll to top");
                    assert.step("scroll");
                },
            },
        });

        // switch pages (should ask to scroll)
        await testUtils.controlPanel.pagerNext(target);
        await testUtils.controlPanel.pagerPrevious(target);
        assert.verifySteps(["scroll", "scroll"], "should ask to scroll when switching pages");

        // change the limit (should not ask to scroll)
        await testUtils.controlPanel.setPagerValue(target, "1-2");
        await testUtils.nextTick();
        assert.strictEqual(testUtils.controlPanel.getPagerValue(target), "1-2");
        assert.verifySteps([], "should not ask to scroll when changing the limit");

        // switch pages again (should still ask to scroll)
        await testUtils.controlPanel.pagerNext(target);

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
                [...target.querySelectorAll(".o_data_cell [name=foo]")].map((el) => el.textContent),
                ["blip", "blip", "yop", "gnap"]
            );

            // click add a new line
            // save the record
            // check line is at the correct place

            const inputText = "ninja";
            await click(target, ".o_list_button_add");
            await editInput(target, '[name="foo"] input', inputText);
            await clickSave(target);
            await click(target, ".o_list_button_add");

            assert.deepEqual(
                [...target.querySelectorAll(".o_data_cell [name=foo]")].map((el) => el.textContent),
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
                    <field name="id" invisible="1"/>
                    <field name="foo" attrs="{'readonly': [['id','!=',False]]}"/>
                    <field name="int_field" attrs="{'invisible': [['id','!=',False]]}"/>
                </tree>`,
        });

        // add a new record
        await click(target, ".o_list_button_add");

        // modifiers should be evaluted to false
        assert.containsOnce(target, ".o_selected_row");
        assert.doesNotHaveClass(
            target.querySelector(".o_selected_row [name=foo].o_field_widget"),
            "o_readonly_modifier"
        );
        assert.containsOnce(target, ".o_selected_row [name=int_field]");

        // set a value and save
        await editInput(target, ".o_selected_row [name=foo] input", "some value");
        await clickSave(target);

        // modifiers should be evaluted to true
        assert.hasClass(
            target.querySelector(".o_data_row [name=foo].o_field_widget"),
            "o_readonly_modifier"
        );
        assert.containsNone(target, ".o_data_row:first-child [name=int_field]");

        // edit again the just created record
        await click(target.querySelector(".o_data_row .o_data_cell"));

        // modifiers should be evaluted to true
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(
            target.querySelector(".o_selected_row [name=foo].o_field_widget"),
            "o_readonly_modifier"
        );
        assert.containsNone(target, ".o_selected_row [name=int_field]");
    });

    QUnit.skipWOWL("readonly boolean in editable list is readonly", async function (assert) {
        assert.expect(6);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="bottom">' +
                '<field name="foo"/>' +
                "<field name=\"bar\" attrs=\"{'readonly': [('foo', '!=', 'yop')]}\"/>" +
                "</tree>",
        });

        // clicking on disabled checkbox with active row does not work
        const rows = target.querySelectorAll(".o_data_row");
        const disabledCell = rows[1].querySelector("[name=bar]");
        await click(rows[1].querySelector(".o_data_cell"));
        assert.containsOnce(disabledCell, ":disabled:checked");
        await click(rows[1].querySelector("[name=bar] label"));
        assert.containsOnce(disabledCell, ":checked", "clicking disabled checkbox did not work");
        assert.ok(
            $(document.activeElement).is('input[type="text"]'),
            "disabled checkbox is not focused after click"
        );

        // clicking on enabled checkbox with active row toggles check mark
        await click(rows[0].querySelector(".o_data_cell"));
        const enabledCell = rows[0].querySelector("[name=bar]");
        assert.containsOnce(enabledCell, ":checked:not(:disabled)");
        await click(rows[0].querySelector("[name=bar] label"));
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

    QUnit.skipWOWL("grouped list with async widget", async function (assert) {
        assert.expect(4);

        var prom = testUtils.makeTestPromise();
        var AsyncWidget = Widget.extend({
            willStart: function () {
                return prom;
            },
            start: function () {
                this.$el.text("ready");
            },
        });
        widgetRegistry.add("asyncWidget", AsyncWidget);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><widget name="asyncWidget"/></tree>',
            groupBy: ["int_field"],
        });

        assert.containsNone(target, ".o_data_row", "no group should be open");

        await click($(target).find(".o_group_header:first"));

        assert.containsNone(
            target,
            ".o_data_row",
            "should wait for async widgets before opening the group"
        );

        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(target, ".o_data_row", 1, "group should be open");
        assert.strictEqual(
            $(target).find(".o_data_row .o_data_cell").text(),
            "ready",
            "async widget should be correctly displayed"
        );

        delete widgetRegistry.map.asyncWidget;
    });

    QUnit.test("grouped lists with groups_limit attribute", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree groups_limit="3"><field name="foo"/></tree>',
            groupBy: ["int_field"],
            mockRPC: function (route, args) {
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

    QUnit.test("grouped list with expand attribute", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ["bar"],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
            },
        });

        assert.containsN(target, ".o_group_header", 2);
        assert.containsN(target, ".o_data_row", 4);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.textContent),
            ["blip", "yop", "blip", "gnap"]
        );

        assert.verifySteps([
            "get_views",
            "web_read_group", // records are fetched alongside groups
        ]);
    });

    QUnit.test("grouped list (two levels) with expand attribute", async function (assert) {
        // the expand attribute only opens the first level groups
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ["bar", "int_field"],
            mockRPC: function (route, args) {
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
        assert.expect(10);

        for (var i = 0; i < 15; i++) {
            serverData.models.foo.records.push({ foo: "record " + i, int_field: i });
        }

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ["int_field"],
            mockRPC: function (route, args) {
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
        await legacyExtraNextTick();
        assert.deepEqual(getPagerValue(target), [4, 4]);
        assert.containsN(target, ".o_group_header", 1); // page 2

        // toggle a filter -> there should be only one group left (on page 1)
        await toggleFilterMenu(target);
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
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "bar");
        await click(target.querySelector(".o_group_header"));

        // enter edition (grouped case)
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_selected_row");

        // click on the body should leave the edition
        await click(target, ".o_list_view");
        assert.containsNone(target, ".o_selected_row");

        // reload without groupBy
        await toggleGroupByMenu(target);
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
        await toggleGroupByMenu(target);
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

        assert.containsOnce(target, ".o_list_button_add");

        // reload with a groupby
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "bar");

        assert.containsNone(target, ".o_list_button_add");

        // reload without groupby
        await toggleMenuItem(target, "bar");

        assert.containsOnce(target, ".o_list_button_add");
    });

    QUnit.test(
        "control panel buttons in multi editable grouped list views",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                groupBy: ["foo"],
                arch: `<tree multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </tree>`,
            });

            assert.containsNone(target, ".o_data_row", "all groups should be closed");
            assert.isVisible(
                target.querySelector(".o_list_button_add"),
                "should have a visible Create button"
            );

            await click(target.querySelector(".o_group_header"));
            assert.containsN(target, ".o_data_row", 2, "first group should be opened");
            assert.isVisible(
                target.querySelector(".o_list_button_add"),
                "should have a visible Create button"
            );

            await click(target.querySelector(".o_data_row .o_list_record_selector input"));
            assert.containsOnce(
                target,
                ".o_data_row:eq(0) .o_list_record_selector input:enabled",
                "should have selected first record"
            );
            assert.isVisible(
                target.querySelector(".o_list_button_add"),
                "should have a visible Create button"
            );

            await click([...target.querySelectorAll(".o_group_header")].pop());
            assert.containsN(target, ".o_data_row", 3, "two groups should be opened");
            assert.isVisible(
                target.querySelector(".o_list_button_add"),
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

        await click(target, ".o_list_button_discard");
        await click(target, ".o_data_row:nth-child(3) .o_data_cell:nth-child(2)");
        assert.containsOnce(target, ".o_selected_row");
        assert.hasClass(target.querySelector(".o_data_row:nth-child(3)"), "o_selected_row");

        await click(target, ".o_list_button_discard");
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

    QUnit.skipWOWL(
        "inputs are disabled when unselecting rows in grouped editable",
        async function (assert) {
            assert.expect(1);

            var $input;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo"/></tree>',
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(
                            $input.prop("disabled"),
                            true,
                            "input should be disabled"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
                groupBy: ["bar"],
            });

            await click($(target).find(".o_group_header:first"));
            await click($(target).find("td:contains(yop)"));
            $input = $(target).find('tr.o_selected_row input[name="foo"]');
            await testUtils.fields.editAndTrigger($input, "lemon", "input");
            await testUtils.fields.triggerKeydown($input, "tab");
        }
    );

    QUnit.skipWOWL(
        "pressing ESC in editable grouped list should discard the current line changes",
        async function (assert) {
            assert.expect(6);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
                groupBy: ["bar"],
            });

            await click($(target).find(".o_group_header:first")); // open first group
            assert.containsN(target, "tr.o_data_row", 3);

            await click($(target).find(".o_data_cell:first"));

            // update name by "foo"
            await testUtils.fields.editAndTrigger(
                $(target).find('tr.o_selected_row .o_data_cell:first input[name="foo"]'),
                "new_value",
                "input"
            );
            // discard by pressing ESC
            await testUtils.fields.triggerKeydown($(target).find('input[name="foo"]'), "escape");
            assert.containsNone(document.body, ".modal", "should not open modal");

            assert.containsOnce(target, "tbody tr td:contains(yop)");
            assert.containsN(target, "tr.o_data_row", 3);
            assert.containsNone(target, "tr.o_data_row.o_selected_row");
            assert.isNotVisible(target.querySelector(".o_list_button_save"));
        }
    );

    QUnit.skipWOWL('pressing TAB in editable="bottom" grouped list', async function (assert) {
        assert.expect(7);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            groupBy: ["bar"],
        });

        // open two groups
        await click($(target).find(".o_group_header:first"));
        assert.containsN(target, ".o_data_row", 3, "first group contains 3 rows");
        await click($(target).find(".o_group_header:nth(1)"));
        assert.containsN(target, ".o_data_row", 4, "first group contains 1 row");

        await click($(target).find(".o_data_cell:first"));
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(3)"), "o_selected_row");

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
    });

    QUnit.skipWOWL('pressing TAB in editable="top" grouped list', async function (assert) {
        assert.expect(7);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            groupBy: ["bar"],
        });

        // open two groups
        await click($(target).find(".o_group_header:first"));
        assert.containsN(target, ".o_data_row", 3, "first group contains 3 rows");
        await click($(target).find(".o_group_header:nth(1)"));
        assert.containsN(target, ".o_data_row", 4, "first group contains 1 row");

        await click($(target).find(".o_data_cell:first"));

        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(3)"), "o_selected_row");

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
    });

    QUnit.skipWOWL("pressing TAB in editable grouped list with create=0", async function (assert) {
        assert.expect(7);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
            groupBy: ["bar"],
        });

        // open two groups
        await click($(target).find(".o_group_header:first"));
        assert.containsN(target, ".o_data_row", 3, "first group contains 3 rows");
        await click($(target).find(".o_group_header:nth(1)"));
        assert.containsN(target, ".o_data_row", 4, "first group contains 1 row");

        await click($(target).find(".o_data_cell:first"));

        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:nth(3)"), "o_selected_row");

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.hasClass($(target).find(".o_data_row:first"), "o_selected_row");
    });

    QUnit.skipWOWL('pressing SHIFT-TAB in editable="bottom" grouped list', async function (assert) {
        assert.expect(6);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ["bar"],
        });

        await click($(target).find(".o_group_header:first")); // open first group
        assert.containsN(target, ".o_data_row", 3, "first group contains 3 rows");
        await click($(target).find(".o_group_header:eq(1)")); // open second group
        assert.containsN(target, ".o_data_row", 4, "first group contains 1 row");

        // navigate inside a group
        await click($(target).find(".o_data_row:eq(1) .o_data_cell")); // select second row of first group
        assert.hasClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

        // press Shft+tab
        $(target)
            .find("tr.o_selected_row input")
            .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
        await testUtils.nextTick();
        assert.hasClass($(target).find("tr.o_data_row:first"), "o_selected_row");
        assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

        // navigate between groups
        await click($(target).find(".o_data_cell:eq(3)")); // select row of second group

        // press Shft+tab
        $(target)
            .find("tr.o_selected_row input")
            .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
        await testUtils.nextTick();
        assert.hasClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");
    });

    QUnit.skipWOWL('pressing SHIFT-TAB in editable="top" grouped list', async function (assert) {
        assert.expect(6);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ["bar"],
        });

        await click($(target).find(".o_group_header:first")); // open first group
        assert.containsN(target, ".o_data_row", 3, "first group contains 3 rows");
        await click($(target).find(".o_group_header:eq(1)")); // open second group
        assert.containsN(target, ".o_data_row", 4, "first group contains 1 row");

        // navigate inside a group
        await click($(target).find(".o_data_row:eq(1) .o_data_cell")); // select second row of first group
        assert.hasClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

        // press Shft+tab
        $(target)
            .find("tr.o_selected_row input")
            .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
        await testUtils.nextTick();
        assert.hasClass($(target).find("tr.o_data_row:first"), "o_selected_row");
        assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

        // navigate between groups
        await click($(target).find(".o_data_cell:eq(3)")); // select row of second group

        // press Shft+tab
        $(target)
            .find("tr.o_selected_row input")
            .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
        await testUtils.nextTick();
        assert.hasClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");
    });

    QUnit.skipWOWL(
        'pressing SHIFT-TAB in editable grouped list with create="0"',
        async function (assert) {
            assert.expect(6);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="top" create="0"><field name="foo" required="1"/></tree>',
                groupBy: ["bar"],
            });

            await click($(target).find(".o_group_header:first")); // open first group
            assert.containsN(target, ".o_data_row", 3, "first group contains 3 rows");
            await click($(target).find(".o_group_header:eq(1)")); // open second group
            assert.containsN(target, ".o_data_row", 4, "first group contains 1 row");

            // navigate inside a group
            await click($(target).find(".o_data_row:eq(1) .o_data_cell")); // select second row of first group
            assert.hasClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

            // press Shft+tab
            $(target)
                .find("tr.o_selected_row input")
                .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
            await testUtils.nextTick();
            assert.hasClass($(target).find("tr.o_data_row:first"), "o_selected_row");
            assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

            // navigate between groups
            await click($(target).find(".o_data_cell:eq(3)")); // select row of second group

            // press Shft+tab
            $(target)
                .find("tr.o_selected_row input")
                .trigger($.Event("keydown", { which: $.ui.keyCode.TAB, shiftKey: true }));
            await testUtils.nextTick();
            assert.hasClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");
        }
    );

    QUnit.skipWOWL("editing then pressing TAB in editable grouped list", async function (assert) {
        assert.expect(19);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ["bar"],
        });

        // open two groups
        await click($(target).find(".o_group_header:first"));
        assert.containsN(target, ".o_data_row", 3, "first group contains 3 rows");
        await click($(target).find(".o_group_header:nth(1)"));
        assert.containsN(target, ".o_data_row", 4, "first group contains 1 row");

        // select and edit last row of first group
        await click($(target).find(".o_data_row:nth(2) .o_data_cell"));
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");
        await editInput($(target).find('.o_selected_row input[name="foo"]'), "new value");

        // Press 'Tab' -> should create a new record as we edited the previous one
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.containsN(target, ".o_data_row", 5);
        assert.hasClass($(target).find(".o_data_row:nth(3)"), "o_selected_row");

        // fill foo field for the new record and press 'tab' -> should create another record
        await editInput($(target).find('.o_selected_row input[name="foo"]'), "new record");
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");

        assert.containsN(target, ".o_data_row", 6);
        assert.hasClass($(target).find(".o_data_row:nth(4)"), "o_selected_row");

        // leave this new row empty and press tab -> should discard the new record and move to the
        // next group
        await testUtils.fields.triggerKeydown($(target).find(".o_selected_row .o_input"), "tab");
        assert.containsN(target, ".o_data_row", 5);
        assert.hasClass($(target).find(".o_data_row:nth(4)"), "o_selected_row");

        assert.verifySteps([
            "web_read_group",
            "/web/dataset/search_read",
            "/web/dataset/search_read",
            "write",
            "read",
            "onchange",
            "create",
            "read",
            "onchange",
        ]);
    });

    QUnit.skipWOWL(
        "editing then pressing TAB (with a readonly field) in grouped list",
        async function (assert) {
            assert.expect(6);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
                mockRPC: function (route, args) {
                    assert.step(args.method || route);
                    return this._super.apply(this, arguments);
                },
                groupBy: ["bar"],
                fieldDebounce: 1,
            });

            await click($(target).find(".o_group_header:first")); // open first group
            // click on first td and press TAB
            await click($(target).find("td:contains(yop)"));
            await testUtils.fields.editAndTrigger(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "new value",
                "input"
            );
            await testUtils.fields.triggerKeydown(
                $(target).find('tr.o_selected_row input[name="foo"]'),
                "tab"
            );

            assert.containsOnce(target, "tbody tr td:contains(new value)");
            assert.verifySteps(["web_read_group", "/web/dataset/search_read", "write", "read"]);
        }
    );

    QUnit.skipWOWL(
        'pressing ENTER in editable="bottom" grouped list view',
        async function (assert) {
            assert.expect(11);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo"/></tree>',
                mockRPC: function (route, args) {
                    assert.step(args.method || route);
                    return this._super.apply(this, arguments);
                },
                groupBy: ["bar"],
            });

            await click($(target).find(".o_group_header:first")); // open first group
            await click($(target).find(".o_group_header:nth(1)")); // open second group
            assert.containsN(target, "tr.o_data_row", 4);
            await click($(target).find(".o_data_row:nth(1) .o_data_cell")); // click on second line
            assert.hasClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

            // press enter in input should move to next record
            await testUtils.fields.triggerKeydown(
                $(target).find("tr.o_selected_row .o_input"),
                "enter"
            );

            assert.hasClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");
            assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

            // press enter on last row should create a new record
            await testUtils.fields.triggerKeydown(
                $(target).find("tr.o_selected_row .o_input"),
                "enter"
            );

            assert.containsN(target, "tr.o_data_row", 5);
            assert.hasClass($(target).find("tr.o_data_row:eq(3)"), "o_selected_row");

            assert.verifySteps([
                "web_read_group",
                "/web/dataset/search_read",
                "/web/dataset/search_read",
                "onchange",
            ]);
        }
    );

    QUnit.skipWOWL('pressing ENTER in editable="top" grouped list view', async function (assert) {
        assert.expect(10);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ["bar"],
        });

        await click($(target).find(".o_group_header:first")); // open first group
        await click($(target).find(".o_group_header:nth(1)")); // open second group
        assert.containsN(target, "tr.o_data_row", 4);
        await click($(target).find(".o_data_row:nth(1) .o_data_cell")); // click on second line
        assert.hasClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

        // press enter in input should move to next record
        await testUtils.fields.triggerKeydown(
            $(target).find("tr.o_selected_row .o_input"),
            "enter"
        );

        assert.hasClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");
        assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

        // press enter on last row should move to first record of next group
        await testUtils.fields.triggerKeydown(
            $(target).find("tr.o_selected_row .o_input"),
            "enter"
        );

        assert.hasClass($(target).find("tr.o_data_row:eq(3)"), "o_selected_row");
        assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");

        assert.verifySteps([
            "web_read_group",
            "/web/dataset/search_read",
            "/web/dataset/search_read",
        ]);
    });

    QUnit.skipWOWL(
        "pressing ENTER in editable grouped list view with create=0",
        async function (assert) {
            assert.expect(10);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
                mockRPC: function (route, args) {
                    assert.step(args.method || route);
                    return this._super.apply(this, arguments);
                },
                groupBy: ["bar"],
            });

            await click($(target).find(".o_group_header:first")); // open first group
            await click($(target).find(".o_group_header:nth(1)")); // open second group
            assert.containsN(target, "tr.o_data_row", 4);
            await click($(target).find(".o_data_row:nth(1) .o_data_cell")); // click on second line
            assert.hasClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

            // press enter in input should move to next record
            await testUtils.fields.triggerKeydown(
                $(target).find("tr.o_selected_row .o_input"),
                "enter"
            );

            assert.hasClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");
            assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(1)"), "o_selected_row");

            // press enter on last row should move to first record of next group
            await testUtils.fields.triggerKeydown(
                $(target).find("tr.o_selected_row .o_input"),
                "enter"
            );

            assert.hasClass($(target).find("tr.o_data_row:eq(3)"), "o_selected_row");
            assert.doesNotHaveClass($(target).find("tr.o_data_row:eq(2)"), "o_selected_row");

            assert.verifySteps([
                "web_read_group",
                "/web/dataset/search_read",
                "/web/dataset/search_read",
            ]);
        }
    );

    QUnit.skipWOWL("cell-level keyboard navigation in non-editable list", async function (assert) {
        assert.expect(16);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo" required="1"/></tree>',
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(
                        event.data.res_id,
                        3,
                        "'switch_view' event has been triggered"
                    );
                },
            },
        });

        assert.ok(
            document.activeElement.classList.contains("o_searchview_input"),
            "default focus should be in search view"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.tagName,
            "INPUT",
            "focus should now be on the record selector"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "up");
        assert.ok(
            document.activeElement.classList.contains("o_searchview_input"),
            "focus should have come back to the search view"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.tagName,
            "INPUT",
            "focus should now be in first row input"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "right");
        assert.strictEqual(document.activeElement.tagName, "TD", "focus should now be in field TD");
        assert.strictEqual(
            document.activeElement.textContent,
            "yop",
            "focus should now be in first row field"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "right");
        assert.strictEqual(
            document.activeElement.textContent,
            "yop",
            "should not cycle at end of line"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.textContent,
            "blip",
            "focus should now be in second row field"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.textContent,
            "gnap",
            "focus should now be in third row field"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.textContent,
            "blip",
            "focus should now be in last row field"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.textContent,
            "blip",
            "focus should still be in last row field (arrows do not cycle)"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "right");
        assert.strictEqual(
            document.activeElement.textContent,
            "blip",
            "focus should still be in last row field (arrows still do not cycle)"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "left");
        assert.strictEqual(
            document.activeElement.tagName,
            "INPUT",
            "focus should now be in last row input"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "left");
        assert.strictEqual(
            document.activeElement.tagName,
            "INPUT",
            "should not cycle at start of line"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "up");
        await testUtils.fields.triggerKeydown($(document.activeElement), "right");
        assert.strictEqual(
            document.activeElement.textContent,
            "gnap",
            "focus should now be in third row field"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
    });

    QUnit.skipWOWL("removing a groupby while adding a line from list", async function (assert) {
        assert.expect(1);

        let checkUnselectRow = false;
        testUtils.mock.patch(ListRenderer, {
            unselectRow(options = {}) {
                if (checkUnselectRow) {
                    assert.step("unselectRow");
                }
                return this._super(...arguments);
            },
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <tree multi_edit="1" editable="bottom">
                    <field name="display_name"/>
                    <field name="foo"/>
                </tree>
            `,
            searchViewArch: `
                <search>
                    <field name="foo"/>
                    <group expand="1" string="Group By">
                        <filter name="groupby_foo" context="{'group_by': 'foo'}"/>
                    </group>
                </search>`,
        });

        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Foo");

        // expand group
        await click(target.querySelector("th.o_group_name"));
        await click(target.querySelector("td.o_group_field_row_add a"));
        checkUnselectRow = true;
        await click(target, ".o_searchview_facet .o_facet_remove");
        assert.verifySteps([]);
        testUtils.mock.unpatch(ListRenderer);
    });

    QUnit.skipWOWL(
        "cell-level keyboard navigation in editable grouped list",
        async function (assert) {
            assert.expect(56);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
                groupBy: ["bar"],
            });

            await click($(target).find(".o_group_header:first")); // open first group
            await click($(target).find("td:contains(blip)")); // select row of first group
            assert.hasClass(
                $(target).find("tr.o_data_row:eq(1)"),
                "o_selected_row",
                "second row should be opened"
            );

            var $secondRowInput = $(target).find("tr.o_data_row:eq(1) td:eq(1) input");
            assert.strictEqual(
                $secondRowInput.val(),
                "blip",
                "second record should be in edit mode"
            );

            await testUtils.fields.editAndTrigger($secondRowInput, "blipbloup", "input");
            assert.strictEqual(
                $secondRowInput.val(),
                "blipbloup",
                "second record should be changed but not saved yet"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "escape");

            assert.containsNone(
                document.body,
                ".modal",
                "record has been modified but modal should not be opened"
            );

            assert.doesNotHaveClass(
                $(target).find("tr.o_data_row:eq(1)"),
                "o_selected_row",
                "second row should be closed"
            );
            assert.strictEqual(document.activeElement.tagName, "TD", "focus is in field td");
            assert.strictEqual(
                document.activeElement.textContent,
                "blip",
                "second field of second record should be focused"
            );
            assert.strictEqual(
                $(target).find("tr.o_data_row:eq(1) td:eq(1)").text(),
                "blip",
                "change should not have been saved"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "left");
            assert.strictEqual(
                document.activeElement.tagName,
                "INPUT",
                "record selector should be focused"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "right");
            assert.strictEqual(document.activeElement.tagName, "TD", "focus is in first record td");
            await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
            var $firstRowInput = $(target).find("tr.o_data_row:eq(0) td:eq(1) input");
            assert.hasClass(
                $(target).find("tr.o_data_row:eq(0)"),
                "o_selected_row",
                "first row should be selected"
            );
            assert.strictEqual($firstRowInput.val(), "yop", "first record should be in edit mode");

            await testUtils.fields.editAndTrigger($firstRowInput, "Zipadeedoodah", "input");
            assert.strictEqual(
                $firstRowInput.val(),
                "Zipadeedoodah",
                "first record should be changed but not saved yet"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
            assert.strictEqual(
                $(target).find("tr.o_data_row:eq(0) td:eq(1)").text(),
                "Zipadeedoodah",
                "first record should be saved"
            );
            assert.doesNotHaveClass(
                $(target).find("tr.o_data_row:eq(0)"),
                "o_selected_row",
                "first row should be closed"
            );
            assert.hasClass(
                $(target).find("tr.o_data_row:eq(1)"),
                "o_selected_row",
                "second row should be opened"
            );
            assert.strictEqual(
                $(target).find("tr.o_data_row:eq(1) td:eq(1) input").val(),
                "blip",
                "second record should be in edit mode"
            );

            assert.strictEqual(
                document.activeElement.value,
                "blip",
                "second record input should be focused"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "right");
            assert.strictEqual(
                document.activeElement.value,
                "blip",
                "second record input should still be focused (arrows movements are disabled in edit)"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            await testUtils.fields.triggerKeydown($(document.activeElement), "left");
            assert.strictEqual(
                document.activeElement.value,
                "blip",
                "second record input should still be focused (arrows movements are still disabled in edit)"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "escape");
            assert.doesNotHaveClass(
                $(target).find("tr.o_data_row:eq(1)"),
                "o_selected_row",
                "second row should be closed"
            );
            assert.strictEqual(document.activeElement.tagName, "TD", "focus is in field td");
            assert.strictEqual(
                document.activeElement.textContent,
                "blip",
                "second field of second record should be focused"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");

            assert.strictEqual(
                document.activeElement.tagName,
                "A",
                'should focus the "Add a line" button'
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");

            assert.strictEqual(
                document.activeElement.textContent,
                "No (1)",
                "focus should be on second group header"
            );
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                3,
                "should have 3 rows displayed"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                4,
                "should have 4 rows displayed"
            );
            assert.strictEqual(
                document.activeElement.textContent,
                "No (1)",
                "focus should still be on second group header"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            assert.strictEqual(
                document.activeElement.textContent,
                "blip",
                "second field of last record should be focused"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            assert.strictEqual(
                document.activeElement.tagName,
                "A",
                'should focus the "Add a line" button'
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            assert.strictEqual(
                document.activeElement.tagName,
                "A",
                "arrow navigation should not cycle (focus still on last row)"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
            await testUtils.fields.editAndTrigger(
                $("tr.o_data_row:eq(4) td:eq(1) input"),
                "cheateur arrete de cheater",
                "input"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                6,
                "should have 6 rows displayed (new record + new edit line)"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "escape");
            assert.strictEqual(
                document.activeElement.tagName,
                "A",
                'should focus the "Add a line" button'
            );

            // come back to the top
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");

            assert.strictEqual(document.activeElement.tagName, "TH", "focus is in table header");
            await testUtils.fields.triggerKeydown($(document.activeElement), "left");
            assert.strictEqual(document.activeElement.tagName, "INPUT", "focus is in header input");
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            await testUtils.fields.triggerKeydown($(document.activeElement), "right");
            assert.strictEqual(document.activeElement.tagName, "TD", "focus is in field td");
            assert.strictEqual(
                document.activeElement.textContent,
                "Zipadeedoodah",
                "second field of first record should be focused"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            assert.strictEqual(
                document.activeElement.textContent,
                "Yes (3)",
                "focus should be on first group header"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                2,
                "should have 2 rows displayed (first group should be closed)"
            );
            assert.strictEqual(
                document.activeElement.textContent,
                "Yes (3)",
                "focus should still be on first group header"
            );

            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                2,
                "should have 2 rows displayed"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "right");
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                5,
                "should have 5 rows displayed"
            );
            assert.strictEqual(
                document.activeElement.textContent,
                "Yes (3)",
                "focus is still in header"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "right");
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                5,
                "should have 5 rows displayed"
            );
            assert.strictEqual(
                document.activeElement.textContent,
                "Yes (3)",
                "focus is still in header"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "left");
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                2,
                "should have 2 rows displayed"
            );
            assert.strictEqual(
                document.activeElement.textContent,
                "Yes (3)",
                "focus is still in header"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "left");
            assert.strictEqual(
                $(target).find("tr.o_data_row").length,
                2,
                "should have 2 rows displayed"
            );
            assert.strictEqual(
                document.activeElement.textContent,
                "Yes (3)",
                "focus is still in header"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            assert.strictEqual(
                document.activeElement.textContent,
                "No (2)",
                "focus should now be on second group header"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            assert.strictEqual(document.activeElement.tagName, "TD", "record td should be focused");
            assert.strictEqual(
                document.activeElement.textContent,
                "blip",
                "second field of first record of second group should be focused"
            );

            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            assert.strictEqual(
                document.activeElement.textContent,
                "cheateur arrete de cheater",
                "second field of last record of second group should be focused"
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "down");
            assert.strictEqual(
                document.activeElement.tagName,
                "A",
                'should focus the "Add a line" button'
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            assert.strictEqual(
                document.activeElement.textContent,
                "cheateur arrete de cheater",
                'second field of last record of second group should be focused (special case: the first td of the "Add a line" line was skipped'
            );
            await testUtils.fields.triggerKeydown($(document.activeElement), "up");
            assert.strictEqual(
                document.activeElement.textContent,
                "blip",
                "second field of first record of second group should be focused"
            );
        }
    );

    QUnit.skipWOWL("execute group header button with keyboard navigation", async function (assert) {
        assert.expect(13);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" +
                '<field name="foo"/>' +
                '<groupby name="m2o">' +
                '<button type="object" name="some_method" string="Do this"/>' +
                "</groupby>" +
                "</tree>",
            groupBy: ["m2o"],
            intercepts: {
                execute_action: function (ev) {
                    assert.strictEqual(ev.data.action_data.name, "some_method");
                },
            },
        });

        assert.containsNone(target, ".o_data_row", "all groups should be closed");

        // focus create button as a starting point
        $(target).find(".o_list_button_add").focus();
        assert.ok(document.activeElement.classList.contains("o_list_button_add"));
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.tagName,
            "INPUT",
            "focus should now be on the record selector (list header)"
        );
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.textContent,
            "Value 1 (3)",
            "focus should be on first group header"
        );

        // unfold first group
        await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
        assert.containsN(target, ".o_data_row", 3, "first group should be open");

        // move to first record of opened group
        await testUtils.fields.triggerKeydown($(document.activeElement), "down");
        assert.strictEqual(
            document.activeElement.tagName,
            "INPUT",
            "focus should be in first row checkbox"
        );

        // move back to the group header
        await testUtils.fields.triggerKeydown($(document.activeElement), "up");
        assert.ok(
            document.activeElement.classList.contains("o_group_name"),
            "focus should be back on first group header"
        );

        // fold the group
        await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
        assert.ok(
            document.activeElement.classList.contains("o_group_name"),
            "focus should still be on first group header"
        );
        assert.containsNone(target, ".o_data_row", "first group should now be folded");

        // unfold the group
        await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
        assert.ok(
            document.activeElement.classList.contains("o_group_name"),
            "focus should still be on first group header"
        );
        assert.containsN(target, ".o_data_row", 3, "first group should be open");

        // simulate a move to the group header button with tab (we can't trigger a native event
        // programmatically, see https://stackoverflow.com/a/32429197)
        $(target).find(".o_group_header .o_group_buttons button:first").focus();
        assert.strictEqual(
            document.activeElement.tagName,
            "BUTTON",
            "focus should be on the group header button"
        );

        // click on the button by pressing enter
        await testUtils.fields.triggerKeydown($(document.activeElement), "enter");
        assert.containsN(target, ".o_data_row", 3, "first group should still be open");
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

    QUnit.skipWOWL(
        "add and discard a line through keyboard navigation without crashing",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
                groupBy: ["bar"],
            });

            await click($(target).find(".o_group_header:first")); // open group
            // Triggers ENTER on "Add a line" wrapper cell
            await testUtils.fields.triggerKeydown(
                $(target).find(".o_group_field_row_add"),
                "enter"
            );
            assert.containsN(
                target,
                "tbody:nth(1) .o_data_row",
                4,
                "new data row should be created"
            );
            await click(target.querySelector(".o_list_button_discard"));
            // At this point, a crash manager should appear if no proper link targetting
            assert.containsN(
                target,
                "tbody:nth(1) .o_data_row",
                3,
                "new data row should be discarded."
            );
        }
    );

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
            arch:
                '<tree editable="top">' +
                '<field name="foo"/>' +
                '<field name="priority"/>' +
                '<field name="m2o"/>' +
                "</tree>",
            groupBy: ["priority"],
            mockRPC: function (route, args) {
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
            arch:
                '<tree editable="top">' + '<field name="foo"/>' + '<field name="m2o"/>' + "</tree>",
            groupBy: ["m2o"],
            mockRPC: function (route, args) {
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
        assert.expect(10);

        patchWithCleanup(localization, {
            direction: "ltr",
        });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" +
                '<field name="foo"/>' +
                '<field name="m2o" optional="hide"/>' +
                '<field name="amount"/>' +
                '<field name="reference" optional="hide"/>' +
                "</tree>",
        });

        assert.containsN(target, "th", 3, "should have 3 th, 1 for selector, 2 for columns");

        assert.containsOnce(
            target,
            "table .o_optional_columns_dropdown",
            "should have the optional columns dropdown toggle inside the table"
        );

        const optionalFieldsToggler = target.querySelector("table").lastElementChild;
        assert.ok(
            optionalFieldsToggler.classList.contains("o_optional_columns_dropdown"),
            "The optional fields toggler is the second last element"
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
        // 5 th (1 for checkbox, 4 for columns)
        assert.containsN(target, "th", 4, "should have 4 th");
        assert.ok(
            $(target).find("th:contains(M2O field)").is(":visible"),
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
        // 3 th (1 for checkbox, 2 for columns)
        assert.containsN(target, "th", 3, "should have 3 th");
        assert.notOk(
            $(target).find("th:contains(M2O field)").is(":visible"),
            "should not have a visible m2o field"
        ); //m2o field not displayed

        await click(target, "table .o_optional_columns_dropdown");
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
            arch:
                "<tree>" +
                '<field name="foo"/>' +
                '<field name="m2o" optional="hide"/>' +
                '<field name="amount"/>' +
                '<field name="reference" optional="hide"/>' +
                "</tree>",
        });

        assert.containsOnce(
            target.querySelector("table"),
            ".o_optional_columns_dropdown",
            "should have the optional columns dropdown toggle inside the table"
        );

        const optionalFieldsToggler = target.querySelector("table").lastElementChild;
        assert.ok(
            optionalFieldsToggler.classList.contains("o_optional_columns_dropdown"),
            "The optional fields toggler is the last element"
        );
    });

    QUnit.test(
        "optional fields do not disappear even after listview reload",
        async function (assert) {
            assert.expect(7);
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    "<tree>" +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                    '<field name="amount"/>' +
                    '<field name="reference" optional="hide"/>' +
                    "</tree>",
            });

            assert.containsN(target, "th", 3, "should have 3 th, 1 for selector, 2 for columns");

            // enable optional field
            await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
            assert.notOk(
                target.querySelector(
                    "div.o_optional_columns_dropdown span.dropdown-item:first-child input"
                ).checked
            );
            await click(target, "div.o_optional_columns_dropdown span.dropdown-item:first-child");
            assert.containsN(target, "th", 4, "should have 4 th 1 for selector, 3 for columns");
            assert.ok(
                $(target).find("th:contains(M2O field)").is(":visible"),
                "should have a visible m2o field"
            ); //m2o field

            var firstRowSelector = target.querySelector("tbody .o_list_record_selector input");
            await click(firstRowSelector);
            await reloadListView(target);
            assert.containsN(
                target,
                "th",
                4,
                "should have 4 th 1 for selector, 3 for columns ever after listview reload"
            );
            assert.ok(
                $(target).find("th:contains(M2O field)").is(":visible"),
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

    QUnit.test("selection is kept when optional fields are toggled", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                "<tree>" +
                '<field name="foo"/>' +
                '<field name="m2o" optional="hide"/>' +
                "</tree>",
        });

        assert.containsN(target, "th", 2);

        // select a record
        await click(target.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(target, ".o_list_record_selector input:checked");

        // add an optional field
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");
        assert.containsN(target, "th", 3);
        assert.containsOnce(target, ".o_list_record_selector input:checked");

        // select all records
        await click(target, "thead .o_list_record_selector input");
        assert.containsN(target, ".o_list_record_selector input:checked", 5);

        // remove an optional field
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");
        assert.containsN(target, "th", 2);
        assert.containsN(target, ".o_list_record_selector input:checked", 5);
    });

    QUnit.test("list view with optional fields and async rendering", async function (assert) {
        assert.expect(14);

        const def = makeDeferred();
        const fieldRegistry = registry.category("fields");
        const CharField = fieldRegistry.get("char");

        class AsyncCharField extends CharField {
            setup() {
                super.setup();
                onWillStart(async () => {
                    assert.ok(true, "the rendering must be async");
                    await def;
                });
            }
        }
        fieldRegistry.add("asyncwidget", AsyncCharField);

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

        assert.containsN(target, "th", 2);
        assert.containsNone(target, ".o_optional_columns_dropdown.show");

        // add an optional field (we click on the label on purpose, as it will trigger
        // a second event on the input)
        await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
        assert.containsOnce(target, ".o_optional_columns_dropdown.show");
        assert.containsNone(target, ".o_optional_columns_dropdown input:checked");

        await click(target, ".o_optional_columns_dropdown span.dropdown-item:first-child label");
        assert.containsN(target, "th", 2);
        assert.containsOnce(target, ".o_optional_columns_dropdown.show");
        assert.containsOnce(target, ".o_optional_columns_dropdown input:checked");

        def.resolve();
        await nextTick();
        assert.containsN(target, "th", 3);
        assert.containsOnce(target, ".o_optional_columns_dropdown.show");
        assert.containsOnce(target, ".o_optional_columns_dropdown input:checked");
    });

    // Remove ?
    QUnit.skipWOWL(
        "open list optional fields dropdown position to right place",
        async function (assert) {
            assert.expect(1);

            serverData.models.bar.fields.name = { string: "Name", type: "char", sortable: true };
            serverData.models.bar.fields.foo = { string: "Foo", type: "char", sortable: true };
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
                                        <field name="foo"/>
                                        <field name="name" optional="hide"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
                resId: 1,
            });
            const listWidth = target.querySelector(".o_list_renderer").offsetWidth;

            await click(target, ".o_optional_columns_dropdown .dropdown-toggle");
            assert.strictEqual(
                target.querySelector(".o_optional_columns").offsetLeft,
                listWidth,
                "optional fields dropdown should opened at right place"
            );
        }
    );

    QUnit.skipWOWL("change the viewType of the current action", async function (assert) {
        assert.expect(25);

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

        assert.containsN(target, "th", 3, "should display 3 th (selector + 2 fields)");

        // enable optional field
        await click($(target).find("table .o_optional_columns_dropdown"));
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
        await click($(target).find("div.o_optional_columns_dropdown span.dropdown-item:first"));
        assert.containsN(target, "th", 4, "should display 4 th (selector + 3 fields)");
        assert.ok(
            $(target).find("th:contains(M2O field)").is(":visible"),
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

        assert.containsN(target, "th", 4, "should display 4 th");
        assert.ok(
            $(target).find("th:contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field
        assert.ok(
            $(target).find("th:contains(O2M field)").is(":visible"),
            "should have a visible o2m field"
        ); //m2o field

        // disable optional field
        await click($(target).find("table .o_optional_columns_dropdown"));
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
            $(target).find("div.o_optional_columns_dropdown span.dropdown-item:last input")
        );
        assert.ok(
            $(target).find("th:contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field
        assert.notOk(
            $(target).find("th:contains(O2M field)").is(":visible"),
            "should have a visible o2m field"
        ); //m2o field
        assert.containsN(target, "th", 3, "should display 3 th");

        await doAction(webClient, 1);

        assert.containsNone(target, ".o_list_view", "should not display the list view anymore");
        assert.containsOnce(target, ".o_kanban_view", "should have switched to the kanban view");

        await doAction(webClient, 2);

        assert.containsNone(target, ".o_kanban_view", "should not havethe kanban view anymoe");
        assert.containsOnce(target, ".o_list_view", "should display the list view");

        assert.containsN(target, "th", 3, "should display 3 th");
        assert.ok(
            $(target).find("th:contains(M2O field)").is(":visible"),
            "should have a visible m2o field"
        ); //m2o field
        assert.notOk(
            $(target).find("th:contains(O2M field)").is(":visible"),
            "should have a visible o2m field"
        ); //m2o field
    });

    QUnit.skipWOWL(
        "list view with optional fields rendering and local storage mock",
        async function (assert) {
            assert.expect(12);

            var forceLocalStorage = true;

            var Storage = RamStorage.extend({
                getItem: function (key) {
                    assert.step("getItem " + key);
                    return forceLocalStorage ? '["m2o"]' : this._super.apply(this, arguments);
                },
                setItem: function (key, value) {
                    assert.step("setItem " + key + " to " + value);
                    return this._super.apply(this, arguments);
                },
            });

            var RamStorageService = AbstractStorageService.extend({
                storage: new Storage(),
            });

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch:
                    "<tree>" +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                    '<field name="reference" optional="show"/>' +
                    "</tree>",
                services: {
                    local_storage: RamStorageService,
                },
                view_id: 42,
            });

            var localStorageKey = "optional_fields,foo,target,42,foo,m2o,reference";

            assert.verifySteps(["getItem " + localStorageKey]);

            assert.containsN(target, "th", 3, "should have 3 th, 1 for selector, 2 for columns");

            assert.ok(
                $(target).find("th:contains(M2O field)").is(":visible"),
                "should have a visible m2o field"
            ); //m2o field

            assert.notOk(
                $(target).find("th:contains(Reference Field)").is(":visible"),
                "should not have a visible reference field"
            );

            // optional fields
            await click($(target).find("table .o_optional_columns_dropdown"));
            assert.containsN(
                target,
                "div.o_optional_columns_dropdown span.dropdown-item",
                2,
                "dropdown have 2 optional fields"
            );

            forceLocalStorage = false;
            // enable optional field
            await click(
                $(target).find("div.o_optional_columns_dropdown span.dropdown-item:eq(1) input")
            );

            assert.verifySteps([
                "setItem " + localStorageKey + ' to ["m2o","reference"]',
                "getItem " + localStorageKey,
            ]);

            // 4 th (1 for checkbox, 3 for columns)
            assert.containsN(target, "th", 4, "should have 4 th");

            assert.ok(
                $(target).find("th:contains(M2O field)").is(":visible"),
                "should have a visible m2o field"
            ); //m2o field

            assert.ok(
                $(target).find("th:contains(Reference Field)").is(":visible"),
                "should have a visible reference field"
            );
        }
    );

    QUnit.skipWOWL("quickcreate in a many2one in a list", async function (assert) {
        assert.expect(2);

        await makeView({
            arch: '<tree editable="top"><field name="m2o"/></tree>',
            serverData,
            resModel: "foo",
        });

        await click($(target).find(".o_data_row:first .o_data_cell:first"));

        const $input = $(target).find(".o_data_row:first .o_data_cell:first input");
        await editInput($input, "aaa");
        $input.trigger("keyup");
        $input.trigger("blur");
        document.body.click();

        await testUtils.nextTick();

        assert.containsOnce(document.body, ".modal", "the quick_create modal should appear");

        await click($(".modal .btn-primary:first"));
        await click(document.body);

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

    QUnit.skipWOWL("editable list: resize column headers", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="top">' +
                '<field name="foo"/>' +
                '<field name="reference" optional="hide"/>' +
                "</tree>",
        });

        // Target handle
        const th = target.getElementsByTagName("th")[1];
        const optionalDropdown = target.getElementsByClassName("o_optional_columns")[0];
        const optionalInitialX = optionalDropdown.getBoundingClientRect().x;
        const resizeHandle = th.getElementsByClassName("o_resize")[0];
        const originalWidth = th.offsetWidth;
        const expectedWidth = Math.floor(originalWidth / 2 + resizeHandle.offsetWidth / 2);
        const delta = originalWidth - expectedWidth;

        await testUtils.dom.dragAndDrop(resizeHandle, th, {
            mousemoveTarget: window,
            mouseupTarget: window,
        });
        const optionalFinalX = Math.floor(optionalDropdown.getBoundingClientRect().x);

        assert.strictEqual(
            th.offsetWidth,
            expectedWidth,
            // 1px for the cell right border
            "header width should be halved (plus half the width of the handle)"
        );
        assert.strictEqual(
            optionalFinalX,
            optionalInitialX - delta,
            "optional columns dropdown should have moved the same amount"
        );
    });

    QUnit.skipWOWL("editable list: resize column headers with max-width", async function (assert) {
        // This test will ensure that, on resize list header,
        // the resized element have the correct size and other elements are not resized
        assert.expect(2);
        serverData.models.foo.records[0].foo = "a".repeat(200);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="top">' +
                '<field name="foo"/>' +
                '<field name="bar"/>' +
                '<field name="reference" optional="hide"/>' +
                "</tree>",
        });

        // Target handle
        const th = target.getElementsByTagName("th")[1];
        const thNext = target.getElementsByTagName("th")[2];
        const resizeHandle = th.getElementsByClassName("o_resize")[0];
        const nextResizeHandle = thNext.getElementsByClassName("o_resize")[0];
        const thOriginalWidth = th.offsetWidth;
        const thNextOriginalWidth = thNext.offsetWidth;
        const thExpectedWidth = Math.floor(thOriginalWidth + thNextOriginalWidth);

        await testUtils.dom.dragAndDrop(resizeHandle, nextResizeHandle, {
            mousemoveTarget: window,
            mouseupTarget: window,
        });

        const thFinalWidth = th.offsetWidth;
        const thNextFinalWidth = thNext.offsetWidth;
        const thWidthDiff = Math.abs(thExpectedWidth - thFinalWidth);

        assert.ok(thWidthDiff <= 1, "Wrong width on resize");
        assert.ok(thNextOriginalWidth === thNextFinalWidth, "Width must not have been changed");
    });

    QUnit.skipWOWL(
        "resize column with several x2many lists in form group",
        async function (assert) {
            assert.expect(3);

            serverData.models.bar.fields.text = { string: "Text field", type: "char" };
            serverData.models.foo.records[0].o2m = [1, 2];

            const form = await makeView({
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

            const th = form.el.getElementsByTagName("th")[0];
            const resizeHandle = th.getElementsByClassName("o_resize")[0];
            const firstTableInitialWidth = form.el.querySelectorAll(".o_field_x2many_list table")[0]
                .offsetWidth;
            const secondTableInititalWidth = form.el.querySelectorAll(
                ".o_field_x2many_list table"
            )[1].offsetWidth;

            assert.strictEqual(
                firstTableInitialWidth,
                secondTableInititalWidth,
                "both table columns have same width"
            );

            await testUtils.dom.dragAndDrop(resizeHandle, form.el.getElementsByTagName("th")[1], {
                position: "right",
            });

            assert.notEqual(
                firstTableInitialWidth,
                form.el.querySelectorAll("thead")[0].offsetWidth,
                "first o2m table is resized and width of table has changed"
            );
            assert.strictEqual(
                secondTableInititalWidth,
                form.el.querySelectorAll("thead")[1].offsetWidth,
                "second o2m table should not be impacted on first o2m in group resized"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "resize column with x2many list with several fields in form notebook",
        async function (assert) {
            assert.expect(1);

            serverData.models.foo.records[0].o2m = [1, 2];

            const form = await makeView({
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

            const th = form.el.getElementsByTagName("th")[0];
            const resizeHandle = th.getElementsByClassName("o_resize")[0];
            const listInitialWidth = form.el.querySelector(".o_list_view").offsetWidth;

            await testUtils.dom.dragAndDrop(resizeHandle, form.el.getElementsByTagName("th")[1], {
                position: "right",
            });

            assert.strictEqual(
                form.el.querySelector(".o_list_view").offsetWidth,
                listInitialWidth,
                "resizing the column should not impact the width of list"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL("enter edition in editable list with <widget>", async function (assert) {
        assert.expect(1);

        // var MyWidget = Widget.extend({
        //     start: function () {
        //         this.$el.ht--removethis--ml('<i class="fa fa-info"/>');
        //     },
        // });
        // widgetRegistry.add("some_widget", MyWidget);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch:
                '<tree editable="top">' +
                '<widget name="some_widget"/>' +
                '<field name="int_field"/>' +
                '<field name="qux"/>' +
                "</tree>",
        });

        // click on int_field cell of first row
        await click($(target).find(".o_data_row:first .o_data_cell:nth(1)"));
        assert.strictEqual(document.activeElement.name, "int_field");

        delete widgetRegistry.map.test;
    });

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

    QUnit.skipWOWL("Date in evaluation context works with date field", async function (assert) {
        assert.expect(11);

        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        const unpatchDate = testUtils.mock.patchDate(1997, 0, 9, 12, 0, 0);
        testUtils.mock.patch(BasicModel, {
            _getEvalContext() {
                const evalContext = this._super(...arguments);
                assert.ok(dateRegex.test(evalContext.today));
                assert.strictEqual(evalContext.current_date, evalContext.today);
                return evalContext;
            },
        });

        serverData.models.foo.fields.birthday = { string: "Birthday", type: "date" };
        serverData.models.foo.records[0].birthday = "1997-01-08";
        serverData.models.foo.records[1].birthday = "1997-01-09";
        serverData.models.foo.records[2].birthday = "1997-01-10";

        await makeView({
            arch: `
                <tree>
                    <field name="birthday" decoration-danger="birthday > today"/>
                </tree>`,
            serverData,
            resModel: "foo",
        });

        assert.containsOnce(target, ".o_data_row .text-danger");

        unpatchDate();
        testUtils.mock.unpatch(BasicModel);
    });

    QUnit.skipWOWL(
        "Datetime in evaluation context works with datetime field",
        async function (assert) {
            assert.expect(6);

            const datetimeRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
            const unpatchDate = testUtils.mock.patchDate(1997, 0, 9, 12, 0, 0);
            testUtils.mock.patch(BasicModel, {
                _getEvalContext() {
                    const evalContext = this._super(...arguments);
                    assert.ok(datetimeRegex.test(evalContext.now));
                    return evalContext;
                },
            });

            /**
             * Returns "1997-01-DD HH:MM:00" with D, H and M holding current UTC values
             * from patched date + (deltaMinutes) minutes.
             * This is done to allow testing from any timezone since UTC values are
             * calculated with the offset of the current browser.
             */
            function dateStringDelta(deltaMinutes) {
                const d = new Date(Date.now() + 1000 * 60 * deltaMinutes);
                return `1997-01-${String(d.getUTCDate()).padStart(2, "0")} ${String(
                    d.getUTCHours()
                ).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}:00`;
            }

            // "datetime" field may collide with "datetime" object in context
            serverData.models.foo.fields.birthday = { string: "Birthday", type: "datetime" };
            serverData.models.foo.records[0].birthday = dateStringDelta(-30);
            serverData.models.foo.records[1].birthday = dateStringDelta(0);
            serverData.models.foo.records[2].birthday = dateStringDelta(+30);

            await makeView({
                arch: `
                <tree>
                    <field name="birthday" decoration-danger="birthday > now"/>
                </tree>`,
                serverData,
                resModel: "foo",
            });

            assert.containsOnce(target, ".o_data_row .text-danger");

            unpatchDate();
            testUtils.mock.unpatch(BasicModel);
        }
    );

    QUnit.skipWOWL("update control panel while list view is mounting", async function (assert) {
        let mountedCounterCall = 0;

        patch(ControlPanel.prototype, "test.ControlPanel", {
            mounted() {
                mountedCounterCall = mountedCounterCall + 1;
                assert.step(`mountedCounterCall-${mountedCounterCall}`);
                this._super(...arguments);
            },
        });

        const MyListView = ListView.extend({
            config: Object.assign({}, ListView.prototype.config, {
                Controller: ListController.extend({
                    async start() {
                        await this._super(...arguments);
                        this.renderer._updateSelection();
                    },
                }),
            }),
        });

        assert.expect(2);

        await makeView({
            View: MyListView,
            model: "event",
            serverData,
            arch: '<tree><field name="name"/></tree>',
        });

        assert.verifySteps(["mountedCounterCall-1"]);

        unpatch(ControlPanel.prototype, "test.ControlPanel");
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
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip"]
        );
        assert.containsN(target, ".o_data_row", 4);

        await click(target, ".o_list_button_add");
        await editInput(target, '.o_data_cell [name="foo"] input', "test");

        // change action and come back
        await doAction(webClient, 2);
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip", "test"]
        );
        assert.containsN(target, ".o_data_row", 5);
    });

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
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip"]
        );

        await click(target.querySelector('.o_data_cell [name="foo"]'));
        await editInput(target, '.o_data_cell [name="foo"] input', "test");

        // change action and come back
        await doAction(webClient, 2);
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
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

        await doAction(webClient, 1);
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["yop", "blip", "gnap", "blip"]
        );

        await click(target.querySelector('.o_data_cell [name="foo"]'));
        await editInput(target, '.o_data_cell [name="foo"] input', "");
        await assert.rejects(doAction(webClient, 2));
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["", "blip", "gnap", "blip"]
        );
        assert.hasClass(target.querySelector('.o_data_cell [name="foo"]'), "o_field_invalid");
        assert.containsN(target, ".o_data_row", 4);
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
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["yop", "blip", "gnap"]
        );

        await click(target.querySelector(".o_list_button_add"));
        await editInput(target, '.o_data_cell [name="foo"] input', "test");
        await pagerNext(target);
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["blip", "test"]
        );

        await pagerPrevious(target);
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
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
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["yop", "blip", "gnap"]
        );

        await click(target.querySelector('.o_data_cell [name="foo"]'));
        await editInput(target, '.o_data_cell [name="foo"] input', "test");
        await pagerNext(target);
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["blip"]
        );

        await pagerPrevious(target);
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
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
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["yop", "blip", "gnap"]
        );

        await click(target.querySelector('.o_data_cell [name="foo"]'));
        await editInput(target, '.o_data_cell [name="foo"] input', "");
        await pagerNext(target);
        assert.hasClass(target.querySelector('.o_data_cell [name="foo"]'), "o_field_invalid");
        assert.deepEqual(
            [...target.querySelectorAll('.o_data_cell [name="foo"]')].map((el) => el.textContent),
            ["", "blip", "gnap"]
        );
    });

    QUnit.skipWOWL("Auto save: save on closing tab/browser", async function (assert) {
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
                if (model === "foo" && method === "write") {
                    assert.deepEqual(args, [[1], { foo: "test" }]);
                }
                return this._super(...arguments);
            },
        });

        await click($(target).find('.o_field_cell[name="foo"]:first'));
        await editInput($(target).find('.o_field_widget[name="foo"]'), "test");

        window.dispatchEvent(new Event("beforeunload"));
        await testUtils.nextTick();
    });

    QUnit.skipWOWL(
        "Auto save: save on closing tab/browser (invalid field)",
        async function (assert) {
            assert.expect(1);

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
                    return this._super(...arguments);
                },
            });

            await click($(target).find('.o_field_cell[name="foo"]:first'));
            await editInput($(target).find('.o_field_widget[name="foo"]'), "");

            window.dispatchEvent(new Event("beforeunload"));
            await testUtils.nextTick();

            assert.verifySteps([], "should not save because of invalid field");
        }
    );

    QUnit.skipWOWL("Auto save: save on closing tab/browser (onchanges)", async function (assert) {
        assert.expect(1);

        serverData.models.foo.onchanges = {
            int_field: function (obj) {
                obj.foo = `${obj.int_field}`;
            },
        };

        const def = testUtils.makeTestPromise();
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
                if (model === "foo" && method === "write") {
                    assert.deepEqual(args, [[1], { int_field: 2021 }]);
                }
                return this._super(...arguments);
            },
        });

        await click($(target).find('.o_field_cell[name="int_field"]:first'));
        await editInput($(target).find('.o_field_widget[name="int_field"]'), "2021");

        window.dispatchEvent(new Event("beforeunload"));
        await testUtils.nextTick();
    });

    QUnit.skipWOWL(
        "edition, then navigation with tab (with a readonly re-evaluated field and onchange)",
        async function (assert) {
            // This test makes sure that if we have a cell in a row that will become
            // read-only after editing another cell, in case the keyboard navigation
            // move over it before it becomes read-only and there are unsaved changes
            // (which will trigger an onchange), the focus of the next activable
            // field will not crash
            assert.expect(4);

            serverData.models.bar.onchanges = {
                o2m: function () {},
            };
            serverData.models.bar.fields.o2m = {
                string: "O2M field",
                type: "one2many",
                relation: "foo",
            };
            serverData.models.bar.records[0].o2m = [1, 4];

            var form = await makeView({
                type: "form",
                model: "bar",
                resId: 1,
                serverData,
                arch:
                    "<form>" +
                    "<group>" +
                    '<field name="display_name"/>' +
                    '<field name="o2m">' +
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    "<field name=\"date\" attrs=\"{'readonly': [('foo', '!=', 'yop')]}\"/>" +
                    '<field name="int_field"/>' +
                    "</tree>" +
                    "</field>" +
                    "</group>" +
                    "</form>",
                mockRPC: function (route, args) {
                    if (args.method === "onchange") {
                        assert.step(args.method + ":" + args.model);
                    }
                    return this._super.apply(this, arguments);
                },
                fieldDebounce: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            var jq_evspecial_focus_trigger = $.event.special.focus.trigger;
            // As KeyboardEvent will be triggered by JS and not from the
            // User-Agent itself, the focus event will not trigger default
            // action (event not being trusted), we need to manually trigger
            // 'change' event on the currently focused element
            $.event.special.focus.trigger = function () {
                if (this !== document.activeElement && this.focus) {
                    var activeElement = document.activeElement;
                    this.focus();
                    $(activeElement).trigger("change");
                }
            };

            // editable target, click on first td and press TAB
            await click(form.$(".o_data_cell:contains(yop)"));
            assert.strictEqual(
                document.activeElement,
                form.$('tr.o_selected_row input[name="foo"]')[0],
                "focus should be on an input with name = foo"
            );
            editInput(form.$('tr.o_selected_row input[name="foo"]'), "new value");
            var tabEvent = $.Event("keydown", { which: $.ui.keyCode.TAB });
            await testUtils.dom.triggerEvents(form.$('tr.o_selected_row input[name="foo"]'), [
                tabEvent,
            ]);
            assert.strictEqual(
                document.activeElement,
                form.$('tr.o_selected_row input[name="int_field"]')[0],
                "focus should be on an input with name = int_field"
            );

            // Restore origin jQuery special trigger for 'focus'
            $.event.special.focus.trigger = jq_evspecial_focus_trigger;

            assert.verifySteps(["onchange:bar"], "onchange method should have been called");
            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "selecting a row after another one containing a table within an html field should be the correct one",
        async function (assert) {
            assert.expect(1);

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
                arch: '<tree editable="top" multi_edit="1">' + '<field name="html"/>' + "</tree>",
            });

            await click($(target).find(".o_data_cell:eq(1)"));
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
});
