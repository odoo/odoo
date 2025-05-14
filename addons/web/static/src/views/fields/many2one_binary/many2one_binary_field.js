import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2XBinary } from "../many2x_binary/many2x_binary_component";

export class Many2OneBinaryField extends Many2XBinary {
    setup() {
        this.notification = useService("notification");
    }

    /** override **/
    get files() {
        const file = this.props.record.data[this.props.name];
        if (!file) {
            return [];
        }
        return [file];
    }

    /** override **/
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

    /** override **/
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
        multiUpload: false,
        numberOfFiles: 1,
    }),
};

registry.category("fields").add("many2one_binary", many2OneBinaryField);
