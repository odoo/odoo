/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class Follower extends Component {
    /**
     * @returns {FollowerView}
     */
    get followerView() {
        return this.props.record;
    }
}

Object.assign(Follower, {
    props: { record: Object },
    template: 'mail.Follower',
});

registerMessagingComponent(Follower);
