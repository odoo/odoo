/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import core from 'web.core';

const getAttachmentNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId -= 1;
        return tmpId;
    };
})();

registerModel({
    name: 'FileUploader',
    identifyingMode: 'xor',
    recordMethods: {
        openBrowserFileUploader() {
            this.fileInput.click();
        },
        /**
         * Called when there are changes in the file input.
         *
         * @param {Event} ev
         * @param {EventTarget} ev.target
         * @param {FileList|Array} ev.target.files
         */
        onChangeAttachment(ev) {
            this.uploadFiles(ev.target.files);
        },
        /**
         * @param {FileList|Array} files
         * @returns {Promise}
         */
        async uploadFiles(files) {
            await this._performUpload({ files });
            if (!this.exists()) {
                return;
            }
            if (this.chatterOwner && !this.chatterOwner.attachmentBoxView) {
                this.chatterOwner.openAttachmentBoxView();
            }
            this.messaging.messagingBus.trigger('o-file-uploader-upload', { files });
            // clear at the end because side-effect of emptying `files`
            this.fileInput.value = '';
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Composer} param0.composer
         * @param {File} param0.file
         * @param {Thread} param0.thread
         * @returns {FormData}
         */
        _createFormData({ composer, file, thread }) {
            const formData = new window.FormData();
            formData.append('csrf_token', core.csrf_token);
            formData.append('is_pending', Boolean(composer));
            formData.append('thread_id', thread && thread.id);
            formData.append('thread_model', thread && thread.model);
            formData.append('ufile', file, file.name);
            return formData;
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Object} param0.attachmentData
         * @param {Composer} param0.composer
         * @param {Thread} param0.thread
         * @returns {Attachment}
         */
        _onAttachmentUploaded({ attachmentData, composer, thread }) {
            if (attachmentData.error || !attachmentData.id) {
                this.messaging.notify({
                    type: 'danger',
                    message: attachmentData.error,
                });
                return;
            }
            return (composer || thread).messaging.models['Attachment'].insert({
                composer: composer,
                originThread: (!composer && thread) ? thread : undefined,
                ...attachmentData,
            });
        },
        /**
         * @private
         * @param {Object} param0
         * @param {FileList|Array} param0.files
         * @returns {Promise}
         */
        async _performUpload({ files }) {
            const webRecord = this.activityListViewItemOwner && this.activityListViewItemOwner.webRecord;
            const composer = this.composerView && this.composerView.composer; // save before async
            const thread = this.thread; // save before async
            const chatter = (
                (this.chatterOwner) ||
                (this.attachmentBoxView && this.attachmentBoxView.chatter) ||
                (this.activityView && this.activityView.activityBoxView.chatter)
            ); // save before async
            const activity = (
                this.activityView && this.activityView.activity ||
                this.activityListViewItemOwner && this.activityListViewItemOwner.activity
            ); // save before async
            const uploadingAttachments = new Map();
            for (const file of files) {
                uploadingAttachments.set(file, this.messaging.models['Attachment'].insert({
                    composer,
                    filename: file.name,
                    id: getAttachmentNextTemporaryId(),
                    isUploading: true,
                    mimetype: file.type,
                    name: file.name,
                    originThread: (!composer && thread) ? thread : undefined,
                }));
            }
            const attachments = [];
            for (const file of files) {
                const uploadingAttachment = uploadingAttachments.get(file);
                if (!uploadingAttachment.exists()) {
                    // This happens when a pending attachment is being deleted by user before upload.
                    continue;
                }
                if ((composer && !composer.exists()) || (thread && !thread.exists())) {
                    return;
                }
                try {
                    const response = await (composer || thread).messaging.browser.fetch('/mail/attachment/upload', {
                        method: 'POST',
                        body: this._createFormData({ composer, file, thread }),
                        signal: uploadingAttachment.uploadingAbortController.signal,
                    });
                    const attachmentData = await response.json();
                    if (uploadingAttachment.exists()) {
                        uploadingAttachment.delete();
                    }
                    if ((composer && !composer.exists()) || (thread && !thread.exists())) {
                        return;
                    }
                    const attachment = this._onAttachmentUploaded({ attachmentData, composer, thread });
                    attachments.push(attachment);
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        throw e;
                    }
                }
            }
            if (activity && activity.exists()) {
                await activity.markAsDone({ attachments });
            }
            if (webRecord) {
                webRecord.model.load({ offset: webRecord.model.root.offset });
            }
            if (chatter && chatter.exists() && chatter.shouldReloadParentFromFileChanged) {
                chatter.reloadParentView();
            }
        },
    },
    fields: {
        activityListViewItemOwner: one('ActivityListViewItem', {
            identifying: true,
            inverse: 'fileUploader',
        }),
        activityView: one('ActivityView', {
            identifying: true,
            inverse: 'fileUploader',
        }),
        attachmentBoxView: one('AttachmentBoxView', {
            identifying: true,
            inverse: 'fileUploader',
        }),
        chatterOwner: one('Chatter', {
            identifying: true,
            inverse: 'fileUploader',
        }),
        composerView: one('ComposerView', {
            identifying: true,
            inverse: 'fileUploader',
        }),
        fileInput: attr({
            /**
             * Create an HTML element that will serve as file input.
             * This element does not need to be inserted in the DOM since it's just
             * use to trigger the file browser and start the upload process.
             */
            compute() {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.multiple = true;
                fileInput.onchange = this.onChangeAttachment;
                return fileInput;
            },
        }),
        thread: one('Thread', {
            compute() {
                if (this.activityView) {
                    return this.activityView.activity.thread;
                }
                if (this.activityListViewItemOwner) {
                    return this.activityListViewItemOwner.activity.thread;
                }
                if (this.attachmentBoxView) {
                    return this.attachmentBoxView.chatter.thread;
                }
                if (this.chatterOwner) {
                    return this.chatterOwner.thread;
                }
                if (this.composerView) {
                    return this.composerView.composer.activeThread;
                }
                return clear();
            },
            required: true,
        })
    },
});
