import {
    defineDocumentSpreadsheetModels,
    defineDocumentSpreadsheetTestAction,
    getBasicData,
    getBasicServerData,
    getDocumentBasicData,
} from "@documents_spreadsheet/../tests/helpers/data";
import {
    createSpreadsheetFromListView,
    invokeInsertListInSpreadsheetDialog,
    spawnListViewForSpreadsheet,
} from "@documents_spreadsheet/../tests/helpers/list_helpers";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { getHighlightsFromStore } from "@documents_spreadsheet/../tests/helpers/store_helpers";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { describe, expect, getFixture, test } from "@odoo/hoot";
import { hover, leave } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { onMounted } from "@odoo/owl";
import { selectCell, setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { Partner, Product, ResUsers } from "@spreadsheet/../tests/helpers/data";
import {
    getCellFormula,
    getCellValue,
    getEvaluatedCell,
} from "@spreadsheet/../tests/helpers/getters";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";
import { getZoneOfInsertedDataSource } from "@spreadsheet/../tests/helpers/pivot";
import { doMenuAction, getActionMenu } from "@spreadsheet/../tests/helpers/ui";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { getSpreadsheetActionModel } from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import { InsertListSpreadsheetMenu } from "@spreadsheet_edition/assets/list_view/insert_list_spreadsheet_menu_owl";
import { insertList } from "@spreadsheet_edition/bundle/list/list_init_callback";
import * as dsHelpers from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    fields,
    mountView,
    onRpc,
    pagerNext,
    patchWithCleanup,
    toggleActionMenu,
    makeServerError,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Deferred } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { ListRenderer } from "@web/views/list/list_renderer";
import { mockActionService } from "../helpers/spreadsheet_test_utils";

defineDocumentSpreadsheetModels();
defineDocumentSpreadsheetTestAction();
describe.current.tags("desktop");

const { topbarMenuRegistry, cellMenuRegistry } = spreadsheet.registries;
const { toZone } = spreadsheet.helpers;

