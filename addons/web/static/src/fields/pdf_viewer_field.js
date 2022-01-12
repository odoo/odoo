/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { standardFieldProps } from "./standard_field_props";
import { FileDownloader, FileUploader } from "./file_handler";

const { Component } = owl;
const { onWillUpdateProps, useState } = owl.hooks;

export class PdfViewerField extends Component {
    setup() {
        this.notification = useService("notification");
        this.state = useState({
            filename: "",
            isValid: true,
            objectUrl: "",
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                this.state.filename = "";
                this.state.objectUrl = "";
            }
        });
    }
    get file() {
        return {
            data: this.props.record.data[this.props.name],
            name:
                this.state.filename ||
                this.props.record.data[this.props.filename] ||
                this.props.filename ||
                null,
        };
    }
    get url() {
        if (this.state.isValid && this.props.value) {
            return (
                "/web/static/lib/pdfjs/web/viewer.html?file=" +
                encodeURIComponent(
                    this.state.objectUrl ||
                        url("/web/content", {
                            model: this.props.record.resModel,
                            id: this.props.record.resId,
                            field: this.props.previewImage || this.props.name,
                        })
                ) +
                `#page=${this.props.record.data[this.props.name + "_page"] || 1}`
            );
        }
    }
    onFileRemove() {
        this.state.isValid = true;
        this.props.update(false);
    }
    onFileUploaded(info) {
        this.state.filename = info.name;
        this.state.isValid = true;
        this.props.update(info.data);
        this.state.objectUrl = info.objectUrl;
    }
    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected pdf"), {
            type: "danger",
        });
    }
}

PdfViewerField.components = {
    FileDownloader,
    FileUploader,
};
PdfViewerField.props = {
    ...standardFieldProps,
    filename: { type: String, optional: true },
    previewImage: { type: String, optional: true },
};
PdfViewerField.template = "web.PdfViewerField";

PdfViewerField.convertAttrsToProps = function (attrs) {
    return {
        filename: attrs.filename,
        previewImage: attrs.options.preview_image,
    };
};

registry.category("fields").add("pdf_viewer", PdfViewerField);
