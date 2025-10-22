import { CallInvitation } from "@mail/discuss/call/common/call_invitation";
import { onChange } from "@mail/utils/common/misc";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CallInvitations extends Component {
    static props = [];
    static components = { CallInvitation };
    static template = "discuss.CallInvitations";

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
    }
}

export const callInvitationsService = {
    dependencies: ["discuss.rtc", "mail.store", "overlay"],
    start(env, services) {
        const store = services["mail.store"];
        let removeOverlay;
        const onChangeRingingThreadsLength = () => {
            if (store.ringingThreads.length > 0) {
                if (!removeOverlay) {
                    removeOverlay = services.overlay.add(CallInvitations, {});
                }
            } else {
                removeOverlay?.();
                removeOverlay = undefined;
            }
        };
        onChangeRingingThreadsLength();
        onChange(store.ringingThreads, "length", onChangeRingingThreadsLength);
    },
};
registry.category("services").add("discuss.call_invitations", callInvitationsService);
