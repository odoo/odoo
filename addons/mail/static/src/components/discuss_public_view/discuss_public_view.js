/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class DiscussPublicView extends Component {

    /**
     * @returns {DiscussPublicView}
     */
     get discussPublicView() {
        return this.props.record;
    }
}

Object.assign(DiscussPublicView, {
    props: { record: Object },
    template: 'mail.DiscussPublicView',
});

registerMessagingComponent(DiscussPublicView);
