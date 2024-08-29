import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, onWillStart } from "@odoo/owl";
import { BaseRecipientsList } from "@mail/core/web/base_recipients_list";


export class MailComposerRecipientList extends Component {
    static template = "mail.MailComposerRecipientList";
    static components = { BaseRecipientsList };
    static props = { ...standardWidgetProps };

    setup() {
        const { Thread } = useService("mail.store");
        this.state = useState({});
        onWillStart(async () => {
            try {
                const resIds = JSON.parse(this.props.record.data.res_ids);
                const thread = await Thread.getOrFetch({
                    model: this.props.record.data.model,
                    id: resIds[0],
                });
                this.state.thread = thread;
            } catch {};
        });
    }
}

const mailComposerRecipientList = {
    component: MailComposerRecipientList
};

registry.category("view_widgets").add("mail_composer_recipient_list", mailComposerRecipientList);
