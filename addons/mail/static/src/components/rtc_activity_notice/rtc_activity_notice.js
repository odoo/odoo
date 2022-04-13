/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcActivityNotice extends Component {}

Object.assign(RtcActivityNotice, {
    props: {},
    template: 'mail.RtcActivityNotice',
});

registerMessagingComponent(RtcActivityNotice);
