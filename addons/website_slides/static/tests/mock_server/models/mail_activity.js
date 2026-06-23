import { mailModels } from "@mail/../tests/mail_test_helpers";

export class MailActivity extends mailModels.MailActivity {
    _store_activity_fields(res) {
        super._store_activity_fields(res);
        res.attr("request_partner_id");
    }
}
