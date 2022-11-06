/** @odoo-module **/

import { messagingService } from "@mail/messaging_service";
import { ormService } from "@web/core/orm_service";
import { EventBus } from "@odoo/owl";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";

export { MessagingServer } from "./messaging_server";

export function makeMessagingEnv(rpc) {
    const user = {
        context: { uid: 2 },
        partnerId: 3,
    };
    const ui = {
        get activeElement() {
            return document.activeElement;
        },
    };
    const router = { current: { hash: { active_id: false } }, pushState() {} };
    const bus_service = new EventBus();
    const env = {
        _t: (s) => s,
        services: {
            rpc,
            user,
            router,
            bus_service,
            action: {},
            dialog: {},
            ui,
            popover: {},
            "mail.activity": {},
        },
    };
    const hotkey = hotkeyService.start(env, { ui });
    env.services.hotkey = hotkey;
    const orm = ormService.start(env, { rpc, user });
    env.services.orm = orm;

    const messaging = messagingService.start(env, { rpc, orm, user, router, bus_service });
    env.services["mail.messaging"] = messaging;
    return env;
}
