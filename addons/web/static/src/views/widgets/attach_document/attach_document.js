/** @odoo-module */

import { FileInput } from "@web/core/file_input/file_input";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from "@odoo/owl";

class AttachDocumentWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onFileUploaded(files) {
        const { action, record } = this.props;
        if (action) {
            const { model, resId, resModel } = record;
            await this.orm.call(resModel, action, [resId], {
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
