/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarCategoryItem extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussSidebarCategoryItem}
     */
    get categoryItem() {
        return this.messaging.models['DiscussSidebarCategoryItem'].get(this.props.categoryItemLocalId);
    }
}

Object.assign(DiscussSidebarCategoryItem, {
    props: {
        categoryItemLocalId: String,
    },
    template: 'mail.DiscussSidebarCategoryItem',
});

registerMessagingComponent(DiscussSidebarCategoryItem);
