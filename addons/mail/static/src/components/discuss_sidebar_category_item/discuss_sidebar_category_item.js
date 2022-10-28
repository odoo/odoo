/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class DiscussSidebarCategoryItem extends Component {

    /**
     * @returns {DiscussSidebarCategoryItem}
     */
    get categoryItem() {
        return this.props.record;
    }

}

Object.assign(DiscussSidebarCategoryItem, {
    props: { record: Object },
    template: 'mail.DiscussSidebarCategoryItem',
});

registerMessagingComponent(DiscussSidebarCategoryItem);
