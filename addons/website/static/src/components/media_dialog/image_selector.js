import { patch } from "@web/core/utils/patch";
import { ImageSelector as HtmlImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

patch(HtmlImageSelector.prototype, {
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push('|', ['url', '=', false], '!', ['url', '=like', '/web/image/website.%']);
        domain.push(['key', '=', false]);
        return domain;
    }
});

patch(HtmlImageSelector, {
    mediaExtraClasses: HtmlImageSelector.mediaExtraClasses.concat(
        "social_media_img",
        (props) => {
            if (
                props.node &&
                props.node.classList.contains("fa") &&
                props.node.closest("div")?.classList.contains("s_social_media")
            ) {
                return "social_media_img";
            }
        },
        (props) => {
            if (
                props.node &&
                props.node.classList.contains("fa") &&
                props.node.closest("div")?.classList.contains("s_social_media")
            ) {
                for (const element of props.node.classList) {
                    if (element.match(/fa-\d{1}x/)) {
                        return element;
                    }
                }
            }
        }
    ),
});
