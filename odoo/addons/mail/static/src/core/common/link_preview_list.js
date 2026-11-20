/* @odoo-module */

import { LinkPreview } from "@mail/core/common/link_preview";

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("models").LinkPreview[]} linkPreviews
 * @property {boolean} [deletable]
 * @extends {Component<Props, Env>}
 */
export class LinkPreviewList extends Component {
    static template = "mail.LinkPreviewList";
    static props = ["linkPreviews", "deletable?"];
    static defaultProps = {
        deletable: false,
    };
    static components = { LinkPreview };
}
