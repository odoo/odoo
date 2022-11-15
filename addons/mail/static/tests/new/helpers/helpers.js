/** @odoo-module **/

import { messagingService } from "@mail/new/messaging_service";
import { activityService } from "@mail/new/activity/activity_service";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { dropzoneService } from "@mail/new/dropzone/dropzone_service";
import { App, EventBus } from "@odoo/owl";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";

const { afterNextRender } = App;

export { TestServer } from "./test_server";

export function makeTestEnv(rpc) {
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
    const action = {};
    const env = {
        _t: (s) => s,
        services: {
            rpc,
            user,
            router,
            bus_service,
            action,
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
    const im_status = { registerToImStatus() {} };
    env.services.im_status = im_status;
    const messaging = messagingService.start(env, {
        rpc,
        orm,
        user,
        router,
        bus_service,
        im_status,
    });
    env.services["mail.messaging"] = messaging;
    const activity = activityService.start(env, {
        action,
        bus_service,
        orm,
        "mail.messaging": messaging,
    });
    env.services["mail.activity"] = activity;
    const popover = popoverService.start();
    env.services.popover = popover;
    const dropzone = dropzoneService.start();
    env.services.dropzone = dropzone;

    return env;
}

/**
 * @param {string} selector
 * @param {string} content
 */
export async function insertText(selector, content) {
    await afterNextRender(() => {
        document.querySelector(selector).focus();
        for (const char of content) {
            document.execCommand("insertText", false, char);
            document
                .querySelector(selector)
                .dispatchEvent(new window.KeyboardEvent("keydown", { key: char }));
            document
                .querySelector(selector)
                .dispatchEvent(new window.KeyboardEvent("keyup", { key: char }));
        }
    });
}
