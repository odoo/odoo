import { makeRoot, makeShadow } from "@im_livechat/embed/common/boot_helpers";

import { mount, whenReady } from "@odoo/owl";

import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getTemplate } from "@web/core/templates";
import { makeEnv, startServices } from "@web/env";
import { session } from "@web/session";

(async function boot() {
    if (!session.livechatData.can_load_livechat) {
        return;
    }
    session.origin = session.livechatData.serverUrl;
    await whenReady();
    if (session.test_mode) {
        await loadBundle("im_livechat.assets_livechat_support_tours");
    }
    const env = Object.assign(makeEnv(), { embedLivechat: true });
    await startServices(env);
    odoo.isReady = true;
    const target = await makeShadow(makeRoot(document.body));
    await mount(MainComponentsContainer, target, {
        env,
        getTemplate,
        translateFn: _t,
        dev: env.debug,
    });
})();
