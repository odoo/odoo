import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isBinarySize, toBase64Length } from "@web/core/utils/binary";
import { download } from "@web/core/network/download";
import { standardFieldProps } from "../standard_field_props";
import { FileUploader } from "../file_handler";
import { _t } from "@web/core/l10n/translation";

import { Component, props, t } from "@odoo/owl";

export const MAX_FILENAME_SIZE_BYTES = 0xff; // filenames do not exceed 255 bytes on Linux/Windows/MacOS

export const binaryFieldProps = {
    ...standardFieldProps,
    acceptedFileExtensions: t.string().optional("*"),
    // See https://www.iana.org/assignments/media-types/media-t.xhtml
    allowedMIMETypes: t.string().optional(),
    fileNameField: t.string().optional(),
    // Show a button instead of file size when there is no file name
    useReplaceButton: t.boolean().optional(),
};

export class BinaryField extends Component {
    static template = "web.BinaryField";
    static components = {
        FileUploader,
    };
    props = props(binaryFieldProps);

    setup() {
        this.notification = useService("notification");
    }

    get trueFileNameField() {
        return (
            this.props.fileNameField || 
            this.props.record.fields[this.props.name].filename_field
        );
    }

    get fileName() {
        let value = this.props.record.data[this.props.name];
        value =
            value && typeof value === "string"
                ? this.props.useReplaceButton
                    ? false
                    : value
                : false;
        
        const fnField = this.trueFileNameField;
        return (this.props.record.data[fnField] || value || "").slice(
            0,
            toBase64Length(MAX_FILENAME_SIZE_BYTES)
        );
    }

    update({ data, name }) {
        const fnField = this.trueFileNameField;
        const changes = { [this.props.name]: data || false };
        if (fnField in this.props.record.fields && this.props.record.data[fnField] !== name) {
            changes[fnField] = name || "";
        }
        return this.props.record.update(changes);
    }

    getDownloadData() {
        return {
            model: this.props.record.resModel,
            id: this.props.record.resId,
            field: this.props.name,
            filename_field: this.trueFileNameField,
            filename: this.fileName || "",
            download: true,
            data: isBinarySize(this.props.record.data[this.props.name])
                ? null
                : this.props.record.data[this.props.name],
        };
    }

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
        useReplaceButton: options.use_replace_button,
    }),
};

export const listBinaryField = {
    ...binaryField,
    component: ListBinaryField,
};

registry.category("fields").add("binary", binaryField);
registry.category("fields").add("list.binary", listBinaryField);
