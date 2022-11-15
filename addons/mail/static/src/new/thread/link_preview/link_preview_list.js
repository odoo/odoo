/** @odoo-module */

import { Component } from "@odoo/owl";
import { LinkPreviewCard } from "./link_preview_card";
import { LinkPreviewImage } from "./link_preview_image";
import { LinkPreviewVideo } from "./link_preview_video";

export class LinkPreviewList extends Component {
    get linkPreviewsImage() {
        return this.props.linkPreviews.filter((linkPreview) =>
            Boolean(linkPreview.image_mimetype || linkPreview.og_mimetype === "image/gif")
        );
    }

    get linkPreviewsVideo() {
        return this.props.linkPreviews.filter((linkPreview) =>
            Boolean(
                linkPreview.og_type &&
                    linkPreview.og_type.startsWith("video") &&
                    !this.linkPreviewsImage.includes(linkPreview)
            )
        );
    }

    get linkPreviewsCard() {
        return this.props.linkPreviews.filter((linkPreview) =>
            Boolean(
                !this.linkPreviewsVideo.includes(linkPreview) &&
                    !this.linkPreviewsImage.includes(linkPreview)
            )
        );
    }
}

Object.assign(LinkPreviewList, {
    template: "mail.link_preview_list",
    components: { LinkPreviewCard, LinkPreviewImage, LinkPreviewVideo },
    defaultProps: {
        canBeDeleted: false,
    },
    props: ["linkPreviews", "canBeDeleted?"],
});
