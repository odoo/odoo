/** @odoo-module **/

import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { attr, one, Model } from "@mail/model";

import { hidePDFJSButtons } from "@web/legacy/js/libs/pdfjs";

Model({
    name: "WebClientViewAttachmentView",
    template: "mail.WebClientViewAttachmentView",
    componentSetup() {
        useUpdateToModel({ methodName: "onComponentUpdate" });
    },
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickNext(ev) {
            ev.preventDefault();
            const index = this.thread.attachmentsInWebClientView.findIndex(
                (attachment) => attachment === this.thread.mainAttachment
            );
            this.setMainAttachmentFromIndex(
                index === this.thread.attachmentsInWebClientView.length - 1 ? 0 : index + 1
            );
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickPrevious(ev) {
            ev.preventDefault();
            const index = this.thread.attachmentsInWebClientView.findIndex(
                (attachment) => attachment === this.thread.mainAttachment
            );
            this.setMainAttachmentFromIndex(
                index === 0 ? this.thread.attachmentsInWebClientView.length - 1 : index - 1
            );
        },
        onComponentUpdate() {
            if (this.iframeViewerPdfRef.el) {
                hidePDFJSButtons(this.iframeViewerPdfRef.el);
            }
        },
        async setMainAttachmentFromIndex(index) {
            await this.thread.setMainAttachment(this.thread.attachmentsInWebClientView[index]);
        },
        /**
         * @private
         */
        _onChangeThreadAttachmentsInWebClientView() {
            if (
                this.thread.areAttachmentsLoaded &&
                !this.thread.isLoadingAttachments &&
                !this.thread.mainAttachment &&
                this.thread.attachmentsInWebClientView.length > 0
            ) {
                this.setMainAttachmentFromIndex(0);
            }
        },
    },
    fields: {
        id: attr({ identifying: true }),
        iframeViewerPdfRef: attr({ ref: "iframeViewerPdf" }),
        thread: one("Thread", { required: true }),
    },
    onChanges: [
        {
            dependencies: [
                "thread.areAttachmentsLoaded",
                "thread.attachmentsInWebClientView",
                "thread.isLoadingAttachments",
            ],
            methodName: "_onChangeThreadAttachmentsInWebClientView",
        },
    ],
});
