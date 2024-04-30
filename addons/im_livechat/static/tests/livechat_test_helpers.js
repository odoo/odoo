import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, serverState } from "@web/../tests/web_test_helpers";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { DiscussChannelMember } from "./mock_server/mock_models/discuss_channel_member";
import { LivechatChannel } from "./mock_server/mock_models/im_livechat_channel";
import { ResGroups } from "./mock_server/mock_models/res_groups";
import { ResLang } from "./mock_server/mock_models/res_lang";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";

export function defineLivechatModels() {
    return defineModels(livechatModels);
}

export const livechatModels = {
    ...mailModels,
    DiscussChannel,
    DiscussChannelMember,
    LivechatChannel,
    ResLang,
    ResPartner,
    ResUsers,
    ResGroups,
};

serverState.groupLivechatId = 42;
