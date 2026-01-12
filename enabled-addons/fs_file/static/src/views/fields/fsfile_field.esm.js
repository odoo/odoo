/** @odoo-module */

/**
 * Copyright 2023 ACSONE SA/NV
 */
import {Component} from "@odoo/owl";
import {FileUploader} from "@web/views/fields/file_handler";
import {MAX_FILENAME_SIZE_BYTES} from "@web/views/fields/binary/binary_field";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {toBase64Length} from "@web/core/utils/binary";
import {useService} from "@web/core/utils/hooks";

export class FSFileField extends Component {
    setup() {
        this.notification = useService("notification");
    }
    get filename() {
        return (this.props.record.data[this.props.name].filename || "").slice(
            0,
            toBase64Length(MAX_FILENAME_SIZE_BYTES)
        );
    }
    get url() {
        return this.props.record.data[this.props.name].url || "";
    }

    onFileRemove() {
        this.props.record.update({[this.props.name]: false});
    }
    onFileUploaded(info) {
        this.props.record.update({
            [this.props.name]: {
                filename: info.name,
                content: info.data,
            },
        });
    }
}

FSFileField.template = "fs_file.FSFileField";
FSFileField.components = {
    FileUploader,
};
FSFileField.props = {
    ...standardFieldProps,
    acceptedFileExtensions: {type: String, optional: true},
};
FSFileField.defaultProps = {
    acceptedFileExtensions: "*",
};

export const fSFileField = {
    component: FSFileField,
};

registry.category("fields").add("fs_file", fSFileField);
