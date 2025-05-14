import { FileInput } from "@web/core/file_input/file_input";
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
        onFileUploaded: Function,
        onFileRemove: Function,
        files: { type: Array },
        acceptedFileExtensions: { type: String, optional: true },
        className: { type: String, optional: true },
        multiUpload: { type: Boolean, optional: true, default: false },
        numberOfFiles: { type: Number, optional: true },
    };

    static defaultProps = {
        multiUpload: false,
    };

    setup() {
        this.notification = useService("notification");
    }

    get uploadText() {
        return this.props.record.fields[this.props.name].string;
    }

    get files() {
        return this.props.files;
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
        await this.props.onFileUploaded(files);
    }

    async onFileRemove(deleteId) {
        await this.props.onFileRemove(deleteId);
    }
}
