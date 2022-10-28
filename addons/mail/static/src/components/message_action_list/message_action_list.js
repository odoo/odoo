/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class MessageActionList extends Component {

    /**
     * @returns {MessageActionList}
     */
    get messageActionList() {
        return this.props.record;
    }

}

Object.assign(MessageActionList, {
    props: { record: Object },
    template: "mail.MessageActionList",
});

registerMessagingComponent(MessageActionList);
