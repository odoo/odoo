/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallInviteRequestPopup extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {CallInviteRequestPopup}
     */
    get callInviteRequestPopup() {
        return this.props.record;
    }

}

Object.assign(CallInviteRequestPopup, {
    props: { record: Object },
    template: 'mail.CallInviteRequestPopup',
});

registerMessagingComponent(CallInviteRequestPopup);
