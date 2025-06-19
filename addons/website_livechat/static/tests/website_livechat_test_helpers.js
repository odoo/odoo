import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { defineModels, defineParams } from "@web/../tests/web_test_helpers";
import { websiteModels } from "@website/../tests/helpers";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { WebsiteVisitor } from "./mock_server/mock_models/website_visitor";

export function defineWebsiteLivechatModels() {
    defineParams({ suite: "website_livechat" }, "replace");
    return defineModels(websiteLivechatModels);
}

export const websiteLivechatModels = {
    ...livechatModels,
    ...websiteModels,
    WebsiteVisitor,
    DiscussChannel,
};
