/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class DiscussPublicView extends Component {

    /**
     * @returns {DiscussPublicView}
     */
     get discussPublicView() {
        return this.messaging && this.messaging.models['DiscussPublicView'].get(this.props.localId);
    }
}

Object.assign(DiscussPublicView, {
    props: { localId: String },
    template: 'mail.DiscussPublicView',
});

registerMessagingComponent(DiscussPublicView);
