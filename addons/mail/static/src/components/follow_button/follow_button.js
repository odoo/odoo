/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';

const { Component } = owl;
const { useState } = owl.hooks;

export class FollowButton extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
        useShouldUpdateBasedOnProps();
        this.state = useState({
            /**
             * Determine whether the unfollow button is highlighted or not.
             */
            isUnfollowButtonHighlighted: false,
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
