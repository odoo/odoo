import { LinkPreviewConfirmDelete } from "@mail/core/common/link_preview_confirm_delete";

import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").LinkPreview} linkPreview
 * @property {boolean} [deletable]
 * @extends {Component<Props, Env>}
 */
export class LinkPreview extends Component {
    static template = "mail.LinkPreview";
    static props = ["linkPreview", "deletable"];
    static components = {};

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
            LinkPreview,
        });
    }

    onImageLoaded() {
        this.env.onImageLoaded?.();
    }
}
