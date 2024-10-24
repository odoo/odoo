import { fields, models } from "@web/../tests/web_test_helpers";

export class MailLinkPreviewMessage extends models.ServerModel {
    _name = "mail.link.preview.message";

    link_preview_id = fields.Many2one({ relation: "mail.link.preview" });
    message_id = fields.Many2one({ relation: "mail.message" });
    is_hidden = fields.Generic({ default: false });
}
