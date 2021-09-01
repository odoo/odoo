/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import core from 'web.core';

const { Component } = owl;
const { useRef } = owl.hooks;

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

    /**
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async uploadFiles(files) {
        this._unlinkExistingAttachments(files);
        this._createUploadingAttachments(files);
        await this._performUpload(files);
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
     * @deprecated
     * @private
     * @param {Object} fileData
     * @returns {mail.attachment}
     */
    _createAttachment(fileData) {
        return this.messaging.models['mail.attachment'].create(Object.assign(
            {},
            fileData,
            this.props.newAttachmentExtraData
        ));
    }

    /**
     * @private
     * @param {File} file
     * @returns {FormData}
     */
    _createFormData(file) {
        const formData = new window.FormData();
        formData.append('csrf_token', core.csrf_token);
        formData.append('is_pending', this.props.isPending);
        formData.append('thread_id', this.thread && this.thread.id);
        formData.append('thread_model', this.thread && this.thread.model);
        formData.append('ufile', file, file.name);
        return formData;
    }

    /**
     * @private
     * @param {FileList|Array} files
     */
    _createUploadingAttachments(files) {
        for (const file of files) {
            this.messaging.models['mail.attachment'].create(
                Object.assign(
                    {
                        filename: file.name,
                        isUploading: true,
                        name: file.name
                    },
                    this.props.newAttachmentExtraData
                ),
            );
        }
    }
    /**
     * @private
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async _performUpload(files) {
        for (const file of files) {
            const uploadingAttachment = this.messaging.models['mail.attachment'].find(attachment =>
                attachment.isUploading &&
                attachment.filename === file.name
            );
            if (!uploadingAttachment) {
                // Uploading attachment no longer exists.
                // This happens when an uploading attachment is being deleted by user.
                continue;
            }
            try {
                const response = await this.env.browser.fetch('/mail/attachment/upload', {
                    method: 'POST',
                    body: this._createFormData(file),
                    signal: uploadingAttachment.uploadingAbortController.signal,
                });
                const attachmentData = await response.json();
                this._onAttachmentUploaded(attachmentData);
            } catch (e) {
                if (e.name !== 'AbortError') {
                    throw e;
                }
            }
        }
    }

    /**
     * @private
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    _unlinkExistingAttachments(files) {
        for (const file of files) {
            const attachment = this.props.attachmentLocalIds
                .map(attachmentLocalId => this.messaging.models['mail.attachment'].get(attachmentLocalId))
                .find(attachment => attachment.name === file.name && attachment.size === file.size);
            // if the files already exits, delete the file before upload
            if (attachment) {
                attachment.remove();
            }
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} filesData
     */
    _onAttachmentUploaded({ accessToken, error, filename, id, mimetype, name, size }) {
        if (error || !id) {
            this.env.services['notification'].notify({
                type: 'danger',
                message: error,
            });
            const relatedUploadingAttachments = this.messaging.models['mail.attachment']
                .find(attachment =>
                    attachment.filename === filename &&
                    attachment.isUploading
                );
            for (const attachment of relatedUploadingAttachments) {
                attachment.delete();
            }
            return;
        }
        const attachment = this.messaging.models['mail.attachment'].insert(
            Object.assign(
                {
                    accessToken,
                    filename,
                    id,
                    mimetype,
                    name,
                    size,
                },
                this.props.newAttachmentExtraData
            ),
        );
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
    defaultProps: {
        isPending: false,
    },
    props: {
        attachmentLocalIds: {
            type: Array,
            element: String,
        },
        isPending: Boolean,
        newAttachmentExtraData: {
            type: Object,
            optional: true,
        },
        threadLocalId: {
            type: String,
            optional: true,
        },
    },
    template: 'mail.FileUploader',
});

registerMessagingComponent(FileUploader, {
    propsCompareDepth: {
        attachmentLocalIds: 1,
        newAttachmentExtraData: 3,
    },
});
