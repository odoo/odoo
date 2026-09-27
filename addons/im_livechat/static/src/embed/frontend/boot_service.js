import { makeRoot, makeShadow } from "@im_livechat/embed/common/boot_helpers";
import { canLoadLivechat } from "@im_livechat/embed/common/misc";
import { LivechatRoot } from "@im_livechat/embed/frontend/livechat_root";
import { onWillDestroy, useApp } from "@odoo/owl";
import { registry } from "@web/core/registry";

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
        const rootEl = makeRoot(target);
        const app = useApp();
        let root;
        makeShadow(rootEl).then((shadow) => {
            env.services["discuss.rtc"].rootEl = shadow;
            root = app.createRoot(LivechatRoot, {
                env: Object.assign(Object.create(env), {
                    rootId: rootEl.getAttribute("id"),
                }),
            });
            return root.mount(shadow);
        });
        onWillDestroy(() => root?.destroy());
    },
};
registry.category("services").add("im_livechat.boot", livechatBootService);
