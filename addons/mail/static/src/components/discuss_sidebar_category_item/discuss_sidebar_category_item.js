/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarCategoryItem extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss_sidebar_category_item}
     */
    get categoryItem() {
        return this.messaging.models['mail.discuss_sidebar_category_item'].get(this.props.categoryItemLocalId);
    }
}

Object.assign(DiscussSidebarCategoryItem, {
    props: {
        categoryItemLocalId: String,
    },
    template: 'mail.DiscussSidebarCategoryItem',
});

registerMessagingComponent(DiscussSidebarCategoryItem);
