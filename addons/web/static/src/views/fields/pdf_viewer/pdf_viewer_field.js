/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { standardFieldProps } from "../standard_field_props";
import { FileUploader } from "../file_handler";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

export class PdfViewerField extends Component {
    setup() {
        this.notification = useService("notification");
        this.state = useState({
            fileName: this.props.record.data[this.props.fileNameField] || "",
            isValid: true,
            objectUrl: "",
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                this.state.fileName = nextProps.record.data[nextProps.fileNameField] || "";
                this.state.objectUrl = "";
            }
        });
    }

    get fileName() {
        return this.state.fileName || this.props.value || "";
    }

    get url() {
        if (!this.state.isValid || !this.props.value) {
            return null;
        }
        const page = this.props.record.data[`${this.props.name}_page`] || 1;
        const file = encodeURIComponent(
            this.state.objectUrl ||
                url("/web/content", {
                    model: this.props.record.resModel,
                    field: this.props.previewImage || this.props.name,
                    id: this.props.record.resId,
                })
        );
        return `/web/static/lib/pdfjs/web/viewer.html?file=${file}#page=${page}`;
    }

    update({ data, name }) {
        this.state.fileName = name || "";
        const { fileNameField, record } = this.props;
        const changes = { [this.props.name]: data || false };
        if (fileNameField in record.fields && record.data[fileNameField] !== name) {
            changes[fileNameField] = name || false;
        }
        return this.props.record.update(changes);
    }

    onFileRemove() {
        this.state.isValid = true;
        this.update({});
    }

    onFileUploaded({ data, name, objectUrl }) {
        this.state.fileName = name;
        this.state.isValid = true;
        this.state.objectUrl = objectUrl;
        this.update({ data, name });
    }

    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected pdf"), {
            type: "danger",
        });
    }
}

PdfViewerField.template = "web.PdfViewerField";
PdfViewerField.components = {
    FileUploader,
};
PdfViewerField.props = {
    ...standardFieldProps,
    fileNameField: { type: String, optional: true },
    previewImage: { type: String, optional: true },
};

PdfViewerField.displayName = _lt("PDF Viewer");
PdfViewerField.supportedTypes = ["binary"];

PdfViewerField.extractProps = ({ attrs }) => {
    return {
        fileNameField: attrs.filename,
        previewImage: attrs.options.preview_image,
    };
};

registry.category("fields").add("pdf_viewer", PdfViewerField);
