/** @odoo-module **/

import { LinkPreviewAside } from "@mail/new/discuss/components/link_preview_aside";

import { Component } from "@odoo/owl";

export class LinkPreviewCard extends Component {}

Object.assign(LinkPreviewCard, {
    template: "mail.link_preview_card",
    components: { LinkPreviewAside },
    props: ["linkPreview", "canBeDeleted"],
});
