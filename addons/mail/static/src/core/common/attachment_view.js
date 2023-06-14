/* @odoo-module */

import { insertThread, setMainAttachmentFromIndex } from "@mail/core/common/thread_service";
import { Component, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";

import { hidePDFJSButtons } from "@web/legacy/js/libs/pdfjs";

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
        this.iframeViewerPdfRef = useRef("iframeViewerPdf");
        this.state = useState({
            /** @type {import("@mail/core/common/thread_model").Thread} */
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
        const index = this.state.thread.attachmentsInWebClientView.findIndex(
            (attachment) => attachment.id === this.state.thread.mainAttachment.id
        );
        setMainAttachmentFromIndex(
            this.state.thread,
            index === this.state.thread.attachmentsInWebClientView.length - 1 ? 0 : index + 1
        );
    }

    onClickPrevious() {
        const index = this.state.thread.attachmentsInWebClientView.findIndex(
            (attachment) => attachment.id === this.state.thread.mainAttachment.id
        );
        setMainAttachmentFromIndex(
            this.state.thread,
            index === 0 ? this.state.thread.attachmentsInWebClientView.length - 1 : index - 1
        );
    }

    updateFromProps(props) {
        this.state.thread = insertThread({
            id: props.threadId,
            model: props.threadModel,
        });
    }
}
