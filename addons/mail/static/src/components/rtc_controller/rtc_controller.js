/** @odoo-module **/

import { useRefs } from '@mail/component_hooks/use_refs/use_refs';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcController extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._getRefs = useRefs();
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get rtcSession() {
        return this.messaging && this.messaging.mailRtc.currentRtcSession;
    }

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCallToggleVideo(ev) {
        await this.thread.toggleCall({
            startWithVideo: true,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCallToggleAudio(ev) {
        await this.thread.toggleCall();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCamera(ev) {
        this.messaging.mailRtc.toggleUserVideo();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickDeafen(ev) {
        await this.rtcSession.toggleDeaf();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMicrophone(ev) {
        this.messaging.mailRtc.toggleMicrophone();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickScreen(ev) {
        this.messaging.mailRtc.toggleScreenShare();
    }

}

Object.assign(RtcController, {
    props: {
        small: {
            type: Boolean,
            optional: true,
        },
        threadLocalId: {
            type: String,
        },
    },
    template: 'mail.RtcController',
});

registerMessagingComponent(RtcController);
