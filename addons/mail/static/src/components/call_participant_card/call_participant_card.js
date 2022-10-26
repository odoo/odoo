/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallParticipantCard extends Component {

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
    get callParticipantCard() {
        return this.props.record;
    }

}

Object.assign(CallParticipantCard, {
    props: { record: Object },
    template: 'mail.CallParticipantCard',
});

registerMessagingComponent(CallParticipantCard);
