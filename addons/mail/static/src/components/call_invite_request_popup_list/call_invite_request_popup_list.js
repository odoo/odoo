/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallInviteRequestPopupList extends Component {
    /**
     * @returns {CallInviteRequestPopupList}
     */
    get callInviteRequestPopupList() {
        return this.props.record;
    }
}

Object.assign(CallInviteRequestPopupList, {
    props: { record: Object },
    template: 'mail.CallInviteRequestPopupList',
});

registerMessagingComponent(CallInviteRequestPopupList);
