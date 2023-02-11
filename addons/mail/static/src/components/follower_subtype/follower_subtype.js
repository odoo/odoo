/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowerSubtype extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.follower|undefined}
     */
    get follower() {
        return this.messaging && this.messaging.models['mail.follower'].get(this.props.followerLocalId);
    }

    /**
     * @returns {mail.follower_subtype}
     */
    get followerSubtype() {
        return this.messaging && this.messaging.models['mail.follower_subtype'].get(this.props.followerSubtypeLocalId);
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
            this.follower.selectSubtype(this.followerSubtype);
        } else {
            this.follower.unselectSubtype(this.followerSubtype);
        }
    }

}

Object.assign(FollowerSubtype, {
    props: {
        followerLocalId: String,
        followerSubtypeLocalId: String,
    },
    template: 'mail.FollowerSubtype',
});

registerMessagingComponent(FollowerSubtype);
