odoo.define('mail/static/src/components/follower_list_menu/follower_list_menu.js', function (require) {
'use strict';

const components = {
    Follower: require('mail/static/src/components/follower/follower.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;
const { useRef, useState } = owl.hooks;

class FollowerListMenu extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        this.state = useState({
            /**
             * Determine whether the dropdown is open or not.
             */
            isDropdownOpen: false,
        });
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            const followers = thread ? thread.followers : [];
            return {
                followers,
                threadChannelType: thread && thread.channel_type,
            };
        }, {
            compareDepth: {
                followers: 1,
            },
        });
        this._dropdownRef = useRef('dropdown');
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

    mounted() {
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
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
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _hide() {
        this.state.isDropdownOpen = false;
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        ev.stopPropagation();
        switch (ev.key) {
            case 'Escape':
                ev.preventDefault();
                this._hide();
                break;
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddChannels(ev) {
        ev.preventDefault();
        this._hide();
        this.thread.promptAddChannelFollower();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddFollowers(ev) {
        ev.preventDefault();
        this._hide();
        this.thread.promptAddPartnerFollower();
    }

    /**
     * Close the dropdown when clicking outside of it.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        // since dropdown is conditionally shown based on state, dropdownRef can be null
        if (this._dropdownRef.el && !this._dropdownRef.el.contains(ev.target)) {
            this._hide();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFollowersButton(ev) {
        this.state.isDropdownOpen = !this.state.isDropdownOpen;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFollower(ev) {
        this._hide();
    }
}

Object.assign(FollowerListMenu, {
    components,
    defaultProps: {
        isDisabled: false,
    },
    props: {
        isDisabled: Boolean,
        threadLocalId: String,
    },
    template: 'mail.FollowerListMenu',
});

return FollowerListMenu;

});
