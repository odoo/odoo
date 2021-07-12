/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcLayoutMenu extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.user_setting}
     */
    get userSetting() {
        return this.messaging.userSetting;
    }

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFilter(ev) {
        ev.preventDefault();
        switch (ev.target.value) {
            case 'all':
                this.userSetting.update({
                    rtcFilterVideoGrid: false,
                });
                break;
            case 'video':
                this.userSetting.update({
                    rtcFilterVideoGrid: true,
                });
                break;
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLayout(ev) {
        ev.preventDefault();
        this.userSetting.setRtcLayout(ev.target.value);
    }
}

Object.assign(RtcLayoutMenu, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.RtcLayoutMenu',
});

registerMessagingComponent(RtcLayoutMenu);
