import { CallInvitation } from "@mail/discuss/call/common/call_invitation";
import { StorePlugin } from "@mail/core/common/store_plugin";

import { Component, Plugin, useOnChange, usePlugin } from "@odoo/owl";

import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { useService } from "@web/core/utils/hooks";

export class CallInvitations extends Component {
    static components = { CallInvitation };
    static template = "discuss.CallInvitations";

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = usePlugin(StorePlugin);
    }
}

export class CallInvitationsPlugin extends Plugin {
    /** @private */
    overlay = usePlugin(OverlayPlugin);
    /** @private */
    store = usePlugin(StorePlugin);

    setup() {
        useOnChange(
            () => [this.store.ringingChannels.length > 0],
            (hasRingingChannels) => {
                if (hasRingingChannels) {
                    return this.overlay.add(CallInvitations, {});
                }
            }
        );
    }
}
