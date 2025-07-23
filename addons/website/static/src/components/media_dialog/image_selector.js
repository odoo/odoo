import { patch } from "@web/core/utils/patch";
import { ImageSelector as HtmlImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

patch(HtmlImageSelector.prototype, {
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push("|", ["url", "=", false], "!", ["url", "=like", "/web/image/website.%"]);
        domain.push(["key", "=", false]);
        return domain;
    },
});

const classesToRemove = ["img-thumbnail"];

patch(HtmlImageSelector, {
    mediaExtraClasses: [
        ...HtmlImageSelector.mediaExtraClasses.filter((cls) => !classesToRemove.includes(cls)),
        "social_media_img",
    ],
});
