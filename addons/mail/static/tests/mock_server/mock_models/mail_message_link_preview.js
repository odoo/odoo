import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { fields, models, makeKwArgs } from "@web/../tests/web_test_helpers";

export class MailMessageLinkPreview extends models.ServerModel {
    _name = "mail.message.link.preview";

    link_preview_id = fields.Many2one({ relation: "mail.link.preview" });
    message_id = fields.Many2one({ relation: "mail.message" });
    is_hidden = fields.Generic({ default: false });

    _to_store(ids, store) {
        for (const message_link_preview of this.browse(ids)) {
            store.add(this.browse(message_link_preview.id), {
                link_preview_id: mailDataHelpers.Store.one(
                    this.env["mail.link.preview"].browse(message_link_preview.link_preview_id),
                ),
                message_id: mailDataHelpers.Store.one(
                    this.env["mail.message"].browse(message_link_preview.message_id),
                    makeKwArgs({ only_id: true })
                ),
            });
        }
    }
}
