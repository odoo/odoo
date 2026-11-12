import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    phone_sanitized = fields.Char();
    phone_formatted = fields.Char();

    _store_avatar_card_fields(res) {
        super._store_avatar_card_fields(res);
        if (res.is_for_internal_users()) {
            res.extend(["phone_formatted", "phone_sanitized"]);
        }
    }
}
