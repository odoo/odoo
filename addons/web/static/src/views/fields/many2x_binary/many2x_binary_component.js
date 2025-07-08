import { FileInput } from "@web/core/file_input/file_input";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class Many2XBinary extends Component {
    static template = "web.Many2XBinary";
    static components = {
        FileInput,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        className: { type: String, optional: true },
        multiUpload: { type: Boolean },
        numberOfFiles: { type: Number, optional: true },
    };

    get uploadText() {
        return this.props.record.fields[this.props.name].string;
    }

    setup() {
        this.notification = useService("notification");
    }

    getUrl(id) {
        return "/web/content/" + id + "?download=true";
    }

    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }

    isImage(file) {
        return file.mimetype.startsWith("image/");
    }

    async onFileUploaded(files) {
        const validFiles = [];
        for (const file of files) {
            if (file.error) {
                this.notification.add(file.error, {
                    title: _t("Uploading error"),
                    type: "danger",
                });
            } else {
                validFiles.push(file);
            }
        }
        return validFiles;
    }
}
