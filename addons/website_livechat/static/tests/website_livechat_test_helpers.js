import { busModels } from "@bus/../tests/bus_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { webModels, defineModels, defineParams } from "@web/../tests/web_test_helpers";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { Website } from "./mock_server/mock_models/website";
import { WebsiteVisitor } from "./mock_server/mock_models/website_visitor";

export function defineWebsiteLivechatModels() {
    defineParams({ suite: "website_livechat" }, "replace");
    return defineModels({
        ...webModels,
        ...busModels,
        ...mailModels,
        ...livechatModels,
        ...websiteLivechatModels,
    });
}

export const websiteLivechatModels = {
    DiscussChannel,
    Website,
    WebsiteVisitor,
};
