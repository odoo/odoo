import { onMounted } from "@odoo/owl";
import { Deferred } from "@odoo/hoot-mock";
import { SpreadsheetFieldSyncAction } from "@spreadsheet_sale_management/bundle/field_sync/action/field_sync_action";
import { getService, patchWithCleanup, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

import {
    getSpreadsheetActionModel,
    getSpreadsheetActionEnv,
} from "@spreadsheet_edition/../tests/helpers/webclient_helpers";

/**
 * @param {object} params
 * @param {number} [params.spreadsheetId]
 */
export async function mountSaleOrderSpreadsheetAction(params = {}) {
    const def = new Deferred();
    let spreadsheetAction = {};
    patchWithCleanup(SpreadsheetFieldSyncAction.prototype, {
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
        tag: "action_sale_order_spreadsheet",
        params: {
            spreadsheet_id: params.spreadsheetId ?? 1,
        },
    });
    await def;
    const model = getSpreadsheetActionModel(spreadsheetAction);
    const env = getSpreadsheetActionEnv(spreadsheetAction);
    return { model, env, webClient };
}
