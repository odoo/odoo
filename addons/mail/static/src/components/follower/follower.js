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
        return this.props.follower;
    }

}

Object.assign(Follower, {
    defaultProps: {
        onClick: () => {},
    },
    props: {
        follower: Object,
        onClick: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.Follower',
});

registerMessagingComponent(Follower);
