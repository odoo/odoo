odoo.define('mail/static/src/components/file_uploader/file_uploader.js', function (require) {
'use strict';

const core = require('web.core');

const { Component } = owl;
const { useRef } = owl.hooks;

class FileUploader extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._fileInputRef = useRef('fileInput');
        this._fileUploadId = _.uniqueId('o_FileUploader_fileupload');
        this._onAttachmentUploaded = this._onAttachmentUploaded.bind(this);
    }

    mounted() {
        $(window).on(this._fileUploadId, this._onAttachmentUploaded);
    }

    willUnmount() {
        $(window).off(this._fileUploadId);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async uploadFiles(files) {
        await this._unlinkExistingAttachments(files);
        this._createTemporaryAttachments(files);
        await this._performUpload(files);
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
     * @param {Object} fileData
     * @returns {mail.attachment}
     */
     _createAttachment(fileData) {
        return this.env.models['mail.attachment'].create(Object.assign(
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
        let formData = new window.FormData();
        formData.append('callback', this._fileUploadId);
        formData.append('csrf_token', core.csrf_token);
        formData.append('id', this.props.uploadId);
        formData.append('model', this.props.uploadModel);
        formData.append('ufile', file, file.name);
        return formData;
    }

    /**
     * @private
     * @param {FileList|Array} files
     */
    _createTemporaryAttachments(files) {
        for (const file of files) {
            this._createAttachment({
                filename: file.name,
                isTemporary: true,
                name: file.name
            });
        }
    }
    /**
     * @private
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async _performUpload(files) {
        for (const file of files) {
            const uploadingAttachment = this.env.models['mail.attachment'].find(attachment =>
                attachment.isTemporary &&
                attachment.filename === file.name
            );

            try {
                const response = await this.env.browser.fetch('/web/binary/upload_attachment', {
                    method: 'POST',
                    body: this._createFormData(file),
                    signal: uploadingAttachment.uploadingAbortController.signal,
                });
                let html = await response.text();
                const template = document.createElement('template');
                template.innerHTML = html.trim();
                window.eval(template.content.firstChild.textContent);
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
    async _unlinkExistingAttachments(files) {
        for (const file of files) {
            const attachment = this.props.attachmentLocalIds
                .map(attachmentLocalId => this.env.models['mail.attachment'].get(attachmentLocalId))
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
     * @param {jQuery.Event} ev
     * @param {...Object} filesData
     */
    async _onAttachmentUploaded(ev, ...filesData) {
        for (const fileData of filesData) {
            const { error, filename, id, mimetype, name, size } = fileData;
            if (error || !id) {
                this.env.services['notification'].notify({
                    type: 'danger',
                    message: owl.utils.escape(error),
                });
                const relatedTemporaryAttachments = this.env.models['mail.attachment']
                    .find(attachment =>
                        attachment.filename === filename &&
                        attachment.isTemporary
                    );
                for (const attachment of relatedTemporaryAttachments) {
                    attachment.delete();
                }
                return;
            }
            // FIXME : needed to avoid problems on uploading
            // Without this the useStore selector of component could be not called
            // E.g. in attachment_box_tests.js
            await new Promise(resolve => setTimeout(resolve));
            const attachment = this._createAttachment({
                filename,
                id,
                mimetype,
                name,
                size,
            });
            this.trigger('o-attachment-created', { attachment });
        }
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
        uploadId: 0,
        uploadModel: 'mail.compose.message'
    },
    props: {
        attachmentLocalIds: {
            type: Array,
            element: String,
        },
        newAttachmentExtraData: {
            type: Object,
            optional: true,
        },
        uploadId: Number,
        uploadModel: String,
    },
    template: 'mail.FileUploader',
});

return FileUploader;

});
