import { CrmLead } from "@crm/../tests/mock_server/mock_models/crm_lead";

import { ResUsers } from "@crm_livechat/../tests/mock_server/mock_models/res_users";

import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { defineModels } from "@web/../tests/web_test_helpers";

export function defineCrmLivechatModels() {
    return defineModels({ ...livechatModels, CrmLead, ResUsers });
}
