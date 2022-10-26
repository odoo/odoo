/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarCategory extends Component {

    /**
     * @returns {DiscussSidebarCategory}
     */
    get category() {
        return this.props.record;
    }
}

Object.assign(DiscussSidebarCategory, {
    props: { record: Object },
    template: 'mail.DiscussSidebarCategory',
});

registerMessagingComponent(DiscussSidebarCategory);
