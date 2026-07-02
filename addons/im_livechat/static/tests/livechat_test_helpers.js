import { IrWebSocket } from "@im_livechat/../tests/mock_server/mock_models/ir_websocket";

import {
    insertText,
    mailModels,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import {
    defineModels,
    serverState,
    patchWithCleanup,
    MockServer,
} from "@web/../tests/web_test_helpers";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { DiscussChannelMember } from "./mock_server/mock_models/discuss_channel_member";
import { LivechatChannel } from "./mock_server/mock_models/im_livechat_channel";
import { LivechatChannelMemberHistory } from "./mock_server/mock_models/im_livechat_channel_member_history";
import { LivechatChannelRule } from "./mock_server/mock_models/livechat_channel_rule";
import { Im_LivechatExpertise } from "./mock_server/mock_models/im_livechat_expertise";
import { ResGroupsPrivilege } from "./mock_server/mock_models/res_groups_privilege";
import { ResGroups } from "./mock_server/mock_models/res_groups";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { session } from "@web/session";

export function defineLivechatModels() {
    return defineModels(livechatModels);
}

/**
 * Type `text` into the livechat composer once it is enabled, then send it.
 *
 * Gating on `:enabled` mirrors real user interaction: the composer is disabled
 * while a chatbot step is being processed, and `insertText` would otherwise
 * write into it regardless. Use this instead of a raw `insertText` + Enter so
 * tests never answer a step the chatbot has not settled on yet.
 *
 * @param {string} text
 */
export async function postLivechatMessage(text) {
    await insertText(".o-mail-Composer-input:enabled", text);
    await triggerHotkey("Enter");
}

export const livechatModels = {
    ...mailModels,
    DiscussChannel,
    DiscussChannelMember,
    LivechatChannel,
    LivechatChannelMemberHistory,
    LivechatChannelRule,
    Im_LivechatExpertise,
    IrWebSocket,
    ResUsers,
    ResGroupsPrivilege,
    ResGroups,
};

serverState.groupLivechatId = 42;
serverState.groupLivechatManagerId = 43;

/**
 * Setup the server side of the livechat app.
 *
 * @returns {Promise<number>} the id of the livechat channel.
 */
export async function loadDefaultEmbedConfig() {
    const pyEnv = MockServer.env ?? (await startServer());
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [serverState.userId],
    });
    patchWithCleanup(session, {
        livechatData: {
            can_load_livechat: true,
            serverUrl: window.origin,
            options: {
                widget_background_color: "#875A7B",
                widget_text_color: "#FFFFFF",
                button_text: "Need help? Chat with us.",
                default_message: "Hello, how may I help you?",
                channel_name: "YourWebsite.com",
                channel_id: livechatChannelId,
                default_username: "Visitor",
                review_link: "https://www.odoo.com",
            },
        },
    });
    return livechatChannelId;
}
