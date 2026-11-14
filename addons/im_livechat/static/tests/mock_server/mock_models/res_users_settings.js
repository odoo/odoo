import { mailModels } from "@mail/../tests/mail_test_helpers";

import { fields } from "@web/../tests/web_test_helpers";

export class ResUsersSettings extends mailModels.ResUsersSettings {
    livechat_push = fields.Boolean({ default: true });

    _store_settings_fields(res) {
        super._store_settings_fields(res);
        res.extend([
            "livechat_username",
            "livechat_lang_ids",
            "livechat_expertise_ids",
            "livechat_push",
        ]);
    }
}
