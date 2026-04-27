import { expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { EventBus } from "@odoo/owl";

import { helpers, registries } from "@odoo/o-spreadsheet";
import { WebClient } from "@web/webclient/webclient";

import {
    addGlobalFilter,
    setCellContent,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/helpers/commands";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { insertPivot } from "@spreadsheet_edition/../tests/helpers/collaborative_helpers";
import {
    defineTestSpreadsheetEditionModels,
    SpreadsheetTest,
} from "@test_spreadsheet_edition/../tests/helpers/data";
import { createSpreadsheetTestAction } from "@test_spreadsheet_edition/../tests/helpers/helpers";
import {
    contains,
    getService,
    mockService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";

const { cellMenuRegistry } = registries;
const { toZone } = helpers;

defineTestSpreadsheetEditionModels();

test("custom colors in color picker", async function () {
    const { model } = await createSpreadsheetTestAction("spreadsheet_test_action", {
        mockRPC: async function (route, args) {
            if (args.method === "join_spreadsheet_session") {
                return {
                    data: {},
                    name: "test",
                    company_colors: ["#875A7B", "not a valid color"],
                };
            }
        },
    });
    expect(model.getters.getCustomColors()).toEqual(["#875A7B"]);
});

test("preserve global filters when navigating through breadcrumb", async function (assert) {
    const { model, env } = await createSpreadsheetTestAction("spreadsheet_test_action");
    await insertPivot(model);
    setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability")');
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Relation Filter",
        modelName: "product",
        defaultValue: [],
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: [37],
    });
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect(".o_list_renderer").toHaveCount(1);
    await contains(".o_back_button").click();
    await contains(".o_topbar_filter_icon").click();
    expect(".o_multi_record_selector").toHaveText("xphone");
});

test("receives collaborative messages when action is restored", async function (assert) {
    const mockBusService = {
        _bus: new EventBus(),
        subscribe(eventName, handler) {
            this._bus.addEventListener("notif", ({ detail }) => {
                if (detail.type === eventName) {
                    handler(detail.payload);
                }
            });
        },
        notify(message) {
            this._bus.trigger("notif", message);
        },
    };
    mockService("bus_service", mockBusService);
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: { content: '=PIVOT.VALUE(1, "probability:sum")' },
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [],
                rows: [],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
            },
        },
    };
    const spreadsheetId = 1;
    SpreadsheetTest._records = [
        {
            id: spreadsheetId,
            name: "my test spreadsheet",
            spreadsheet_data: JSON.stringify(spreadsheetData),
        },
    ];
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "spreadsheet_test_action",
        params: {
            spreadsheet_id: 1,
            res_model: "spreadsheet.test",
        },
    });
    await animationFrame();
    await click(".o-grid-overlay", { button: 2, position: "top-left" });
    await animationFrame();
    await contains('.o-menu-item[data-name="pivot_see_records"]').click();
    await waitFor(".o_list_renderer");
    const revisionWebSocketMessage = {
        id: spreadsheetId,
        type: "REMOTE_REVISION",
        version: 1,
        serverRevisionId: "START_REVISION",
        nextRevisionId: "2",
        clientId: "raoul",
        commands: [
            {
                type: "SET_FORMATTING",
                sheetId: "sheet1",
                target: [toZone("A1")],
                style: { bold: true },
            },
        ],
    };
    // simulate a collaborative revision by pushing the revision
    // to the websocket bus.
    getService("bus_service").notify({
        id: spreadsheetId,
        type: "spreadsheet",
        payload: revisionWebSocketMessage,
    });
    await animationFrame();
    await contains(".o_back_button").click();
    expect('.o-menu-item-button[title="Bold (Ctrl+B)"]').toHaveClass("active");
});
