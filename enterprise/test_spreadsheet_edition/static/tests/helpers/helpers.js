/** @odoo-module **/

import { animationFrame } from "@odoo/hoot-mock";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { WebClient } from "@web/webclient/webclient";
import { getService, mountWithCleanup, patchWithCleanup, makeMockServer } from "@web/../tests/web_test_helpers";
import {
    prepareWebClientForSpreadsheet,
    getSpreadsheetActionModel,
    getSpreadsheetActionEnv,
} from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import { SpreadsheetTestAction } from "@test_spreadsheet_edition/spreadsheet_test_action";
import { VersionHistoryAction } from "@spreadsheet_edition/bundle/actions/version_history/version_history_action";
import { SpreadsheetTest, getDummyBasicServerData } from "./data";
import { getPyEnv } from "@spreadsheet/../tests/helpers/data";
import { session } from "@web/session";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData

 * @typedef {object} SpreadsheetTestParams
 * @property {number} [spreadsheetId]
 * @property {ServerData} [serverData] Data to be injected in the mock server
 * @property {Function} [mockRPC] Mock rpc function
 * @property {boolean} [fromSnapshot]
 * @property {number | string} [threadId]
 * @property {WebClient} [webClient]
 */

/**
 * @param {string} actionTag Action tag ("spreadsheet_test_action" or "action_open_spreadsheet_history")
 * @param {SpreadsheetTestParams} params
 */
export async function createSpreadsheetTestAction(actionTag, params = {}) {
    /** @type {any} */
    let spreadsheetAction;
    let { webClient } = params;
    const SpreadsheetActionComponent =
        actionTag === "spreadsheet_test_action" ? SpreadsheetTestAction : VersionHistoryAction;
    patchWithCleanup(SpreadsheetActionComponent.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });

    const serverData = params.serverData || getDummyBasicServerData();
    let spreadsheetId = params.spreadsheetId;
    if (!spreadsheetId) {
        spreadsheetId = createNewDummySpreadsheet(serverData);
    }

    if (!webClient) {
        await prepareWebClientForSpreadsheet();
        webClient = await makeSpreadsheetMockEnv({
            serverData,
            mockRPC: params.mockRPC,
        });
        await mountWithCleanup(WebClient);
    }

    await getService("action").doAction({
        type: "ir.actions.client",
        tag: actionTag,
        params: {
            spreadsheet_id: spreadsheetId,
            res_model: "spreadsheet.test",
            from_snapshot: params.fromSnapshot,
            thread_id: params.threadId,
        },
    });
    await animationFrame();
    return {
        model: getSpreadsheetActionModel(spreadsheetAction),
        env: getSpreadsheetActionEnv(spreadsheetAction),
        action: spreadsheetAction,
    };
}

/**
 *
 * @param {ServerData} serverData
 * @param {object} [data] spreadsheet data
 * @returns {number}
 */
export function createNewDummySpreadsheet(serverData, data) {
    if (!serverData.models["spreadsheet.test"].records) {
        serverData.models["spreadsheet.test"].records = [];
    }
    const spreadsheetDummy = serverData.models["spreadsheet.test"].records;
    const maxId = spreadsheetDummy.length ? Math.max(...spreadsheetDummy.map((d) => d.id)) : 0;
    const spreadsheetId = maxId + 1;
    spreadsheetDummy.push({
        id: spreadsheetId,
        name: "Untitled Dummy Spreadsheet",
        spreadsheet_data: data ? JSON.stringify(data) : "{}",
    });
    return spreadsheetId;
}

export async function setupWithThreads(workbookdata = {}) {
    SpreadsheetTest._records = [
        {
            id: 1,
            name: "Untitled Dummy Spreadsheet",
            spreadsheet_data: JSON.stringify(workbookdata),
        },
    ];

    // When sending messages, the user needs to exist and be correctly configured in the server data so he can edit his messages.
    const { env: pyEnv } = await makeMockServer();
    if ("res.users" in pyEnv) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = pyEnv["res.users"];
        const store = new mailDataHelpers.Store();
        ResUsers._init_store_data(store);
        patchWithCleanup(session, {
            storeData: store.get_result(),
        });
    }
    const result = await createSpreadsheetTestAction("spreadsheet_test_action", {
        spreadsheetId: 1,
    });
    return { ...result, spreadsheetId: 1, pyEnv: getPyEnv() };
}

export async function createThread(model, pyEnv, threadPosition, messages = []) {
    const [spreadsheetId] = pyEnv["spreadsheet.test"].search([], { limit: 1 });
    const threadId = pyEnv["spreadsheet.cell.thread"].create({
        dummy_id: spreadsheetId,
    });
    messages.forEach((msg) =>
        pyEnv["mail.message"].create({
            body: `<p>${msg}</p>`,
            message_type: "comment",
            model: "spreadsheet.cell.thread",
            res_id: threadId,
        })
    );
    const result = model.dispatch("ADD_COMMENT_THREAD", { ...threadPosition, threadId });
    await animationFrame();
    return result;
}
