import {
    defineDocumentSpreadsheetModels,
    defineDocumentSpreadsheetTestAction,
    DocumentsDocument,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import {
    createSpreadsheetFromPivotView,
    createSpreadsheetWithPivot,
} from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { getHighlightsFromStore } from "@documents_spreadsheet/../tests/helpers/store_helpers";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { hover, leave } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { helpers, registries } from "@odoo/o-spreadsheet";
import {
    addGlobalFilter,
    selectCell,
    setCellContent,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/helpers/commands";
import { getBasicPivotArch } from "@spreadsheet/../tests/helpers/data";
import {
    getCell,
    getCellFormula,
    getCellValue,
    getCorrespondingCellFormula,
    getEvaluatedCell,
} from "@spreadsheet/../tests/helpers/getters";
import {
    getZoneOfInsertedDataSource,
    insertPivotInSpreadsheet,
} from "@spreadsheet/../tests/helpers/pivot";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { contains, MockServer } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { mockActionService } from "../helpers/spreadsheet_test_utils";
const { cellMenuRegistry, topbarMenuRegistry } = registries;
const { toCartesian, toZone } = helpers;

defineDocumentSpreadsheetModels();
defineDocumentSpreadsheetTestAction();
describe.current.tags("desktop");

let target;

const reinsertDynamicPivotPath = ["data", "reinsert_dynamic_pivot", "reinsert_dynamic_pivot_1"];
const reinsertStaticPivotPath = ["data", "reinsert_static_pivot", "reinsert_static_pivot_1"];

beforeEach(() => {
    target = getFixture();
});

test("Reinsert a dynamic pivot", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, reinsertDynamicPivotPath, env);
    expect(getCorrespondingCellFormula(model, "E10")).toBe(`=PIVOT(1)`, {
        message: "It should be part of a pivot formula",
    });
});

test("Reinsert a static pivot", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, reinsertStaticPivotPath, env);
    expect(getCellFormula(model, "E10")).toBe(
        `=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",1)`,
        {
            message: "It should contain a pivot formula",
        }
    );
});

test("Reinsert a pivot with a contextual search domain", async function () {
    const serverData = getBasicServerData();
    const uid = user.userId;
    serverData.models.partner.records = [{ id: 1, probability: 0.5, foo: uid }];
    serverData.views["partner,false,search"] = /* xml */ `
                <search>
                    <filter string="Filter" name="filter" domain="[('foo', '=', uid)]"/>
                </search>
            `;
    const { model, env } = await createSpreadsheetFromPivotView({
        serverData,
        additionalContext: { search_default_filter: 1 },
    });

    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, reinsertStaticPivotPath, env);
    expect(getCellFormula(model, "E10")).toBe(
        `=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",${uid})`,
        { message: "It should contain a pivot formula" }
    );
});

test("Reinsert pivot menu item should be hidden if the pivot is invalid", async function () {
    const { model, env } = await createSpreadsheet();
    setCellContent(model, "A1", "Customer");
    selectCell(model, "A1");
    const pivot = topbarMenuRegistry
        .getMenuItems()
        .find((item) => item.id === "insert")
        .children(env)
        .find((item) => item.id === "insert_pivot");
    await pivot.execute(env);

    const reinsertDynamicPivot = topbarMenuRegistry
        .getMenuItems()
        .find((item) => item.id === "data")
        .children(env)
        .find((item) => item.id === "reinsert_dynamic_pivot");
    expect(reinsertDynamicPivot.isVisible(env)).toBe(true);
    setCellContent(model, "A1", "", "Sheet1");
    expect(reinsertDynamicPivot.isVisible(env)).toBe(false);
});

test("Reinsert a pivot in a too small sheet", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("CREATE_SHEET", { cols: 1, rows: 1, sheetId: "111" });
    model.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: sheetId,
        sheetIdTo: "111",
    });
    selectCell(model, "A1");
    await doMenuAction(topbarMenuRegistry, reinsertDynamicPivotPath, env);
    expect(model.getters.getNumberCols("111")).toBe(6);
    expect(model.getters.getNumberRows("111")).toBe(5);
    expect(getCorrespondingCellFormula(model, "B3")).toBe(`=PIVOT(1)`, {
        message: "It should be part of a pivot formula",
    });
});

