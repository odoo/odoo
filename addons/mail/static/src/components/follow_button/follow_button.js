odoo.define('mail/static/src/components/follow_button/follow_button.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;
const { useState } = owl.hooks;

class FollowButton extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            /**
             * Determine whether the unfollow button is highlighted or not.
             */
            isUnfollowButtonHighlighted: false,
        });
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                thread: thread ? thread.__state : undefined,
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

return FollowButton;

});
