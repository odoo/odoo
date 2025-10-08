import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2XBinary } from "../many2x_binary/many2x_binary_component";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class Many2OneBinaryField extends Component {
    static template = "web.Many2OneBinaryField";
    static components = {
        Many2XBinary,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        className: { type: String, optional: true },
    };

    setup() {
        this.notification = useService("notification");
    }

    get file() {
        const file = this.props.record.data[this.props.name];
        if (!file) {
            return [];
        }
        return [file];
    }

    async onFileUploaded(files) {
        const file = files.at(-1);
        if (file.error) {
            return this.notification.add(file.error, {
                title: _t("Uploading error"),
                type: "danger",
            });
        }
        await this.props.record.update({ [this.props.name]: { id: file.id } });
    }

    async onFileRemove(deleteId) {
        await this.props.record.update({ [this.props.name]: false });
    }
}

export const many2OneBinaryField = {
    component: Many2OneBinaryField,
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
    ],
    supportedTypes: ["many2one"],
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        className: attrs.class,
    }),
};

registry.category("fields").add("many2one_binary", many2OneBinaryField);
