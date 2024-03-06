import { models } from "@web/../tests/web_test_helpers";

export class MailLinkPreview extends models.ServerModel {
    _name = "mail.link.preview";

    /** @param {object} linkPreview */
    _link_preview_format(linkPreview) {
        return {
            id: linkPreview.id,
            message: { id: linkPreview.message_id[0] || linkPreview.message_id },
            image_mimetype: linkPreview.image_mimetype,
            og_description: linkPreview.og_description,
            og_image: linkPreview.og_image,
            og_mimetype: linkPreview.og_mimetype,
            og_title: linkPreview.og_title,
            og_type: linkPreview.og_type,
            source_url: linkPreview.source_url,
        };
    }
}
