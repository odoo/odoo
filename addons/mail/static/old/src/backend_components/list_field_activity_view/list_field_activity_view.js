/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";

import { Component } from "@odoo/owl";

export class ListFieldActivityView extends Component {
    get listFieldActivityView() {
        return this.props.record;
    }
}

Object.assign(ListFieldActivityView, {
    props: { record: Object },
    template: "mail.ListFieldActivityView",
});

registerMessagingComponent(ListFieldActivityView);
