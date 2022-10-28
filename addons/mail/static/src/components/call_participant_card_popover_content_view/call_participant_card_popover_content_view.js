/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallParticipantCardPopoverContentView extends Component {

    /**
     * @returns {CallParticipantCardPopoverContentView}
     */
    get callParticipantCardPopoverContentView() {
        return this.props.record;
    }

}

Object.assign(CallParticipantCardPopoverContentView, {
    props: { record: Object },
    template: 'mail.CallParticipantCardPopoverContentView',
});

registerMessagingComponent(CallParticipantCardPopoverContentView);
