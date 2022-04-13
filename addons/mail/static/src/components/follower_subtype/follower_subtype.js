/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowerSubtype extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {FollowerSubtypeView}
     */
    get followerSubtypeView() {
        return this.messaging && this.messaging.models['FollowerSubtypeView'].get(this.props.localId);
    }

}

Object.assign(FollowerSubtype, {
    props: { localId: String },
    template: 'mail.FollowerSubtype',
});

registerMessagingComponent(FollowerSubtype);
