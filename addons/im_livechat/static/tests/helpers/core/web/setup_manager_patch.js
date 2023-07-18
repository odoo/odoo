/* @odoo-module */

import { livechatCoreWeb } from "@im_livechat/core/web/livechat_core_web_service";

import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { patch } from "@web/core/utils/patch";

patch(setupManager, "im_livechat/core/web", {
    setupServices(...args) {
        return {
            ...this._super(...args),
            "im_livechat.core.web": livechatCoreWeb,
        };
    },
});
