/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowerView extends Component {
    /**
     * @returns {FollowerView}
     */
    get followerView() {
        return this.props.record;
    }
}

Object.assign(FollowerView, {
    props: { record: Object },
    template: 'mail.FollowerView',
});

registerMessagingComponent(FollowerView);
