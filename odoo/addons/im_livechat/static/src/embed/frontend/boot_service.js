/* @odoo-module */

import { makeRoot, makeShadow } from "@im_livechat/embed/common/boot_helpers";
import { LivechatRoot } from "@im_livechat/embed/frontend/livechat_root";
import { isAvailable } from "@im_livechat/embed/common/livechat_data";
import { _t } from "@web/core/l10n/translation";
import { App } from "@odoo/owl";

import { templates } from "@web/core/assets";
import { registry } from "@web/core/registry";

registry.category("main_components").remove("mail.ChatWindowContainer");

export const livechatBootService = {
    dependencies: ["mail.messaging"],

    /**
     * To be overriden in tests.
     */
    getTarget() {
        return document.body;
    },

    start(env) {
        if (!isAvailable) {
            return;
        }
        const target = this.getTarget();
        const root = makeRoot(target);
        makeShadow(root).then((shadow) => {
            new App(LivechatRoot, {
                env,
                templates,
                translatableAttributes: ["data-tooltip"],
                translateFn: _t,
                dev: env.debug,
            }).mount(shadow);
        });
    },
};
registry.category("services").add("im_livechat.boot", livechatBootService);
