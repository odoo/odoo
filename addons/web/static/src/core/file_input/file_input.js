/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { Component, hooks, QWeb } = owl;
const { useRef } = hooks;

/**
 * Custom file input
 *
 * Component representing a customized input of type file. It takes a sub-template
 * in its default t-slot and uses it as the trigger to open the file upload
 * prompt.
 * @extends Component
 *
 * Props:
 * @param {string} [props.accepted_file_extensions='*'] Comma-separated
 *      list of authorized file extensions (default to all).
 * @param {string} [props.action='/web/binary/upload'] Route called when
 *      a file is uploaded in the input.
 * @param {string} [props.id]
 * @param {string} [props.model]
 * @param {string} [props.multi_upload=false] Whether the input should allow
 *      to upload multiple files at once.
 */
export class FileInput extends Component {
    setup() {
        this.http = useService("http");
        this.fileInputRef = useRef("file-input");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Upload an attachment to the given action with the given parameters:
     * - ufile: list of files contained in the file input
     * - csrf_token: CSRF token provided by the odoo global object
     * - model: a specific model which will be given when creating the attachment
     * - id: the id of the model target instance
     * @private
     */
    async onFileInputChange() {
        const { action, model, id } = this.props;
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: [...this.fileInputRef.el.files],
        };
        if (model) {
            params.model = model;
        }
        if (id) {
            params.id = id;
        }
        const fileData = await this.http.post(action, params, "text");
        const parsedFileData = JSON.parse(fileData);
        if (parsedFileData.error) {
            throw new Error(parsedFileData.error);
        }
        this.trigger("uploaded", { files: parsedFileData });
    }

    /**
     * Redirect clicks from the trigger element to the input.
     * @private
     */
    onTriggerClicked() {
        this.fileInputRef.el.click();
    }
}

FileInput.defaultProps = {
    accepted_file_extensions: "*",
    action: "/web/binary/upload",
    multi_upload: false,
};
FileInput.props = {
    accepted_file_extensions: { type: String, optional: 1 },
    action: { type: String, optional: 1 },
    id: { type: Number, optional: 1 },
    model: { type: String, optional: 1 },
    multi_upload: { type: Boolean, optional: 1 },
};
FileInput.template = "web.FileInput";

QWeb.registerComponent("FileInput", FileInput);
