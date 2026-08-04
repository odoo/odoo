import { ResUsersSettings } from "@mail/core/common/res_users_settings_model";

import { patch } from "@web/core/utils/patch";

patch(ResUsersSettings.prototype, {
    setup() {
        super.setup();
        /** @type {number[]} */
        this.livechat_expertise_ids = undefined;
        /** @type {number[]} */
        this.livechat_lang_ids = undefined;
        /** @type {string|undefined} */
        this.livechat_username = undefined;
    },
});
