import { mailModels } from "@mail/../tests/mail_test_helpers";

export class MailMessage extends mailModels.MailMessage {
    _author_to_store_partner_fields() {
        return [...super._author_to_store_partner_fields(), "im_status", "leave_date_to"];
    }
}
