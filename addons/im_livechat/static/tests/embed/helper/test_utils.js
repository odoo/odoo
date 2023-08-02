/* @odoo-module */

import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";

import { LivechatButton } from "@im_livechat/embed/core_ui/livechat_button";

import { ChatWindowContainer } from "@mail/core/common/chat_window_container";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { App, onMounted } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { fakeCookieService } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup, makeDeferred } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";

// =============================================================================
// HELPERS
// =============================================================================

let cookie = {};
QUnit.testDone(() => (cookie = {}));

/**
 * Set a cookie to be used by the current test.
 *
 * @param {string} key
 * @param {string} val
 */
export function setCookie(key, val) {
    cookie[key] = val;
}

// =============================================================================
// SETUP
// =============================================================================

/**
 * Setup the server side of the livechat app.
 *
 * @returns {Promise<number>} the id of the livechat channel.
 */
export async function loadDefaultConfig() {
    const pyEnv = await getPyEnv();
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [pyEnv.currentUserId],
    });
    patchWithCleanup(session, {
        livechatData: {
            isAvailable: true,
            serverUrl: window.origin,
            options: {
                header_background_color: "#875A7B",
                button_background_color: "#875A7B",
                title_color: "#FFFFFF",
                button_text_color: "#FFFFFF",
                button_text: "Have a Question? Chat with us.",
                input_placeholder: false,
                default_message: "Hello, how may I help you?",
                channel_name: "YourWebsite.com",
                channel_id: livechatChannelId,
                default_username: "Visitor",
            },
        },
    });
    return livechatChannelId;
}

patch(App.prototype, {
    mount() {
        registerCleanup(() => this.destroy());
        return super.mount(...arguments);
    },
});

/**
 * Mount the livechat button into the webclient.
 *
 * @param {Object} param0
 * @returns {Promise<any>}
 */
export async function start({ mockRPC } = {}) {
    setupManager.setupServiceRegistries();
    registry.category("services").add(
        "cookie",
        {
            start() {
                const service = fakeCookieService.start(...arguments);
                return {
                    ...service,
                    get current() {
                        return {
                            ...service.current,
                            ...cookie,
                        };
                    },
                };
            },
        },
        { force: true }
    );
    const mainComponentRegistry = registry.category("main_components");
    mainComponentRegistry.add("LivechatButton", { Component: LivechatButton });
    mainComponentRegistry.add("ChatWindowContainer", { Component: ChatWindowContainer });
    const livechatButtonAvailableDeferred = makeDeferred();
    patchWithCleanup(LivechatButton.prototype, {
        setup() {
            super.setup(...arguments);
            onMounted(() => livechatButtonAvailableDeferred.resolve());
        },
    });
    const pyEnv = await getPyEnv();
    const { env } = await createWebClient({
        serverData: {
            models: pyEnv.getData(),
            views: pyEnv.getViews(),
        },
        mockRPC,
    });
    await livechatButtonAvailableDeferred;
    return env;
}