test("Reinsert a pivot with new data", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    MockServer.env["partner"].create({
        active: true,
        foo: 25, // <- New value inserted
        bar: false,
        date: "2016-12-11",
        product_id: 41,
        probability: 15,
        field_with_array_agg: 4,
        create_date: "2016-12-11",
        tag_ids: [],
    });
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, reinsertStaticPivotPath, env);
    expect(getCellFormula(model, "I8")).toBe(`=PIVOT.HEADER(1,"foo",25)`);
    expect(getCellFormula(model, "I10")).toBe(
        `=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",25)`
    );
});

test("Reinsert a pivot with an updated record", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    expect(getCellValue(model, "B1")).toBe(1);
    expect(getCellValue(model, "C1")).toBe(2);
    expect(getCellValue(model, "D1")).toBe(12);
    const partnerRecords = MockServer.env["partner"];
    partnerRecords[0].foo = 99;
    partnerRecords[1].foo = 99;
    // updated measures
    partnerRecords[0].probability = 88;
    partnerRecords[1].probability = 77;
    selectCell(model, "A10");
    await doMenuAction(topbarMenuRegistry, reinsertDynamicPivotPath, env);
    await animationFrame();
    expect(getCellValue(model, "D10")).toBe(99, {
        message: "The header should have been updated",
    });
    expect(getCellValue(model, "D14")).toBe(77 + 88, {
        message: "The value should have been updated",
    });
});

test("Reinsert an Odoo pivot which has no formula on the sheet (meaning the data is not loaded)", async function () {
    const spreadsheetData = {
        version: 16,
        sheets: [
            {
                id: "sheet1",
            },
        ],
        pivots: {
            1: {
                id: 1,
                colGroupBys: ["foo"],
                domain: [],
                measures: [{ field: "probability", operator: "avg" }],
                model: "partner",
                rowGroupBys: ["bar"],
                context: {},
            },
        },
    };
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        DocumentsDocument._records[0], // res_company.document_spreadsheet_folder_id
        {
            id: 45,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            name: "Spreadsheet",
            handler: "spreadsheet",
        },
    ];
    const { model, env } = await createSpreadsheet({
        serverData,
        spreadsheetId: 45,
    });
    await doMenuAction(topbarMenuRegistry, reinsertStaticPivotPath, env);
    expect(getCellFormula(model, "C1")).toBe(`=PIVOT.HEADER(1,"foo",2)`);
    expect(getCellFormula(model, "C2")).toBe(`=PIVOT.HEADER(1,"foo",2,"measure","probability")`);
    expect(getCellFormula(model, "C3")).toBe(`=PIVOT.VALUE(1,"probability","bar",FALSE,"foo",2)`);
    await animationFrame();
    expect(getCellValue(model, "C1")).toBe(2);
    expect(getCellValue(model, "C2")).toBe("Probability");
    expect(getCellValue(model, "C3")).toBe(15);
});

test("Keep applying filter when pivot is re-inserted", async function () {
    const { model, env, pivotId } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                    <pivot>
                        <field name="bar" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
    });
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Filter",
        },
        {
            pivot: {
                [pivotId]: {
                    chain: "product_id",
                    type: "many2one",
                },
            },
        }
    );
    await animationFrame();
    await setGlobalFilterValue(model, {
        id: "42",
        value: [41],
    });
    await animationFrame();
    expect(getCellValue(model, "B3")).toBe("", {
        message: "The value should have been filtered",
    });
    expect(getCellValue(model, "C3")).toBe("", {
        message: "The value should have been filtered",
    });
    await doMenuAction(topbarMenuRegistry, reinsertDynamicPivotPath, env);
    await animationFrame();
    expect(getCellValue(model, "B3")).toBe("", {
        message: "The value should still be filtered",
    });
    expect(getCellValue(model, "C3")).toBe("", {
        message: "The value should still be filtered",
    });
});

test("undo pivot reinsert", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, reinsertDynamicPivotPath, env);
    expect(getCorrespondingCellFormula(model, "E10")).toBe(`=PIVOT(1)`, {
        message: "It should contain a pivot formula",
    });
    model.dispatch("REQUEST_UNDO");
    expect(getCell(model, "E10")).toBe(undefined, {
        message: "It should have removed the re-inserted pivot",
    });
});

