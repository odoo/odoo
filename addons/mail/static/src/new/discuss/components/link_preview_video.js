/** @odoo-module **/

import { LinkPreviewAside } from "@mail/new/discuss/components/link_preview_aside";

import { Component } from "@odoo/owl";

export class LinkPreviewVideo extends Component {}

Object.assign(LinkPreviewVideo, {
    template: "mail.link_preview_video",
    components: { LinkPreviewAside },
    props: ["linkPreview", "canBeDeleted"],
});