test("List export with a invisible field", async () => {
    const { model } = await createSpreadsheetFromListView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,list": `
                        <list string="Partners">
                            <field name="foo" column_invisible="1"/>
                            <field name="bar"/>
                        </list>`,
            },
        },
    });
    expect(model.getters.getListDefinition("1").columns).toEqual(["bar"]);
});

test("List export with a widget handle", async () => {
    const { model } = await createSpreadsheetFromListView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,list": `
                            <list string="Partners">
                                <field name="foo" widget="handle"/>
                                <field name="bar"/>
                            </list>`,
            },
        },
    });
    expect(model.getters.getListDefinition("1").columns).toEqual(["bar"]);
});

test("Lists are inserted with a table in the webclient", async () => {
    const { model } = await createSpreadsheetFromListView();
    const sheetId = model.getters.getActiveSheetId();
    const table = model.getters.getTable({ sheetId, col: 2, row: 2 });
    expect(table.range.zone).toEqual(toZone("A1:D11"));
});

test("property fields are not exported", async () => {
    const data = getBasicData();
    const propertyDefinition = {
        type: "char",
        name: "property_char",
        string: "Property char",
    };
    const product = Product._records[0];
    product.properties_definitions = [propertyDefinition];
    data.partner.records = [
        {
            id: 1,
            bar: true,
            product_id: product.id,
            partner_properties: {
                [propertyDefinition.name]: "CHAR",
            },
        },
    ];
    const propertyField = fields.Properties({
        string: "Property char",
        definition_record: "product_id",
        definition_record_field: "properties_definitions",
    });
    Partner._fields.partner_properties = propertyField;
    const { model } = await createSpreadsheetFromListView({
        actions: async () => {
            // display the property which is an optional column
            await contains(".o_optional_columns_dropdown_toggle").click();
            await contains(".o-dropdown--menu input[type='checkbox']").click();
            expect(".o_list_renderer th[data-name='partner_properties.property_char']").toHaveCount(
                1
            );
            expect.step("display_property");
        },
        serverData: {
            models: data,
            views: {
                "partner,false,list": /*xml*/ `
                        <list>
                            <field name="product_id"/>
                            <field name="bar"/>
                            <field name="partner_properties"/>
                        </list>`,
            },
        },
    });
    expect(model.getters.getListDefinition("1").columns).toEqual(["product_id", "bar"]);
    expect.verifySteps(["display_property"]);
});

test("json fields are not exported", async () => {
    const { model } = await createSpreadsheetFromListView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,list": `
                        <list string="Partners">
                            <field name="jsonField"/>
                            <field name="bar"/>
                        </list>`,
            },
        },
    });
    expect(model.getters.getListDefinition("1").columns).toEqual(["bar"]);
});

test("list side panel is open at insertion", async function () {
    await createSpreadsheetFromListView();
    expect(".o-listing-details-side-panel").toHaveCount(1);
});

test("An error is displayed in the side panel if the list has invalid model", async function () {
    const { model, env } = await createSpreadsheetFromListView({
        mockRPC: async function (route, { model, method, kwargs }) {
            if (model === "unknown" && method === "fields_get") {
                throw makeServerError({ code: 404 });
            }
        },
    });
    await contains(".o-sidePanelClose").click();
    const listId = model.getters.getListIds()[0];
    const listDefinition = model.getters.getListModelDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDefinition,
            metaData: {
                ...listDefinition.metaData,
                resModel: "unknown",
            },
        },
    });
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();

    expect(".o-validation-error").toHaveCount(1);
});

test("Open list properties", async function () {
    const { env } = await createSpreadsheetFromListView();

    await doMenuAction(topbarMenuRegistry, ["data", "item_list_1"], env);
    await animationFrame();
    const target = getFixture();
    const title = target.querySelector(".o-sidePanelTitle").innerText;
    expect(title).toBe("List properties");

    const sections = target.querySelectorAll(".o-section");
    expect(sections.length).toBe(6, { message: "it should have 6 sections" });
    const [listName, listModel, columns, domain] = sections;

    expect(listName.children[0]).toHaveText("List Name");
    expect(listName.children[1]).toHaveText("(#1) Partners");

    expect(listModel.children[0]).toHaveText("Model");
    expect(listModel.children[1]).toHaveText("Partner (partner)");

    expect(columns.children[0]).toHaveText("Columns");

    expect(domain.children[0]).toHaveText("Domain");
    expect(domain.children[1]).toHaveText("Match all records\nInclude archived");
});

test("A warning is displayed in the menu item if the list is unused", async function () {
    const { model } = await createSpreadsheetFromListView();
    model.dispatch("CREATE_SHEET", { sheetId: "sh2", name: "Sheet2" });
    insertListInSpreadsheet(model, {
        sheetId: "sh2",
        model: "product",
        columns: ["name", "active"],
    });
    const target = getFixture();
    await contains("div[data-id='data']").click();

    const menuItemList1 = target.querySelector("div[data-name='item_list_1']");
    const menuItemList2 = target.querySelector("div[data-name='item_list_2']");
    expect(menuItemList1.querySelector(".o-unused-list-icon")).toEqual(null);
    expect(menuItemList2.querySelector(".o-unused-list-icon")).toEqual(null);

    model.dispatch("DELETE_SHEET", { sheetId: "sh2" });
    await animationFrame();

    expect(menuItemList1.querySelector(".o-unused-list-icon")).toEqual(null);
    expect(menuItemList2.querySelector(".o-unused-list-icon")).toHaveCount(1);
});

test("A warning is displayed in the side panel if the list is unused", async function () {
    const { model, env } = await createSpreadsheetFromListView();

    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();

    expect(".o-validation-warning").toHaveCount(0);

    model.dispatch("CREATE_SHEET", { sheetId: "sh2", name: "Sheet2" });
    const activeSheetId = model.getters.getActiveSheetId();
    model.dispatch("ACTIVATE_SHEET", { sheetIdFrom: activeSheetId, sheetIdTo: "sh2" });
    model.dispatch("DELETE_SHEET", { sheetId: activeSheetId });
    await animationFrame();

    expect(".o-validation-warning").toHaveCount(1);

    model.dispatch("REQUEST_UNDO");
    await animationFrame();
    expect(".o-validation-warning").toHaveCount(0);
});

test("Deleting the list closes the side panel", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    const titleSelector = ".o-sidePanelTitle";
    expect(titleSelector).toHaveText("List properties");

    model.dispatch("REMOVE_ODOO_LIST", { listId });
    await animationFrame();
    expect(titleSelector).toHaveCount(0);
});

test("Undo a list insertion closes the side panel", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    const titleSelector = ".o-sidePanelTitle";
    expect(titleSelector).toHaveText("List properties");

    model.dispatch("REQUEST_UNDO");
    model.dispatch("REQUEST_UNDO");
    await animationFrame();
    expect(titleSelector).toHaveCount(0);
});

test("Add list in an existing spreadsheet", async () => {
    const { model, env } = await createSpreadsheetFromListView();
    const list = model.getters.getListDefinition("1");
    const fields = model.getters.getListDataSource("1").getFields();
    const callback = insertList.bind({ isEmptySpreadsheet: false })({
        list: {
            ...list,
            columns: list.columns.map((col) => ({ name: col })),
        },
        threshold: 10,
        fields: fields,
        name: "my list",
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42", position: 1 });
    const activeSheetId = model.getters.getActiveSheetId();
    expect(model.getters.getSheetIds()).toEqual([activeSheetId, "42"]);
    await callback(model, env.__spreadsheet_stores__);
    expect(model.getters.getSheetIds().length).toBe(3);
    expect(model.getters.getSheetIds()[0]).toEqual(activeSheetId);
    expect(model.getters.getSheetIds()[1]).toBe("42");
    expect(".o-listing-details-side-panel").toHaveCount(1);
});

test("Verify absence of list properties on non-list cell", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    selectCell(model, "Z26");
    const root = cellMenuRegistry.getAll().find((item) => item.id === "listing_properties");
    expect(root.isVisible(env)).toBe(false);
});

test("Verify absence of list properties on formula with invalid list Id", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    setCellContent(model, "A1", `=ODOO.LIST.HEADER("fakeId", "foo")`);
    const root = cellMenuRegistry.getAll().find((item) => item.id === "listing_properties");
    expect(root.isVisible(env)).toBe(false);
    setCellContent(model, "A1", `=ODOO.LIST("fakeId", "2", "bar")`);
    expect(root.isVisible(env)).toBe(false);
});

test("Re-insert a list correctly ask for lines number", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    selectCell(model, "Z26");
    await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
    await animationFrame();
    expect(".modal-body input").toHaveCount(1);
    expect(".modal-body input").toHaveProperty("type", "number");

    await contains(".o_dialog .btn-secondary").click(); // cancel
    expect(getCellFormula(model, "Z26")).toBe("", { message: "the list is not re-inserted" });

    await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
    await animationFrame();
    await contains(".o_dialog .btn-primary").click(); // confirm
    expect(getCellFormula(model, "Z26")).toBe('=ODOO.LIST.HEADER(1,"foo")', {
        message: "the list is re-inserted",
    });
});

test("Validates input and shows error message when input is invalid", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    selectCell(model, "Z1");

    await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
    await animationFrame();

    await contains(".modal-body input").edit("");
    await contains(".modal-content > .modal-footer > .btn-primary").click();

    expect(".modal-body span.text-danger:only").toHaveText("Please enter a valid number.");
});

test("Re-insert a list with a selected number of records", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    selectCell(model, "Z1");

    await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
    await animationFrame();

    await contains(".modal-body input").edit("2000");
    await contains(".modal-content > .modal-footer > .btn-primary").click();

    expect(model.getters.getNumberRows(model.getters.getActiveSheetId())).toBe(2001);
});

test("Re-insert a list also applies a table", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    const sheetId = model.getters.getActiveSheetId();
    let table = model.getters.getTable({ sheetId, col: 0, row: 49 });
    expect(table).toBe(undefined);

    selectCell(model, "A50");

    await doMenuAction(topbarMenuRegistry, ["data", "reinsert_list", "reinsert_list_1"], env);
    await animationFrame();

    await contains(".modal-body input").edit("10");
    await contains(".modal-content > .modal-footer > .btn-primary").click();

    table = model.getters.getTable({ sheetId, col: 0, row: 49 });
    expect(table.range.zone).toEqual(toZone("A50:D60"));
});

test("user related context is not saved in the spreadsheet", async function () {
    ResUsers._records = getDocumentBasicData().models["res.users"].records;
    registry.category("favoriteMenu").add(
        "insert-list-spreadsheet-menu",
        {
            Component: InsertListSpreadsheetMenu,
            groupNumber: 4,
        },
        { sequence: 5 }
    );

    patchWithCleanup(ListRenderer.prototype, {
        async getListForSpreadsheet() {
            const result = await super.getListForSpreadsheet(...arguments);
            expect(result.list.context).toEqual(
                {
                    default_stage_id: 5,
                },
                { message: "user related context is not stored in context" }
            );
            return result;
        },
    });

    const testSession = {
        user_companies: {
            allowed_companies: {
                15: { id: 15, name: "Hermit" },
            },
            current_company: 15,
        },
    };
    patchWithCleanup(session, testSession);
    const userCtx = user.context;
    patchWithCleanup(user, {
        get context() {
            return Object.assign({}, userCtx, {
                allowed_company_ids: [15],
                tz: "bx",
                lang: "FR",
                uid: 4,
            });
        },
    });
    patchWithCleanup(user, { userId: 4 });
    const context = {
        ...user.context,
        default_stage_id: 5,
    };
    const { env } = await mountView({
        type: "list",
        resModel: "partner",
        context,
        arch: `
                <list string="Partners">
                    <field name="bar"/>
                    <field name="product_id"/>
                </list>
            `,
        config: {
            actionType: "ir.actions.act_window",
            getDisplayName: () => "Test",
            viewType: "list",
        },
    });
    await invokeInsertListInSpreadsheetDialog(env);
    await contains(".modal button.btn-primary").click();
});

test("Selected records from current page are inserted correctly", async function () {
    const def = new Deferred();
    let spreadsheetAction = {};
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                spreadsheetAction = this;
                def.resolve();
            });
        },
    });
    const serverData = {
        models: getBasicData(),
        views: {
            "partner,false,list": `
                    <list limit="2">
                        <field name="foo"/>
                    </list>`,
        },
    };
    await spawnListViewForSpreadsheet({
        serverData,
    });

    /** Insert the selected records from current page in a new spreadsheet */
    const target = getFixture();
    await contains(target.querySelectorAll("td.o_list_record_selector input")[1]).click();
    await pagerNext();
    await contains(target.querySelectorAll("td.o_list_record_selector input")[0]).click();
    await toggleActionMenu();
    const insertMenuItem = [...target.querySelectorAll(".o-dropdown--menu .o_menu_item")].filter(
        (el) => el.innerText === "Insert in spreadsheet"
    )[0];
    await contains(insertMenuItem).click();
    await contains(".modal-content > .modal-footer > .btn-primary").click();

    await def;
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A2")).toBe(17, {
        message: "First record from page 2 (i.e. 3 of 4 records) should be inserted",
    });
    expect(getCellValue(model, "A3")).toBe(null);
});

test("Selected all records from current page are inserted correctly", async function () {
    const def = new Deferred();
    let spreadsheetAction = {};
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                spreadsheetAction = this;
                def.resolve();
            });
        },
    });
    const serverData = {
        models: getBasicData(),
        views: {
            "partner,false,list": `
                    <list limit="2">
                        <field name="foo"/>
                    </list>`,
        },
    };
    await spawnListViewForSpreadsheet({
        serverData,
    });

    /** Insert the selected records from current page in a new spreadsheet */
    const target = getFixture();
    await contains(target.querySelectorAll("td.o_list_record_selector input")[1]).click();
    await contains(target.querySelectorAll("td.o_list_record_selector input")[0]).click();
    await contains(".o_list_select_domain").click();
    await toggleActionMenu();
    const insertMenuItem = [...target.querySelectorAll(".o-dropdown--menu .o_menu_item")].filter(
        (el) => el.innerText === "Insert in spreadsheet"
    )[0];
    await contains(insertMenuItem).click();
    await contains(".modal-content > .modal-footer > .btn-primary").click();

    await def;
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A2")).toBe(12, {
        message: "First record from page 2 (i.e. 3 of 4 records) should be inserted",
    });
    expect(getCellValue(model, "A3")).toBe(1);
    expect(getCellValue(model, "A4")).toBe(17);
    expect(getCellValue(model, "A5")).toBe(2);
});

test("Insert in spreadsheet is avaiblable on a list grouped by m2m field", async function () {
    let spreadsheetAction;
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });
    const serverData = {
        models: getBasicData(),
        views: {
            "partner,false,list": `
                    <list>
                        <field name="foo"/>
                    </list>`,
        },
    };
    await spawnListViewForSpreadsheet({
        serverData,
        groupBy: ["tag_ids"],
    });
    const target = getFixture();
    await contains(target.querySelectorAll(".o_list_record_selector input")[0]).click();
    await toggleActionMenu();
    await contains(".o-dropdown--menu .o_menu_item:has(.oi-view-list)").click();
    await contains(".modal button.btn-primary").click();
    await animationFrame();

    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A2")).toBe(12);
    expect(getCellValue(model, "A3")).toBe(1);
    expect(getCellValue(model, "A4")).toBe(17);
    expect(getCellValue(model, "A5")).toBe(2);
});

test("Can see record of a list", async function () {
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
                    expect.step(params.res_model);
                    expect.step(params.res_id.toString());
                },
            },
        },
    };
    selectCell(model, "A2");
    const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
    await root.execute(env);
    expect.verifySteps(["partner", dataSource.getIdFromPosition(0).toString()]);

    selectCell(model, "A3");
    await root.execute(env);
    expect.verifySteps(["partner", dataSource.getIdFromPosition(1).toString()]);

    // From a cell inside a merge
    model.dispatch("ADD_MERGE", {
        sheetId: model.getters.getActiveSheetId(),
        target: [toZone("A3:B3")],
        force: true, // there are data in B3
    });
    selectCell(model, "B3");
    await root.execute(env);
    expect.verifySteps(["partner", dataSource.getIdFromPosition(1).toString()]);
});

test("See record of list is only displayed on list formula with only one list formula", async function () {
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
    expect(root.isVisible(env)).toBe(false);
    selectCell(model, "A2");
    expect(root.isVisible(env)).toBe(true);
    selectCell(model, "A3");
    expect(root.isVisible(env)).toBe(false);
});

test("See records is visible even if the formula is lowercase", async function () {
    const { env, model } = await createSpreadsheetFromListView();
    selectCell(model, "B2");
    const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
    expect(root.isVisible(env)).toBe(true);
    setCellContent(model, "B2", getCellFormula(model, "B2").replace("ODOO.LIST", "odoo.list"));
    expect(root.isVisible(env)).toBe(true);
});

test("See records is not visible if the formula is in error", async function () {
    const { env, model } = await createSpreadsheetFromListView();
    selectCell(model, "B2");
    const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
    expect(root.isVisible(env)).toBe(true);
    setCellContent(
        model,
        "B2",
        getCellFormula(model, "B2").replace(`ODOO.LIST(1`, `ODOO.LIST("5)`)
    ); //Invalid id
    expect(getEvaluatedCell(model, "B2").message).not.toBe(undefined);
    expect(root.isVisible(env)).toBe(false);
});

test("See record.isVisible() don't throw on spread values", async function () {
    const { env, model } = await createSpreadsheet();
    setCellContent(model, "A1", "A1");
    setCellContent(model, "A2", "A2");
    setCellContent(model, "C1", "=TRANSPOSE(A1:A2)");
    selectCell(model, "D1");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
    expect(root.isVisible(env)).toBe(false);
});

test("Cannot see record of list formula without value", async function () {
    const { env, model } = await createSpreadsheetFromListView();
    expect(getCellFormula(model, "A6")).toBe(`=ODOO.LIST(1,5,"foo")`);
    expect(getCellValue(model, "A6")).toBe("", { message: "A6 is empty" });
    selectCell(model, "A6");
    const action = await getActionMenu(cellMenuRegistry, ["list_see_record"], env);
    expect(action.isVisible(env)).toBe(false);
});

test("'See records' loads a specific action if set in the list definition", async function () {
    const actionXmlId = "spreadsheet.partner_action";
    const { webClient, model } = await createSpreadsheetFromListView({ actionXmlId });
    const actionService = webClient.env.services.action;
    const env = {
        ...webClient.env,
        model,
        services: {
            ...model.config.custom.env.services,
            action: {
                ...actionService,
                doAction: (params) => {
                    expect(params.id).not.toBe(undefined);
                    expect(params.xml_id).not.toBe(undefined);
                    expect.step(params.res_model);
                    expect.step(params.res_id.toString());
                },
            },
        },
    };
    selectCell(model, "C3");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
    await root.execute(env);
    expect.verifySteps(["partner", "2"]);
});

test("Context is passed correctly to the action service", async function () {
    const serverData = getBasicServerData();
    const actionXmlId = "spreadsheet.partner_action";
    serverData.views["partner,false,search"] = /* xml */ `
        <search>
            <filter string="Filter" name="filter" context="{'search_default_filter': 1}" />
        </search>
    `;

    const { model, env } = await createSpreadsheetFromListView({
        serverData,
        actionXmlId,
        additionalContext: { search_default_filter: 1 },
    });

    mockActionService((action) => {
        expect.step("loadAction");
        expect(action.context).toEqual({ search_default_filter: 1 });
    });

    selectCell(model, "A2");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "list_see_record");
    await root.execute(env);
    expect.verifySteps(["loadAction"]);
});

