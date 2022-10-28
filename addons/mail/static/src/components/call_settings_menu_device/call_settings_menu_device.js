/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallSettingsMenuDevice extends Component {
    /**
     * @returns {CallSettingsMenuDevice}
     */
    get callSettingsMenuDevice() {
        return this.props.record;
    }
}

Object.assign(CallSettingsMenuDevice, {
    props: { record: Object },
    template: 'mail.CallSettingsMenuDevice',
});

registerMessagingComponent(CallSettingsMenuDevice);
