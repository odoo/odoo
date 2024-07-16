import { makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailLinkPreview extends models.ServerModel {
    _name = "mail.link.preview";

    /** @param {object} linkPreview */
    _to_store(ids, store) {
        for (const linkPreview of this.browse(ids)) {
            const [data] = this.read(
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
                makeKwArgs({ load: false })
            );
            data.message = linkPreview.message_id ? { id: linkPreview.message_id } : false;
            store.add("mail.link.preview", data);
        }
    }
}
