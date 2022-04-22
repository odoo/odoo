/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onWillUnmount, useRef } = owl;

export class FollowerListMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._dropdownRef = useRef('dropdown');
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
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
     * @return {FollowerListMenuView}
     */
    get followerListMenuView() {
        return this.messaging && this.messaging.models['FollowerListMenuView'].get(this.props.localId);
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
        this.followerListMenuView.hide();
        this.followerListMenuView.thread.promptAddPartnerFollower();
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
            this.followerListMenuView.hide();
        }
    }

}

Object.assign(FollowerListMenu, {
    defaultProps: {
        isDisabled: false,
        isChatterButton: false,
    },
    props: {
        isDisabled: { type: Boolean, optional: true },
        isChatterButton: { type: Boolean, optional: true },
        localId: String,
    },
    template: 'mail.FollowerListMenu',
});

registerMessagingComponent(FollowerListMenu);
