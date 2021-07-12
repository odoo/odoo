/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { browser } from "@web/core/browser/browser";

const { Component } = owl;
const { useState } = owl.hooks;

export class RtcConfigurationMenu extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            userDevices: undefined,
        });
    }

    async willStart() {
        this.state.userDevices = await browser.navigator.mediaDevices.enumerateDevices();
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.configuration_menu}
     */
    get rtcConfigurationMenu() {
        return this.messaging && this.messaging.userSetting.rtcConfigurationMenu;
    }

    /**
     * @returns {mail.user_setting}
     */
    get userSetting() {
        return this.messaging && this.messaging.userSetting;
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

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCLickRegisterKeyButton() {
        this.rtcConfigurationMenu.onCLickRegisterKeyButton();
    }
}

Object.assign(RtcConfigurationMenu, {
    template: 'mail.RtcConfigurationMenu',
});

registerMessagingComponent(RtcConfigurationMenu);
