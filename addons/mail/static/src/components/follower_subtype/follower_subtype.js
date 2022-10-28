/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
