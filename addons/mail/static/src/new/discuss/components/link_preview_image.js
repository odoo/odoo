/** @odoo-module **/

import { LinkPreviewAside } from "@mail/new/discuss/components/link_preview_aside";

import { Component } from "@odoo/owl";

export class LinkPreviewImage extends Component {
    get imageUrl() {
        return this.props.linkPreview.og_image
            ? this.props.linkPreview.og_image
            : this.props.linkPreview.source_url;
    }
}

Object.assign(LinkPreviewImage, {
    template: "mail.link_preview_image",
    components: { LinkPreviewAside },
    props: ["linkPreview", "canBeDeleted"],
});
