/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
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
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'FileUploaderView', propNameAsRecordLocalId: 'localId' });
        this._fileInputRef = useRef('fileInput');
        this._fileUploadId = _.uniqueId('o_FileUploader_fileupload');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get fileUploaderView() {
        return this.messaging && this.messaging.models['FileUploaderView'].get(this.props.localId);
    }

    /**
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async uploadFiles(files) {
        await this._performUpload({ files });
        this._fileInputRef.el.value = '';
    }

    openBrowserFileUploader() {
        this._fileInputRef.el.click();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
    }

    /**
     * @private
     * @param {Object} param0
     * @param {FileList|Array} param0.files
     * @returns {Promise}
     */
    async _performUpload({ files }) {
        const composer = this.fileUploaderView.composerView && this.fileUploaderView.composerView.composer; // save before async
        const thread = this.fileUploaderView.thread; // save before async
        const chatter = this.fileUploaderView.attachmentBoxView && this.fileUploaderView.attachmentBoxView.chatter; // save before async
        const activity = this.fileUploaderView.activityView && this.fileUploaderView.activityView.activity; // save before async
        const uploadingAttachments = new Map();
        for (const file of files) {
            uploadingAttachments.set(file, this.messaging.models['Attachment'].insert({
                composer: composer && replace(composer),
                filename: file.name,
                id: geAttachmentNextTemporaryId(),
                isUploading: true,
                mimetype: file.type,
                name: file.name,
                originThread: (!composer && thread) ? replace(thread) : undefined,
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
                const attachment = this._onAttachmentUploaded({ attachmentData, composer, thread });
                attachments.push(attachment);
            } catch (e) {
                if (e.name !== 'AbortError') {
                    throw e;
                }
            }
        }
        if (chatter && chatter.exists() && chatter.hasParentReloadOnAttachmentsChanged) {
            chatter.reloadParentView();
        }
        if (activity && activity.exists()) {
            activity.markAsDone({ attachments });
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

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
            this.env.services['notification'].notify({
                type: 'danger',
                message: attachmentData.error,
            });
            return;
        }
        return this.messaging.models['Attachment'].insert({
            composer: composer && replace(composer),
            originThread: (!composer && thread) ? replace(thread) : undefined,
            ...attachmentData,
        });
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
    props: { localId: String },
    template: 'mail.FileUploader',
});

registerMessagingComponent(FileUploader);
