import { WebClient } from "@web/webclient/webclient";
import { mountWithCleanup, getService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { loadBundle } from "@web/core/assets";
import { getFixture } from "@odoo/hoot";
import { Spreadsheet } from "@odoo/o-spreadsheet";

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
