import { crmModels } from "@crm/../tests/crm_test_helpers";

import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { defineModels } from "@web/../tests/web_test_helpers";

export function defineCrmLivechatModels() {
    return defineModels({ ...crmModels, ...livechatModels });
}
