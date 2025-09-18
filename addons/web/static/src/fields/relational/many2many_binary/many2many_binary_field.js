// @ts-check

/** @module @web/fields/relational/many2many_binary/many2many_binary_field - File attachment list field for Many2many relations to ir.attachment */

import { Component } from "@odoo/owl";
import { FileInput } from "@web/components/file_input/file_input";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/fields/standard_field_props";

import { useX2ManyCrud } from "../x2many_crud";

export class Many2ManyBinaryField extends Component {
    static template = "web.Many2ManyBinaryField";
    static components = {
        FileInput,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        className: { type: String, optional: true },
        numberOfFiles: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.operations = useX2ManyCrud(
            () => this.props.record.data[this.props.name],
            true,
        );
    }

    /** @returns {string} Field label used as upload button text */
    get uploadText() {
        return this.props.record.fields[this.props.name].string;
    }
    /** @returns {Array<Object>} Attachment data objects with `id` set to resId */
    get files() {
        return this.props.record.data[this.props.name].records.map((record) => ({
            ...record.data,
            id: record.resId,
        }));
    }

    /**
     * @param {number} id - Attachment record ID
     * @returns {string} Download URL for the attachment
     */
    getUrl(id) {
        return `/web/content/${id}?download=true`;
    }

    /**
     * @param {{ name: string }} file
     * @returns {string} File extension without the leading dot
     */
    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }

    /**
     * @param {{ mimetype: string }} file
     * @returns {boolean}
     */
    isImage(file) {
        return file.mimetype.startsWith("image/");
    }

    /** @param {Array<{ id: number, error?: string }>} files - Uploaded file descriptors */
    async onFileUploaded(files) {
        for (const file of files) {
            if (file.error) {
                return this.notification.add(file.error, {
                    title: _t("Uploading error"),
                    type: "danger",
                });
            }
            await this.operations.saveRecord([file.id]);
        }
    }

    /** @param {number} deleteId - resId of the attachment to unlink */
    async onFileRemove(deleteId) {
        const record = this.props.record.data[this.props.name].records.find(
            (record) => record.resId === deleteId,
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
        numberOfFiles: options.number_of_files,
    }),
};

registry.category("fields").add("many2many_binary", many2ManyBinaryField);
