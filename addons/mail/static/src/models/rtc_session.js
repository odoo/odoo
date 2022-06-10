/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'RtcSession',
    identifyingFields: ['id'],
    lifecycleHooks: {
        _willDelete() {
            this.reset();
        },
    },
    recordMethods: {
        onBroadcastTimeout() {
            this.messaging.rpc(
                {
                    route: '/mail/rtc/session/update_and_broadcast',
                    params: {
                        session_id: this.id,
                        values: {
                            is_camera_on: this.isCameraOn,
                            is_deaf: this.isDeaf,
                            is_muted: this.isSelfMuted,
                            is_screen_sharing_on: this.isScreenSharingOn,
                        },
                    },
                },
                { shadow: true },
            );
        },
        /**
         * restores the session to its default values
         */
        reset() {
            this.messaging.browser.clearTimeout(this.connectionRecoveryTimeout);
            this._removeAudio();
            this.removeVideo();
            this.update({
                audioElement: clear(),
                broadcastTimer: clear(),
                connectionRecoveryTimeout: clear(),
                isTalking: clear(),
                localCandidateType: clear(),
                remoteCandidateType: clear(),
            });
        },
        /**
         * cleanly removes the video stream of the session
         */
        removeVideo() {
            if (this.videoStream) {
                for (const track of this.videoStream.getTracks() || []) {
                    track.stop();
                }
            }
            this.update({
                videoStream: clear(),
            });
        },
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
            if (this.isOwnSession) {
                return;
            }
            if (this.partner && this.partner.volumeSetting) {
                this.partner.volumeSetting.update({ volume });
            }
            if (this.guest && this.guest.volumeSetting) {
                this.guest.volumeSetting.update({ volume });
            }
            if (this.messaging.isCurrentUserGuest) {
                return;
            }
            this.messaging.userSetting.saveVolumeSetting({
                partnerId: this.partner && this.partner.id,
                guestId: this.guest && this.guest.id,
                volume,
            });
        },
        /**
         * Toggles the deaf state of the current session, this must be a session
         * of the current partner.
         */
        async toggleDeaf() {
            if (!this.rtcAsCurrentSession) {
                return;
            }
            if (this.messaging.rtc.currentRtcSession.isDeaf) {
                await this.messaging.rtc.undeafen();
            } else {
                await this.messaging.rtc.deafen();
            }
        },
        /**
         * updates the record and notifies the server of the change
         *
         * @param {Object} data
         */
        updateAndBroadcast(data) {
            if (!this.rtcAsCurrentSession) {
                return;
            }
            const data2 = Object.assign({}, data, { broadcastTimer: [clear(), insertAndReplace()] });
            this.update(data2);
        },
        /**
         * Updates the rtcSession with information on the type of candidate used
         * to establish the connections.
         *
         * @private
         */
        async updateConnectionTypes() {
            if (!this.rtcPeerConnection) {
                return;
            }
            const stats = await this.rtcPeerConnection.peerConnection.getStats();
            for (const { localCandidateId, remoteCandidateId, state, type } of stats.values()) {
                if (type === 'candidate-pair' && state === 'succeeded' && localCandidateId) {
                    const localCandidate = stats.get(localCandidateId);
                    const remoteCandidate = stats.get(remoteCandidateId);
                    this.update({
                        localCandidateType: localCandidate ? localCandidate.candidateType : clear(),
                        remoteCandidateType: remoteCandidate ? remoteCandidate.candidateType : clear(),
                    });
                    return;
                }
            }
            this.update({
                localCandidateType: clear(),
                remoteCandidateType: clear(),
            });
        },
        /**
         * Updates the RtcSession with a new track.
         *
         * @param {Track} [track]
         */
        updateStream(track) {
            const stream = new window.MediaStream();
            stream.addTrack(track);

            if (track.kind === 'audio') {
                this._setAudio({
                    audioStream: stream,
                    isSelfMuted: false,
                    isTalking: false,
                });
            }
            if (track.kind === 'video') {
                this.update({ videoStream: stream });
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            if (!this.channel) {
                return;
            }
            if (this.partner) {
                return `/mail/channel/${this.channel.id}/partner/${this.partner.id}/avatar_128`;
            }
            if (this.guest) {
                return `/mail/channel/${this.channel.id}/guest/${this.guest.id}/avatar_128?unique=${this.guest.name}`;
            }
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsMute() {
            return this.isSelfMuted || this.isDeaf;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsOwnSession() {
            if (!this.messaging) {
                return;
            }
            return (this.partner && this.messaging.currentPartner === this.partner) ||
                (this.guest && this.messaging.currentGuest === this.guest);
        },
        /**
         * Updates the track that is broadcasted to the remote of this session.
         * This will start new transaction by triggering a negotiationneeded event
         * on the peerConnection given as parameter.
         *
         * negotiationneeded -> offer -> answer -> ...
         *
         * @param {String} trackKind
         * @param {Object} [param1]
         * @param {boolean} [param1.initTransceiver]
         */
        async updateRemoteTrack(trackKind, { initTransceiver } = {}) {
            if (!this.rtcAsConnectedSession) {
                return;
            }
            const track = trackKind === 'audio' ? this.rtcAsConnectedSession.audioTrack : this.rtcAsConnectedSession.videoTrack;
            let transceiverDirection = track ? 'sendrecv' : 'recvonly';
            if (trackKind === 'video' && !this.rtcPeerConnection.acceptsVideoStream) {
                transceiverDirection = track ? 'sendonly' : 'inactive';
            }
            let transceiver;
            if (initTransceiver) {
                transceiver = this.rtcPeerConnection.peerConnection.addTransceiver(trackKind);
            } else {
                transceiver = this.rtcPeerConnection.getTransceiver(trackKind);
            }
            if (track) {
                try {
                    await transceiver.sender.replaceTrack(track);
                    transceiver.direction = transceiverDirection;
                } catch (_e) {
                    // ignored, the track is probably already on the peerConnection.
                }
                return;
            }
            try {
                await transceiver.sender.replaceTrack(null);
                transceiver.direction = transceiverDirection;
            } catch (_e) {
                // ignored, the transceiver is probably already removed
            }
            if (trackKind === 'video') {
                this.rtcAsConnectedSession.notifyPeers([this.id], {
                    event: 'trackChange',
                    type: 'peerToPeer',
                    payload: {
                        type: 'video',
                        state: { isSendingVideo: false },
                    },
                });
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (this.partner) {
                return this.partner.name;
            }
            if (this.guest) {
                return this.guest.name;
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeRtcAsConnectedSession() {
            if (!this.messaging || !this.messaging.rtc) {
                return clear();
            }
            if (this.rtcPeerConnection) {
                return replace(this.messaging.rtc);
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computePeerToken() {
            return String(this.id);
        },
        /**
         * @private
         * @returns {number} float
         */
        _computeVolume() {
            if (this.partner && this.partner.volumeSetting) {
                return this.partner.volumeSetting.volume;
            } else if (this.guest && this.guest.volumeSetting) {
                return this.guest.volumeSetting.volume;
            }
            if (this.audioElement) {
                return this.audioElement.volume;
            }
        },
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
                try {
                    this.audioElement.srcObject = undefined;
                } catch (_error) {
                    // ignore error during remove, the value will be overwritten at next usage anyway
                }
            }
            this.update({
                audioStream: clear(),
                isAudioInError: false,
            });
        },
        /**
         * @private
         * @param {Object} param0
         * @param {MediaStream} param0.audioStream
         * @param {boolean} param0.isSelfMuted
         * @param {boolean} param0.isTalking
         */
        async _setAudio({ audioStream, isSelfMuted, isTalking }) {
            const audioElement = this.audioElement || new window.Audio();
            try {
                audioElement.srcObject = audioStream;
            } catch (error) {
                this.update({ isAudioInError: true });
                console.error(error);
            }
            audioElement.load();
            if (this.partner && this.partner.volumeSetting) {
                audioElement.volume = this.partner.volumeSetting.volume;
            } else if (this.guest && this.guest.volumeSetting) {
                audioElement.volume = this.guest.volumeSetting.volume;
            } else {
                audioElement.volume = this.volume;
            }
            audioElement.muted = this.messaging.rtc.currentRtcSession.isDeaf;
            // Using both autoplay and play() as safari may prevent play() outside of user interactions
            // while some browsers may not support or block autoplay.
            audioElement.autoplay = true;
            this.update({
                audioElement,
                audioStream,
                isSelfMuted,
                isTalking,
            });
            try {
                await audioElement.play();
                if (!this.exists()) {
                    return;
                }
                this.update({ isAudioInError: false });
            } catch (error) {
                if (typeof error === 'object' && error.name === 'NotAllowedError') {
                    // Ignored as some browsers may reject play() calls that do not
                    // originate from a user input.
                    return;
                }
                if (this.exists()) {
                    this.update({ isAudioInError: true });
                }
                console.error(error);
            }
        },
    },
    fields: {
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
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        broadcastTimer: one('Timer', {
            inverse: 'rtcSessionOwnerAsBroadcast',
            isCausal: true,
        }),
        /**
         * The mail.channel of the session, rtc sessions are part and managed by
         * mail.channel
         */
        channel: one('Thread', {
            inverse: 'rtcSessions',
        }),
        connectionRecoveryTimeout: attr(),
        /**
         * State of the connection with this session, uses RTCPeerConnection.iceConnectionState
         * once a peerConnection has been initialized.
         */
        connectionState: attr({
            default: 'Waiting for the peer to send a RTC offer',
        }),
        guest: one('Guest', {
            inverse: 'rtcSessions',
        }),
        /**
         * Id of the record on the server.
         */
        id: attr({
            readonly: true,
            required: true,
        }),
        /**
         * Channels on which this session is inviting the current partner,
         * this serves as an explicit inverse as it seems to confuse it with
         * other session-channel relations otherwise.
         */
        calledChannels: many('Thread', {
            inverse: 'rtcInvitingSession',
        }),
        /**
         * The participant cards of this session,
         * this is used to know how many views are displaying this session.
         */
        callParticipantCards: many('CallParticipantCard', {
            inverse: 'rtcSession',
            isCausal: true,
        }),
        /**
         * States whether there is currently an error with the audio element.
         */
        isAudioInError: attr({
            default: false,
        }),
        /**
         * Determines if the user is broadcasting a video from a user device (camera).
         */
        isCameraOn: attr({
            default: false,
        }),
        /**
         * States whether the current user/guest has initiated the RTC session connection offer.
         * Useful when attempting to recover a failed peer connection by
         * inverting the connection offer direction.
         */
        isCurrentUserInitiatorOfConnectionOffer: attr({
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
        isSelfMuted: attr({
            default: false,
        }),
        /**
         * Determine whether current session is unable to speak.
         */
        isMute: attr({
            compute: '_computeIsMute',
            default: false,
        }),
        /**
         * Determines if the session is a session of the current partner.
         * This can be true for many sessions, as one user can have multiple
         * sessions active across several tabs, browsers and devices.
         * To determine if this session is the active session of this tab,
         * use this.rtcAsCurrentSession instead.
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
         * RTCIceCandidate.type String
         */
        localCandidateType: attr(),
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
        partner: one('Partner', {
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
         * RTCIceCandidate.type String
         */
        remoteCandidateType: attr(),
        /**
         * If set, this session is the session of the current user and is in the active RTC call.
         * This information is distinct from this.isOwnSession as there can be other
         * sessions from other channels with the same partner (sessions opened from different
         * tabs or devices).
         */
        rtcAsCurrentSession: one('Rtc', {
            inverse: 'currentRtcSession',
        }),
        rtcAsConnectedSession: one('Rtc', {
            compute: '_computeRtcAsConnectedSession',
            inverse: 'connectedRtcSessions',
        }),
        rtcPeerConnection: one('RtcPeerConnection', {
            inverse: 'rtcSession',
            isCausal: true,
        }),
        /**
         * Contains the RTCDataChannel of the rtc session.
         */
        rtcDataChannel: one('RtcDataChannel', {
            inverse: 'rtcSession',
            isCausal: true,
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
            default: 0.5,
            compute: '_computeVolume',
        }),
    },
});
