/** @odoo-module */

import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { SpreadsheetTemplateAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_template/spreadsheet_template_action";
import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "@spreadsheet_edition/../tests/utils/webclient_helpers";

/**
 * @typedef {import("@spreadsheet/../tests/utils/data").ServerData} ServerData
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
    let { webClient } = params;
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
        webClient = await createWebClient({
            serverData: params.serverData || getBasicServerData(),
            mockRPC: params.mockRPC,
        });
    }

    await doAction(
        webClient,
        {
            type: "ir.actions.client",
            tag: actionTag,
            params: {
                spreadsheet_id: params.spreadsheetId,
                convert_from_template: params.convert_from_template,
            },
        },
        { clearBreadcrumbs: true } // Sometimes in test defining custom action, Odoo opens on the action instead of opening on root
    );
    await nextTick();
    return {
        webClient,
        model: getSpreadsheetActionModel(spreadsheetAction),
        env: getSpreadsheetActionEnv(spreadsheetAction),
        transportService: spreadsheetAction.transportService,
    };
}

/**
 * Create an empty spreadsheet
 *
 * @param {SpreadsheetTestParams} params
 */
export async function createSpreadsheet(params = {}) {
    if (!params.serverData) {
        params.serverData = getBasicServerData();
    }
    if (!params.spreadsheetId) {
        const documents = params.serverData.models["documents.document"].records;
        const spreadsheetId = Math.max(...documents.map((d) => d.id)) + 1;
        documents.push({
            id: spreadsheetId,
            name: UNTITLED_SPREADSHEET_NAME,
            spreadsheet_data: "{}",
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
        const templates = params.serverData.models["spreadsheet.template"].records;
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
 * Mock the action service of the env, and add the mockDoAction function to it.
 */
export function mockActionService(env, mockDoAction) {
    patchWithCleanup(env.services.action, {
        doAction(action) {
            mockDoAction(action);
        },
    });
}

/**
 * @param {HTMLElement} target
 * @returns {HTMLElement}
 */
export function getConnectedUsersEl(target) {
    return target.querySelector(".o_spreadsheet_number_users");
}

/**
 * @param {HTMLElement} target
 * @returns {HTMLElement}
 */
export function getConnectedUsersElImage(target) {
    return target.querySelector(".o_spreadsheet_number_users i");
}

/**
 *
 * @param {HTMLElement} target
 * @returns {string}
 */
export function getSynchedStatus(target) {
    /** @type {HTMLElement} */
    const content = target.querySelector(".o_spreadsheet_sync_status");
    return content.innerText;
}

/**
 * @param {HTMLElement} target
 * @returns {number}
 */
export function displayedConnectedUsers(target) {
    return parseInt(getConnectedUsersEl(target).innerText);
}
