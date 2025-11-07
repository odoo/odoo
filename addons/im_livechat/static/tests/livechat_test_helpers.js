import { mailModels, startServer } from "@mail/../tests/mail_test_helpers";
import { RatingRating } from "@rating/../tests/mock_server/models/rating_rating";
import {
    defineModels,
    serverState,
    patchWithCleanup,
    MockServer,
} from "@web/../tests/web_test_helpers";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { DiscussChannelMember } from "./mock_server/mock_models/discuss_channel_member";
import { LivechatChannel } from "./mock_server/mock_models/im_livechat_channel";
import { LivechatChannelRule } from "./mock_server/mock_models/livechat_channel_rule";
import { Im_LivechatExpertise } from "./mock_server/mock_models/im_livechat_expertise";
import { ResGroupsPrivilege } from "./mock_server/mock_models/res_groups_privilege";
import { ResGroups } from "./mock_server/mock_models/res_groups";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { session } from "@web/session";

export function defineLivechatModels() {
    return defineModels(livechatModels);
}

export const livechatModels = {
    ...mailModels,
    DiscussChannel,
    DiscussChannelMember,
    LivechatChannel,
    LivechatChannelRule,
    Im_LivechatExpertise,
    RatingRating,
    ResPartner,
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
                header_background_color: "#875A7B",
                button_background_color: "#875A7B",
                title_color: "#FFFFFF",
                button_text_color: "#FFFFFF",
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
