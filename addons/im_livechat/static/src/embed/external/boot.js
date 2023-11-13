/* @odoo-module */

import { LivechatButton } from "@im_livechat/embed/core_ui/livechat_button";
import { makeShadow, makeRoot } from "@im_livechat/embed/boot_helpers";
import { LivechatContainer } from "@im_livechat/embed/external/livechat_container";
import { serverUrl } from "@im_livechat/embed/livechat_data";

import { mount, whenReady } from "@odoo/owl";

import { templates } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
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
                let rpcId = 0;
                return function rpc(route, params = {}, settings) {
                    if (!route.match(/^(?:https?:)?\/\//)) {
                        route = session.origin + route;
                    }
                    return jsonrpc(env, rpcId++, route, params, settings);
                };
            },
        },
        { force: true }
    );
    await whenReady();
    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("LivechatRoot", { Component: LivechatButton });
    const env = makeEnv();
    await startServices(env);
    odoo.isReady = true;
    const target = await makeShadow(makeRoot(document.body));
    await mount(LivechatContainer, target, {
        env,
        templates,
        translateFn: env._t,
        dev: env.debug,
    });
})();
