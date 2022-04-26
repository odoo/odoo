/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcConfigurationMenuDevice extends Component {}

Object.assign(RtcConfigurationMenuDevice, {
    props: { device: Object },
    template: 'mail.RtcConfigurationMenuDevice',
});

registerMessagingComponent(RtcConfigurationMenuDevice);
