/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { useRef } = owl.hooks;

export class RtcCallParticipantCard extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._volumeMenuAnchorRef = useRef('volumeMenuAnchor');
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread|undefined}
     */
    get rtcSession() {
        return this.messaging.models['mail.rtc_session'].get(this.props.rtcSessionLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeVolume(ev) {
        this.rtcSession.setVolume(parseFloat(ev.target.value));
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickVideo(ev) {
        ev.stopPropagation();
        this.messaging.toggleFocusedRtcSession(this.rtcSession.id);
    }

    /**
     * This listens to the right click event, and used to redirect the event
     * as a click on the popover.
     *
     * @private
     * @param {Event} ev
     */
    async _onContextMenu(ev) {
        ev.preventDefault();
        this._volumeMenuAnchorRef.el && this._volumeMenuAnchorRef.el.click();
    }
}

Object.assign(RtcCallParticipantCard, {
    props: {
        /**
         * whether the element should show the content in a minimized way.
         * TODO should probably be a different template to make it simpler?
         */
        isMinimized: {
            type: Boolean,
            optional: true,
        },
        rtcSessionLocalId: {
            type: String,
        },
    },
    template: 'mail.RtcCallParticipantCard',
});

registerMessagingComponent(RtcCallParticipantCard);
