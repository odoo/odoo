/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { checkFileSize } from "@web/core/utils/files";

/**
 * Custom file input
 *
 * Component representing a customized input of type file. It takes a sub-template
 * in its default t-slot and uses it as the trigger to open the file upload
 * prompt.
 * @extends Component
 *
 * Props:
 * @param {string} [props.acceptedFileExtensions='*'] Comma-separated
 *      list of authorized file extensions (default to all).
 * @param {string} [props.route='/web/binary/upload'] Route called when
 *      a file is uploaded in the input.
 * @param {string} [props.resId]
 * @param {string} [props.resModel]
 * @param {string} [props.multiUpload=false] Whether the input should allow
 *      to upload multiple files at once.
 */
export class FileInput extends Component {
    setup() {
        this.http = useService("http");
        this.notification = useService("notification");
        this.fileInputRef = useRef("file-input");
        this.state = useState({
            // Disables upload button if currently uploading.
            isDisable: false,
        });

        onMounted(() => {
            if (this.props.autoOpen) {
                this.onTriggerClicked();
            }
        });
    }

    get httpParams() {
        const { resId, resModel } = this.props;
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: [...this.fileInputRef.el.files],
        };
        if (resModel) {
            params.model = resModel;
        }
        if (resId !== undefined) {
            params.id = resId;
        }
        return params;
    }

    async uploadFiles(params) {
        if (params.ufile.length) {
            const fileSize = params.ufile[0].size;
            if (!checkFileSize(fileSize, this.notification)) {
                return null;
            }
        }
        const fileData = await this.http.post(this.props.route, params, "text");
        const parsedFileData = JSON.parse(fileData);
        if (parsedFileData.error) {
            throw new Error(parsedFileData.error);
        }
        return parsedFileData;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Upload an attachment to the given route with the given parameters:
     * - ufile: list of files contained in the file input
     * - csrf_token: CSRF token provided by the odoo global object
     * - resModel: a specific model which will be given when creating the attachment
     * - resId: the id of the resModel target instance
     */
    async onFileInputChange() {
        this.state.isDisable = true;
        const parsedFileData = await this.uploadFiles(this.httpParams);
        if (parsedFileData) {
            // When calling onUpload, also pass the files to allow to get data like their names
            this.props.onUpload(
                parsedFileData,
                this.fileInputRef.el ? this.fileInputRef.el.files : []
            );
            // Because the input would not trigger this method if the same file name is uploaded,
            // we must clear the value after handling the upload
            this.fileInputRef.el.value = null;
        }
        this.state.isDisable = false;
    }

    /**
     * Redirect clicks from the trigger element to the input.
     */
    async onTriggerClicked() {
        if (await this.props.beforeOpen()) {
            this.fileInputRef.el.click();
        }
    }
}

FileInput.defaultProps = {
    acceptedFileExtensions: "*",
    hidden: false,
    multiUpload: false,
    onUpload: () => {},
    route: "/web/binary/upload_attachment",
    beforeOpen: async () => true,
};
FileInput.props = {
    acceptedFileExtensions: { type: String, optional: true },
    autoOpen: { type: Boolean, optional: true },
    hidden: { type: Boolean, optional: true },
    multiUpload: { type: Boolean, optional: true },
    onUpload: { type: Function, optional: true },
    beforeOpen: { type: Function, optional: true },
    resId: { type: Number, optional: true },
    resModel: { type: String, optional: true },
    route: { type: String, optional: true },
    "*": true,
};
FileInput.template = "web.FileInput";
