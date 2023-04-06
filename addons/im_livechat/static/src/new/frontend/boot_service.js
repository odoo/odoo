/** @odoo-module */

import { App } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { serverUrl, isAvailable } from "../../livechat_data";
import { LivechatRoot } from "../core/livechat_root";
import { createRootNode, initializeLivechatContainer } from "../core/boot_helpers";

session.origin = serverUrl;
registry.category("main_components").remove("mail.ChatWindowContainer");

export const livechatBootService = {
    dependencies: ["mail.messaging"],

    /**
     * To be overriden in tests.
     */
    createRootNode() {
        return createRootNode();
    },

    start(env) {
        if (!isAvailable) {
            return;
        }
        const root = this.createRootNode();
        initializeLivechatContainer(root).then((target) => {
            new App(LivechatRoot, {
                env,
                templates,
                translatableAttributes: ["data-tooltip"],
                translateFn: env._t,
                dev: env.debug,
            }).mount(target);
        });
    },
};
registry.category("services").add("im_livechat.boot", livechatBootService);
