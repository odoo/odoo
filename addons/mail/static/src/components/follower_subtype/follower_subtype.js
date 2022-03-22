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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on cancel button.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeCheckbox(ev) {
        if (ev.target.checked) {
            this.followerSubtypeView.follower.selectSubtype(this.followerSubtypeView.subtype);
        } else {
            this.followerSubtypeView.follower.unselectSubtype(this.followerSubtypeView.subtype);
        }
    }

}

Object.assign(FollowerSubtype, {
    props: { localId: String },
    template: 'mail.FollowerSubtype',
});

registerMessagingComponent(FollowerSubtype);
