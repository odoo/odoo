import { Component, props, types as t } from "@odoo/owl";

export class MessagingMenuEmpty extends Component {
    static template = "mail.MessagingMenuEmpty";
    props = props({
        title: t.string(),
        subtitle: t.string().optional(),
        action: t.object().optional(),
    });
}
