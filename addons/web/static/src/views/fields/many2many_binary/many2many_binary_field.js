/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "../standard_field_props";
import { FileInput } from "@web/core/file_input/file_input";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

import { Component } from "@odoo/owl";

export class Many2ManyBinaryField extends Component {
    static template = "web.Many2ManyBinaryField";
    static components = {
        FileInput,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        className: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.operations = useX2ManyCrud(() => this.props.value, true);
    }

    get uploadText() {
        return this.props.record.fields[this.props.name].string;
    }
    get files() {
        return this.props.value.records.map((record) => record.data);
    }

    getUrl(id) {
        return "/web/content/" + id + "?download=true";
    }

    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }

    async onFileUploaded(files) {
        for (const file of files) {
            if (file.error) {
                return this.notification.add(file.error, {
                    title: this.env._t("Uploading error"),
                    type: "danger",
                });
            }
            await this.operations.saveRecord([file.id]);
        }
    }

    async onFileRemove(deleteId) {
        const record = this.props.value.records.find((record) => record.data.id === deleteId);
        this.operations.removeRecord(record);
    }
}

export const many2ManyBinaryField = {
    component: Many2ManyBinaryField,
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        className: attrs.class,
    }),
};

registry.category("fields").add("many2many_binary", many2ManyBinaryField);
