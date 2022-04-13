/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";

const { Component } = owl;

export class RtcCallParticipantCard extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'volumeMenuAnchorRef', modelName: 'RtcCallParticipantCard', refName: 'volumeMenuAnchor' });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {Thread|undefined}
     */
    get callParticipantCard() {
        return this.messaging.models['RtcCallParticipantCard'].get(this.props.localId);
    }

}

Object.assign(RtcCallParticipantCard, {
    props: { localId: String },
    template: 'mail.RtcCallParticipantCard',
    components: { Popover },
});

registerMessagingComponent(RtcCallParticipantCard);
