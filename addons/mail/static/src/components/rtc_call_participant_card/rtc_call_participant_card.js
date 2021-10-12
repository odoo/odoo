/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;
const { useRef } = owl.hooks;

export class RtcCallParticipantCard extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._contextMenuAnchorRef = useRef('contextMenuAnchor');
        useComponentToModel({ fieldName: 'component', modelName: 'mail.rtc_call_participant_card', propNameAsRecordLocalId: 'callParticipantCardLocalId' });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread|undefined}
     */
    get callParticipantCard() {
        return this.messaging.models['mail.rtc_call_participant_card'].get(this.props.callParticipantCardLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This listens to the right click event, and used to redirect the event
     * as a click on the popover.
     *
     * @private
     * @param {Event} ev
     */
    async _onContextMenu(ev) {
        if (!this._contextMenuAnchorRef || !this._contextMenuAnchorRef.el) {
            return;
        }
        ev.preventDefault();
        this._contextMenuAnchorRef.el.click();
    }
}

Object.assign(RtcCallParticipantCard, {
    props: {
        callParticipantCardLocalId: {
            type: String,
        },
    },
    template: 'mail.RtcCallParticipantCard',
});

registerMessagingComponent(RtcCallParticipantCard);