test("reinsert pivot with anchor on merge but not top left", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    const sheetId = model.getters.getActiveSheetId();
    const [pivotId] = model.getters.getPivotIds();
    const pivotZone = getZoneOfInsertedDataSource(model, "pivot", pivotId);
    model.dispatch("REMOVE_TABLE", { sheetId, target: [pivotZone] });
    expect(getCellFormula(model, "B2")).toBe(
        `=PIVOT.HEADER(1,"foo",1,"measure","probability:avg")`,
        {
            message: "It should contain a pivot formula",
        }
    );
    model.dispatch("ADD_MERGE", {
        sheetId,
        target: [{ top: 0, bottom: 1, left: 0, right: 0 }],
        force: true,
    });
    selectCell(model, "A2"); // A1 and A2 are merged; select A2
    const { col, row } = toCartesian("A2");
    expect(model.getters.isInMerge({ sheetId, col, row })).toBe(true);
    await doMenuAction(topbarMenuRegistry, reinsertDynamicPivotPath, env);
    expect(getCellFormula(model, "B2")).toBe(
        `=PIVOT.HEADER(1,"foo",1,"measure","probability:avg")`,
        {
            message: "It should contain a pivot formula",
        }
    );
});

test("Verify presence of pivot properties on pivot cell", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    selectCell(model, "B2");
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_properties");
    expect(root.isVisible(env)).toBe(true);
});

test("Verify absence of pivot properties on non-pivot cell", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    selectCell(model, "Z26");
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_properties");
    expect(root.isVisible(env)).toBe(false);
});

test("Verify absence of pivot properties on formula with invalid pivot Id", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    setCellContent(model, "A1", `=PIVOT.HEADER("fakeId")`);
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_properties");
    expect(root.isVisible(env)).toBe(false);
    setCellContent(model, "A1", `=PIVOT.VALUE("fakeId", "probability", "foo", 2)`);
    expect(root.isVisible(env)).toBe(false);
});

test("verify absence of pivots in top menu bar in a spreadsheet without a pivot", async function () {
    await createSpreadsheet();
    expect("div[data-id='pivots']").toHaveCount(0);
});

test("Verify presence of pivots in top menu bar in a spreadsheet with a pivot", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();
    await insertPivotInSpreadsheet(model, "PIVOT#2", { arch: getBasicPivotArch() });
    expect(target.querySelector("div[data-id='data']")).not.toBe(null, {
        message: "The 'Pivots' menu should be in the dom",
    });

    const root = topbarMenuRegistry.getMenuItems().find((item) => item.id === "data");
    const childrenNames = root.children(env).map((name) => name.name(env).toString()); // toString to force translation
    expect(childrenNames.find((name) => name === "(#1) Partners by Foo")).not.toBe(undefined);
    expect(childrenNames.find((name) => name === "(#2) Partner Pivot")).not.toBe(undefined);
    // bottom children
    expect(childrenNames.find((name) => name === "Refresh all data")).not.toBe(undefined);
    expect(childrenNames.find((name) => name === "Re-insert dynamic pivot")).not.toBe(undefined);
    expect(childrenNames.find((name) => name === "Re-insert static pivot")).not.toBe(undefined);
    expect(childrenNames.find((name) => name === "Re-insert list")).not.toBe(undefined);
});

test("Pivot focus changes on top bar menu click", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();
    await insertPivotInSpreadsheet(model, "PIVOT#2", { arch: getBasicPivotArch() });

    await doMenuAction(topbarMenuRegistry, ["data", "item_pivot_1"], env);
    await animationFrame();
    expect(".os-pivot-title").toHaveValue("Partners by Foo");

    await doMenuAction(topbarMenuRegistry, ["data", "item_pivot_2"], env);
    await animationFrame();
    expect(".os-pivot-title").toHaveValue("Partner Pivot");
});

