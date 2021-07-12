/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

function factory(dependencies) {

    class RtcSession extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            const res = super._created(...arguments);
            this._timeoutId = undefined;
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            this.reset();
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('is_camera_on' in data) {
                data2.isCameraOn = data.is_camera_on;
            }
            if ('is_deaf' in data) {
                data2.isDeaf = data.is_deaf;
            }
            if ('is_muted' in data) {
                data2.isMuted = data.is_muted;
            }
            if ('is_screen_sharing_on' in data) {
                data2.isScreenSharingOn = data.is_screen_sharing_on;
            }

            // relations
            if ('partner' in data) {
                data2.partner = insert(data.partner);
            }
            if ('channel' in data) {
                data2.channel = insert(data.channel);
            }
            return data2;
        }

        /**
         * Notifies the server that this session is still in active usage
         * to prevent garbage collection.
         */
        async pingServer() {
            if (!this.mailRtc) {
                return;
            }
            await await this.async(() => this.env.services.rpc({
                model: 'mail.rtc.session',
                method: 'ping',
                args: [[this.id]],
            }, { shadow: true }));
        }

        /**
         * restores the session to its default values
         */
        reset() {
            this._timeoutId && browser.clearTimeout(this._timeoutId);
            this._removeAudio();
            this.removeVideo();
            this.update({
                audioElement: clear(),
                isTalking: clear(),
            });
        }

        /**
         * cleanly removes the video stream of the session
         *
         * @param {Object} [param0]
         * @param {Object} [param0.stopTracks] true if tracks have to be stopped,
         * it is optional as tracks can be removed but still necessary for transceivers.
         */
        removeVideo({ stopTracks = true } = {}) {
            if (this.videoStream && stopTracks) {
                for (const track of this.videoStream.getTracks() || []) {
                    track.stop();
                }
            }
            this.update({
                videoStream: clear(),
            });
        }

        /**
         * @param {Object} param0
         * @param {MediaStream} param0.audioStream
         * @param {boolean} param0.isMuted
         * @param {boolean} param0.isTalking
         */
        setAudio({ audioStream, isMuted, isTalking }) {
            this._removeAudio();
            const audioElement = this.audioElement || new window.Audio();
            audioElement.srcObject = audioStream;
            audioElement.volume = this.partner && this.partner.volumeSetting ? this.partner.volumeSetting.volume : 1;
            audioElement.muted = this.messaging.mailRtc.currentRtcSession.isDeaf;
            audioElement.play();
            this.update({
                audioElement,
                audioStream,
                isMuted,
                isTalking,
            });
        }

        /**
         * @param {number} volume
         */
        setVolume(volume) {
            /**
             * Manually updating the volume field as it will not update based on
             * the change of the volume property of the audioElement alone.
             */
            this.update({ volume });
            if (this.audioElement) {
                this.audioElement.volume = volume;
            }
            if (!this.partner || this.isOwnSession) {
                return;
            }
            if (this.partner.volumeSetting) {
                this.partner.volumeSetting.update({ volume });
            }
            this.messaging.userSetting.saveVolumeSetting(this.partner.id, volume);
        }

        /**
         * Toggles the deaf state of the current session, this must be a session
         * of the current partner.
         */
        async toggleDeaf() {
            if (!this.mailRtc) {
                return;
            }
            this.updateAndBroadcast({
                isDeaf: !this.isDeaf,
            });
            for (const session of this.messaging.models['mail.rtc_session'].all()) {
                if (!session.audioElement) {
                    continue;
                }
                session.audioElement.muted = this.isDeaf;
            }
            if (this.channel.mailRtc) {
                /**
                 * Ensures that the state of the microphone matches the deaf state
                 * and notifies peers.
                 */
                await this.async(() => this.channel.mailRtc.toggleMicrophone({
                    requestAudioDevice: false,
                }));
            }
        }

        /**
         * updates the record and notifies the server of the change
         *
         * @param {Object} data
         */
        updateAndBroadcast(data) {
            if (!this.mailRtc) {
                return;
            }
            this.update(data);
            this._debounce(async () => {
                await this.async(() => {
                    this.env.services.rpc(
                        {
                            model: "mail.rtc.session",
                            method: "update_and_broadcast",
                            args: [
                                [this.id],
                                {
                                    is_camera_on: this.isCameraOn,
                                    is_deaf: this.isDeaf,
                                    is_muted: this.isMuted,
                                    is_screen_sharing_on: this.isScreenSharingOn,
                                },
                            ],
                        },
                        { shadow: true }
                    );
                });
            }, 3000);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarSrc() {
            return this.partner ? `/web/image/res.partner/${this.partner.id}/avatar_128` : '';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsOwnSession() {
            return this.messaging && this.messaging.currentPartner === this.partner;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            return this.partner ? this.partner.name : '';
        }

        /**
         * @private
         * @returns {string}
         */
        _computePeerToken() {
            return String(this.id);
        }

        /**
         * @private
         * @returns {number} float
         */
        _computeVolume() {
            if (this.partner && this.partner.volumeSetting) {
                return this.partner.volumeSetting.volume;
            }
            if (this.audioElement) {
                return this.audioElement.volume;
            }
            return 1;
        }

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         */
        _debounce(f, delay) {
            this._timeoutId && browser.clearTimeout(this._timeoutId);
            this._timeoutId = browser.setTimeout(() => {
                if (!this.exists()) {
                    return;
                }
                f();
            }, delay);
        }

        /**
         * cleanly removes the audio stream of the session
         *
         * @private
         */
        _removeAudio() {
            if (this.audioStream) {
                for (const track of this.audioStream.getTracks() || []) {
                    track.stop();
                }
            }
            if (this.audioElement) {
                this.audioElement.pause();
                this.audioElement.srcObject = undefined;
            }
            this.update({
                audioStream: clear(),
            });
        }

    }

    RtcSession.fields = {
        /**
         * HTMLAudioElement that plays and control the audioStream of the user,
         * it is not mounted on the DOM as it can operate from the JS.
         */
        audioElement: attr(),
        /**
         * MediaStream
         */
        audioStream: attr(),
        /**
         * The relative url of the image that represents the session.
         */
        avatarSrc: attr({
            compute: '_computeAvatarSrc',
        }),
        /**
         * The mail.channel of the session, rtc sessions are part and managed by
         * mail.channel
         */
        channel: many2one('mail.thread', {
            inverse: 'rtcSessions',
            required: true,
        }),
        /**
         * State of the connection with this session, uses RTCPeerConnection.iceConnectionState
         * once a peerConnection has been initialized.
         */
        connectionState: attr({
            default: 'Waiting for the peer to send a RTC offer',
        }),
        /**
         * Id of the record on the server.
         */
        id: attr({
            required: true,
        }),
        /**
         * Determines if the user is broadcasting a video from a user device (camera).
         */
        isCameraOn: attr({
            default: false,
        }),
        /**
         * Determines if the user is deafened, which means that all incoming
         * audio tracks are disabled.
         */
        isDeaf: attr({
            default: false,
        }),
        /**
         * Determines if the user's microphone is in a muted state, which
         * means that they cannot send sound regardless of the push to talk or
         * voice activation (isTalking) state.
         */
        isMuted: attr({
            default: false,
        }),
        /**
         * Determines if the session is a session of the current partner.
         * This can be true for many sessions, as one user can have multiple
         * sessions active across several tabs, browsers and devices.
         * To determine if this session is the active session of this tab,
         * use this.mailRtc instead.
         */
        isOwnSession: attr({
            compute: '_computeIsOwnSession',
        }),
        /**
         * Determines if the user is sharing their screen.
         */
        isScreenSharingOn: attr({
            default: false,
        }),
        /**
         * Determines if the user is currently talking, which is based on
         * voice activation or push to talk.
         */
        isTalking: attr({
            default: false,
        }),
        /**
         * If set, this session is the session of the current user and is in the active RTC call.
         * This information is distinct from this.isOwnSession as there can be other
         * sessions from other channels with the same partner (sessions opened from different
         * tabs or devices).
         */
        mailRtc: one2one('mail.rtc', {
            inverse: 'currentRtcSession',
        }),
        /**
         * Name of the session, based on the partner name if set.
         */
        name: attr({
            compute: '_computeName',
        }),
        /**
         * If set, the partner who owns this rtc session,
         * there can be multiple rtc sessions per partner if the partner
         * has open sessions in multiple channels, but only one session per
         * channel is allowed.
         */
        partner: many2one('mail.partner', {
            inverse: 'rtcSessions',
        }),
        /**
         * Token to identify the session, it is currently just the toString
         * id of the record.
         */
        peerToken: attr({
            compute: '_computePeerToken',
        }),
        /**
         * MediaStream of the user's video.
         *
         * Should be divided into userVideoStream and displayStream,
         * once we allow both share and cam feeds simultaneously.
         */
        videoStream: attr(),
        /**
         * The volume of the audio played from this session.
         */
        volume: attr({
            compute: '_computeVolume',
        }),
    };

    RtcSession.modelName = 'mail.rtc_session';

    return RtcSession;
}

registerNewModel('mail.rtc_session', factory);
