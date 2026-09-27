import { fields, models } from "@web/../tests/web_test_helpers";

export class MailMessageLinkPreview extends models.ServerModel {
    _name = "mail.message.link.preview";

    link_preview_id = fields.Many2one({ relation: "mail.link.preview" });
    message_id = fields.Many2one({ relation: "mail.message" });
    is_hidden = fields.Generic({ default: false });

    _store_message_link_preview_fields(res) {
        res.one("link_preview_id", "_store_link_preview_fields", { sudo: true });
        res.one("message_id", [], { sudo: true });
    }
}
