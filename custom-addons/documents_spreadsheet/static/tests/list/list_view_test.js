/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { insertList } from "@spreadsheet_edition/bundle/list/list_init_callback";
import { InsertListSpreadsheetMenu } from "@spreadsheet_edition/assets/list_view/insert_list_spreadsheet_menu_owl";
import { selectCell, setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getBasicData, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { getCellFormula, getEvaluatedCell } from "@spreadsheet/../tests/utils/getters";
import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    patchDate,
    editInput,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import {
    createSpreadsheetFromListView,
    invokeInsertListInSpreadsheetDialog,
} from "../utils/list_helpers";
import { createSpreadsheet } from "../spreadsheet_test_utils.js";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";
import { session } from "@web/session";
import * as dsHelpers from "@web/../tests/core/domain_selector_tests";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/utils/list";

const { topbarMenuRegistry, cellMenuRegistry } = spreadsheet.registries;
const { toZone } = spreadsheet.helpers;

QUnit.module("documents_spreadsheet > list view", {}, () => {
    QUnit.test("List export with a invisible field", async (assert) => {
        const { model } = await createSpreadsheetFromListView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,list": `
                        <tree string="Partners">
                            <field name="foo" column_invisible="1"/>
                            <field name="bar"/>
                        </tree>`,
                    "partner,false,search": "<search/>",
                },
            },
        });
        assert.deepEqual(model.getters.getListDefinition("1").columns, ["bar"]);
    });

    QUnit.test("List export with a widget handle", async (assert) => {
        const { model } = await createSpreadsheetFromListView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,list": `
                            <tree string="Partners">
                                <field name="foo" widget="handle"/>
                                <field name="bar"/>
                            </tree>`,
                    "partner,false,search": "<search/>",
                },
            },
        });
        assert.deepEqual(model.getters.getListDefinition("1").columns, ["bar"]);
    });

    QUnit.test("property fields are not exported", async (assert) => {
        const data = getBasicData();
        const propertyDefinition = {
            type: "char",
            name: "property_char",
            string: "Property char",
        };
        const product = data.product.records[0];
        product.properties_definitions = [propertyDefinition];
        data.partner.records = [
            {
                id: 1,
                bar: true,
                product_id: product.id,
                partner_properties: [{ ...propertyDefinition, value: "CHAR" }],
            },
        ];
        const { model } = await createSpreadsheetFromListView({
            actions: async (fixture) => {
                // display the property which is an optional column
                await click(fixture, ".o_optional_columns_dropdown_toggle");
                await click(fixture, ".o_optional_columns_dropdown input[type='checkbox']");
                assert.containsOnce(
                    fixture,
                    ".o_list_renderer th[data-name='partner_properties.property_char']"
                );
                assert.step("display_property");
            },
            serverData: {
                models: data,
                views: {
                    "partner,false,list": /*xml*/ `
                        <tree>
                            <field name="product_id"/>
                            <field name="bar"/>
                            <field name="partner_properties"/>
                        </tree>`,
                    "partner,false,search": "<search/>",
                },
            },
        });
        assert.deepEqual(model.getters.getListDefinition("1").columns, ["product_id", "bar"]);
        assert.verifySteps(["display_property"]);
    });

    QUnit.test("json fields are not exported", async (assert) => {
        const { model } = await createSpreadsheetFromListView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,list": `
                        <tree string="Partners">
                            <field name="jsonField"/>
                            <field name="bar"/>
                        </tree>`,
                    "partner,false,search": "<search/>",
                },
            },
        });
        assert.deepEqual(model.getters.getListDefinition("1").columns, ["bar"]);
    });

    QUnit.test("Open list properties properties", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();

        await doMenuAction(topbarMenuRegistry, ["data", "item_list_1"], env);
        await nextTick();
        const target = getFixture();
        let title = target.querySelector(".o-sidePanelTitle").innerText;
        assert.equal(title, "List properties");

        const sections = target.querySelectorAll(".o_side_panel_section");
        assert.equal(sections.length, 4, "it should have 4 sections");
        const [pivotName, pivotModel, domain] = sections;

        assert.equal(pivotName.children[0].innerText, "List Name");
        assert.equal(pivotName.children[1].innerText, "(#1) Partners");

        assert.equal(pivotModel.children[0].innerText, "Model");
        assert.equal(pivotModel.children[1].innerText, "Partner (partner)");

        assert.equal(domain.children[0].innerText, "Domain");
        assert.equal(domain.children[1].innerText, "Match all records\nInclude archived");

        // opening from a non pivot cell
        model.dispatch("SELECT_ODOO_LIST", {});
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId: undefined,
        });
        await nextTick();
        title = target.querySelector(".o-sidePanelTitle").innerText;
        assert.equal(title, "List properties");

        assert.containsOnce(target, ".o_side_panel_select");
    });

    QUnit.test("Deleting the list closes the side panel", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        const [listId] = model.getters.getListIds();
        model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId,
        });
        await nextTick();
        const fixture = getFixture();
        const titleSelector = ".o-sidePanelTitle";
        assert.equal(fixture.querySelector(titleSelector).innerText, "List properties");

        model.dispatch("REMOVE_ODOO_LIST", { listId });
        await nextTick();
        assert.equal(fixture.querySelector(titleSelector), null);
        assert.equal(model.getters.getSelectedListId(), undefined);
    });

    QUnit.test("Undo a list insertion closes the side panel", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        const [listId] = model.getters.getListIds();
        model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId,
        });
        await nextTick();
        const fixture = getFixture();
        const titleSelector = ".o-sidePanelTitle";
        assert.equal(fixture.querySelector(titleSelector).innerText, "List properties");

        model.dispatch("REQUEST_UNDO");
        model.dispatch("REQUEST_UNDO");
        await nextTick();
        assert.equal(fixture.querySelector(titleSelector), null);
        assert.equal(model.getters.getSelectedListId(), undefined);
    });

    QUnit.test("Add list in an existing spreadsheet", async (assert) => {
        const { model } = await createSpreadsheetFromListView();
        const list = model.getters.getListDefinition("1");
        const fields = model.getters.getListDataSource("1").getFields();
        const callback = insertList.bind({ isEmptySpreadsheet: false })({
            list: list,
            threshold: 10,
            fields: fields,
        });
        model.dispatch("CREATE_SHEET", { sheetId: "42", position: 1 });
        const activeSheetId = model.getters.getActiveSheetId();
        assert.deepEqual(model.getters.getSheetIds(), [activeSheetId, "42"]);
        await callback(model);
        assert.strictEqual(model.getters.getSheetIds().length, 3);
        assert.deepEqual(model.getters.getSheetIds()[0], activeSheetId);
        assert.deepEqual(model.getters.getSheetIds()[1], "42");
    });

    QUnit.test("Verify absence of list properties on non-list cell", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        selectCell(model, "Z26");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "listing_properties");
        assert.notOk(root.isVisible(env));
    });

    QUnit.test(
        "Verify absence of list properties on formula with invalid list Id",
        async function (assert) {
            const { model, env } = await createSpreadsheetFromListView();
            setCellContent(model, "A1", `=ODOO.LIST.HEADER("fakeId", "foo")`);
            const root = cellMenuRegistry.getAll().find((item) => item.id === "listing_properties");
            assert.notOk(root.isVisible(env));
            setCellContent(model, "A1", `=ODOO.LIST("fakeId", "2", "bar")`);
            assert.notOk(root.isVisible(env));
        }
    );

    QUnit.test("Re-insert a list correctly ask for lines number", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        selectCell(model, "Z26");
        await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
        await nextTick();
        /** @type {HTMLInputElement} */
        const input = document.body.querySelector(".modal-body input");
        assert.ok(input);
        assert.strictEqual(input.type, "number");

        await click(document, ".o_dialog .btn-secondary"); // cancel
        assert.strictEqual(getCellFormula(model, "Z26"), "", "the list is not re-inserted");

        await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
        await nextTick();
        await click(document, ".o_dialog .btn-primary"); // confirm
        assert.strictEqual(
            getCellFormula(model, "Z26"),
            '=ODOO.LIST.HEADER(1,"foo")',
            "the list is re-inserted"
        );
    });

    QUnit.test("Re-insert a list with a selected number of records", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        selectCell(model, "Z1");

        await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
        await nextTick();

        /** @type {HTMLInputElement} */
        const input = document.body.querySelector(".modal-body input");
        input.value = 2000;
        await triggerEvent(input, null, "input");
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));

        assert.strictEqual(model.getters.getNumberRows(model.getters.getActiveSheetId()), 2001);
    });

    QUnit.test(
        "Validates input and shows error message when input is invalid",
        async function (assert) {
            const { model, env } = await createSpreadsheetFromListView();
            selectCell(model, "Z1");

            await doMenuAction(
                topbarMenuRegistry,
                ["data", "reinsert_list", "reinsert_list_1"],
                env
            );
            await nextTick();

            /** @type {HTMLInputElement} */
            const input = document.body.querySelector(".modal-body input");
            input.value = "";
            await triggerEvent(input, null, "input");

            await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
            assert.containsOnce(document.body, ".modal-body span.text-danger");

            const errorMessage = document.body.querySelector(
                ".modal-body span.text-danger"
            ).textContent;
            assert.strictEqual(
                errorMessage,
                "Please enter a valid number.",
                "Expected error message"
            );
        }
    );

    QUnit.test("user related context is not saved in the spreadsheet", async function (assert) {
        setupViewRegistries();

        registry.category("favoriteMenu").add(
            "insert-list-spreadsheet-menu",
            {
                Component: InsertListSpreadsheetMenu,
                groupNumber: 4,
            },
            { sequence: 5 }
        );

        patchWithCleanup(ListRenderer.prototype, {
            getListForSpreadsheet() {
                const result = super.getListForSpreadsheet(...arguments);
                assert.deepEqual(
                    result.list.context,
                    {
                        default_stage_id: 5,
                    },
                    "user related context is not stored in context"
                );
                return result;
            },
        });

        const userContext = {
            allowed_company_ids: [15],
            tz: "bx",
            lang: "FR",
            uid: 4,
        };
        const testSession = {
            uid: 4,
            user_companies: {
                allowed_companies: {
                    15: { id: 15, name: "Hermit" },
                },
                current_company: 15,
            },
            user_context: userContext,
        };
        patchWithCleanup(session, testSession);
        const context = {
            ...userContext,
            default_stage_id: 5,
        };
        const serverData = { models: getBasicData() };
        const { env } = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            context,
            arch: `
                <tree string="Partners">
                    <field name="bar"/>
                    <field name="product_id"/>
                </tree>
            `,
            config: {
                actionType: "ir.actions.act_window",
                getDisplayName: () => "Test",
                viewType: "list",
            },
        });
        const target = getFixture();
        await invokeInsertListInSpreadsheetDialog(env);
        await click(target, ".modal button.btn-primary");
    });

    QUnit.test("Can see record of a list", async function (assert) {
        const { webClient, model } = await createSpreadsheetFromListView();
        const listId = model.getters.getListIds()[0];
        const dataSource = model.getters.getListDataSource(listId);
        const env = {
            ...webClient.env,
            model,
            services: {
                ...model.config.custom.env.services,
                action: {
                    doAction: (params) => {
                        assert.step(params.res_model);
                        assert.step(params.res_id.toString());
                    },
                },
            },
        };
        selectCell(model, "A2");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
        await root.execute(env);
        assert.verifySteps(["partner", dataSource.getIdFromPosition(0).toString()]);

        selectCell(model, "A3");
        await root.execute(env);
        assert.verifySteps(["partner", dataSource.getIdFromPosition(1).toString()]);

        // From a cell inside a merge
        model.dispatch("ADD_MERGE", {
            sheetId: model.getters.getActiveSheetId(),
            target: [toZone("A3:B3")],
            force: true, // there are data in B3
        });
        selectCell(model, "B3");
        await root.execute(env);
        assert.verifySteps(["partner", dataSource.getIdFromPosition(1).toString()]);
    });

    QUnit.test(
        "See record of list is only displayed on list formula with only one list formula",
        async function (assert) {
            const { webClient, model } = await createSpreadsheetFromListView();
            const env = {
                ...webClient.env,
                model,
                services: model.config.custom.env.services,
            };
            setCellContent(model, "A1", "test");
            setCellContent(model, "A2", `=ODOO.LIST("1","1","foo")`);
            setCellContent(model, "A3", `=ODOO.LIST("1","1","foo")+LIST("1","1","foo")`);
            const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");

            selectCell(model, "A1");
            assert.strictEqual(root.isVisible(env), false);
            selectCell(model, "A2");
            assert.strictEqual(root.isVisible(env), true);
            selectCell(model, "A3");
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test("See records is visible even if the formula is lowercase", async function (assert) {
        const { env, model } = await createSpreadsheetFromListView();
        selectCell(model, "B2");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
        assert.ok(root.isVisible(env));
        setCellContent(model, "B2", getCellFormula(model, "B2").replace("ODOO.LIST", "odoo.list"));
        assert.ok(root.isVisible(env));
    });

    QUnit.test("See records is not visible if the formula is in error", async function (assert) {
        const { env, model } = await createSpreadsheetFromListView();
        selectCell(model, "B2");
        const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
        assert.ok(root.isVisible(env));
        setCellContent(
            model,
            "B2",
            getCellFormula(model, "B2").replace(`ODOO.LIST(1`, `ODOO.LIST("5)`)
        ); //Invalid id
        assert.ok(getEvaluatedCell(model, "B2").error.message);
        assert.notOk(root.isVisible(env));
    });

    QUnit.test("See record.isVisible() don't throw on spread values", async function (assert) {
        const { env, model } = await createSpreadsheet();
        setCellContent(model, "A1", "A1");
        setCellContent(model, "A2", "A2");
        setCellContent(model, "C1", "=TRANSPOSE(A1:A2)");
        selectCell(model, "D1");
        await nextTick();
        const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
        assert.notOk(root.isVisible(env));
    });

    QUnit.test("Update the list title from the side panel", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView();
        // opening from a pivot cell
        const sheetId = model.getters.getActiveSheetId();
        const listA3 = model.getters.getListIdFromPosition({ sheetId, col: 0, row: 2 });
        model.dispatch("SELECT_ODOO_LIST", { listId: listA3 });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId: listA3,
        });
        await nextTick();
        await click(document.body.querySelector(".o_sp_en_rename"));
        await editInput(document, ".o_sp_en_name", "new name");
        await click(document.body.querySelector(".o_sp_en_save"));
        assert.equal(model.getters.getListName(listA3), "new name");
    });

    QUnit.test("list with a contextual domain", async (assert) => {
        // TODO: the date is coded at 12PM so the test won't fail if the timezone is not UTC. It will still fail on some
        // timezones (GMT +13). The good way to do the test would be to patch the time zone and the date correctly.
        // But PyDate uses new Date() instead of luxon, which cannot be correctly patched.
        patchDate(2016, 4, 14, 12, 0, 0);
        const serverData = getBasicServerData();
        serverData.models.partner.records = [
            {
                id: 1,
                probability: 0.5,
                date: "2016-05-14",
            },
        ];
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter string="Filter" name="filter" domain="[('date', '=', context_today())]"/>
            </search>
        `;
        serverData.views["partner,false,list"] = /* xml */ `
            <tree>
                <field name="foo"/>
            </tree>
        `;
        const { model } = await createSpreadsheetFromListView({
            serverData,
            additionalContext: { search_default_filter: 1 },
            mockRPC: function (route, args) {
                if (args.method === "web_search_read") {
                    assert.deepEqual(
                        args.kwargs.domain,
                        [["date", "=", "2016-05-14"]],
                        "data should be fetched with the evaluated the domain"
                    );
                    assert.step("web_search_read");
                }
            },
        });
        const listId = "1";
        assert.deepEqual(
            model.getters.getListDefinition(listId).domain,
            '[("date", "=", context_today())]'
        );
        assert.deepEqual(
            model.exportData().lists[listId].domain,
            '[("date", "=", context_today())]',
            "domain is exported with the dynamic value"
        );
        assert.verifySteps([
            "web_search_read", // list view is loaded
            "web_search_read", // the data is loaded in the spreadsheet
        ]);
    });

    QUnit.test("Update the list domain from the side panel", async function (assert) {
        const { model, env } = await createSpreadsheetFromListView({
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    return true;
                }
            },
        });
        const [listId] = model.getters.getListIds();
        model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId,
        });
        await nextTick();
        const fixture = getFixture();
        await click(fixture.querySelector(".o_edit_domain"));
        await dsHelpers.addNewRule(fixture);
        await click(fixture.querySelector(".modal-footer .btn-primary"));
        assert.deepEqual(model.getters.getListDefinition(listId).domain, [["id", "=", 1]]);
        assert.equal(dsHelpers.getConditionText(fixture), "ID = 1");
    });

    QUnit.test(
        "Inserting a list preserves the ascending sorting from the list",
        async function (assert) {
            const serverData = getBasicServerData();
            serverData.models.partner.fields.foo.sortable = true;
            const { model } = await createSpreadsheetFromListView({
                serverData,
                orderBy: [{ name: "foo", asc: true }],
                linesNumber: 4,
            });
            assert.ok(getEvaluatedCell(model, "A2").value <= getEvaluatedCell(model, "A3").value);
            assert.ok(getEvaluatedCell(model, "A3").value <= getEvaluatedCell(model, "A4").value);
            assert.ok(getEvaluatedCell(model, "A4").value <= getEvaluatedCell(model, "A5").value);
        }
    );

    QUnit.test(
        "Inserting a list preserves the descending sorting from the list",
        async function (assert) {
            const serverData = getBasicServerData();
            serverData.models.partner.fields.foo.sortable = true;
            const { model } = await createSpreadsheetFromListView({
                serverData,
                orderBy: [{ name: "foo", asc: false }],
                linesNumber: 4,
            });
            assert.ok(getEvaluatedCell(model, "A2").value >= getEvaluatedCell(model, "A3").value);
            assert.ok(getEvaluatedCell(model, "A3").value >= getEvaluatedCell(model, "A4").value);
            assert.ok(getEvaluatedCell(model, "A4").value >= getEvaluatedCell(model, "A5").value);
        }
    );

    QUnit.test(
        "Sorting from the list is displayed in the properties panel",
        async function (assert) {
            const serverData = getBasicServerData();
            serverData.models.partner.fields.foo.sortable = true;
            serverData.models.partner.fields.bar.sortable = true;
            const { model, env } = await createSpreadsheetFromListView({
                serverData,
                orderBy: [
                    { name: "foo", asc: true },
                    { name: "bar", asc: false },
                ],
                linesNumber: 4,
            });
            const sheetId = model.getters.getActiveSheetId();
            const listId = model.getters.getListIds(sheetId)[0];
            model.dispatch("SELECT_ODOO_LIST", { listId });
            env.openSidePanel("LIST_PROPERTIES_PANEL", {
                listId,
            });
            await nextTick();
            const fixture = getFixture();
            const sortingSection = fixture.querySelectorAll(".o_side_panel_section")[3];
            const barSortingText = sortingSection.querySelectorAll("div")[1].innerText;
            const fooSortingText = sortingSection.querySelectorAll("div")[2].innerText;
            assert.strictEqual(barSortingText, "Bar (descending)");
            assert.strictEqual(fooSortingText, "Foo (ascending)");
        }
    );

    QUnit.test("can refresh a sorted list in the properties panel", async function (assert) {
        const serverData = getBasicServerData();
        serverData.models.partner.fields.foo.sortable = true;
        serverData.models.partner.fields.bar.sortable = true;
        const { model, env } = await createSpreadsheetFromListView({
            serverData,
            orderBy: [{ name: "foo", asc: true }],
            linesNumber: 4,
        });
        const sheetId = model.getters.getActiveSheetId();
        const listId = model.getters.getListIds(sheetId)[0];
        model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {
            listId,
        });
        await nextTick();
        const fixture = getFixture();
        const sortingSection = fixture.querySelectorAll(".o_side_panel_section")[3];
        assert.strictEqual(sortingSection.querySelectorAll("div")[1].innerText, "Foo (ascending)");
        await click(fixture, ".o_refresh_list");
        assert.strictEqual(sortingSection.querySelectorAll("div")[1].innerText, "Foo (ascending)");
    });

    QUnit.test(
        "Opening the sidepanel of a list while the panel of another list is open updates the side panel",
        async function (assert) {
            const { model, env } = await createSpreadsheetFromListView({});
            insertListInSpreadsheet(model, {
                model: "product",
                columns: ["name", "active"],
            });

            const listIds = model.getters.getListIds();
            const fixture = getFixture();

            model.dispatch("SELECT_ODOO_LIST", { listId: listIds[0] });
            env.openSidePanel("LIST_PROPERTIES_PANEL", {});
            await nextTick();
            let modelName = fixture.querySelector(".o_side_panel_section .o_model_name");
            assert.equal(modelName.innerText, "Partner (partner)");

            model.dispatch("SELECT_ODOO_LIST", { listId: listIds[1] });
            env.openSidePanel("LIST_PROPERTIES_PANEL", {});
            await nextTick();
            modelName = fixture.querySelector(".o_side_panel_section .o_model_name");
            assert.equal(modelName.innerText, "Product (product)");
        }
    );
});
