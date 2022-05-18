/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { download } from "@web/core/network/download";
import { standardFieldProps } from "./standard_field_props";
import { FileDownloader, FileUploader } from "./file_handler";
import { _lt } from "@web/core/l10n/translation";

const { Component, onWillUpdateProps, useState } = owl;

function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

export class BinaryField extends Component {
    setup() {
        this.notification = useService("notification");
        this.state = useState({
            fileName: this.props.fileName || "",
            isValid: true,
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                this.state.fileName = "";
            }
        });
    }
    get file() {
        return {
            data: this.props.fileData,
            name: this.state.fileName || this.props.fileData || null,
        };
    }
    async onFileDownload() {
        await download({
            data: {
                model: this.props.record.resModel,
                id: this.props.record.resId,
                field: this.props.name,
                filename_field: this.file.name,
                filename: this.file.name || "",
                download: true,
                data: isBinarySize(this.props.fileData) ? null : this.props.fileData,
            },
            url: "/web/content",
        });
    }
    onFileRemove() {
        this.state.isValid = true;
        this.props.update(false);
    }
    onFileUploaded(file) {
        this.state.fileName = file.name;
        this.state.isValid = true;
        this.props.update(file);
    }
    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected binary"), {
            type: "danger",
        });
    }
}

BinaryField.components = {
    FileDownloader,
    FileUploader,
};
BinaryField.props = {
    ...standardFieldProps,
    fileData: { type: String, optional: true },
    fileName: { type: String, optional: true },
    acceptedFileExtensions: { type: String, optional: true },
    isDownloadable: { type: Boolean, optional: true },
};
BinaryField.defaultProps = {
    acceptedFileExtensions: "*",
    fileData: "",
    isDownloadable: true,
};
BinaryField.template = "web.BinaryField";
BinaryField.displayName = _lt("File");
BinaryField.supportedTypes = ["binary"];
BinaryField.extractProps = (fieldName, record, attrs) => {
    return {
        fileData: record.data[fieldName] || "",
        fileName: record.data[attrs.filename] || "",
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
        isDownloadable: !(record.isReadonly(fieldName) && record.mode === "edit"),
        update: (file) => {
            const changes = { [fieldName]: file.data || false };
            if (attrs.filename && attrs.filename !== fieldName) {
                changes[attrs.filename] = file.name || false;
            }
            record.update(changes);
        },
    };
};

registry.category("fields").add("binary", BinaryField);
