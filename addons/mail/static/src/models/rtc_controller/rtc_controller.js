/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { create } from '@mail/model/model_field_command';

function factory(dependencies) {

    class RtcController extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this.onClickCamera = this.onClickCamera.bind(this);
            this.onClickDeafen = this.onClickDeafen.bind(this);
            this.onClickMicrophone = this.onClickMicrophone.bind(this);
            this.onClickRejectCall = this.onClickRejectCall.bind(this);
            this.onClickScreen = this.onClickScreen.bind(this);
            this.onClickToggleAudioCall = this.onClickToggleAudioCall.bind(this);
            this.onClickToggleVideoCall = this.onClickToggleVideoCall.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {MouseEvent} ev
         */
        onClickCamera(ev) {
            this.messaging.mailRtc.toggleUserVideo();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickDeafen(ev) {
            await this.messaging.mailRtc.currentRtcSession.toggleDeaf();
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickMicrophone(ev) {
            this.messaging.mailRtc.toggleMicrophone();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickRejectCall(ev) {
            await this.callViewer.threadView.thread.leaveCall();
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickScreen(ev) {
            this.messaging.mailRtc.toggleScreenShare();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleAudioCall(ev) {
            await this.callViewer.threadView.thread.toggleCall();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleVideoCall(ev) {
            await this.callViewer.threadView.thread.toggleCall({
                startWithVideo: true,
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _computeIsSmall() {
            return this.callViewer && this.callViewer.threadView.compact && !this.callViewer.isFullScreen;
        }

    }

    RtcController.fields = {
        callViewer: one2one('mail.rtc_call_viewer', {
            inverse: 'rtcController',
        }),
        isSmall: attr({
            compute: '_computeIsSmall',
        }),
        rtcOptionList: one2one('mail.rtc_option_list', {
            default: create(),
            inverse: 'rtcController',
            isCausal: true,
            required: true,
        }),
    };

    RtcController.modelName = 'mail.rtc_controller';

    return RtcController;
}

registerNewModel('mail.rtc_controller', factory);
