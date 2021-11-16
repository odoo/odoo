/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace } from '@mail/model/model_field_command';

import core from 'web.core';

const geAttachmentNextTemporaryId = (function() {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

function factory(dependencies) {

    class FileUploader extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {FileList|Array} files
         * @returns {Promise}
         */
        async performUpload(files) {
            const uploadingAttachments = new Map();
            for (const file of files) {
                uploadingAttachments.set(file, this.messaging.models['mail.attachment'].insert({
                    composer: this.composer && replace(this.composer),
                    filename: file.name,
                    id: geAttachmentNextTemporaryId(),
                    isUploading: true,
                    mimetype: file.type,
                    name: file.name,
                    originThread: (!this.composer && this.thread) ? replace(this.thread) : clear(),
                }));
            }
            for (const file of files) {
                const uploadingAttachment = uploadingAttachments.get(file);
                if (!uploadingAttachment.exists()) {
                    // This happens when a pending attachment is being deleted by user before upload.
                    continue;
                }
                if ((this.composer && !this.composer.exists()) || (this.thread && !this.thread.exists())) {
                    return;
                }
                try {
                    const response = await this.env.browser.fetch('/mail/attachment/upload', {
                        method: 'POST',
                        body: this._createFormData(file),
                        signal: uploadingAttachment.uploadingAbortController.signal,
                    });
                    const attachmentData = await response.json();
                    if (uploadingAttachment.exists()) {
                        uploadingAttachment.delete();
                    }
                    if ((this.composer && !this.composer.exists()) || (this.thread && !this.thread.exists())) {
                        return;
                    }
                    this._attachmentUploaded(attachmentData);
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        throw e;
                    }
                }
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Object} param0
         * @param {Object} attachmentData
         * @param {mail.composer} param0.composer
         * @param {mail.thread} param0.thread
         */
        _attachmentUploaded(attachmentData) {
            if (attachmentData.error || !attachmentData.id) {
                this.env.services['notification'].notify({
                    type: 'danger',
                    message: attachmentData.error,
                });
                return;
            }
            const attachment = this.messaging.models['mail.attachment'].insert({
                composer: this.composer && replace(this.composer),
                originThread: this.thread ? replace(this.thread) : undefined,
                ...attachmentData,
            });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {mail.composer} param0.composer
         * @param {File} param0.file
         * @param {mail.thread} param0.thread
         * @returns {FormData}
         */
        _createFormData(file) {
            console.log(this.composer.activeThread);
            const formData = new window.FormData();
            formData.append('csrf_token', core.csrf_token);
            formData.append('is_pending', Boolean(this.composer));
            formData.append('thread_id', this.thread && this.thread.id);
            formData.append('thread_model', this.thread && this.thread.model);
            formData.append('ufile', file, file.name);
            return formData;
        }

        _computeThread() {
            if (this.chatter) {
                return replace(this.chatter.thread);
            }
            if (this.activity) {
                return replace(this.activity.thread);
            }
            if (this.composer) {
                return replace(this.composer.activeThread);
            }
        }

    }

    FileUploader.fields = {
        activity: one2one('mail.activity', {
            inverse: 'fileUploader',
            readonly: true,
        }),
        chatter: one2one('mail.chatter', {
            inverse: 'fileUploader',
            readonly: true,
        }),
        composer: one2one('mail.composer', {
            inverse: 'fileUploader',
            readonly: true,
        }),
        fileUploaderView: one2one('mail.file_uploader_view', {
            default: insertAndReplace(),
            inverse: 'fileUploader',
            isCausal: true,
        }),
        thread: one2one('mail.thread', {
            compute: '_computeThread',
            required: true,
        }),
    };
    FileUploader.identifyingFields = [['activity',  'chatter', 'composer']];
    FileUploader.modelName = 'mail.file_uploader';

    return FileUploader;
}

registerNewModel('mail.file_uploader', factory);
