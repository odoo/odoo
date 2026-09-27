import { defineModels } from "@web/../tests/web_test_helpers";
import { hrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { websiteLivechatModels } from "@website_livechat/../tests/website_livechat_test_helpers";
import { DiscussChannel } from "@website_livechat/../tests/mock_server/mock_models/discuss_channel";
import { DiscussChannelMember } from "@im_livechat/../tests/mock_server/mock_models/discuss_channel_member";

export function defineTestDiscussFullModels() {
    return defineModels(testDiscussFullModels);
}

export const testDiscussFullModels = {
    ...websiteLivechatModels,
    ...hrHolidaysModels,
    // reimport the livechat ones
    DiscussChannelMember,
    DiscussChannel,
};
