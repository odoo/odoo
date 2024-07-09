import { models } from "@web/../tests/web_test_helpers";

export class MailLinkPreview extends models.ServerModel {
    _name = "mail.link.preview";

    /** @param {object} linkPreview */
    _to_store(ids, store) {
        for (const linkPreview of this.browse(ids)) {
            store.add("LinkPreview", {
                id: linkPreview.id,
                image_mimetype: linkPreview.image_mimetype,
                message: linkPreview.message_id ? { id: linkPreview.message_id } : false,
                og_description: linkPreview.og_description,
                og_image: linkPreview.og_image,
                og_mimetype: linkPreview.og_mimetype,
                og_title: linkPreview.og_title,
                og_type: linkPreview.og_type,
                source_url: linkPreview.source_url,
            });
        }
    }
}
