/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isBinarySize } from "@web/core/utils/binary";
import { download } from "@web/core/network/download";
import { standardFieldProps } from "../standard_field_props";
import { FileUploader } from "../file_handler";
import { _lt } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";
export class BinaryField extends Component {
    static template = "web.BinaryField";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        fileNameField: { type: String, optional: true },
    };
    static defaultProps = {
        acceptedFileExtensions: "*",
    };

    setup() {
        this.notification = useService("notification");
    }

    get fileName() {
        return (
            this.props.record.data[this.props.fileNameField] ||
            this.props.record.data[this.props.name] ||
            ""
        );
    }

    update({ data, name }) {
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
                data: isBinarySize(this.props.record.data[this.props.name])
                    ? null
                    : this.props.record.data[this.props.name],
            },
            url: "/web/content",
        });
    }
}

export const binaryField = {
    component: BinaryField,
    displayName: _lt("File"),
    supportedOptions: [
        {
            label: _lt("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
    ],
    supportedTypes: ["binary"],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        fileNameField: attrs.filename,
    }),
};

registry.category("fields").add("binary", binaryField);
