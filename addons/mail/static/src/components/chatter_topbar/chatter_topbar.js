/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatterTopbar extends Component {

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.messaging && this.messaging.models['Chatter'].get(this.props.localId);
    }

}

Object.assign(ChatterTopbar, {
    props: { localId: String },
    template: 'mail.ChatterTopbar',
});

registerMessagingComponent(ChatterTopbar);
