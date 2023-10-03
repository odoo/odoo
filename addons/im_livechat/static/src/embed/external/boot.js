/* @odoo-module */

import { makeRoot, makeShadow } from "@im_livechat/embed/boot_helpers";
import { LivechatButton } from "@im_livechat/embed/core_ui/livechat_button";
import { serverUrl } from "@im_livechat/embed/livechat_data";

import { ChatWindowContainer } from "@mail/core/common/chat_window_container";

import { mount, whenReady } from "@odoo/owl";

import { templates } from "@web/core/assets";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { session } from "@web/session";

(async function boot() {
    session.origin = serverUrl;
    await whenReady();
    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("LivechatRoot", { Component: LivechatButton });
    mainComponentsRegistry.add("ChatWindowContainer", { Component: ChatWindowContainer });
    const env = makeEnv();
    await startServices(env);
    odoo.isReady = true;
    const target = await makeShadow(makeRoot(document.body));
    await mount(MainComponentsContainer, target, {
        env,
        templates,
        dev: env.debug,
    });
})();
