/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { useRef } = owl.hooks;

export class RtcCallParticipantCard extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._volumeMenuAnchorRef = useRef('volumeMenuAnchor');
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
        if (!this._volumeMenuAnchorRef || !this._volumeMenuAnchorRef.el) {
            return;
        }
        ev.preventDefault();
        this._volumeMenuAnchorRef.el.click();
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
