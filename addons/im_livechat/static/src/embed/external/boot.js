/* @odoo-module */

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { makeShadow, makeRoot } from "@im_livechat/embed/common/boot_helpers";
import { serverUrl } from "@im_livechat/embed/common/livechat_data";

import { mount, whenReady } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { getTemplate } from "@web/core/templates";
import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { session } from "@web/session";

(async function boot() {
    session.origin = serverUrl;
    await whenReady();
    const overlaysRegistry = registry.category("overlays");
    overlaysRegistry.add("LivechatRoot", { component: LivechatButton });
    const env = makeEnv();
    await startServices(env);
    odoo.isReady = true;
    const target = await makeShadow(makeRoot(document.body));
    await mount(OverlayContainer, target, {
        env,
        getTemplate,
        translateFn: _t,
        dev: env.debug,
    });
})();