test("A warning is displayed in the menu item if the pivot is unused", async function () {
    const { model } = await createSpreadsheetFromPivotView();
    model.dispatch("CREATE_SHEET", { sheetId: "sh2", name: "Sheet2" });
    await insertPivotInSpreadsheet(model, "PIVOT#2", { sheetId: "sh2" });
    await contains("div[data-id='data']").click();

    const menuItemPivot1 = target.querySelector("div[data-name='item_pivot_1']");
    const menuItemPivot2 = target.querySelector("div[data-name='item_pivot_2']");

    expect(menuItemPivot1.querySelectorAll(".o-unused-pivot-icon")).toHaveLength(0);
    expect(menuItemPivot2.querySelectorAll(".o-unused-pivot-icon")).toHaveLength(0);

    model.dispatch("DELETE_SHEET", { sheetId: "sh2" });
    await animationFrame();

    expect(menuItemPivot1.querySelectorAll(".o-unused-pivot-icon")).toHaveLength(0);
    expect(menuItemPivot2.querySelectorAll(".o-unused-pivot-icon")).toHaveLength(1);
});

test("Can rebuild the Odoo domain of records based on the according merged pivot cell", async function () {
    const { webClient, model } = await createSpreadsheetFromPivotView();
    const env = {
        ...webClient.env,
        model,
        services: {
            ...model.config.custom.env.services,
            action: {
                doAction: (params) => {
                    expect.step(params.res_model);
                    expect.step(JSON.stringify(params.domain));
                },
            },
        },
    };
    const sheetId = model.getters.getActiveSheetId();
    const [pivotId] = model.getters.getPivotIds();
    const pivotZone = getZoneOfInsertedDataSource(model, "pivot", pivotId);
    model.dispatch("REMOVE_TABLE", { sheetId, target: [pivotZone] });

    model.dispatch("ADD_MERGE", {
        sheetId,
        target: [toZone("C3:D3")],
        force: true, // there are data in D3
    });
    selectCell(model, "D3");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    await root.execute(env);
    expect.verifySteps(["partner", `[["foo","=",2],["bar","=",false]]`]);
});

test("See records is visible even if the formula is lowercase", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "B4");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    expect(root.isVisible(env)).toBe(true);
    setCellContent(model, "B4", getCellFormula(model, "B4").replace("PIVOT.VALUE", "pivot.value"));
    expect(root.isVisible(env)).toBe(true);
});

test("See records is not visible if the formula is in error", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "B4");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    expect(root.isVisible(env)).toBe(true);
    setCellContent(
        model,
        "B4",
        getCellFormula(model, "B4").replace(`PIVOT.VALUE(1`, `PIVOT.VALUE("5)`)
    ); //Invalid id
    expect(getEvaluatedCell(model, "B4").message).not.toBe(undefined);
    expect(root.isVisible(env)).toBe(false);
});

test("'See records' loads a specific action if set in the pivot definition", async function () {
    const actionXmlId = "spreadsheet.partner_action";
    const { webClient, model } = await createSpreadsheetFromPivotView({ actionXmlId });
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
                    expect.step(JSON.stringify(params.domain));
                },
            },
        },
    };
    selectCell(model, "C3");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    await root.execute(env);
    expect.verifySteps(["partner", `[["foo","=",2],["bar","=",false]]`]);
});

test("Context is passed correctly to the action service", async function () {
    const serverData = getBasicServerData();
    const actionXmlId = "spreadsheet.partner_action";

    serverData.views["partner,false,search"] = /* xml */ `
        <search>
            <filter string="Filter" name="filter" context="{'search_default_filter': 1}" />
        </search>
    `;
    const { env, model } = await createSpreadsheetFromPivotView({
        serverData,
        additionalContext: { search_default_filter: 1 },
        actionXmlId,
    });

    mockActionService((action) => {
        expect.step("loadAction");
        expect(action.context).toEqual({ search_default_filter: 1 });
    });

    selectCell(model, "C2");
    await animationFrame();
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    await root.execute(env);
    expect.verifySteps(["loadAction"]);
});

test("Pivot cells are highlighted when hovering their menu item", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();
    const sheetId = model.getters.getActiveSheetId();
    await contains(".o-sidePanelClose").click();
    await contains(".o-topbar-top div[data-id='data']").click();

    await hover("div[data-name='item_pivot_1']");
    const pivotId = model.getters.getPivotIds()[0];
    const zone = getZoneOfInsertedDataSource(model, "pivot", pivotId);
    expect(getHighlightsFromStore(env)).toEqual([
        { color: "#37A850", sheetId, zone, noFill: true },
    ]);

    await leave("div[data-name='item_pivot_1");
    expect(getHighlightsFromStore(env)).toEqual([]);
});
