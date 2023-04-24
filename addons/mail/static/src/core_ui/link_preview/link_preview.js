/* @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { LinkPreviewConfirmDelete } from "./link_preview_confirm_delete";
import { useViewer, Viewable } from "@mail/viewer/viewer_hook";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/link_preview_model").LinkPreview} linkPreview
 * @property {boolean} [deletable]
 * @extends {Component<Props, Env>}
 */
export class LinkPreview extends Component {
    static template = "mail.LinkPreview";
    static props = ["linkPreview", "deletable"];

    setup() {
        this.dialogService = useService("dialog");
        this.viewer = useViewer();
    }

    openViewer() {
        const viewable = new Viewable(
            this.props.linkPreview.imageUrl,
            this.props.linkPreview.imageUrl,
            this.props.linkPreview.image_mimetype
        );
        this.viewer.open(viewable);
    }

    onClick() {
        this.dialogService.add(LinkPreviewConfirmDelete, {
            linkPreview: this.props.linkPreview,
            LinkPreview,
        });
    }
}
