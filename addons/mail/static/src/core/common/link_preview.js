import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { Gif } from "@mail/core/common/gif";
import { LinkPreviewConfirmDelete } from "@mail/core/common/link_preview_confirm_delete";

import { Component } from "@odoo/owl";

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
        this.ui = useService("ui");
        this.state = useState({ startVideo: false, videoLoaded: false });
        this.videoRef = useRef("video");
        this.imageRef = useRef("image");
        useLayoutEffect(
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
        const img = this.imageRef?.el;
        if (!img || !img.naturalWidth || !img.naturalHeight) {
            return;
        }
        const aspectRatio = img.naturalWidth / img.naturalHeight;
        // Determine if image is squarish (aspect ratio between 2:3 and 3:2)
        this.linkPreview.hasSquarishCardImage = aspectRatio >= 0.67 && aspectRatio <= 1.5;
        this.env.onImageLoaded?.();
    }
}
