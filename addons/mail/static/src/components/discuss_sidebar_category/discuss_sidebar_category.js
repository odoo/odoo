/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarCategory extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss_sidebar_category}
     */
    get category() {
        return this.messaging.models['mail.discuss_sidebar_category'].get(this.props.categoryLocalId);
    }
}

Object.assign(DiscussSidebarCategory, {
    props: {
        categoryLocalId: String,
    },
    template: 'mail.DiscussSidebarCategory',
});

registerMessagingComponent(DiscussSidebarCategory);
