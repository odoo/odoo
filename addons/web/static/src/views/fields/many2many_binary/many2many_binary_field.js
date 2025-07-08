import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XBinary } from "../many2x_binary/many2x_binary_component";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

export class Many2ManyBinaryField extends Many2XBinary {
    setup() {
        super.setup();
        this.operations = useX2ManyCrud(() => this.props.record.data[this.props.name], true);
    }

    get files() {
        return this.props.record.data[this.props.name].records.map((record) => ({
            ...record.data,
            id: record.resId,
        }));
    }

    async onFileUploaded(files) {
        const validFiles = await super.onFileUploaded(files);
        for (const file of validFiles) {
            await this.operations.saveRecord([file.id]);
        }
    }

    async onFileRemove(deleteId) {
        const record = this.props.record.data[this.props.name].records.find(
            (record) => record.resId === deleteId
        );
        this.operations.removeRecord(record);
    }
}

export const many2ManyBinaryField = {
    component: Many2ManyBinaryField,
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
        {
            label: _t("Number of files"),
            name: "number_of_files",
            type: "integer",
        },
    ],
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        className: attrs.class,
        multiUpload: true,
        numberOfFiles: options.number_of_files,
    }),
};

registry.category("fields").add("many2many_binary", many2ManyBinaryField);
