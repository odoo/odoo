import { FileInput } from "@web/core/file_input/file_input";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

/**
 * Dummy base component for binary attachment fields.
 *
 * This component provides the common UI and behavior for fields that allow uploading files,
 * such as many2many_binary, many2one_binary, etc. It is not meant to be used directly.
 *
 * Requirements:
 * - Provide the `files` getter to define the list of attached files.
 * - Override `onFileUploaded()` to handle uploaded files as needed.
 * - Implement `onFileRemove()` if file removal is enabled in the UI.
 *
 * UI includes file upload via FileInput and basic rendering support for previewing or downloading files.
 */
export class Many2XBinary extends Component {
    static template = "web.Many2XBinary";
    static components = {
        FileInput,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        className: { type: String, optional: true },
        multiUpload: { type: Boolean },
        numberOfFiles: { type: Number, optional: true },
    };

    // Should be overridden to return the list of files
    get files() {
        return [];
    }

    get uploadText() {
        return this.props.record.fields[this.props.name].string;
    }

    getUrl(id) {
        return "/web/content/" + id + "?download=true";
    }

    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }

    isImage(file) {
        return file.mimetype.startsWith("image/");
    }

    onFileUploaded(files) {
        // To be overridden
    }

    onFileRemove(deleteId) {
        // To be overridden
    }
}
