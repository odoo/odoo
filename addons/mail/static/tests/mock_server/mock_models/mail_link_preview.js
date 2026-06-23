import { models } from "@web/../tests/web_test_helpers";

export class MailLinkPreview extends models.ServerModel {
    _name = "mail.link.preview";

    _store_link_preview_fields(res) {
        res.extend(["image_mimetype", "og_description", "og_image", "og_mimetype", "og_site_name"]);
        res.extend(["og_title", "og_type", "source_url"]);
    }
}
