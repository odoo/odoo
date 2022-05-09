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
        return this.props.record;
    }

}

Object.assign(FollowerSubtype, {
    props: { record: Object },
    template: 'mail.FollowerSubtype',
});

registerMessagingComponent(FollowerSubtype);
