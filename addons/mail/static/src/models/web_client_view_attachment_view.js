/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';

import { hidePDFJSButtons } from '@web/legacy/js/libs/pdfjs';

registerModel({
    name: 'WebClientViewAttachmentView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickNext(ev) {
            ev.preventDefault();
            const index = this.thread.attachmentsInWebClientView.findIndex(attachment => attachment === this.thread.mainAttachment);
            this.setMainAttachmentFromIndex(index === this.thread.attachmentsInWebClientView.length - 1 ? 0 : index + 1);
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickPrevious(ev) {
            ev.preventDefault();
            const index = this.thread.attachmentsInWebClientView.findIndex(attachment => attachment === this.thread.mainAttachment);
            this.setMainAttachmentFromIndex(index === 0 ? this.thread.attachmentsInWebClientView.length - 1 : index - 1);
        },
        onComponentUpdate() {
            if (this.iframeViewerPdfRef.el) {
                hidePDFJSButtons(this.iframeViewerPdfRef.el);
            }
            this.component.trigger('preview_attachment_validation');
        },
        async setMainAttachmentFromIndex(index) {
            await this.thread.setMainAttachment(this.thread.attachmentsInWebClientView[index]);
        },
        /**
         * @private
         */
        _onChangeThreadAttachmentsInWebClientView() {
            if (this.thread.model === 'account.move.line') {
                // account.move.line is not actually a thread in python
                this.setMainAttachmentFromIndex(0);
                return;
            }
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
        component: attr(),
        id: attr({
            identifying: true,
            readonly: true,
            required: true,
        }),
        iframeViewerPdfRef: attr(),
        thread: one('Thread', {
            required: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['thread.areAttachmentsLoaded', 'thread.attachmentsInWebClientView', 'thread.isLoadingAttachments'],
            methodName: '_onChangeThreadAttachmentsInWebClientView',
        }),
    ],
});
