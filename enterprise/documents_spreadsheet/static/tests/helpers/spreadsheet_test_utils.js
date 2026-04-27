import { makeDocumentsSpreadsheetMockEnv } from "@documents_spreadsheet/../tests/helpers/model";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { SpreadsheetTemplateAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_template/spreadsheet_template_action";
import { animationFrame, queryFirst, queryText } from "@odoo/hoot-dom";
import { getBasicServerData } from "@documents_spreadsheet/../tests/helpers/data";
import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import {
    getService,
    mockService,
    mountWithCleanup,
    patchTranslations,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";
import { DocumentsDocument, SpreadsheetTemplate } from "./data";

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 */

/**
 * @typedef {object} SpreadsheetTestParams
 * @property {object} [webClient] Webclient already configured
 * @property {number} [spreadsheetId] Id of the spreadsheet
 * @property {ServerData} [serverData] Data to be injected in the mock server
 * @property {Function} [mockRPC] Mock rpc function
 */

/**
 * Open a spreadsheet action
 *
 * @param {string} actionTag Action tag ("action_open_spreadsheet" or "action_open_template")
 * @param {SpreadsheetTestParams} params
 */
async function createSpreadsheetAction(actionTag, params) {
    const SpreadsheetActionComponent =
        actionTag === "action_open_spreadsheet" ? SpreadsheetAction : SpreadsheetTemplateAction;
    const { webClient } = params;
    /** @type {any} */
    let spreadsheetAction;
    patchWithCleanup(SpreadsheetActionComponent.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });
    if (!webClient) {
        await prepareWebClientForSpreadsheet();
        await makeDocumentsSpreadsheetMockEnv(params);
        await mountWithCleanup(WebClient);
    }
    await getService("action").doAction(
        {
            type: "ir.actions.client",
            tag: actionTag,
            params: {
                spreadsheet_id: params.spreadsheetId,
            },
        },
        { clearBreadcrumbs: true } // Sometimes in test defining custom action, Odoo opens on the action instead of opening on root
    );
    await animationFrame();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    return {
        webClient,
        model,
        env: getSpreadsheetActionEnv(spreadsheetAction),
        transportService: model.config.transportService,
    };
}

/**
 * Create an empty spreadsheet
 *
 * @param {SpreadsheetTestParams} params
 */
export async function createSpreadsheet(params = {}) {
    patchTranslations();
    if (!params.serverData) {
        params.serverData = getBasicServerData();
    }
    if (!params.spreadsheetId) {
        const documents = DocumentsDocument._records;
        const spreadsheetId = Math.max(...documents.map((d) => d.id)) + 1;
        documents.push({
            id: spreadsheetId,
            name: UNTITLED_SPREADSHEET_NAME.toString(), // toString() to force translation
            spreadsheet_data: "{}",
            active: true,
        });
        params = { ...params, spreadsheetId };
    }
    return createSpreadsheetAction("action_open_spreadsheet", params);
}

/**
 * Create a spreadsheet template
 *
 * @param {SpreadsheetTestParams} params
 */
export async function createSpreadsheetTemplate(params = {}) {
    if (!params.serverData) {
        params.serverData = getBasicServerData();
    }
    if (!params.spreadsheetId) {
        const templates = SpreadsheetTemplate._records;
        const spreadsheetId = Math.max(...templates.map((d) => d.id)) + 1;
        templates.push({
            id: spreadsheetId,
            name: "test template",
            spreadsheet_data: "{}",
        });
        params = { ...params, spreadsheetId };
    }
    return createSpreadsheetAction("action_open_template", params);
}

/**
 * @param {typeof Services["action"].doAction}
 */
export function mockActionService(doAction) {
    mockService("action", { doAction });
}

/**
 * @param {HTMLElement} [root]
 * @returns {HTMLElement}
 */
export function getConnectedUsersEl(root) {
    return queryFirst(".o_spreadsheet_number_users", { root });
}

/**
 * @param {HTMLElement} [root]
 * @returns {HTMLElement}
 */
export function getConnectedUsersElImage(root) {
    return queryFirst(".o_spreadsheet_number_users i", { root });
}

/**
 *
 * @param {HTMLElement} [root]
 * @returns {string}
 */
export function getSynchedStatus(root) {
    return queryText(".o_spreadsheet_sync_status:first", { root });
}

/**
 * @param {HTMLElement} [root]
 * @returns {number}
 */
export function displayedConnectedUsers(root) {
    return parseInt(queryText(getConnectedUsersEl(root)));
}
