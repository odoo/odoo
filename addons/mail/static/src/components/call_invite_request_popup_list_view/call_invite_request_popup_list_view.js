/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallInviteRequestPopupListView extends Component {}

Object.assign(CallInviteRequestPopupListView, {
    props: {},
    template: 'mail.CallInviteRequestPopupListView',
});

registerMessagingComponent(CallInviteRequestPopupListView);
