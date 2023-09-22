/* @odoo-module */

import { LivechatButton } from "@im_livechat/embed/core_ui/livechat_button";
import { makeShadow, makeRoot } from "@im_livechat/embed/boot_helpers";
import { serverUrl } from "@im_livechat/embed/livechat_data";

import { ChatWindowContainer } from "@mail/core/common/chat_window_container";

import { mount, whenReady } from "@odoo/owl";

import { templates } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { jsonrpc } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { session } from "@web/session";

(async function boot() {
    session.origin = serverUrl;
    const { fetch } = browser;
    browser.fetch = function (url, ...args) {
        if (!url.match(/^(?:https?:)?\/\//)) {
            url = session.origin + url;
        }
        return fetch(url, ...args);
    };
    registry.category("services").add(
        "rpc",
        {
            async: true,
            start(env) {
                return function rpc(route, params = {}, settings = {}) {
                    if (!route.match(/^(?:https?:)?\/\//)) {
                        route = session.origin + route;
                    }
                    return jsonrpc(route, params, { bus: env.bus, ...settings });
                };
            },
        },
        { force: true }
    );
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
