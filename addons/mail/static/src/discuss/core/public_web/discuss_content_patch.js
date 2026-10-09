import { useOnChange } from "@odoo/owl";

import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { Call } from "@mail/discuss/call/common/call";
import { getCallActionComponent } from "@mail/discuss/call/common/call_action_list";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(DiscussContent.components, { Call, PipBanner });

patch(DiscussContent.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
        // close action panel when opening a side channel
        useOnChange(
            () => [this.store.discuss.sideChannel],
            (sideChannel) => {
                if (sideChannel && this.threadActions.activeAction) {
                    this.threadActions.activeAction.actionPanelClose({ closeAll: true });
                }
            }
        );
        // close side channel when opening an action panel
        useOnChange(
            () => [this.threadActions.activeAction],
            (activeAction) => {
                if (activeAction && !activeAction.popover) {
                    this.store.discuss.sideChannel = undefined;
                }
            }
        );
    },
    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent(params) {
        return getCallActionComponent(params) ?? super.getActionComponent(params);
    },
});
