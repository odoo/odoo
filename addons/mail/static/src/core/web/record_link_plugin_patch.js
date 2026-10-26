import { RecordLinkPlugin } from "@mail/core/common/record_link_plugin";
import { getRecordLinkParams } from "@mail/utils/common/format";

import { usePlugin } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

patch(RecordLinkPlugin.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = usePlugin(ActionPlugin);
    },
    async resolveRecordLink(href) {
        const params = getRecordLinkParams(href);
        if (!params?.action) {
            return super.resolveRecordLink(...arguments);
        }
        const action = await this.action.loadAction(params.action).catch(() => {});
        if (action?.type === "ir.actions.act_window" && action.res_model) {
            return { id: params.resId, model: action.res_model };
        }
    },
});
