import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Gif } from "@mail/core/common/gif";
import { LinkPreviewConfirmDelete } from "@mail/core/common/link_preview_confirm_delete";

import { Component, props, proxy, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class LinkPreview extends Component {
    static components = { Gif };
    static template = "mail.LinkPreview";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            messageLinkPreview: types.instanceOf(this.store["mail.message.link.preview"].Class),
        });
        this.dialogService = useService("dialog");
        this.ui = useService("ui");
        this.state = proxy({ startVideo: false, videoLoaded: false });
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
