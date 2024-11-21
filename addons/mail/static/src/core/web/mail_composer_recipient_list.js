import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, onWillStart } from "@odoo/owl";
import { BaseRecipientsList } from "@mail/core/web/base_recipients_list";

export class MailComposerRecipientList extends Component {
    static template = "mail.MailComposerRecipientList";
    static components = { BaseRecipientsList };
    static props = {
        ...standardWidgetProps,
        thread_model_field: { type: String },
        thread_id_field: { type: String },
    };

    setup() {
        const { Thread } = useService("mail.store");
        this.state = useState({});
        onWillStart(async () => {
            const threadIdFieldType = this.props.record.fields[this.props.thread_id_field].type;
            let threadId;
            if (threadIdFieldType === "text") {
                // composer stores id in a string representing an array
                threadId = JSON.parse(this.props.record.data[this.props.thread_id_field])[0];
            } else if (threadIdFieldType === "many2one_reference") {
                // scheduled message stores id as a many2one reference
                threadId = this.props.record.data[this.props.thread_id_field].resId;
            } else {
                console.error("Thread id field type not supported");
                return;
            }
            try {
                const thread = await Thread.getOrFetch({
                    model: this.props.record.data[this.props.thread_model_field],
                    id: threadId,
                });
                this.state.thread = thread;
            } catch (e) {
                console.error(e);
            }
        });
    }
}

const mailComposerRecipientList = {
    component: MailComposerRecipientList,
    extractProps: ({ attrs }) => ({
        thread_model_field: attrs.thread_model_field,
        thread_id_field: attrs.thread_id_field,
    }),
};

registry.category("view_widgets").add("mail_composer_recipient_list", mailComposerRecipientList);
