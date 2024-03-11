/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class SnailmailNotificationPopoverContentView extends Component {

    /**
     * @returns {SnailmailNotificationPopoverContentView}
     */
    get snailmailNotificationPopoverContentView() {
        return this.props.record;
    }

}

Object.assign(SnailmailNotificationPopoverContentView, {
    props: { record: Object },
    template: 'snailmail.SnailmailNotificationPopoverContentView',
});

registerMessagingComponent(SnailmailNotificationPopoverContentView);

