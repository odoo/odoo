/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { FileUploader } from "./file_handler";

const { Component, useState } = owl;

export class Many2ManyBinaryField extends Component {
    setup() {
        this.state = useState({
            files: [],
        });
        console.log(this.props);
    }

    get url() {
        //TODO
    }

    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }
    onFileUploaded(file) {
        console.log(file);
        this.state.files.push(file);
    }

    onFileRemove(ev) {
        console.log(ev.target.dataset.id);
    }
}

Many2ManyBinaryField.components = {
    FileUploader,
};
Many2ManyBinaryField.template = "web.Many2ManyBinaryField";
Many2ManyBinaryField.props = {
    ...standardFieldProps,
    acceptedFileExtensions: { type: String, optional: true },
    className: { type: String, optional: true },
    uploadText: { type: String, optional: true },
    setAsInvalid: { type: Function, optional: true },
};
Many2ManyBinaryField.defaultProps = {
    setAsInvalid: () => {},
};
Many2ManyBinaryField.isEmpty = () => false;
Many2ManyBinaryField.extractProps = (fieldName, record, attrs) => {
    return {
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
        className: attrs.class,
        uploadText: record.data[fieldName].field.string,
        setAsInvalid: () => record.setInvalidField(fieldName),
    };
};

registry.category("fields").add("many2many_binary", Many2ManyBinaryField);
