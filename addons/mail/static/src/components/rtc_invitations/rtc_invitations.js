/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallInviteRequestPopupList extends Component {}

Object.assign(CallInviteRequestPopupList, {
    props: {},
    template: 'mail.CallInviteRequestPopupList',
});

registerMessagingComponent(CallInviteRequestPopupList);
