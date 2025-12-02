import { models } from "@web/../tests/web_test_helpers";

export class MailLinkPreview extends models.ServerModel {
    _name = "mail.link.preview";

    get _to_store_defaults() {
        return [
            "image_mimetype",
            "message_id",
            "og_description",
            "og_image",
            "og_mimetype",
            "og_title",
            "og_type",
            "source_url",
        ];
    }
}
