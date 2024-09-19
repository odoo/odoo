import { LinkPreviewConfirmDelete } from "@mail/core/common/link_preview_confirm_delete";

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").LinkPreview} linkPreview
 * @property {import("models").Message} message
 * @property {boolean} [deletable]
 * @extends {Component<Props, Env>}
 */
export class LinkPreview extends Component {
    static template = "mail.LinkPreview";
    static props = ["linkPreview", "message?", "deletable"];
    static components = {};

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    onClick() {
        this.dialogService.add(LinkPreviewConfirmDelete, {
            linkPreview: this.props.linkPreview,
            message: this.props.message,
            LinkPreview,
        });
    }

    onImageLoaded() {
        this.env.onImageLoaded?.();
    }
}
