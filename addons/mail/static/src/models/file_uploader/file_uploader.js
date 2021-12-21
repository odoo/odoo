/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { replace, link, clear } from '@mail/model/model_field_command';

import core from 'web.core';

const geAttachmentNextTemporaryId = (function() {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

registerModel({
    name: 'FileUploader',
    identifyingFields: [['activityView', 'attachmentBoxView', 'composerView']],
    lifecycleHooks: {
        _created() {
            this._onChangeAttachment = this._onChangeAttachment.bind(this);
            this.openBrowserFileUploader = this.openBrowserFileUploader.bind(this);
        },
    },
    recordMethods: {
        /**
         * @param {FileList|Array} files
         * @returns {Promise}
         */
        async uploadFiles(files) {
            await this._performUpload(files);
            this.fileInputRef.el.value = '';
        },
        openBrowserFileUploader() {
            this.fileInputRef.el.click();
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Composer} param0.composer
         * @param {File} param0.file
         * @param {Thread} param0.thread
         * @returns {FormData}
         */
        _createFormData(file) {
            const formData = new window.FormData();
            formData.append('csrf_token', core.csrf_token);
            if (this.composerView) {
                formData.append('is_pending', Boolean(this.composerView.composer));
            }
            formData.append('thread_id', this.thread && this.thread.id);
            formData.append('thread_model', this.thread && this.thread.model);
            formData.append('ufile', file, file.name);
            return formData;
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Composer} param0.composer
         * @param {FileList|Array} param0.files
         * @param {Thread} param0.thread
         * @returns {Promise}
         */
        async _performUpload(files) {
            const uploadingAttachments = new Map();
            for (const file of files) {
                uploadingAttachments.set(file, this.messaging.models['Attachment'].insert({
                    composer: this.composerView && this.composerView.composer && replace(this.composerView.composer),
                    filename: file.name,
                    id: geAttachmentNextTemporaryId(),
                    isUploading: true,
                    mimetype: file.type,
                    name: file.name,
                    originThread: (this.thread) ? replace(this.thread) : undefined,
                }));
            }
            for (const file of files) {
                const uploadingAttachment = uploadingAttachments.get(file);
                if (!uploadingAttachment.exists()) {
                    // This happens when a pending attachment is being deleted by user before upload.
                    continue;
                }
                if ((this.composerView && this.composerView.composer && !this.composerView.composer.exists()) || (this.thread && !this.thread.exists())) {
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
                    if ((this.composerView && this.composerView.composer && !this.composerView.composer.exists()) || (this.thread && !this.thread.exists())) {
                        return;
                    }
                    this._onAttachmentUploaded(attachmentData);
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        throw e;
                    }
                }
            }
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Object} attachmentData
         * @param {Composer} param0.composer
         * @param {Thread} param0.thread
         */
        _onAttachmentUploaded(attachmentData) {
            if (attachmentData.error || !attachmentData.id) {
                this.env.services['notification'].notify({
                    type: 'danger',
                    message: attachmentData.error,
                });
                return;
            }
            const attachment = this.messaging.models['Attachment'].insert({
                composer: this.composerView && this.composerView.composer && replace(this.composerView.composer),
                originThread: (this.thread) ? replace(this.thread) : undefined,
                ...attachmentData,
            });
            // if (this.props.onAttachmentCreated) {
            //     this.props.onAttachmentCreated({ attachment });
            // }
        },
        /**
         * Called when there are changes in the file input.
         *
         * @private
         * @param {Event} ev
         * @param {EventTarget} ev.target
         * @param {FileList|Array} ev.target.files
         */
        async _onChangeAttachment(ev) {
            await this.uploadFiles(ev.target.files);
        },
        _computeThread() {
            if (this.composerView) {
                return link(this.composerView.composer.activeThread);
            }
            if (this.attachmentBoxView) {
                return link(this.attachmentBoxView.chatter.thread);
            }
            if (this.activityView) {
                return link(this.activityView.activity.thread);
            }
            return clear();
        }
    },
    fields: {
        activityView: one2one('ActivityView', {
            inverse: 'fileUploader',
            readonly: true,
        }),
        attachmentBoxView: one2one('AttachmentBoxView', {
            inverse: 'fileUploader',
            readonly: true,
        }),
        composerView: one2one('ComposerView', {
            inverse: 'fileUploader',
            readonly: true,
        }),
        fileInputRef: attr(),
        thread: one2one('Thread', {
            compute: '_computeThread',
        }),
    },
});
