/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { FileUploader } from "./file_handler";
import { useService } from "@web/core/utils/hooks";

const { Component, useState } = owl;

export class Many2ManyBinaryField extends Component {
    setup() {
        this.state = useState({
            files: this.props.value.records.map((record) => record.data),
        });
        this.orm = useService("orm");
    }

    getUrl(id) {
        return "/web/content/" + id + "?download=true";
    }

    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }

    async onFileUploaded(file) {
        const data = await this.orm.call("ir.attachment", "name_create", [file], {
            context: this.props.context,
        });
        const ids = [...this.props.value.currentIds, data[0]];
        this.props.value.replaceWith(ids);

        const res = {
            ...data[1],
            id: data[0],
        };
        this.state.files.push(res);
    }

    async onFileRemove(ev) {
        const ids = this.props.value.currentIds.filter((id) => id !== Number(ev.target.dataset.id));
        this.props.value.replaceWith(ids);
    }
}

Many2ManyBinaryField.template = "web.Many2ManyBinaryField";
Many2ManyBinaryField.components = {
    FileUploader,
};
Many2ManyBinaryField.props = {
    ...standardFieldProps,
    acceptedFileExtensions: { type: String, optional: true },
    className: { type: String, optional: true },
    uploadText: { type: String, optional: true },
    items: { type: Object, optional: true },
};

Many2ManyBinaryField.supportedTypes = ["many2many"];

Many2ManyBinaryField.isEmpty = () => false;
Many2ManyBinaryField.extractProps = (fieldName, record, attrs) => {
    return {
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
        className: attrs.class,
        uploadText: record.fields[fieldName].string,
    };
};

registry.category("fields").add("many2many_binary", Many2ManyBinaryField);
