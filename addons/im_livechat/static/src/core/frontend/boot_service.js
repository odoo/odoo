import { makeRoot, makeShadow } from "@im_livechat/embed/common/boot_helpers";
import { canLoadLivechat } from "@im_livechat/embed/common/misc";
import { LivechatRoot } from "@im_livechat/embed/frontend/livechat_root";
import { App } from "@odoo/owl";
import { appTranslateFn } from "@web/core/l10n/translation";

import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";

export const livechatBootService = {
    dependencies: ["mail.store"],

    /**
     * To be overriden in tests.
     */
    getTarget() {
        return document.body;
    },

    start(env) {
        if (!canLoadLivechat()) {
            return;
        }
        const target = this.getTarget();
        const root = makeRoot(target);
        makeShadow(root).then((shadow) => {
            new App(LivechatRoot, {
                env,
                getTemplate,
                translatableAttributes: ["data-tooltip"],
                translateFn: appTranslateFn,
                dev: env.debug,
            }).mount(shadow);
        });
    },
};
registry.category("services").add("im_livechat.boot", livechatBootService);
