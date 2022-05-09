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
        return this.props.record;
    }

}

Object.assign(RtcConfigurationMenu, {
    props: { record: Object },
    template: 'mail.RtcConfigurationMenu',
});

registerMessagingComponent(RtcConfigurationMenu);
