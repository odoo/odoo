import { makeRoot, makeShadow } from "@im_livechat/embed/common/boot_helpers";
import { LivechatRoot } from "@im_livechat/embed/frontend/livechat_root";
import { _t } from "@web/core/l10n/translation";
import { App } from "@odoo/owl";

import { getTemplate } from "@web/core/templates";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

registry.category("main_components").remove("mail.ChatHub");

export const livechatBootService = {
    dependencies: ["mail.store"],

    /**
     * To be overriden in tests.
     */
    getTarget() {
        return document.body;
    },

    start(env) {
        if (!session.livechatData?.isAvailable) {
            return;
        }
        const target = this.getTarget();
        const root = makeRoot(target);
        makeShadow(root).then((shadow) => {
            new App(LivechatRoot, {
                env,
                getTemplate,
                translatableAttributes: ["data-tooltip"],
                translateFn: _t,
                dev: env.debug,
            }).mount(shadow);
        });
    },
};
registry.category("services").add("im_livechat.boot", livechatBootService);
