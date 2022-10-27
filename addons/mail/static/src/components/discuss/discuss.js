/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.props.record;
    }
}

Object.assign(DiscussView, {
    props: { record: Object },
    template: 'mail.DiscussView',
});

registerMessagingComponent(DiscussView);
