/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowerSubtypeView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {FollowerSubtypeView}
     */
    get followerSubtypeView() {
        return this.props.record;
    }

}

Object.assign(FollowerSubtypeView, {
    props: { record: Object },
    template: 'mail.FollowerSubtypeView',
});

registerMessagingComponent(FollowerSubtypeView);
