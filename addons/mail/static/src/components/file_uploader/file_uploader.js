/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { replace } from '@mail/model/model_field_command';

import core from 'web.core';

const { Component } = owl;
const { useRef } = owl.hooks;

const geAttachmentNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId -= 1;
        return tmpId;
    };
})();

export class FileUploader extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._fileInputRef = useRef('fileInput');
        this._fileUploadId = _.uniqueId('o_FileUploader_fileupload');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get composerView() {
        return this.messaging.models['mail.composer_view'].get(this.props.composerViewLocalId);
    }

    /**
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async uploadFiles(files) {
        await this._performUpload({
            composer: this.composerView && this.composerView.composer,
            files,
            thread: this.thread,
        });
        this._fileInputRef.el.value = '';
    }

    openBrowserFileUploader() {
        this._fileInputRef.el.click();
    }

    get thread() {
        return this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
                this._onAttachmentUploaded({ attachmentData, composer, thread });
            } catch (e) {
                if (e.name !== 'AbortError') {
                    throw e;
                }
            }
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} param0
     * @param {Object} attachmentData
     * @param {mail.composer} param0.composer
     * @param {mail.thread} param0.thread
     */
    _onAttachmentUploaded({ attachmentData, composer, thread }) {
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
        this.trigger('o-attachment-created', { attachment });
    }

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
    }

}

Object.assign(FileUploader, {
    props: {
        composerViewLocalId: {
            type: String,
            optional: true,
        },
        threadLocalId: {
            type: String,
            optional: true,
        },
    },
    template: 'mail.FileUploader',
});

registerMessagingComponent(FileUploader);
