import {
    defineDocumentSpreadsheetModels,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { makeDocumentsSpreadsheetMockEnv } from "@documents_spreadsheet/../tests/helpers/model";
import { mockActionService } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { describe, expect, test } from "@odoo/hoot";
import { click, dblclick, press } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { prepareWebClientForSpreadsheet } from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

const serviceRegistry = registry.category("services");

const serverData = getBasicServerData();
serverData.models["documents.document"].records = [
    {
        id: 1,
        name: "My spreadsheet",
        spreadsheet_data: "{}",
        folder_id: 1,
        handler: "spreadsheet",
        is_favorited: false,
    },
    {
        id: 2,
        name: "Untitled spreadsheet",
        spreadsheet_data: "{}",
        folder_id: 1,
        handler: "spreadsheet",
        is_favorited: false,
    },
    {
        id: 3,
        name: "My image",
        spreadsheet_data: "{}",
        folder_id: 1,
        handler: "image",
        is_favorited: false,
    },
];

function getDefaultProps() {
    return {
        type: "PIVOT",
        name: "Pipeline",
        actionOptions: {},
        close: () => {},
    };
}

/**
 * Create a spreadsheet model from a List controller
 *
 * @param {object} config
 * @param {object} [config.serverData] Data to be injected in the mock server
 * @param {object} [config.props] Props to be given to the component
 * @param {function} [config.mockRPC] Mock rpc function
 *
 * @returns {Promise<{target: HTMLElement, env: import("@web/env").OdooEnv}>}
 */
async function mountSpreadsheetSelectorDialog(config = {}) {
    await prepareWebClientForSpreadsheet();
    const env = await makeDocumentsSpreadsheetMockEnv({
        serverData: config.serverData || serverData,
        mockRPC: config.mockRPC,
    });
    //@ts-ignore
    env.dialogData = {
        isActive: true,
        close: () => {},
    };
    const props = {
        ...getDefaultProps(),
        ...(config.props || {}),
    };
    await mountWithCleanup(SpreadsheetSelectorDialog, { env, props });
    return { env };
}

test("Display only spreadsheet and a blank spreadsheet", async () => {
    await mountSpreadsheetSelectorDialog();
    expect(".o-spreadsheet-grid:not(.o-spreadsheet-grid-ghost-item)").toHaveCount(3);
});

test("Threshold is not displayed with pivot type", async () => {
    await mountSpreadsheetSelectorDialog({ props: { type: "PIVOT" } });
    expect(".modal-title").toHaveText("Select a spreadsheet to insert your pivot.");
    expect(".o-sp-dialog-meta-name-label").toHaveText("Name of the pivot:");
    expect(".o-sp-dialog-meta-threshold").toHaveCount(0);
});

test("Threshold is not displayed with link type", async () => {
    await mountSpreadsheetSelectorDialog({ props: { type: "LINK" } });
    expect(".modal-title").toHaveText("Select a spreadsheet to insert your link.");
    expect(".o-sp-dialog-meta-name-label").toHaveText("Name of the link:");
    expect(".o-sp-dialog-meta-threshold").toHaveCount(0);
});

test("Threshold is not displayed with graph type", async () => {
    await mountSpreadsheetSelectorDialog({ props: { type: "GRAPH" } });
    expect(".modal-title").toHaveText("Select a spreadsheet to insert your graph.");
    expect(".o-sp-dialog-meta-name-label").toHaveText("Name of the graph:");
    expect(".o-sp-dialog-meta-threshold").toHaveCount(0);
});

test("Threshold is displayed with list type", async () => {
    await mountSpreadsheetSelectorDialog({ props: { type: "LIST" } });
    expect(".modal-title").toHaveText("Select a spreadsheet to insert your list.");
    expect(".o-sp-dialog-meta-name-label").toHaveText("Name of the list:");
    expect(".o-sp-dialog-meta-threshold").toHaveCount(1);
});

test("Can change the name of an object", async () => {
    const NEW_NAME = "new name";
    const fakeActionService = {
        name: "action",
        start() {
            return {
                doAction(action) {
                    expect.step(action.tag);
                    expect(action.params.preProcessingActionData.name).toBe("new name");
                    expect(action.params.preProcessingAsyncActionData.name).toBe("new name");
                },
            };
        },
    };
    serviceRegistry.add("action", fakeActionService, { force: true });
    await mountSpreadsheetSelectorDialog();
    await contains(".o-sp-dialog-meta-name input").edit(NEW_NAME);
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("Can change the threshold of a list object", async () => {
    const threshold = 10;
    const fakeActionService = {
        name: "action",
        start() {
            return {
                doAction(action) {
                    expect.step(action.tag);
                    expect(action.params.preProcessingActionData.threshold).toEqual(threshold);
                    expect(action.params.preProcessingAsyncActionData.threshold).toEqual(threshold);
                },
            };
        },
    };
    serviceRegistry.add("action", fakeActionService, { force: true });
    await mountSpreadsheetSelectorDialog({
        props: { type: "LIST", threshold: 4 },
    });
    /** @type {HTMLInputElement} */
    expect(".o-sp-dialog-meta-threshold-input").toHaveValue(4);
    await contains(".o-sp-dialog-meta-threshold-input").edit(threshold.toString());
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("Change the search bar content trigger a new search with updated domain", async () => {
    await mountSpreadsheetSelectorDialog({
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheets" && args.model === "documents.document") {
                expect.step(JSON.stringify(args.args[0]));
            }
        },
    });
    await contains(".o-sp-searchview-input").edit("a");
    expect.verifySteps(["[]"]);
    await advanceTime(500);
    expect.verifySteps([JSON.stringify([["name", "ilike", "a"]])]);
});

test("Pager is limited to 9 elements", async () => {
    const data = JSON.parse(JSON.stringify(serverData));
    data.models["documents.document"].records = [];
    // Insert 20 elements
    for (let i = 1; i <= 20; i++) {
        data.models["documents.document"].records.push({
            folder_id: 1,
            id: i,
            handler: "spreadsheet",
            name: `Spreadsheet_${i}`,
            spreadsheet_data: "{}",
        });
    }
    await mountSpreadsheetSelectorDialog({
        serverData: data,
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheets" && args.model === "documents.document") {
                expect.step(
                    JSON.stringify({ offset: args.kwargs.offset, limit: args.kwargs.limit })
                );
            }
        },
    });
    await contains(".o_pager_next").click();
    await contains(".o_pager_next").click();
    expect.verifySteps([
        JSON.stringify({ offset: 0, limit: 9 }),
        JSON.stringify({ offset: 9, limit: 9 }),
        JSON.stringify({ offset: 18, limit: 9 }),
    ]);
});

test("Can select the empty spreadsheet", async () => {
    mockActionService((action) => {
        expect.step("doAction");
        expect(action.params.spreadsheet_id).toBe(789);
    });
    await mountSpreadsheetSelectorDialog({
        mockRPC: async function (route, args) {
            if (
                args.model === "documents.document" &&
                args.method === "action_open_new_spreadsheet"
            ) {
                expect.step("action_open_new_spreadsheet");
                return {
                    type: "ir.actions.client",
                    tag: "action_open_spreadsheet",
                    params: {
                        spreadsheet_id: 789,
                    },
                };
            }
        },
    });
    await contains(".o-blank-spreadsheet-grid img").click();
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["action_open_new_spreadsheet", "doAction"]);
});

