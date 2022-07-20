/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { download } from "@web/core/network/download";
import { standardFieldProps } from "../standard_field_props";
import { FileUploader } from "../file_handler";
import { _lt } from "@web/core/l10n/translation";

const { Component, onWillUpdateProps, useState } = owl;

function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

export class BinaryField extends Component {
    setup() {
        this.notification = useService("notification");
        this.state = useState({
            fileName: this.fileName || "",
            isValid: true,
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                this.state.fileName = "";
            }
        });
    }

    get fileName() {
        return this.props.record.data[this.props.fileNameField];
    }
    get file() {
        return {
            data: this.props.value,
            name: this.state.fileName || this.props.value || null,
        };
    }
    get isDownloadable() {
        return !(
            this.props.record.isReadonly(this.props.name) && this.props.record.mode === "edit"
        );
    }

    update(file) {
        const changes = { [this.props.name]: file.data || false };
        if (this.props.fileNameField && this.props.fileNameField !== this.props.name) {
            changes[this.props.fileNameField] = file.name || false;
        }
        return this.props.record.update(changes);
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
                data: isBinarySize(this.props.value) ? null : this.props.value,
            },
            url: "/web/content",
        });
    }
    onFileRemove() {
        this.state.isValid = true;
        this.update(false);
    }
    onFileUploaded(file) {
        this.state.fileName = file.name;
        this.state.isValid = true;
        this.update(file);
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
    FileUploader,
};
BinaryField.props = {
    ...standardFieldProps,
    acceptedFileExtensions: { type: String, optional: true },
    fileNameField: { type: String, optional: true },
};
BinaryField.defaultProps = {
    acceptedFileExtensions: "*",
};

BinaryField.displayName = _lt("File");
BinaryField.supportedTypes = ["binary"];

BinaryField.extractProps = ({ attrs }) => {
    return {
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
        fileNameField: attrs.filename,
    };
};

registry.category("fields").add("binary", BinaryField);
