import { mailModels } from "@mail/../tests/mail_test_helpers";

export class ResUsersSettings extends mailModels.ResUsersSettings {
    _store_settings_fields(res) {
        super._store_settings_fields(res);
        res.extend(["livechat_username", "livechat_lang_ids", "livechat_expertise_ids"]);
    }
}
