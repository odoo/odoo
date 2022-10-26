/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { Component, onMounted, useRef } = owl;

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
        this.fileInputRef = useRef("file-input");

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
        const parsedFileData = await this.uploadFiles(this.httpParams);
        this.props.onUpload(parsedFileData);
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
