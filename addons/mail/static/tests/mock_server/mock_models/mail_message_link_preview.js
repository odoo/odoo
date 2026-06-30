import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { fields, models } from "@web/../tests/web_test_helpers";

export class MailMessageLinkPreview extends models.ServerModel {
    _name = "mail.message.link.preview";

    link_preview_id = fields.Many2one({ relation: "mail.link.preview" });
    message_id = fields.Many2one({ relation: "mail.message" });
    is_hidden = fields.Generic({ default: false });

    get _to_store_defaults() {
        return [mailDataHelpers.Store.one("link_preview_id"), "message_id"];
    }
}
