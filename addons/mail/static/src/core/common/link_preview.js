import { Gif } from "@mail/core/common/gif";
import { LinkPreviewConfirmDelete } from "@mail/core/common/link_preview_confirm_delete";

import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").LinkPreview} linkPreview
 * @property {import("models").Message} [message]
 * @property {Boolean} [gifPaused]
 * @property {function} [delete] Function bound to the delete button
 * @property {function} [deleteAll] Function bound to the delete all button
 * @extends {Component<Props, Env>}
 */
export class LinkPreview extends Component {
    static template = "mail.LinkPreview";
    static props = ["linkPreview", "delete?", "deleteAll?", "gifPaused?", "message?"];
    static components = { Gif };

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.state = useState({ startVideo: false, videoLoaded: false });
        this.videoRef = useRef("video");
        useEffect(
            (el) => {
                if (el) {
                    el.onload = () => (this.state.videoLoaded = true);
                }
            },
            () => [this.videoRef.el]
        );
    }

    onClick() {
        this.dialogService.add(LinkPreviewConfirmDelete, {
            linkPreview: this.props.linkPreview,
            delete: this.props.delete,
            deleteAll: this.props.deleteAll,
            LinkPreview,
        });
    }

    onImageLoaded() {
        this.env.onImageLoaded?.();
    }
}
