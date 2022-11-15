/** @odoo-module */

import { Component } from "@odoo/owl";
import { LinkPreviewAside } from "./link_preview_aside";

export class LinkPreviewCard extends Component {}

Object.assign(LinkPreviewCard, {
    template: "mail.link_preview_card",
    components: { LinkPreviewAside },
    props: ["linkPreview", "canBeDeleted"],
});
