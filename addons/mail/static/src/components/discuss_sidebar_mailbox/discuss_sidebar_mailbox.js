/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarMailboxView extends Component {

    /**
     * @returns {DiscussSidebarMailboxView}
     */
    get discussSidebarMailboxView() {
        return this.props.record;
    }

}

Object.assign(DiscussSidebarMailboxView, {
    props: { record: Object },
    template: 'mail.DiscussSidebarMailboxView',
});

registerMessagingComponent(DiscussSidebarMailboxView);
