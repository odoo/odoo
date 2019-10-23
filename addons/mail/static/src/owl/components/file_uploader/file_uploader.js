odoo.define('mail.component.FileUploader', function (require) {
'use strict';

const { Component } = owl;
const { useDispatch, useRef } = owl.hooks;
const core = require('web.core');

class FileUploader extends Component {
    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeDispatch = useDispatch();
        this._fileInputRef = useRef('fileInput');
        this._onAttachmentUploaded = this._onAttachmentUploaded.bind(this);
    }

    mounted() {
        $(window).on(this.props.fileUploadId, this._onAttachmentUploaded);
    }

    willUnmount() {
        $(window).off(this.props.fileUploadId);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {FileList|Array} files
     * @return {Promise}
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
     */
     _createAttachment(fileData) {
        this.storeDispatch('createAttachment', Object.assign({},
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
        formData.append('callback', this.props.fileUploadId);
        formData.append('csrf_token', core.csrf_token);
        formData.append('id', '0');
        formData.append('model', 'mail.compose.message');
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
     * @param {string} filename
     */
     _deleteTemporaryAttachment(filename) {
        const temporaryAttachmentLocalId = this.env.store.state.temporaryAttachmentLocalIds[filename];
        if (temporaryAttachmentLocalId) {
            this.storeDispatch('deleteAttachment', temporaryAttachmentLocalId);
        }
    }

    /**
     * @private
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async _performUpload(files) {
        for (const file of files) {
            const response = await window.fetch('/web/binary/upload_attachment', {
                method: 'POST',
                body: this._createFormData(file),
            });
            let html = await response.text();
            const template = document.createElement('template');
            template.innerHTML = html.trim();
            window.eval(template.content.firstChild.textContent);
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
                .map(localId => this.env.store.state.attachments[localId])
                .find(attachment =>
                    attachment.name === file.name && attachment.size === file.size
                );
            // if the files already exits, delete the file before upload
            if (attachment) {
                await this.storeDispatch('unlinkAttachment', attachment.localId);
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
                this.env.do_warn(error);
                this._deleteTemporaryAttachment(filename);
                return;
            }
            // FIXME : needed to avoid problems on uploading
            // Without this the useStore selector of component could be not called
            // E.g. in attachment_box_tests.js
            await new Promise(resolve => setTimeout(resolve));
            this._createAttachment({ filename, id, mimetype, name, size });
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

FileUploader.defaultProps = {
    fileUploadId: _.uniqueId('o_FileUploader_fileupload')
};

FileUploader.props = {
    attachmentLocalIds: {
        type: Array,
        element: String,
    },
    fileUploadId: {
        type: String,
    },
    newAttachmentExtraData: {
        type: Object,
        optional: true,
    }
};

FileUploader.template = 'mail.component.FileUploader';

return FileUploader;

});
