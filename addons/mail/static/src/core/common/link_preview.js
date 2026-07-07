import { Gif } from "@mail/core/common/gif";
import { LinkPreviewConfirmDelete } from "@mail/core/common/link_preview_confirm_delete";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, proxy, signal, t, useOnChange } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class LinkPreview extends Component {
    static components = { Gif };
    static template = "mail.LinkPreview";

    videoRef = signal.ref();
    imageRef = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.messageLinkPreview = propComputed(
            "messageLinkPreview",
            t.instanceOf(this.store["mail.message.link.preview"])
        );
        this.dialogService = useService("dialog");
        this.ui = useService("ui");
        this.state = proxy({ startVideo: false, videoLoaded: false });
        useOnChange(
            () => [this.videoRef()],
            (el) => {
                if (el) {
                    el.onload = () => (this.state.videoLoaded = true);
                }
            }
        );
    }

    get linkPreview() {
        return this.messageLinkPreview().link_preview_id;
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ messageLinkPreviewAtRender: import("models").MessageLinkPreview }} param1
     */
    onClick(ev, { messageLinkPreviewAtRender }) {
        this.dialogService.add(LinkPreviewConfirmDelete, {
            LinkPreview,
            messageLinkPreview: messageLinkPreviewAtRender,
        });
    }

    onImageLoaded() {
        const img = this.imageRef();
        if (!img || !img.naturalWidth || !img.naturalHeight) {
            return;
        }
        const aspectRatio = img.naturalWidth / img.naturalHeight;
        // Determine if image is squarish (aspect ratio between 2:3 and 3:2)
        this.linkPreview.hasSquarishCardImage = aspectRatio >= 0.67 && aspectRatio <= 1.5;
        this.env.onImageLoaded?.();
    }
}
