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
                    "message_id",
                    "og_description",
                    "og_image",
                    "og_mimetype",
                    "og_title",
                    "og_type",
                    "source_url",
                ],
                makeKwArgs({ load: false })
            );
            store.add(this.browse(linkPreview.id), data);
        }
    }
}
