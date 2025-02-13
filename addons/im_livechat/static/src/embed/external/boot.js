import { makeRoot, makeShadow } from "@im_livechat/embed/common/boot_helpers";

import { mount, whenReady } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getTemplate } from "@web/core/templates";
import { Deferred } from "@web/core/utils/concurrency";
import { makeEnv, startServices } from "@web/env";
import { session } from "@web/session";
import { loadBundle } from "@web/core/assets";

odoo.livechatReady = new Deferred();

(async function boot() {
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
    odoo.livechatReady.resolve();
})();
