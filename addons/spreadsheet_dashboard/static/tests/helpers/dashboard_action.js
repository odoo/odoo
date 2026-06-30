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
