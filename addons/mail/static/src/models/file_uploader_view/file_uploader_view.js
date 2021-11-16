/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

import core from 'web.core';

const geAttachmentNextTemporaryId = (function() {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

function factory(dependencies) {

    class FileUploaderView extends dependencies['mail.model'] {

        _created() {
            this.onChangeAttachment = this.onChangeAttachment.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Called when there are changes in the file input.
         *
         * @param {Event} ev
         * @param {EventTarget} ev.target
         * @param {FileList|Array} ev.target.files
         */
        async onChangeAttachment(ev) {
            await this.uploadFiles(ev.target.files);
        }

        /**
         * @param {FileList|Array} files
         * @returns {Promise}
         */
        async uploadFiles(files) {
            await this._performUpload({
                composer: this.thread.composer,
                files,
                thread: this.thread,
            });
            this.fileUploaderRef.el.value = '';
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
        _attachmentUploaded({ attachmentData, composer, thread }) {
            if (attachmentData.error || !attachmentData.id) {
                this.env.services['notification'].notify({
                    type: 'danger',
                    message: attachmentData.error,
                });
                return;
            }
            const attachment = this.messaging.models['mail.attachment'].insert({
                composer: composer && replace(composer),
                originThread: (!composer && thread) ? replace(thread) : undefined,
                ...attachmentData,
            });
            this.component.trigger('o-attachment-created', { attachment });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {mail.composer} param0.composer
         * @param {File} param0.file
         * @param {mail.thread} param0.thread
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
        }

        /**
         * @private
         * @param {Object} param0
         * @param {mail.composer} param0.composer
         * @param {FileList|Array} param0.files
         * @param {mail.thread} param0.thread
         * @returns {Promise}
         */
        async _performUpload({ composer, files, thread }) {
            const uploadingAttachments = new Map();
            for (const file of files) {
                uploadingAttachments.set(file, this.messaging.models['mail.attachment'].insert({
                    composer: composer && replace(composer),
                    filename: file.name,
                    id: geAttachmentNextTemporaryId(),
                    isUploading: true,
                    mimetype: file.type,
                    name: file.name,
                    originThread: (!composer && thread) ? replace(thread) : undefined,
                }));
            }
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
                    const response = await this.env.browser.fetch('/mail/attachment/upload', {
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
                    this._attachmentUploaded({ attachmentData, composer, thread });
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        throw e;
                    }
                }
            }
        }

    }

    FileUploaderView.fields = {
        thread: one2one('mail.thread', {
            inverse: 'fileUploaderView',
            required: true,
            readonly: true,
        }),
        component: attr(),
        fileUploaderRef: attr(),
    };
    FileUploaderView.identifyingFields = ['thread'];
    FileUploaderView.modelName = 'mail.file_uploader_view';

    return FileUploaderView;
}

registerNewModel('mail.file_uploader_view', factory);
