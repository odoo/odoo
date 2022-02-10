/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onWillUnmount, useRef, useState } = owl;

export class FollowerListMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.state = useState({
            /**
             * Determine whether the dropdown is open or not.
             */
            isDropdownOpen: false,
        });
        this._dropdownRef = useRef('dropdown');
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
        this._onClickFollower = this._onClickFollower.bind(this);
    }

    _mounted() {
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    _willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {Thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.threadLocalId);
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
    defaultProps: {
        isDisabled: false,
    },
    props: {
        isDisabled: { type: Boolean, optional: true },
        threadLocalId: String,
    },
    template: 'mail.FollowerListMenu',
});

registerMessagingComponent(FollowerListMenu);
