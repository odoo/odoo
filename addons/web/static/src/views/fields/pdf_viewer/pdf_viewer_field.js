/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { standardFieldProps } from "../standard_field_props";
import { FileUploader } from "../file_handler";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

export class PdfViewerField extends Component {
    static template = "web.PdfViewerField";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            isValid: true,
            objectUrl: "",
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                this.state.objectUrl = "";
            }
        });
    }

    get url() {
        if (!this.state.isValid || !this.props.record.data[this.props.name]) {
            return null;
        }
        const page = this.props.record.data[`${this.props.name}_page`] || 1;
        const file = encodeURIComponent(
            this.state.objectUrl ||
                url("/web/content", {
                    model: this.props.record.resModel,
                    field: this.props.name,
                    id: this.props.record.resId,
                })
        );
        return `/web/static/lib/pdfjs/web/viewer.html?file=${file}#page=${page}`;
    }

    update({ data }) {
        const changes = { [this.props.name]: data || false };
        return this.props.record.update(changes);
    }

    onFileRemove() {
        this.state.isValid = true;
        this.update({});
    }

    onFileUploaded({ data, objectUrl }) {
        this.state.isValid = true;
        this.state.objectUrl = objectUrl;
        this.update({ data });
    }

    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(_t("Could not display the selected pdf"), {
            type: "danger",
        });
    }
}

export const pdfViewerField = {
    component: PdfViewerField,
    displayName: _t("PDF Viewer"),
    supportedOptions: [
        {
            label: _t("Preview image"),
            name: "preview_image",
            type: "field",
            availableTypes: ["binary"],
        },
    ],
    supportedTypes: ["binary"],
};

registry.category("fields").add("pdf_viewer", pdfViewerField);
