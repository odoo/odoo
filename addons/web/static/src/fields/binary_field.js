/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { download } from "@web/core/network/download";
import { standardFieldProps } from "./standard_field_props";
import { FileDownloader, FileUploader } from "./file_handler";

const { Component } = owl;
const { onWillUpdateProps, useState } = owl.hooks;

function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

export class BinaryField extends Component {
    setup() {
        this.notification = useService("notification");
        this.state = useState({
            filename: "",
            isValid: true,
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                this.state.filename = "";
            }
        });
    }
    get file() {
        return {
            data: this.props.record.data[this.props.name],
            name:
                this.state.filename ||
                this.props.record.data[this.props.filename] ||
                this.props.filename ||
                this.props.value,
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
                data: isBinarySize(this.props.value) ? null : this.props.value,
            },
            url: "/web/content",
        });
    }
    onFileRemove() {
        this.state.isValid = true;
        this.props.update(false);
        this.props.record.update(this.props.filename, false);
    }
    onFileUploaded(info) {
        this.state.filename = info.name;
        this.state.isValid = true;
        this.props.update(info.data);
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
    filename: { type: String, optional: true },
    acceptedFileExtensions: { type: String, optional: true },
};
BinaryField.defaultProps = {
    acceptedFileExtensions: "*",
};
BinaryField.template = "web.BinaryField";

BinaryField.convertAttrsToProps = function (attrs) {
    return {
        filename: attrs.filename,
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
    };
};

registry.category("fields").add("binary", BinaryField);
