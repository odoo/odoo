import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailLinkPreview extends models.ServerModel {
    _name = "mail.link.preview";

    /** @param {object} linkPreview */
    _to_store(ids, store) {
        for (const linkPreview of this.browse(ids)) {
            const [data] = this._read_format(
                linkPreview.id,
                [
                    "image_mimetype",
                    "og_description",
                    "og_image",
                    "og_mimetype",
                    "og_title",
                    "og_type",
                    "source_url",
                ],
                false
            );
            data.message = mailDataHelpers.Store.one(
                this.env["mail.message"].browse(linkPreview.message_id),
                makeKwArgs({ only_id: true })
            );
            store.add(this.browse(linkPreview.id), data);
        }
    }
}
