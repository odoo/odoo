import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { helpdeskModels } from "@helpdesk/../tests/helpdesk_test_helpers";
import { ResUsers } from "@website_helpdesk_livechat/../tests/mock_server/models/res_users";

export const websiteHelpdeskLivechatModels = { ...helpdeskModels, ...livechatModels, ResUsers };

export function defineWebsiteHelpdeskLivechatModels() {
    return defineModels(websiteHelpdeskLivechatModels);
}
