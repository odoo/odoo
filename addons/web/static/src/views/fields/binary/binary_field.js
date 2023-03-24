/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isBinarySize } from "@web/core/utils/binary";
import { download } from "@web/core/network/download";
import { standardFieldProps } from "../standard_field_props";
import { FileUploader } from "../file_handler";
import { _lt } from "@web/core/l10n/translation";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
export class BinaryField extends Component {
    setup() {
        this.notification = useService("notification");
        this.state = useState({
            fileName: this.props.record.data[this.props.fileNameField] || "",
        });
        onWillUpdateProps((nextProps) => {
            this.state.fileName = nextProps.record.data[nextProps.fileNameField] || "";
        });
    }

    get fileName() {
        return this.state.fileName || this.props.value || "";
    }

    update({ data, name }) {
        this.state.fileName = name || "";
        const { fileNameField, record } = this.props;
        const changes = { [this.props.name]: data || false };
        if (fileNameField in record.fields && record.data[fileNameField] !== name) {
            changes[fileNameField] = name || false;
        }
        return this.props.record.update(changes);
    }

    async onFileDownload() {
        await download({
            data: {
                model: this.props.record.resModel,
                id: this.props.record.resId,
                field: this.props.name,
                filename_field: this.fileName,
                filename: this.fileName || "",
                download: true,
                data: isBinarySize(this.props.value) ? null : this.props.value,
            },
            url: "/web/content",
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
