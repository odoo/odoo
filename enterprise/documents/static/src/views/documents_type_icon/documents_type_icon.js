import { Component, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";


class DocumentsTypeIcon extends Component {
    static template = "documents.DocumentsTypeIcon";
    static props = { ...standardFieldProps };

    setup() {
        this.fileInput = useRef("fileInput");
    }

    onClickDocumentsRequest() {
        this.fileInput.el.click();
    }

    async onReplaceDocument() {
        if (!this.fileInput.el.files.length) {
            return;
        }
        await this.env.model.env.documentsView.bus.trigger("documents-upload-files", {
            files: this.fileInput.el.files,
            accessToken: this.props.record.data.access_token,
        });
        this.fileInput.el.value = "";
    }
}

const documentsTypeIcon = {
    component: DocumentsTypeIcon,
};

registry.category("fields").add("documents_type_icon", documentsTypeIcon);
