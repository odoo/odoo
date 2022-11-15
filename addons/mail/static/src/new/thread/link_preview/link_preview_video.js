/** @odoo-module */

import { Component } from "@odoo/owl";
import { LinkPreviewAside } from "./link_preview_aside";

export class LinkPreviewVideo extends Component {}

Object.assign(LinkPreviewVideo, {
    template: "mail.link_preview_video",
    components: { LinkPreviewAside },
    props: ["linkPreview", "canBeDeleted"],
});
