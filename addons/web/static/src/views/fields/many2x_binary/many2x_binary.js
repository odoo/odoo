import { FileInput } from "@web/core/file_input/file_input";
import { standardFieldProps } from "../standard_field_props";

import { Component, t, useProps } from "@odoo/owl";

export class Many2XBinary extends Component {
    static template = "web.Many2XBinary";
    static components = {
        FileInput,
    };
    props = useProps({
        ...standardFieldProps,
        onFileUploaded: t.function(),
        onFileRemove: t.function(),
        files: t.array(),
        acceptedFileExtensions: t.string().optional(),
        className: t.string().optional(),
        multiUpload: t.boolean().optional(false),
        numberOfFiles: t.number().optional(),
    });

    get uploadText() {
        return this.props.record.fields[this.props.name].string;
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
}
