/* @odoo-module */

import { rtcService } from "@mail/discuss/rtc/rtc_service";
import { CallMenu } from "@mail/discuss/rtc/call_menu";
import { CallInvitations } from "@mail/discuss/rtc/call_invitations";
import { discussStoreService } from "@mail/discuss/discuss_store_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

patch(setupManager, "discuss", {
    setupServices() {
        return {
            ...this._super(...arguments),
            "discuss.store": discussStoreService,
            "mail.rtc": rtcService,
        };
    },
    setupMainComponentRegistry() {
        this._super(...arguments);
        registry.category("main_components").add("mail.CallInvitations", {
            Component: CallInvitations,
        });
    },
    setupMessagingServiceRegistries() {
        this._super(...arguments);
        registry
            .category("systray")
            .add("mail.CallMenu", { Component: CallMenu }, { sequence: 15 });
    },
});
