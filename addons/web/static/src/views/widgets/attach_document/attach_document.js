/** @odoo-module */

import { FileInput } from "@web/core/file_input/file_input";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from "@odoo/owl";

export class AttachDocumentWidget extends Component {
    setup() {
        this.http = useService("http");
        this.notification = useService("notification");

        this.fileInput = document.createElement("input");
        this.fileInput.type = "file";
        this.fileInput.accept = "*";
        this.fileInput.multiple = true;
        this.fileInput.onchange = this.onInputChange.bind(this);
    }

    async onInputChange() {
        const fileData = await this.http.post(
            "/web/binary/upload_attachment",
            {
                csrf_token: odoo.csrf_token,
                ufile: [...this.fileInput.files],
                model: this.props.record.resModel,
                id: this.props.record.resId,
            },
            "text"
        );
        const parsedFileData = JSON.parse(fileData);
        if (parsedFileData.error) {
            throw new Error(parsedFileData.error);
        }
        await this.onFileUploaded(parsedFileData);
    }

    async triggerUpload() {
        if (await this.beforeOpen()) {
            this.fileInput.click();
        }
    }

    async onFileUploaded(files) {
        const { action, record } = this.props;
        if (action) {
            const { model, resId, resModel } = record;
            await this.env.services.orm.call(resModel, action, [resId], {
                attachment_ids: files.map((file) => file.id),
            });
            await record.load();
            model.notify();
        }
    }

    beforeOpen() {
        return this.props.record.save();
    }
}

AttachDocumentWidget.template = "web.AttachDocument";
AttachDocumentWidget.components = {
    FileInput,
};
AttachDocumentWidget.props = {
    ...standardWidgetProps,
    string: { type: String },
    action: { type: String, optional: true },
    highlight: { type: Boolean },
};
AttachDocumentWidget.extractProps = ({ attrs }) => {
    const { action, highlight, string } = attrs;
    return {
        action,
        highlight: !!highlight,
        string,
    };
};

registry.category("view_widgets").add("attach_document", AttachDocumentWidget);
