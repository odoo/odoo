import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
import { IMAGE_MIMETYPES } from "@html_editor/main/media/media_dialog/file_selector";
import { ImageSelector as HtmlImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

patch(HtmlImageSelector.prototype, {
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push("|", ["url", "=", false], "!", ["url", "=like", "/web/image/website.%"]);
        domain.push(["key", "=", false]);

        const websiteId = this.env.services.website?.currentWebsiteId;
        if (!websiteId) {
            return domain;
        }

        // A website logo exists as two attachments: the clean copy the user
        // uploaded and the one bound to the logo field (blurry, because it's
        // rendered downscaled). Show the clean copy in the media manager hide
        // the blurry bound one.
        const regular = Domain.and([
            domain,
            ["|", ["res_model", "!=", "website"], ["res_field", "=", false]],
        ]);
        const websiteUploads = Domain.and([
            [["res_model", "=", "website"]],
            [["res_id", "=", websiteId]],
            [["res_field", "=", false]],
            [["mimetype", "in", IMAGE_MIMETYPES]],
        ]);
        return Domain.or([websiteUploads, regular]).toList();
    },
});

patch(HtmlImageSelector, {
    mediaExtraClasses: [...HtmlImageSelector.mediaExtraClasses, "social_media_img"],
});
