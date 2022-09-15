/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallParticipantCardView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'volumeMenuAnchorRef', refName: 'volumeMenuAnchor' });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {Thread|undefined}
     */
    get callParticipantCardView() {
        return this.props.record;
    }

}

Object.assign(CallParticipantCardView, {
    props: { record: Object },
    template: 'mail.CallParticipantCardView',
});

registerMessagingComponent(CallParticipantCardView);
