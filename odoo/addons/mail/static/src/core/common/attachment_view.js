/* @odoo-module */

import { Component, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { hidePDFJSButtons } from "@web/libs/pdfjs";

/**
 * @typedef {Object} Props
 * @property {number} threadId
 * @property {string} threadModel
 * @extends {Component<Props, Env>}
 */
export class AttachmentView extends Component {
    static template = "mail.AttachmentView";
    static components = {};
    static props = ["threadId", "threadModel"];

    setup() {
        this.threadService = useService("mail.thread");
        this.store = useState(useService("mail.store"));
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
        this.threadService.setMainAttachmentFromIndex(
            this.state.thread,
            index >= this.state.thread.attachmentsInWebClientView.length - 1 ? 0 : index + 1
        );
    }

    onClickPrevious() {
        const index = this.state.thread.attachmentsInWebClientView.findIndex((attachment) =>
            attachment.eq(this.state.thread.mainAttachment)
        );
        this.threadService.setMainAttachmentFromIndex(
            this.state.thread,
            index <= 0 ? this.state.thread.attachmentsInWebClientView.length - 1 : index - 1
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
}
