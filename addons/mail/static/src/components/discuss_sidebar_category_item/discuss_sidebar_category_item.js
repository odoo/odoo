/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarCategoryItem extends Component {

    /**
     * @returns {DiscussSidebarCategoryItem}
     */
    get categoryItem() {
        return this.messaging.models['DiscussSidebarCategoryItem'].get(this.props.localId);
    }

}

Object.assign(DiscussSidebarCategoryItem, {
    props: { localId: String },
    template: 'mail.DiscussSidebarCategoryItem',
});

registerMessagingComponent(DiscussSidebarCategoryItem);