test("Update the list title from the side panel", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    await contains(".o_sp_en_rename").click();
    await contains(".o_sp_en_name").edit("new name");
    await contains(".o_sp_en_save").click();
    expect(model.getters.getListName(listId)).toBe("new name");
});

test("list with a contextual domain", async () => {
    // TODO: the date is coded at 12PM so the test won't fail if the timezone is not UTC. It will still fail on some
    // timezones (GMT +13). The good way to do the test would be to patch the time zone and the date correctly.
    // But PyDate uses new Date() instead of luxon, which cannot be correctly patched.
    mockDate("2016-05-14 12:00:00");
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
            <list>
                <field name="foo"/>
            </list>
        `;
    const { model } = await createSpreadsheetFromListView({
        serverData,
        additionalContext: { search_default_filter: 1 },
        mockRPC: function (route, args) {
            if (args.method === "web_search_read") {
                expect(args.kwargs.domain).toEqual([["date", "=", "2016-05-14"]], {
                    message: "data should be fetched with the evaluated the domain",
                });
                expect.step("web_search_read");
            }
        },
    });
    const listId = "1";
    expect(model.getters.getListDefinition(listId).domain).toEqual(
        '[("date", "=", context_today())]'
    );
    expect(model.exportData().lists[listId].domain).toBe('[("date", "=", context_today())]', {
        message: "domain is exported with the dynamic value",
    });
    expect.verifySteps([
        "web_search_read", // list view is loaded
        "web_search_read", // the data is loaded in the spreadsheet
    ]);
});

test("Update the list domain from the side panel", async function () {
    onRpc("/web/domain/validate", () => true);
    const { model, env } = await createSpreadsheetFromListView();
    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    const fixture = getFixture();
    await contains(".o_edit_domain").click();
    await dsHelpers.addNewRule();
    await contains(".modal-footer .btn-primary").click();
    expect(model.getters.getListDefinition(listId).domain).toEqual([["id", "=", 1]]);
    expect(dsHelpers.getConditionText(fixture)).toBe("Id = 1");
});

test("Update the list sorting from the side panel", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    await contains(".add-dimension").click();
    for (let i = 0; i < 5; i++) {
        await contains(".o-popover input").press("ArrowDown");
    }
    await contains(".o-autocomplete-value-focus").click();
    expect(model.getters.getListDefinition(listId).orderBy).toEqual([{ name: "date", asc: true }]);
    await contains(".add-dimension").click();
    for (let i = 0; i < 7; i++) {
        await contains(".o-popover input").press("ArrowDown");
    }
    await contains(".o-autocomplete-value-focus").click();
    const fixture = getFixture();
    fixture.querySelector(".o-select-order").value = false;
    fixture.querySelector(".o-select-order").dispatchEvent(new Event("change"));
    expect(model.getters.getListDefinition(listId).orderBy).toEqual([
        { name: "date", asc: false },
        { name: "foo", asc: true },
    ]);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getListDefinition(listId).orderBy).toEqual([
        { name: "date", asc: true },
        { name: "foo", asc: true },
    ]);
    await contains(".o-delete-rule").click();
    expect(model.getters.getListDefinition(listId).orderBy).toEqual([{ name: "foo", asc: true }]);
});

test("List sorting selector should display only sortable fields", async function () {
    Partner._fields.foo = fields.Integer({ sortable: false });
    Partner._fields.bar = fields.Boolean({ sortable: false });
    const { model, env } = await createSpreadsheetFromListView({});
    const [listId] = model.getters.getListIds();
    const fixture = getFixture();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    await contains(".add-dimension").click();
    const options = [...fixture.querySelectorAll(".o-popover .o-autocomplete-dropdown > div")];
    const availableFields = options.map((el) => el.innerText);
    expect(availableFields).toEqual([
        "Active",
        "Creation Date",
        "Currency",
        "Date",
        "Display name",
        "field_with_array_agg",
        "Id",
        "Json Field",
        "Last Modified on",
        "Money!",
        "name",
        "Probability",
        "Product",
        "Properties",
        "Tags",
        "Users",
    ]);
});

test("List sorting selector should not display already used fields", async function () {
    Partner._fields.foo = fields.Integer({ sortable: false });
    Partner._fields.bar = fields.Boolean({ sortable: false });
    const { model, env } = await createSpreadsheetFromListView({});
    const [listId] = model.getters.getListIds();
    const fixture = getFixture();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    await contains(".add-dimension").click();
    await contains(".o-popover input").press("ArrowDown");
    await contains(".o-popover input").press("ArrowDown");
    await contains(".o-autocomplete-value-focus").click();
    await contains(".add-dimension").click();
    let options = [...fixture.querySelectorAll(".o-popover .o-autocomplete-dropdown > div")];
    let availableFields = options.map((el) => el.innerText);
    expect(availableFields).toEqual([
        "Active",
        /* "Creation Date", this field should not be available anymore as it is used */
        "Currency",
        "Date",
        "Display name",
        "field_with_array_agg",
        "Id",
        "Json Field",
        "Last Modified on",
        "Money!",
        "name",
        "Probability",
        "Product",
        "Properties",
        "Tags",
        "Users",
    ]);
    await contains(".o-popover input").press("ArrowDown");
    await contains(".o-popover input").press("ArrowDown");
    await contains(".o-autocomplete-value-focus").click();
    await contains(".add-dimension").click();
    options = [...fixture.querySelectorAll(".o-popover .o-autocomplete-dropdown > div")];
    availableFields = options.map((el) => el.innerText);
    expect(availableFields).toEqual([
        "Active",
        /* "Creation Date", this field should not be available anymore as it is used */
        /* "Currency", this field should not be available anymore as it is used */
        "Date",
        "Display name",
        "field_with_array_agg",
        "Id",
        "Json Field",
        "Last Modified on",
        "Money!",
        "name",
        "Probability",
        "Product",
        "Properties",
        "Tags",
        "Users",
    ]);
});

test("List sorting selector should display used fields again when corresponding rule is deleted", async function () {
    Partner._fields.foo = fields.Integer({ sortable: false });
    Partner._fields.bar = fields.Boolean({ sortable: false });
    const { model, env } = await createSpreadsheetFromListView({});
    const [listId] = model.getters.getListIds();
    const fixture = getFixture();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    await contains(".add-dimension").click();
    await contains(".o-popover input").press("ArrowDown");
    await contains(".o-popover input").press("ArrowDown");
    await contains(".o-autocomplete-value-focus").click();
    await contains(".add-dimension").click();
    let options = [...fixture.querySelectorAll(".o-popover .o-autocomplete-dropdown > div")];
    let availableFields = options.map((el) => el.innerText);
    expect(availableFields).toEqual([
        "Active",
        /* "Creation Date", this field should not be available anymore as it is used */
        "Currency",
        "Date",
        "Display name",
        "field_with_array_agg",
        "Id",
        "Json Field",
        "Last Modified on",
        "Money!",
        "name",
        "Probability",
        "Product",
        "Properties",
        "Tags",
        "Users",
    ]);
    await contains(".o-delete-rule").click();
    await contains(".add-dimension").click();
    options = [...fixture.querySelectorAll(".o-popover .o-autocomplete-dropdown > div")];
    availableFields = options.map((el) => el.innerText);
    expect(availableFields).toEqual([
        "Active",
        "Creation Date",
        "Currency",
        "Date",
        "Display name",
        "field_with_array_agg",
        "Id",
        "Json Field",
        "Last Modified on",
        "Money!",
        "name",
        "Probability",
        "Product",
        "Properties",
        "Tags",
        "Users",
    ]);
});

test("Inserting a list preserves the ascending sorting from the list", async function () {
    const serverData = getBasicServerData();
    Partner._fields.foo.sortable = true;
    const { model } = await createSpreadsheetFromListView({
        serverData,
        orderBy: [{ name: "foo", asc: true }],
        linesNumber: 4,
    });
    expect(getEvaluatedCell(model, "A2").value <= getEvaluatedCell(model, "A3").value).not.toBe(
        undefined
    );
    expect(getEvaluatedCell(model, "A3").value <= getEvaluatedCell(model, "A4").value).not.toBe(
        undefined
    );
    expect(getEvaluatedCell(model, "A4").value <= getEvaluatedCell(model, "A5").value).not.toBe(
        undefined
    );
});

test("Inserting a list preserves the descending sorting from the list", async function () {
    const serverData = getBasicServerData();
    Partner._fields.foo.sortable = true;
    const { model } = await createSpreadsheetFromListView({
        serverData,
        orderBy: [{ name: "foo", asc: false }],
        linesNumber: 4,
    });
    expect(getEvaluatedCell(model, "A2").value >= getEvaluatedCell(model, "A3").value).not.toBe(
        undefined
    );
    expect(getEvaluatedCell(model, "A3").value >= getEvaluatedCell(model, "A4").value).not.toBe(
        undefined
    );
    expect(getEvaluatedCell(model, "A4").value >= getEvaluatedCell(model, "A5").value).not.toBe(
        undefined
    );
});

test("Sorting from the list is displayed in the properties panel", async function () {
    const serverData = getBasicServerData();
    Partner._fields.foo.sortable = true;
    Partner._fields.bar.sortable = true;
    const { model, env } = await createSpreadsheetFromListView({
        serverData,
        orderBy: [
            { name: "foo", asc: true },
            { name: "bar", asc: false },
        ],
        linesNumber: 4,
    });
    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();
    expect(".o_sorting_rule_column:eq(0)").toHaveText("Bar");
    expect(".o_sorting_rule_column:eq(1)").toHaveText("Foo");
    /** Bar should be descending */
    expect(".o-select-order:eq(0)").toHaveValue("false");
    /** Foo should be ascending */
    expect(".o-select-order:eq(1)").toHaveValue("true");
});

test("Opening the sidepanel of a list while the panel of another list is open updates the side panel", async function () {
    const { model, env } = await createSpreadsheetFromListView({});
    insertListInSpreadsheet(model, {
        model: "product",
        columns: ["name", "active"],
    });

    const listIds = model.getters.getListIds();
    const fixture = getFixture();

    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId: listIds[0] });
    await animationFrame();
    let modelName = fixture.querySelector(".o-section .o_model_name");
    expect(modelName).toHaveText("Partner (partner)");

    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId: listIds[1] });
    await animationFrame();
    modelName = fixture.querySelector(".o-section .o_model_name");
    expect(modelName).toHaveText("Product (product)");
});

test("Duplicate a list from the side panel", async function () {
    const serverData = getBasicServerData();
    Partner._fields.foo.sortable = true;
    const { model, env } = await createSpreadsheetFromListView({
        serverData,
        orderBy: [{ name: "foo", asc: true }],
    });
    const [listId] = model.getters.getListIds();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId });
    await animationFrame();

    expect(model.getters.getListIds().length).toBe(1);
    expect(".o_sp_en_display_name").toHaveText("(#1) Partners by Foo");
    await contains(".os-cog-wheel-menu-icon").click();
    await contains(".o-popover .fa-clone").click();
    expect(model.getters.getListIds().length).toBe(2);
    expect(".o_sp_en_display_name").toHaveText("(#2) Partners by Foo");
});

test("List export from an action with an xml ID", async function () {
    const actionXmlId = "spreadsheet.partner_action";
    const { model } = await createSpreadsheetFromListView({ actionXmlId });
    expect(model.getters.getListDefinition("1").actionXmlId).toBe("spreadsheet.partner_action");
});

test("List cells are highlighted when their side panel is open", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    const sheetId = model.getters.getActiveSheetId();
    env.openSidePanel("LIST_PROPERTIES_PANEL", { listId: "1" });
    await animationFrame();

    const zone = getZoneOfInsertedDataSource(model, "list", "1");
    expect(getHighlightsFromStore(env)).toEqual([{ sheetId, zone, noFill: true }]);
    await contains(".o-sidePanelClose").click();
    expect(getHighlightsFromStore(env)).toEqual([]);
});

test("List cells are highlighted when hovering the list menu item", async function () {
    const { model, env } = await createSpreadsheetFromListView();
    await contains(".o-sidePanelClose").click();
    const sheetId = model.getters.getActiveSheetId();
    await contains(".o-topbar-top div[data-id='data']").click();

    await hover("div[data-name='item_list_1']");
    const zone = getZoneOfInsertedDataSource(model, "list", "1");
    expect(getHighlightsFromStore(env)).toEqual([{ sheetId, zone, noFill: true }]);

    await leave("div[data-name='item_list_1']");
    expect(getHighlightsFromStore(env)).toEqual([]);
});

test("Inserting a grouped list ignore groups", async function () {
    const serverData = getBasicServerData();
    Partner._fields.foo.sortable = true;
    onRpc("partner", "web_read_group", ({ kwargs }) => {
        if (kwargs.groupby) {
            // The mock server cannot handle orderby count
            kwargs.orderby = "";
        }
    });
    const { model } = await createSpreadsheetFromListView({
        actions: async (fixture) => {
            // display the property which is an optional column
            await contains(".o_searchview_dropdown_toggler").click();
            await contains(".o_add_custom_group_menu").select("bar");
            await contains(".o_searchview_facet_label").click();
        },
        serverData,
        linesNumber: 4,
    });
    expect(getEvaluatedCell(model, "A2").value <= getEvaluatedCell(model, "A3").value).not.toBe(
        undefined
    );
});
