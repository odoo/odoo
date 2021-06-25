/** @odoo-module **/

import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useStore } from '@mail/component_hooks/use_store/use_store';

const { Component } = owl;
const { useState } = owl.hooks;

export class FollowButton extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        this.state = useState({
            /**
             * Determine whether the unfollow button is highlighted or not.
             */
            isUnfollowButtonHighlighted: false,
        });
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                threadIsCurrentPartnerFollowing: thread && thread.isCurrentPartnerFollowing,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFollow(ev) {
        this.thread.follow();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnfollow(ev) {
        this.thread.unfollow();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseLeaveUnfollow(ev) {
        this.state.isUnfollowButtonHighlighted = false;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseEnterUnfollow(ev) {
        this.state.isUnfollowButtonHighlighted = true;
    }

}

Object.assign(FollowButton, {
    defaultProps: {
        isDisabled: false,
    },
    props: {
        isDisabled: Boolean,
        threadLocalId: String,
    },
    template: 'mail.FollowButton',
});
