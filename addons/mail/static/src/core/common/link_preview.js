import { Gif } from "@mail/core/common/gif";
import { LinkPreviewConfirmDelete } from "@mail/core/common/link_preview_confirm_delete";

import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").MessageLinkPreview} messageLinkPreview
 * @extends {Component<Props, Env>}
 */
export class LinkPreview extends Component {
    static template = "mail.LinkPreview";
    static props = ["messageLinkPreview"];
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

    get linkPreview() {
        return this.props.messageLinkPreview.link_preview_id;
    }

    onClick() {
        this.dialogService.add(LinkPreviewConfirmDelete, {
            LinkPreview,
            messageLinkPreview: this.props.messageLinkPreview,
        });
    }

    onImageLoaded() {
        this.env.onImageLoaded?.();
    }
}
