/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcInvitations extends Component {}

Object.assign(RtcInvitations, {
    props: {},
    template: 'mail.RtcInvitations',
});

registerMessagingComponent(RtcInvitations);
