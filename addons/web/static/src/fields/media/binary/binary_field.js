// @ts-check

/** @module @web/fields/media/binary/binary_field - File upload/download field for Binary columns */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { isBinarySize, toBase64Length } from "@web/core/utils/format/binary";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/fields/file_handler";
import { standardFieldProps } from "@web/fields/standard_field_props";

export const MAX_FILENAME_SIZE_BYTES = 0xff; // filenames do not exceed 255 bytes on Linux/Windows/MacOS

export class BinaryField extends Component {
    static template = "web.BinaryField";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        // See https://www.iana.org/assignments/media-types/media-types.xhtml
        allowedMIMETypes: { type: String, optional: true },
        fileNameField: { type: String, optional: true },
    };
    static defaultProps = {
        acceptedFileExtensions: "*",
    };

    setup() {
        this.notification = useService("notification");
    }

    /** @returns {string} Display filename, truncated to max filesystem length */
    get fileName() {
        let value = this.props.record.data[this.props.name];
        value = value && typeof value === "string" ? value : false;
        return (this.props.record.data[this.props.fileNameField] || value || "").slice(
            0,
            toBase64Length(MAX_FILENAME_SIZE_BYTES),
        );
    }

    /**
     * @param {{ data: string|false, name: string }} payload Uploaded file data and name
     * @returns {Promise} Record update promise
     */
    update({ data, name }) {
        const { fileNameField, record } = this.props;
        const changes = { [this.props.name]: data || false };
        if (fileNameField in record.fields && record.data[fileNameField] !== name) {
            changes[fileNameField] = name || "";
        }
        return this.props.record.update(changes);
    }

    /** @returns {Object} Parameters for the /web/content download endpoint */
    getDownloadData() {
        return {
            model: this.props.record.resModel,
            id: this.props.record.resId,
            field: this.props.name,
            filename_field: this.fileName,
            filename: this.fileName || "",
            download: true,
            data: isBinarySize(this.props.record.data[this.props.name])
                ? null
                : this.props.record.data[this.props.name],
        };
    }

    /** Triggers a browser download of the binary field content */
    async onFileDownload() {
        await download({
            data: this.getDownloadData(),
            url: "/web/content",
        });
    }
}

export class ListBinaryField extends BinaryField {
    static template = "web.ListBinaryField";
}

export const binaryField = {
    component: BinaryField,
    displayName: _t("File"),
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
        {
            label: _t("Allowed file mimetype"),
            name: "allowed_mime_type",
            type: "string",
        },
    ],
    supportedTypes: ["binary"],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        allowedMIMETypes: options.allowed_mime_type,
        fileNameField: attrs.filename,
    }),
};

export const listBinaryField = {
    ...binaryField,
    component: ListBinaryField,
};

registry.category("fields").add("binary", binaryField);
registry.category("fields").add("list.binary", listBinaryField);
