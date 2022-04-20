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

    /**
     * @return {Thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.threadLocalId);
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

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseEnterUnfollow(ev) {
        if (!this.followButtonView) {
            return;
        }
        this.followButtonView.update({ isUnfollowButtonHighlighted: true });
    }

}

Object.assign(FollowButton, {
    defaultProps: {
        isDisabled: false,
        isChatterButton: false,
    },
    props: {
        isDisabled: { type: Boolean, optional: true },
        threadLocalId: String,
        isChatterButton: { type: Boolean, optional: true },
        localId: String,
    },
    template: 'mail.FollowButton',
});

registerMessagingComponent(FollowButton);
