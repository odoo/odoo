import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { registry } from "@web/core/registry";
import { Many2XBinary } from "../many2x_binary/many2x_binary";
import { standardFieldProps } from "../standard_field_props";

import { Component, t, usePlugin, useProps } from "@odoo/owl";

export class Many2OneBinaryField extends Component {
    static template = "web.Many2OneBinaryField";
    static components = {
        Many2XBinary,
    };
    props = useProps({
        ...standardFieldProps,
        acceptedFileExtensions: t.string().optional(),
        className: t.string().optional(),
    });

    setup() {
        this.notification = usePlugin(NotificationPlugin);
    }

    get files() {
        const attachment = this.props.record.data[this.props.name];
        return attachment ? [attachment] : [];
    }

    async onFileUploaded([file]) {
        if (!file) {
            return;
        }
        if (file.error) {
            return this.notification.add(file.error, {
                title: _t("Uploading error"),
                type: "danger",
            });
        }
        await this.props.record.update({
            [this.props.name]: {
                id: file.id,
                display_name: file.name,
                name: file.name,
                mimetype: file.mimetype,
            },
        });
    }

    async onFileRemove() {
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

registry.category("fields").add("many2one_binary", many2OneBinaryField);
