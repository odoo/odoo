/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";

const { Component, useRef } = owl;

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
     * @returns {Thread|undefined}
     */
    get callParticipantCard() {
        return this.messaging.models['RtcCallParticipantCard'].get(this.props.localId);
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
    props: { localId: String },
    template: 'mail.RtcCallParticipantCard',
    components: { Popover },
});

registerMessagingComponent(RtcCallParticipantCard);
