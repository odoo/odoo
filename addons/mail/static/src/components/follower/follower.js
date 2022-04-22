/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Follower extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Follower}
     */
    get follower() {
        return this.messaging && this.messaging.models['Follower'].get(this.props.followerLocalId);
    }

}

Object.assign(Follower, {
    defaultProps: {
        onClick: () => {},
    },
    props: {
        followerLocalId: String,
        onClick: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.Follower',
});

registerMessagingComponent(Follower);
