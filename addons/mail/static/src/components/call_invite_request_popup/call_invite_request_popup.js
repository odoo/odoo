/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallInviteRequestPopupView extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {CallInviteRequestPopupView}
     */
    get callInviteRequestPopupView() {
        return this.props.record;
    }

}

Object.assign(CallInviteRequestPopupView, {
    props: { record: Object },
    template: 'mail.CallInviteRequestPopupView',
});

registerMessagingComponent(CallInviteRequestPopupView);