test("Can select an existing spreadsheet", async () => {
    mockActionService((action) => {
        expect.step("doAction");
        expect(action.params.spreadsheet_id).toBe(1);
    });
    await mountSpreadsheetSelectorDialog();
    await contains('.o-spreadsheet-grid div[data-id="1"]').focus();
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["doAction"]);
});

test("Selected spreadsheet is identifiable", async () => {
    await mountSpreadsheetSelectorDialog();
    expect(".o-spreadsheet-grid.o-blank-spreadsheet-grid .o-spreadsheet-grid-image").toHaveClass(
        "o-spreadsheet-grid-selected",
        { message: "Blank spreadsheet should be selected by default" }
    );
    await contains('.o-spreadsheet-grid div[data-id="1"]').focus();
    expect('.o-spreadsheet-grid div[data-id="1"]').toHaveClass("o-spreadsheet-grid-selected", {
        message: "Selected spreadsheet should be identifiable",
    });
});

test("Can double click an existing spreadsheet", async () => {
    mockActionService((action) => {
        expect.step(action.tag);
        expect(action.params.spreadsheet_id).toBe(1);
    });
    await mountSpreadsheetSelectorDialog();
    await dblclick(`.o-spreadsheet-grid div[data-id="1"]`);
    await animationFrame();
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("Can double click the empty spreadsheet", async () => {
    mockActionService((action) => expect.step(action.tag));
    await mountSpreadsheetSelectorDialog();
    await dblclick(".o-blank-spreadsheet-grid img");
    await animationFrame();
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("Can open blank spreadsheet with enter key", async () => {
    mockActionService((action) => expect.step(action.tag));
    await mountSpreadsheetSelectorDialog();
    await contains(".o-blank-spreadsheet-grid img").press("Enter");
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("Can open existing spreadsheet with enter key", async () => {
    mockActionService((action) => expect.step(action.tag));
    await mountSpreadsheetSelectorDialog();
    await contains('.o-spreadsheet-grid div[data-id="1"]').press("Enter");
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("Offset reset to zero after searching for spreadsheet in spreadsheet selector dialog", async () => {
    const data = JSON.parse(JSON.stringify(serverData));
    data.models["documents.document"].records = [];
    // Insert 12 elements
    for (let i = 1; i <= 12; i++) {
        data.models["documents.document"].records.push({
            folder_id: 1,
            id: i,
            handler: "spreadsheet",
            name: `Spreadsheet_${i}`,
            spreadsheet_data: "{}",
        });
    }

    await mountSpreadsheetSelectorDialog({
        serverData: data,
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheets" && args.model === "documents.document") {
                expect.step(
                    JSON.stringify({ offset: args.kwargs.offset, limit: args.kwargs.limit })
                );
            }
        },
    });

    await contains(".o_pager_next").click();
    expect.verifySteps([
        JSON.stringify({ offset: 0, limit: 9 }),
        JSON.stringify({ offset: 9, limit: 9 }),
    ]);

    await contains(".o-sp-searchview-input").edit("1");
    await advanceTime(500);

    expect.verifySteps([JSON.stringify({ offset: 0, limit: 9 })]);
    expect(".o_pager_value").toHaveText("1-4", {
        message: "Pager should be reset to 1-4 after searching for spreadsheet",
    });
});

test("Can navigate through spreadsheets with arrow keys", async () => {
    await mountSpreadsheetSelectorDialog();

    const defaultSheet = ".o-spreadsheet-grid.o-blank-spreadsheet-grid .o-spreadsheet-grid-image";

    expect(defaultSheet).toHaveClass("o-spreadsheet-grid-selected", {
        message: "Blank spreadsheet should be selected by default",
    });

    // Navigate to the first spreadsheet
    await click(defaultSheet);
    await press("ArrowRight");
    await animationFrame();

    expect('.o-spreadsheet-grid div[data-id="1"]').toHaveClass("o-spreadsheet-grid-selected", {
        message: "First spreadsheet should be selected",
    });

    // Navigate back to the blank spreadsheet
    await press("ArrowLeft");
    await animationFrame();

    expect(defaultSheet).toHaveClass("o-spreadsheet-grid-selected", {
        message: "Blank spreadsheet should be selected",
    });
});
