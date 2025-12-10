import { patch } from "@web/core/utils/patch";
import { ImageSelector as HtmlImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

patch(HtmlImageSelector.prototype, {
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        // Add website logos to media manager
        domain.unshift(
            "|",
            "|",
            "&",
            ["res_model", "=", "website"],
            ["res_id", "=", this.env.services.website.currentWebsiteId],
            ["res_field", "=", "logo"]
        );
        domain.push("|", ["url", "=", false], "!", ["url", "=like", "/web/image/website.%"]);
        domain.push(["key", "=", false]);
        return domain;
    },
});

patch(HtmlImageSelector, {
    mediaExtraClasses: [...HtmlImageSelector.mediaExtraClasses, "social_media_img"],
});
