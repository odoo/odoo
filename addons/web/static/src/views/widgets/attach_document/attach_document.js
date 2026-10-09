import { registry } from "@web/core/registry";
import { useFileUploader } from "@web/core/utils/files";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, t, useProps } from "@odoo/owl";

export class AttachDocumentWidget extends Component {
    static template = "web.AttachDocument";
    props = useProps({
        ...standardWidgetProps,
        acceptedFileExtensions: t.string().optional(),
        string: t.string(),
        action: t.string().optional(),
        highlight: t.boolean(),
    });

    setup() {
        this.uploadFiles = useFileUploader();
        this.fileInput = document.createElement("input");
        this.fileInput.type = "file";
        this.fileInput.accept = this.props.acceptedFileExtensions || "*";
        this.fileInput.multiple = true;
        this.fileInput.onchange = this.onInputChange.bind(this);
    }

    async onInputChange() {
        const files = await this.uploadFiles("/web/binary/upload_attachment", {
            ufile: [...this.fileInput.files],
            model: this.props.record.resModel,
            id: this.props.record.resId,
        });
        if (files) {
            await this.onFileUploaded(files);
        }
    }

    async triggerUpload() {
        if (await this.beforeOpen()) {
            this.fileInput.click();
        }
    }

    async onFileUploaded(files) {
        const { action, record } = this.props;
        if (action) {
            const { resId, resModel } = record;
            await this.env.services.orm.call(resModel, action, [resId], {
                attachment_ids: files.map((file) => file.id),
            });
            await record.load();
        }
    }

    beforeOpen() {
        return this.props.record.save();
    }
}

export const attachDocumentWidget = {
    component: AttachDocumentWidget,
    extractProps: ({ attrs, options }) => {
        const { action, highlight, string } = attrs;
        return {
            action,
            highlight: !!highlight,
            string,
            acceptedFileExtensions: options.accepted_file_extensions,
        };
    },
};

registry.category("view_widgets").add("attach_document", attachDocumentWidget);
