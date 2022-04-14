/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { browser } from "@web/core/browser/browser";

const { Component, onWillStart, useState } = owl;

export class RtcConfigurationMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.state = useState({
            userDevices: undefined,
        });
        onWillStart(() => this._willStart());
    }

    async _willStart() {
        this.state.userDevices = await browser.navigator.mediaDevices.enumerateDevices();
    }

    /**
     * @returns {RtcConfigurationMenu|undefined}
     */
    get rtcConfigurationMenu() {
        return this.messaging && this.messaging.models['RtcConfigurationMenu'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeDelay(ev) {
        this.rtcConfigurationMenu.onChangeDelay(ev.target.value);
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onChangePushToTalk(ev) {
        this.rtcConfigurationMenu.onChangePushToTalk();
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeSelectAudioInput(ev) {
        this.rtcConfigurationMenu.onChangeSelectAudioInput(ev.target.value);
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeThreshold(ev) {
        this.rtcConfigurationMenu.onChangeThreshold(ev.target.value);
    }

}

Object.assign(RtcConfigurationMenu, {
    props: { localId: String },
    template: 'mail.RtcConfigurationMenu',
});

registerMessagingComponent(RtcConfigurationMenu);
