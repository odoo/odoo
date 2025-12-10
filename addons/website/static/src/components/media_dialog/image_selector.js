import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
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

        // Surface this site's uploaded media (res_field=false) - including
        // logos uploaded via the media manager - in every media dialog. The
        // bound `website.logo` row (res_field='logo') is kept hidden: its
        // `/web/image/website/<id>/logo` URL serves a downscaled render that
        // looks blurry next to the original upload.
        const regular = Domain.and([
            domain,
            ["|", ["res_model", "!=", "website"], ["res_field", "=", false]],
        ]);
        const websiteUploads = Domain.and([
            [["res_model", "=", "website"]],
            [["res_id", "=", websiteId]],
            [["res_field", "=", false]],
        ]);
        return Domain.or([websiteUploads, regular]).toList();
    },
});

patch(HtmlImageSelector, {
    mediaExtraClasses: [...HtmlImageSelector.mediaExtraClasses, "social_media_img"],
});
