import { PopoutableMixin } from "@mail/core/common/popoutable_mixin";

import { Component, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { hidePDFJSButtons } from "@web/libs/pdfjs";

export const AttachmentViewVisibilityControllerMixin = (component) =>
    class extends component {
        get attachmentViewParentElementClassList() {
            const attachmentViewEl = document.querySelector(".o-mail-Attachment");
            let parentElementClassList;
            if ((parentElementClassList = attachmentViewEl?.parentElement?.classList)) {
                return parentElementClassList;
            }
            return null;
        }

        showAttachmentView() {
            const parentElementClassList = this.attachmentViewParentElementClassList;
            const hiddenClass = "d-none";
            if (parentElementClassList?.contains(hiddenClass)) {
                parentElementClassList.remove(hiddenClass);
            }
        }

        hideAttachmentView() {
            const parentElementClassList = this.attachmentViewParentElementClassList;
            const hiddenClass = "d-none";
            if (!parentElementClassList?.contains(hiddenClass)) {
                parentElementClassList?.add(hiddenClass);
            }
        }
    };

/**
 * @typedef {Object} Props
 * @property {number} threadId
 * @property {string} threadModel
 * @extends {Component<Props, Env>}
 */
export class AttachmentView extends AttachmentViewVisibilityControllerMixin(
    PopoutableMixin(Component)
) {
    static template = "mail.AttachmentView";
    static components = {};
    static props = ["threadId", "threadModel"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.uiService = useService("ui");
        this.iframeViewerPdfRef = useRef("iframeViewerPdf");
        this.state = useState({
            /** @type {import("models").Thread|undefined} */
            thread: undefined,
        });
        useEffect(() => {
            if (this.iframeViewerPdfRef.el) {
                hidePDFJSButtons(this.iframeViewerPdfRef.el);
            }
        });
        this.updateFromProps(this.props);
        onWillUpdateProps((props) => this.updateFromProps(props));
    }

    onClickNext() {
        const index = this.state.thread.attachmentsInWebClientView.findIndex((attachment) =>
            attachment.eq(this.state.thread.mainAttachment)
        );
        this.state.thread.setMainAttachmentFromIndex(
            index === this.state.thread.attachmentsInWebClientView.length - 1 ? 0 : index + 1
        );
    }

    onClickPrevious() {
        const index = this.state.thread.attachmentsInWebClientView.findIndex((attachment) =>
            attachment.eq(this.state.thread.mainAttachment)
        );
        this.state.thread.setMainAttachmentFromIndex(
            index === 0 ? this.state.thread.attachmentsInWebClientView.length - 1 : index - 1
        );
    }

    updateFromProps(props) {
        this.state.thread = this.store.Thread.insert({
            id: props.threadId,
            model: props.threadModel,
        });
    }

    get displayName() {
        return this.state.thread.mainAttachment.filename;
    }

    /********** Popoutable mixin overrides **********/
    beforePopout() {
        this.hideAttachmentView();
        this.uiService.bus.trigger("resize");
    }
    afterPopoutClosed() {
        this.showAttachmentView();
        this.uiService.bus.trigger("resize");
    }
    get popoutComponent() {
        return PopoutAttachmentView;
    }
    /************************************************/

    popoutAttachment() {
        this.popout();
    }
}

/*
 * AttachmentView inside popout window.
 * Popout features disabled as this only makes sense in the non-popout AttachmentView.
 */
export class PopoutAttachmentView extends AttachmentView {
    static template = "mail.PopoutAttachmentView";
    popout() {}
    resetPopout() {}
}
