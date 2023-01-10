/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

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
            this.messaging.rtc.toggleUserVideo();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickDeafen(ev) {
            await this.messaging.rtc.currentRtcSession.toggleDeaf();
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickMicrophone(ev) {
            this.messaging.rtc.toggleMicrophone();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickRejectCall(ev) {
            if (this.callViewer.threadView.thread.hasPendingRtcRequest) {
                return;
            }
            await this.callViewer.threadView.thread.leaveCall();
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickScreen(ev) {
            this.messaging.rtc.toggleScreenShare();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleAudioCall(ev) {
            if (this.callViewer.threadView.thread.hasPendingRtcRequest) {
                return;
            }
            await this.callViewer.threadView.thread.toggleCall();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleVideoCall(ev) {
            if (this.callViewer.threadView.thread.hasPendingRtcRequest) {
                return;
            }
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
            return Boolean(this.callViewer && this.callViewer.threadView.compact && !this.callViewer.isFullScreen);
        }

    }

    RtcController.fields = {
        callViewer: one2one('mail.rtc_call_viewer', {
            inverse: 'rtcController',
            readonly: true,
            required: true,
        }),
        isSmall: attr({
            compute: '_computeIsSmall',
        }),
        rtcOptionList: one2one('mail.rtc_option_list', {
            default: insertAndReplace(),
            inverse: 'rtcController',
            isCausal: true,
            required: true,
        }),
    };
    RtcController.identifyingFields = ['callViewer'];
    RtcController.modelName = 'mail.rtc_controller';

    return RtcController;
}

registerNewModel('mail.rtc_controller', factory);
