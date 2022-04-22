/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowButton extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {FollowButtonView}
     */
    get followButtonView() {
        return this.messaging && this.messaging.models['FollowButtonView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseLeaveUnfollow(ev) {
        if (!this.followButtonView) {
            return;
        }
        this.followButtonView.update({ isUnfollowButtonHighlighted: false });
    }

}

Object.assign(FollowButton, {
    props: { localId: String },
    template: 'mail.FollowButton',
});

registerMessagingComponent(FollowButton);
