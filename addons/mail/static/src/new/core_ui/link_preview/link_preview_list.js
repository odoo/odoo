/* @odoo-module */

import { Component } from "@odoo/owl";
import { LinkPreview } from "./link_preview";

/**
 * @typedef {Object} Props
 * @property {import("@mail/new/core/link_preview_model").LinkPreview[]} linkPreviews
 * @property {boolean} [deletable]
 * @extends {Component<Props, Env>}
 */
export class LinkPreviewList extends Component {
    static template = "mail.link_preview_list";
    static props = ["linkPreviews", "deletable?"];
    static defaultProps = {
        deletable: false,
    };
    static components = { LinkPreview };
}
