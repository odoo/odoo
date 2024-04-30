import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { Website } from "./mock_server/mock_models/website";
import { WebsiteVisitor } from "./mock_server/mock_models/website_visitor";

export function defineWebsiteLivechatModels() {
    return defineModels(websiteLivechatModels);
}

export const websiteLivechatModels = {
    ...livechatModels,
    DiscussChannel,
    Website,
    WebsiteVisitor,
};
