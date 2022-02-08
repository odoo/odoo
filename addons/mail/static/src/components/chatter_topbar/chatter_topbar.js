/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatterTopbar extends Component {

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.messaging && this.messaging.models['Chatter'].get(this.props.chatterLocalId);
    }

}

Object.assign(ChatterTopbar, {
    props: { chatterLocalId: String },
    template: 'mail.ChatterTopbar',
});

registerMessagingComponent(ChatterTopbar);
