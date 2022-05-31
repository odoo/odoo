/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallSettingsMenuDevice extends Component {}

Object.assign(CallSettingsMenuDevice, {
    props: { device: Object },
    template: 'mail.CallSettingsMenuDevice',
});

registerMessagingComponent(CallSettingsMenuDevice);
