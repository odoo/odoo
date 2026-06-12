import { CallInvitation } from "@mail/discuss/call/common/call_invitation";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CallInvitations extends Component {
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
        /** @type {import("models").Store} */
        const store = services["mail.store"];
        let removeOverlay;
        const onChangeRingingThreadsLength = () => {
            if (store.ringingChannels.length > 0) {
                if (!removeOverlay) {
                    removeOverlay = services.overlay.add(CallInvitations, {});
                }
            } else {
                removeOverlay?.();
                removeOverlay = undefined;
            }
        };
        onChangeRingingThreadsLength();
        store.registerOnChange(store.ringingChannels, "length", onChangeRingingThreadsLength);
    },
};
registry.category("services").add("discuss.call_invitations", callInvitationsService);
