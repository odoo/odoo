import { LinkPreview } from "@mail/core/common/link_preview";

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("models").MessageLinkPreview[]} messageLinkPreviews
 * @extends {Component<Props, Env>}
 */
export class MessageLinkPreviewList extends Component {
    static template = "mail.MessageLinkPreviewList";
    static props = ["messageLinkPreviews"];
    static components = { LinkPreview };
}
