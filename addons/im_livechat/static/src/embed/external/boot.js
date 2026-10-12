import { makeRoot, makeShadow } from "@im_livechat/embed/common/boot_helpers";
import { canLoadLivechat } from "@im_livechat/embed/common/misc";

import { whenReady } from "@odoo/owl";

import { loadBundle } from "@web/core/assets";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { mountComponent } from "@web/env";
import { session } from "@web/session";

(async function boot() {
    if (!canLoadLivechat()) {
        return;
    }
    session.origin = session.livechatData.serverUrl;
    await whenReady();
    if (session.test_mode) {
        await loadBundle("im_livechat.assets_livechat_support_tours");
    }
    const root = makeRoot(document.body);
    const target = await makeShadow(root);
    const { env } = await mountComponent(MainComponentsContainer, target, {
        name: "Odoo livechat",
    });
    env.rootId = root.getAttribute("id");
    env.services["discuss.rtc"].rootEl = target;
    odoo.isReady = true;
})();
