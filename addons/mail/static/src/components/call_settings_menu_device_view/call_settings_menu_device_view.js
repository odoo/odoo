/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallSettingsMenuDeviceView extends Component {}

Object.assign(CallSettingsMenuDeviceView, {
    props: { device: Object },
    template: 'mail.CallSettingsMenuDeviceView',
});

registerMessagingComponent(CallSettingsMenuDeviceView);
