/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { createWebClient } from "@web/../tests/webclient/helpers";
import {
    patchWithCleanup,
    makeDeferred,
    getFixture,
    getTriggerHotkey,
} from "@web/../tests/helpers/utils";

import { livechatBootService } from "@im_livechat/new/frontend/boot_service";
import { publicLivechatService } from "@im_livechat/new/core/livechat_service";
import { LivechatButton } from "@im_livechat/new/core_ui/livechat_button";

import { onMounted } from "@odoo/owl";

import {
    setupManager,
    setupMessagingServiceRegistries,
} from "@mail/../tests/helpers/webclient_setup";
import { afterNextRender, getClick, getInsertText } from "@mail/../tests/helpers/test_utils";

// =============================================================================
// HELPERS
// =============================================================================

let shadowRoot;
QUnit.testDone(() => (shadowRoot = null));

export function click(selector) {
    return getClick({ target: shadowRoot, afterNextRender })(selector);
}

export function insertText(selector, text, options) {
    return getInsertText({ target: shadowRoot[0] })(selector, text, options);
}

export function triggerHotkey(key) {
    return getTriggerHotkey({ target: shadowRoot[0] })(key);
}

// =============================================================================
// SETUP
// =============================================================================

patch(setupManager, "im_livechat", {
    setupServices(...args) {
        const services = this._super(...args);
        return {
            "im_livechat.livechat": publicLivechatService,
            "im_livechat.boot": {
                ...livechatBootService,
                createRootNode() {
                    const root = document.createElement("div");
                    root.classList.add("o_livechat_root");
                    getFixture().appendChild(root);
                    return root;
                },
            },
            ...services,
        };
    },
    setupLivechatData({ channelId, currentPartnerId }) {
        return {
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
                channel_id: channelId,
                current_partner_id: currentPartnerId,
                default_username: "Visitor",
            },
        };
    },
});

/**
 * Mount the livechat button into the webclient.
 *
 * @param {Object} param0
 * @returns {Promise<any>}
 */
export async function start({ mockRPC } = {}) {
    const pyEnv = await startServer();
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [pyEnv.currentUserId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [[0, 0, { partner_id: pyEnv.currentPartnerId }]],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    patchWithCleanup(session, {
        livechatData: setupManager.setupLivechatData({
            channelId,
            currentPartnerId: pyEnv.currentPartnerId,
        }),
    });
    await setupMessagingServiceRegistries();
    const livechatButtonAvailableDeferred = makeDeferred();
    patchWithCleanup(LivechatButton.prototype, {
        setup() {
            this._super(...arguments);
            onMounted(() => livechatButtonAvailableDeferred.resolve());
        },
    });
    const { env } = await createWebClient({
        serverData: {
            models: pyEnv.getData(),
            views: pyEnv.getViews(),
        },
        mockRPC,
    });
    await livechatButtonAvailableDeferred;
    shadowRoot = $(document.querySelector(".o_livechat_root").shadowRoot);
    return {
        env,
        root: shadowRoot,
    };
}
