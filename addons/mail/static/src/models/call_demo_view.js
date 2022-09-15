/** @odoo-module **/

import { attr, one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';

registerModel({
    name: 'CallDemoView',
    recordMethods: {
        /**
         * Stops recording user's microphone.
         */
        disableMicrophone() {
            this.audioRef.el.srcObject = null;
            if (!this.audioStream) {
                return;
            }
            this.stopTracksOnMediaStream(this.audioStream);
            this.update({ audioStream: null });
        },
        /**
         * Stops recording user's video device.
         */
        disableVideo() {
            this.videoRef.el.srcObject = null;
            if (!this.videoStream) {
                return;
            }
            this.stopTracksOnMediaStream(this.videoStream);
            this.update({ videoStream: null });
        },
        /**
         * Asks for access to the user's microphone if not granted yet, then
         * starts recording and defines the resulting audio stream as the source
         * of the audio element in order to play the audio feedback.
         */
        async enableMicrophone() {
            if (!this.doesBrowserSupportMediaDevices) {
                return;
            }
            try {
                const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.update({ audioStream });
                this.audioRef.el.srcObject = this.audioStream;
            } catch {
                // TODO: display popup asking the user to re-enable their mic
            }
        },
        /**
         * Asks for access to the user's video device if not granted yet, then
         * starts recording and defines the resulting video stream as the source
         * of the video element in order to display the video feedback.
         */
        async enableVideo() {
            if (!this.doesBrowserSupportMediaDevices) {
                return;
            }
            try {
                const videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
                this.update({ videoStream });
                this.videoRef.el.srcObject = this.videoStream;
            } catch {
                // TODO: display popup asking the user to re-enable their camera
            }
        },
        /**
         * Handles click on the "disable microphone" button.
         */
        onClickDisableMicrophoneButton() {
            this.disableMicrophone();
        },
        /**
         * Handles click on the "disable video" button.
         */
        onClickDisableVideoButton() {
            this.disableVideo();
        },
        /**
         * Handles click on the "enable microphone" button.
         */
        onClickEnableMicrophoneButton() {
            this.enableMicrophone();
        },
        /**
         * Handles click on the "enable video" button.
         */
        onClickEnableVideoButton() {
            this.enableVideo();
        },
        /**
         * Iterates tracks of the provided MediaStream, calling the `stop`
         * method on each of them.
         *
         * @param {MediaStream} mediaStream
         */
        stopTracksOnMediaStream(mediaStream) {
            for (const track of mediaStream.getTracks()) {
                track.stop();
            }
        },
    },
    fields: {
        /**
         * Ref to the audio element used for the audio feedback.
         */
        audioRef: attr(),
        /**
         * The MediaStream from the microphone.
         *
         * Default set to null to be consistent with the default value of
         * `HTMLMediaElement.srcObject`.
         */
        audioStream: attr({
            default: null,
        }),
        /**
         * States whether the browser has the required APIs for
         * microphone/camera recording.
         */
        doesBrowserSupportMediaDevices: attr({
            compute() {
                return Boolean(
                    navigator.mediaDevices &&
                    navigator.mediaDevices.getUserMedia &&
                    window.MediaStream
                );
            },
        }),
        /**
         * States if the user's microphone is currently recording.
         */
        isMicrophoneEnabled: attr({
            compute() {
                return this.audioStream !== null;
            },
        }),
        /**
         * States if the user's camera is currently recording.
         */
        isVideoEnabled: attr({
            compute() {
                return this.videoStream !== null;
            },
        }),
        /**
         * Ref to the video element used for the video feedback.
         */
        videoRef: attr(),
        /**
         * The MediaStream from the camera.
         *
         * Default set to null to be consistent with the default value of
         * `HTMLMediaElement.srcObject`.
         */
        videoStream: attr({
            default: null,
        }),
        /**
         * States the welcome view containing this media preview.
         */
        welcomeView: one('WelcomeView', {
            identifying: true,
            inverse: 'callDemoView',
        }),
    },
});
