import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XBinary } from "../many2x_binary/many2x_binary_component";

export class Many2OneBinaryField extends Many2XBinary {
    get files() {
        const file = this.props.record.data[this.props.name];
        if (!file) {
            return [];
        }
        return [file];
    }

    async onFileUploaded(files) {
        const validFiles = await super.onFileUploaded(files);
        const lastFile = validFiles.at(-1);
        if (lastFile) {
            await this.props.record.update({ [this.props.name]: { id: lastFile.id } });
        }
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
        multiUpload: false,
        numberOfFiles: 1,
    }),
};

registry.category("fields").add("many2one_binary", many2OneBinaryField);
