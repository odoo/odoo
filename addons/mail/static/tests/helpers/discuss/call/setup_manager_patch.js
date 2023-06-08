/* @odoo-module */

import { CallInvitations } from "@mail/discuss/call/common/call_invitations";
import { CallMenu } from "@mail/discuss/call/common/call_menu";
import { rtcService } from "@mail/discuss/call/common/rtc_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

patch(setupManager, "discuss/call", {
    setupServices(...args) {
        return {
            ...this._super(...args),
            "discuss.rtc": rtcService,
        };
    },
    setupMainComponentRegistry() {
        this._super();
        registry.category("main_components").add("discuss.CallInvitations", {
            Component: CallInvitations,
        });
    },
    setupMessagingServiceRegistries(...args) {
        this._super(...args);
        registry
            .category("systray")
            .add("discuss.CallMenu", { Component: CallMenu }, { sequence: 15 });
    },
});
