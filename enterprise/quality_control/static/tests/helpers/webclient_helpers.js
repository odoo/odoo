import { onMounted } from "@odoo/owl";
import { Deferred } from "@odoo/hoot-mock";
import { getService, patchWithCleanup, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

import {
    getSpreadsheetActionModel,
    getSpreadsheetActionEnv,
} from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import { QualityCheckSpreadsheetAction } from "@quality_control/spreadsheet_bundle/quality_check_spreadsheet_action/quality_check_spreadsheet_action";

/**
 * @param {object} params
 * @param {number} [params.spreadsheetId]
 */
export async function mountQualitySpreadsheetAction(params = {}) {
    const def = new Deferred();
    let spreadsheetAction = {};
    patchWithCleanup(QualityCheckSpreadsheetAction.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                spreadsheetAction = this;
                def.resolve();
            });
        },
    });
    const webClient = await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "action_spreadsheet_quality",
        params: {
            spreadsheet_id: params.spreadsheetId ?? 1,
            ...params,
        },
    });
    await def;
    const model = getSpreadsheetActionModel(spreadsheetAction);
    const env = getSpreadsheetActionEnv(spreadsheetAction);
    return { model, env, webClient };
}
