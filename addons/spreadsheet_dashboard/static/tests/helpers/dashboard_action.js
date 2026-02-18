import { getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Spreadsheet } from "@odoo/o-spreadsheet";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import {
    getService,
    makeMockServer,
    MockServer,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { WebClient } from "@web/webclient/webclient";
import { getDashboardServerData } from "./data";
import { DashboardLoader } from "../../src/bundle/dashboard_action/dashboard_loader_service";
/**
 * @param {object} params
 * @param {object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @param {number} [params.spreadsheetId]
 * @returns {Promise}
 */
export async function createSpreadsheetDashboard(params = {}) {
    let model = undefined;
    patchWithCleanup(Spreadsheet.prototype, {
        setup() {
            super.setup();
            model = this.env.model;
        },
    });

    await makeSpreadsheetMockEnv(params);
    await loadBundle("web.chartjs_lib");
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "action_spreadsheet_dashboard",
        params: {
            dashboard_id: params.spreadsheetId,
        },
    });

    return { model, fixture: getFixture() };
}

export async function createDashboardActionWithData(data) {
    if (!MockServer.env) {
        await makeMockServer();
    }
    const json = JSON.stringify(data);
    const [dashboard] = MockServer.env["spreadsheet.dashboard"];
    dashboard.spreadsheet_data = json;
    dashboard.json_data = json;
    const { fixture, model } = await createSpreadsheetDashboard({ spreadsheetId: dashboard.id });
    await animationFrame();
    return { fixture, model };
}

/**
 * @param {object} [params]
 * @param {object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @returns {Promise<DashboardLoader>}
 */
export async function createDashboardLoader(params = {}) {
    const env = await makeSpreadsheetMockEnv({
        serverData: params.serverData || getDashboardServerData(),
        mockRPC: params.mockRPC,
    });
    return new DashboardLoader(env, env.services.orm, async (dashboardId) => {
        const [record] = await env.services.orm.read(
            "spreadsheet.dashboard",
            [dashboardId],
            ["spreadsheet_data"]
        );
        return { data: JSON.parse(record.spreadsheet_data), revisions: [] };
    });
}
