/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { browser } from "@web/core/browser/browser";

const { Component, onWillStart, useState } = owl;

export class CallSettingsMenu extends Component {

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
     * @returns {CallSettingsMenu}
     */
    get callSettingsMenu() {
        return this.props.record;
    }

}

Object.assign(CallSettingsMenu, {
    props: { record: Object },
    template: 'mail.CallSettingsMenu',
});

registerMessagingComponent(CallSettingsMenu);
