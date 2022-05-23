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
                model: this.props.resModel,
                id: this.props.resId,
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

BinaryField.template = "web.BinaryField";
BinaryField.components = {
    FileDownloader,
    FileUploader,
};
BinaryField.props = {
    ...standardFieldProps,
    acceptedFileExtensions: { type: String, optional: true },
    fileData: { type: String, optional: true },
    fileName: { type: String, optional: true },
    isDownloadable: { type: Boolean, optional: true },
    resId: { type: [Number, Boolean], optional: true },
    resModel: { type: String, optional: true },
};
BinaryField.defaultProps = {
    acceptedFileExtensions: "*",
    fileData: "",
    isDownloadable: true,
};

BinaryField.displayName = _lt("File");
BinaryField.supportedTypes = ["binary"];

BinaryField.extractProps = (fieldName, record, attrs) => {
    return {
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
        fileData: record.data[fieldName] || "",
        fileName: record.data[attrs.filename] || "",
        isDownloadable: !(record.isReadonly(fieldName) && record.mode === "edit"),
        resId: record.resId,
        resModel: record.resModel,
        update: (file) => {
            const changes = { [fieldName]: file.data || false };
            if (attrs.filename && attrs.filename !== fieldName) {
                changes[attrs.filename] = file.name || false;
            }
            return record.update(changes);
        },
    };
};

registry.category("fields").add("binary", BinaryField);
