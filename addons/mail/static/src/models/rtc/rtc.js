/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2many, one2one } from '@mail/model/model_field';
import { clear, insert, unlink } from '@mail/model/model_field_command';

import { monitorAudio } from '@mail/utils/media_monitoring/media_monitoring';

/**
 * The order in which transceivers are added, relevant for RTCPeerConnection.getTransceivers which returns
 * transceivers in insertion order as per webRTC specifications.
 */
const TRANSCEIVER_ORDER = ['audio', 'video'];

function factory(dependencies) {

    const getRTCPeerNotificationNextTemporaryId = (function () {
        let tmpId = 0;
        return () => {
            tmpId += 1;
            return tmpId;
        };
    })();

    class Rtc extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            // technical fields that are not exposed
            // Especially important for _peerConnections, as garbage collection of peerConnections is important for
            // peerConnection.close().
            /**
             * Object { token: dataChannel<RTCDataChannel> }
             * Contains the RTCDataChannels with the other rtc sessions.
             */
            this._dataChannels = {};
            /**
             * callback to properly end the audio monitoring.
             * If set it indicates that we are currently monitoring the local
             * audioTrack for the voice activation feature.
             */
            this._disconnectAudioMonitor = undefined;
            /**
             * Object { token: timeoutId<Number> }
             * Contains the timeoutIds of the reconnection attempts.
             */
            this._fallBackTimeouts = {};
            /**
             * Set of peerTokens, used to track which calls are outgoing,
             * which is used when attempting to recover a failed peer connection by
             * inverting the call direction.
             */
            this._outGoingCallTokens = new Set();
             /**
             * Object { token: peerConnection<RTCPeerConnection> }
             * Contains the RTCPeerConnection established with the other rtc sessions.
             * Exposing this field and keeping references to closed peer connections may lead
             * to difficulties reconnecting to the same peer.
             */
            this._peerConnections = {};
            /**
             *  timeoutId for the push to talk release delay.
             */
            this._pushToTalkTimeoutId = undefined;

            this._onKeyDown = this._onKeyDown.bind(this);
            this._onKeyUp = this._onKeyUp.bind(this);
            browser.addEventListener('keydown', this._onKeyDown);
            browser.addEventListener('keyup', this._onKeyUp);
            // Disconnects the RTC session if the page is closed or reloaded.
            this._onBeforeUnload = this._onBeforeUnload.bind(this);
            browser.addEventListener('beforeunload', this._onBeforeUnload);
            /**
             * Call all sessions for which no peerConnection is established at
             * a regular interval to try to recover any connection that failed
             * to start.
             *
             * This is distinct from this._recoverConnection which tries to restores
             * connection that were established but failed or timed out.
             */
            this._intervalId = browser.setInterval(async () => {
                if (!this.currentRtcSession || !this.channel) {
                    return;
                }
                await this._pingServer();
                if (!this.currentRtcSession || !this.channel) {
                    return;
                }
                this._callSessions();
            }, 30000); // 30 seconds
        }

        /**
         * @override
         */
        async _willDelete() {
            browser.removeEventListener('beforeunload', this._onBeforeUnload);
            browser.removeEventListener('keydown', this._onKeyDown);
            browser.removeEventListener('keyup', this._onKeyUp);
            browser.clearInterval(this._intervalId);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Removes and disconnects all the peerConnections that are not current members of the call.
         *
         * @param {mail.rtc_session[]} currentSessions list of sessions of this call.
         */
        async filterCallees(currentSessions) {
            const currentSessionsTokens = new Set(currentSessions.map(session => session.peerToken));
            for (const token of Object.keys(this._peerConnections)) {
                if (!currentSessionsTokens.has(token)) {
                    this._addLogEntry(token, 'session removed from the server');
                    this._removePeer(token);
                }
            }
            if (this.channel && this.currentRtcSession && !currentSessionsTokens.has(this.currentRtcSession.peerToken)) {
                // if the current RTC session is not in the channel sessions, this call is no longer valid.
                this.channel.endCall();
            }
        }

        /**
         * @param {array} [allowedTokens] tokens of the peerConnections for which
         * the incoming video traffic is allowed. If undefined, all traffic is
         * allowed.
         */
        filterIncomingVideoTraffic(allowedTokens) {
            const tokenSet = new Set(allowedTokens);
            for (const [token, peerConnection] of Object.entries(this._peerConnections)) {
                const fullDirection = this.videoTrack ? 'sendrecv' : 'recvonly';
                const limitedDirection = this.videoTrack ? 'sendonly' : 'inactive';
                const transceiver = this._getTransceiver(peerConnection, 'video');
                if (!transceiver) {
                    continue;
                }
                if (!tokenSet.size || tokenSet.has(token)) {
                    transceiver.direction = fullDirection;
                } else {
                    transceiver.direction = limitedDirection;
                }
            }
        }

        /**
         * @param {number|String} sender id of the session that sent the notification
         * @param {String} content JSON
         */
        async handleNotification(sender, content) {
            const { event, channelId, payload } = JSON.parse(content);
            const rtcSession = this.messaging.models['mail.rtc_session'].findFromIdentifyingData({ id: sender });
            if (!rtcSession || rtcSession.channel !== this.channel) {
                // does handle notifications targeting a different session
                return;
            }
            if (!this.isClientRtcCompatible) {
                return;
            }
            if (!this._peerConnections[sender] && (!channelId || !this.channel || channelId !== this.channel.id)) {
                return;
            }
            switch (event) {
                case "offer":
                    this._addLogEntry(sender, `received notification: ${event}`, { step: 'received offer' });
                    await this._handleRtcTransactionOffer(rtcSession.peerToken, payload);
                    break;
                case "answer":
                    this._addLogEntry(sender, `received notification: ${event}`, { step: 'received answer' });
                    await this._handleRtcTransactionAnswer(rtcSession.peerToken, payload);
                    break;
                case "ice-candidate":
                    await this._handleRtcTransactionICECandidate(rtcSession.peerToken, payload);
                    break;
                case "disconnect":
                    this._addLogEntry(sender, `received notification: ${event}`, { step: ' peer cleanly disconnected ' });
                    this._removePeer(rtcSession.peerToken);
                    break;
                case 'trackChange':
                    this._handleTrackChange(rtcSession, payload);
                    break;
            }
        }

        /**
         * @param {Object} param0
         * @param {string} param0.currentSessionId the Id of the 'mail.rtc_session'
                  of the current partner for the current call
         * @param {Array<Object>} [param0.iceServers]
         * @param {boolean} [param0.startWithAudio]
         * @param {boolean} [param0.startWithVideo]
         * @param {'user-video'|'display'} [param0.videoType] 'user-video' or 'display'
         */
        async initSession({ currentSessionId, iceServers, startWithAudio, startWithVideo, videoType = 'user-video' }) {
            // Initializing a new session implies closing the current session.
            this.reset();
            this.update({
                currentRtcSession: insert({ id: currentSessionId }),
                iceServers: iceServers || this.iceServers,
            });

            await this._callSessions();
            await this.updateLocalAudioTrack(startWithAudio);
            if (startWithVideo) {
                await this._toggleVideoBroadcast({ type: videoType });
            }
        }

        /**
         * Resets the state of the model and cleanly ends all connections and
         * streams.
         *
         * @private
         */
        reset() {
            if (this._peerConnections) {
                const peerTokens = Object.keys(this._peerConnections);
                for (const token of peerTokens) {
                    this._removePeer(token);
                }
            }

            this._disconnectAudioMonitor && this._disconnectAudioMonitor();
            this.audioTrack && this.audioTrack.stop();
            this.videoTrack && this.videoTrack.stop();

            this._disconnectAudioMonitor = undefined;
            this._dataChannels = {};
            this._fallBackTimeouts = {};
            this._outGoingCallTokens = new Set();
            this._peerConnections = {};

            this.update({
                currentRtcSession: clear(),
                logs: clear(),
                sendUserVideo: clear(),
                sendDisplay: clear(),
                videoTrack: clear(),
                audioTrack: clear(),
            });
        }

        /**
         * Mutes and unmutes the microphone, will not unmute if deaf.
         *
         * @param {Object} [param0]
         * @param {string} [param0.requestAudioDevice] true if requesting the audio input device
         *                 from the user
         */
        async toggleMicrophone({ requestAudioDevice = true } = {}) {
            const shouldMute = this.currentRtcSession.isDeaf || !this.currentRtcSession.isMuted;
            this.currentRtcSession.updateAndBroadcast({ isMuted: shouldMute || !this.audioTrack });
            if (!this.audioTrack && !shouldMute && requestAudioDevice) {
                // if we don't have an audioTrack, we try to request it again
                await this.updateLocalAudioTrack(true);
            }
            await this.async(() => this._updateLocalAudioTrackEnabledState());
        }

        /**
         * toggles screen broadcasting to peers.
         */
        async toggleScreenShare() {
            this._toggleVideoBroadcast({ type: 'display' });
        }

        /**
         * Toggles user video (eg: webcam) broadcasting to peers.
         */
        async toggleUserVideo() {
            this._toggleVideoBroadcast({ type: 'user-video' });
        }

        /**
         * @param {Boolean} audio
         */
        async updateLocalAudioTrack(audio) {
            if (this.audioTrack) {
                this.audioTrack.stop();
            }
            this.update({ audioTrack: clear() });
            if (!this.channel) {
                return;
            }
            if (audio) {
                let audioTrack;
                try {
                    const audioStream = await browser.navigator.mediaDevices.getUserMedia({ audio: this.messaging.userSetting.getAudioConstraints() });
                    audioTrack = audioStream.getAudioTracks()[0];
                } catch (e) {
                    this.env.services.notification.notify({
                        message: _.str.sprintf(
                            this.env._t(`"%s" requires microphone access`),
                            window.location.host,
                        ),
                        type: 'warning',
                    });
                    if (this.currentRtcSession) {
                        this.currentRtcSession.updateAndBroadcast({ isMuted: true });
                    }
                    return;
                }
                if (!this.currentRtcSession) {
                    // The getUserMedia promise could resolve when the call is ended
                    // in which case the track is no longer relevant.
                    audioTrack.stop();
                    return;
                }
                audioTrack.addEventListener('ended', async () => {
                    // this mostly happens when the user retracts microphone permission.
                    await this.async(() => this.updateLocalAudioTrack(false));
                    this.currentRtcSession.updateAndBroadcast({ isMuted: true });
                    await this.async(() => this._updateLocalAudioTrackEnabledState());
                });
                this.currentRtcSession.updateAndBroadcast({ isMuted: false });
                audioTrack.enabled = !this.currentRtcSession.isMuted && this.currentRtcSession.isTalking;
                this.update({ audioTrack });
                await this.async(() => this.updateVoiceActivation());
                for (const [token, peerConnection] of Object.entries(this._peerConnections)) {
                    await this._updateRemoteTrack(peerConnection, 'audio', { token });
                }
            }
        }

        /**
         * @param {MediaTrackConstraints Object} constraints
         */
        updateVideoConfig(constraints) {
            const videoConfig = Object.assign(this.videoConfig, constraints);
            this.update({ videoConfig });
            this.videoTrack && this.videoTrack.applyConstraints(this.videoConfig);
        }

        /**
         * Updates the way broadcast of the local audio track is handled,
         * attaches an audio monitor for voice activation if necessary.
         */
        async updateVoiceActivation() {
            this._disconnectAudioMonitor && this._disconnectAudioMonitor();
            if (this.messaging.userSetting.usePushToTalk || !this.channel || !this.audioTrack) {
                this.currentRtcSession.update({ isTalking: false });
                await this._updateLocalAudioTrackEnabledState();
                return;
            }
            try {
                this._disconnectAudioMonitor = await monitorAudio(this.audioTrack, {
                    onThreshold: async (isAboveThreshold) => {
                        this._setSoundBroadcast(isAboveThreshold);
                    },
                    volumeThreshold: this.messaging.userSetting.voiceActivationThreshold,
                });
            } catch (e) {
                /**
                 * The browser is probably missing audioContext,
                 * in that case, voice activation is not enabled
                 * and the microphone is always 'on'.
                 */
                this.env.services.notification.notify({
                    message: this.env._t("Your browser does not support voice activation"),
                    type: 'warning',
                });
                this.currentRtcSession.update({ isTalking: true });
            }
            await this._updateLocalAudioTrackEnabledState();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {String} token
         * @param {String} entry
         * @param {Object} [param2]
         * @param {Error} [param2.error]
         * @param {String} [param2.step] current step of the flow
         * @param {String} [param2.state] current state of the connection
         */
        _addLogEntry(token, entry, { error, step, state } = {}) {
            if (!this.modelManager.isDebug) {
                return;
            }
            if (!(token in this.logs)) {
                this.logs[token] = { step: '', state: '', logs: [] };
            }
            const trace = window.Error().stack || '';
            this.logs[token].logs.push({
                event: `${window.moment().format('h:mm:ss')}: ${entry}`,
                error: error && {
                    name: error.name,
                    message: error.message,
                    stack: error.stack && error.stack.split('\n'),
                },
                trace: trace.split('\n'),
            });
            if (step) {
                this.logs[token].step = step;
            }
            if (state) {
                this.logs[token].state = state;
            }
        }

        /**
         * @private
         * @param {String} token
         */
        async _callPeer(token) {
            const peerConnection = this._createPeerConnection(token);
            for (const trackKind of TRANSCEIVER_ORDER) {
                await this._updateRemoteTrack(peerConnection, trackKind, { initTransceiver: true, token });
            }
            this._outGoingCallTokens.add(token);
        }

        /**
         * Call all the sessions that do not have an already initialized peerConnection.
         *
         * @private
         */
        _callSessions() {
            if (!this.channel.rtcSessions) {
                return;
            }
            for (const session of this.channel.rtcSessions) {
                if (session.peerToken in this._peerConnections) {
                    continue;
                }
                if (session === this.currentRtcSession) {
                    continue;
                }
                session.update({
                    connectionState: 'Not connected: sending initial RTC offer',
                });
                this._addLogEntry(session.peerToken, 'init call', { step: 'init call' });
                this._callPeer(session.peerToken);
            }
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsClientRtcCompatible() {
            return window.RTCPeerConnection && window.MediaStream;
        }

        /**
         * Creates and setup a RTCPeerConnection.
         *
         * @private
         * @param {String} token
         */
        _createPeerConnection(token) {
            const peerConnection = new window.RTCPeerConnection({ iceServers: this.iceServers });
            this._addLogEntry(token, `RTCPeerConnection created`, { step: 'peer connection created' });
            peerConnection.onicecandidate = async (event) => {
                if (!event.candidate) {
                    return;
                }
                await this._notifyPeers([token], {
                    event: 'ice-candidate',
                    payload: { candidate: event.candidate },
                });
            };
            peerConnection.oniceconnectionstatechange = (event) => {
                this._onICEConnectionStateChange(peerConnection.iceConnectionState, token);
            };
            peerConnection.onconnectionstatechange = (event) => {
                this._onConnectionStateChange(peerConnection.connectionState, token);
            };
            peerConnection.onicecandidateerror = async (error) => {
                this._addLogEntry(token, `ice candidate error`);
                this._recoverConnection(token, { delay: this.recoveryTimeout, reason: 'ice candidate error' });
            };
            peerConnection.onnegotiationneeded = async (event) => {
                const offer = await peerConnection.createOffer();
                try {
                    await peerConnection.setLocalDescription(offer);
                } catch (e) {
                    // Possibly already have a remote offer here: cannot set local description
                    this._addLogEntry(token, `couldn't setLocalDescription`, { error: e });
                    return;
                }
                this._addLogEntry(token, `sending notification: offer`, { step: 'sending offer' });
                await this._notifyPeers([token], {
                    event: 'offer',
                    payload: { sdp: peerConnection.localDescription },
                });
            };
            peerConnection.ontrack = ({ transceiver, track }) => {
                this._addLogEntry(token, `received ${track.kind} track`);
                this._updateExternalSessionTrack(track, token);
            };
            const dataChannel = peerConnection.createDataChannel("notifications", { negotiated: true, id: 1 });
            dataChannel.onmessage = (event) => {
                this.handleNotification(token, event.data);
            };
            dataChannel.onopen = async () => {
                /**
                 * FIXME? it appears that the track yielded by the peerConnection's 'ontrack' event is always enabled,
                 * even when it is disabled on the sender-side.
                 */
                try {
                    await this._notifyPeers([token], {
                        event: 'trackChange',
                        type: 'peerToPeer',
                        payload: {
                            type: 'audio',
                            state: { isTalking: this.currentRtcSession.isTalking, isMuted: this.currentRtcSession.isMuted },
                        },
                    });
                } catch (e) {
                    if (!(e instanceof DOMException) || e.name !== "OperationError") {
                        throw e;
                    }
                    this._addLogEntry(token, `failed to send on datachannel; dataChannelInfo: ${this._serializeRTCDataChannel(dataChannel)}`, { error: e });
                }
            };
            this._peerConnections[token] = peerConnection;
            this._dataChannels[token] = dataChannel;
            return peerConnection;
        }

        /**
         * @private
         * @param {RTCPeerConnection} peerConnection
         * @param {String} trackKind
         * @returns {RTCRtpTransceiver} the transceiver used for this trackKind.
         */
        _getTransceiver(peerConnection, trackKind) {
            const transceivers = peerConnection.getTransceivers();
            return transceivers[TRANSCEIVER_ORDER.indexOf(trackKind)];
        }

        /**
         * @private
         * @param {String} fromToken
         * @param {Object} param1
         * @param {Object} param1.sdp Session Description Protocol
         */
        async _handleRtcTransactionAnswer(fromToken, { sdp }) {
            const peerConnection = this._peerConnections[fromToken];
            if (!peerConnection || this.invalidIceConnectionStates.has(peerConnection.iceConnectionState) || peerConnection.signalingState === 'stable') {
                return;
            }
            if (peerConnection.signalingState === 'have-remote-offer') {
                // we already have an offer
                return;
            }
            const rtcSessionDescription = new window.RTCSessionDescription(sdp);
            try {
                await peerConnection.setRemoteDescription(rtcSessionDescription);
            } catch (e) {
                this._addLogEntry(fromToken, 'answer handling: Failed at setting remoteDescription', { error: e });
                // ignored the transaction may have been resolved by another concurrent offer.
            }
        }

        /**
         * @private
         * @param {String} fromToken
         * @param {Object} param1
         * @param {Object} param1.candidate RTCIceCandidateInit
         */
        async _handleRtcTransactionICECandidate(fromToken, { candidate }) {
            const peerConnection = this._peerConnections[fromToken];
            if (!peerConnection || this.invalidIceConnectionStates.has(peerConnection.iceConnectionState)) {
                return;
            }
            const rtcIceCandidate = new window.RTCIceCandidate(candidate);
            try {
                await peerConnection.addIceCandidate(rtcIceCandidate);
            } catch (error) {
                this._addLogEntry(fromToken, 'ICE candidate handling: failed at adding the candidate to the connection', { error });
                this._recoverConnection(fromToken, { delay: this.recoveryTimeout, reason: 'failed at adding ice candidate' });
            }
        }

        /**
         * @private
         * @param {String} fromToken
         * @param {Object} param1
         * @param {Object} param1.sdp Session Description Protocol
         */
        async _handleRtcTransactionOffer(fromToken, { sdp }) {
            const peerConnection = this._peerConnections[fromToken] || this._createPeerConnection(fromToken);

            if (!peerConnection || this.invalidIceConnectionStates.has(peerConnection.iceConnectionState)) {
                return;
            }
            if (peerConnection.signalingState === 'have-remote-offer') {
                // we already have an offer
                return;
            }
            const rtcSessionDescription = new window.RTCSessionDescription(sdp);
            try {
                await peerConnection.setRemoteDescription(rtcSessionDescription);
            } catch (e) {
                this._addLogEntry(fromToken, 'offer handling: failed at setting remoteDescription', { error: e });
                return;
            }
            await this._updateRemoteTrack(peerConnection, 'audio', { token: fromToken });
            await this._updateRemoteTrack(peerConnection, 'video', { token: fromToken });

            let answer;
            try {
                answer = await peerConnection.createAnswer();
            } catch (e) {
                this._addLogEntry(fromToken, 'offer handling: failed at creating answer', { error: e });
                return;
            }
            try {
                await peerConnection.setLocalDescription(answer);
            } catch (e) {
                this._addLogEntry(fromToken, 'offer handling: failed at setting localDescription', { error: e });
                return;
            }

            this._addLogEntry(fromToken, `sending notification: answer`, { step: 'sending answer' });
            await this._notifyPeers([fromToken], {
                event: 'answer',
                payload: { sdp: peerConnection.localDescription },
            });
            this._recoverConnection(fromToken, { delay: this.recoveryTimeout, reason: 'standard answer timeout' });
        }

        /**
         * @private
         * @param {mail.rtc_session} rtcSession
         * @param {Object} param1
         * @param {String} param1.type 'audio' or 'video'
         * @param {Object} param1.state
         */
        _handleTrackChange(rtcSession, { type, state }) {
            const { isMuted, isTalking, isSendingVideo, isDeaf } = state;
            if (type === 'audio') {
                if (!rtcSession.audioStream) {
                    return;
                }
                rtcSession.update({
                    isMuted,
                    isTalking,
                    isDeaf,
                });
            }
            if (type === 'video' && isSendingVideo === false) {
                /**
                 * Since WebRTC "unified plan", the local track is tied to the
                 * remote transceiver.sender and not the remote track. Therefore
                 * when the remote track is 'ended' the local track is not 'ended'
                 * but only 'muted'. This is why we do not stop the local track
                 * until the peer is completely removed.
                 */
                rtcSession.update({ videoStream: clear() });
            }
        }

        /**
         * @private
         * @param {String[]} targetToken
         * @param {Object} param1
         * @param {String} param1.event
         * @param {Object} [param1.payload]
         * @param {String} [param1.type] 'server' or 'peerToPeer',
         *                 'peerToPeer' requires an active RTCPeerConnection
         */
        async _notifyPeers(targetTokens, { event, payload, type = 'server' }) {
            if (!targetTokens.length || !this.channel || !this.currentRtcSession) {
                return;
            }
            if (type === 'server') {
                this.update({
                    peerNotificationsToSend: insert({
                        channelId: this.channel.id,
                        event,
                        id: getRTCPeerNotificationNextTemporaryId(),
                        payload,
                        senderId: this.currentRtcSession.id,
                        targetTokens
                    }),
                });
                await this._sendPeerNotifications();
            }

            if (type === 'peerToPeer') {
                for (const token of targetTokens) {
                    const dataChannel = this._dataChannels[token];
                    if (!dataChannel || dataChannel.readyState !== 'open') {
                        continue;
                    }
                    dataChannel.send(JSON.stringify({
                        event,
                        channelId: this.channel.id,
                        payload,
                    }));
                }
            }
        }

        /**
         * Pings the server to ensure this session is kept alive.
         */
        async _pingServer() {
            const channel = this.channel;
            const { rtcSessions } = await this.env.services.rpc({
                route: '/mail/channel/ping',
                params: {
                    'channel_id': channel.id,
                    'check_rtc_session_ids': channel.rtcSessions.map(rtcSession => rtcSession.id),
                    'rtc_session_id': this.currentRtcSession.id,
                },
            }, { shadow: true });
            if (channel.exists()) {
                channel.updateRtcSessions(rtcSessions);
            }
        }

        /**
         * Attempts a connection recovery by closing and restarting the call
         * from the receiving end.
         *
         * @private
         * @param {String} token
         * @param {Object} [param1]
         * @param {number} [param1.delay] in ms
         * @param {string} [param1.reason]
         */
        _recoverConnection(token, { delay = 0, reason = '' } = {}) {
            if (this._fallBackTimeouts[token]) {
                return;
            }
            this._fallBackTimeouts[token] = browser.setTimeout(async () => {
                delete this._fallBackTimeouts[token];
                const peerConnection = this._peerConnections[token];
                if (!peerConnection || !this.channel) {
                    return;
                }
                if (this._outGoingCallTokens.has(token)) {
                    return;
                }
                if (peerConnection.iceConnectionState === 'connected') {
                    return;
                }
                this._addLogEntry(token, `calling back to recover ${peerConnection.iceConnectionState} connection, reason: ${reason}`);
                await this._notifyPeers([token], {
                    event: 'disconnect',
                });
                this._removePeer(token);
                this._callPeer(token);
            }, delay);
        }

        /**
         * Cleans up a peer by closing all its associated content and the connection.
         *
         * @private
         * @param {String} token
         */
        _removePeer(token) {
            const rtcSession = this.messaging.models['mail.rtc_session'].findFromIdentifyingData({ id: token });
            if (rtcSession) {
                rtcSession.reset();
            }
            const dataChannel = this._dataChannels[token];
            if (dataChannel) {
                dataChannel.close();
            }
            delete this._dataChannels[token];
            const peerConnection = this._peerConnections[token];
            if (peerConnection) {
                this._removeRemoteTracks(peerConnection);
                peerConnection.close();
            }
            delete this._peerConnections[token];
            browser.clearTimeout(this._fallBackTimeouts[token]);
            delete this._fallBackTimeouts[token];

            this._outGoingCallTokens.delete(token);
            this._addLogEntry(token, 'peer removed', { step: 'peer removed' });
        }

        /**
         * Terminates the Transceivers of the peer connection.
         *
         * @private
         * @param {RTCPeerConnection} peerConnection
         */
        _removeRemoteTracks(peerConnection) {
            const RTCRtpSenders = peerConnection.getSenders();
            for (const sender of RTCRtpSenders) {
                try {
                    peerConnection.removeTrack(sender);
                } catch (e) {
                    // ignore error
                }
            }
            for (const transceiver of peerConnection.getTransceivers()) {
                try {
                    transceiver.stop();
                } catch (e) {
                    // transceiver may already be stopped by the remote.
                }
            }
        }

        /**
         * Sends this peer notifications to send as soon as the last pending
         * sending finishes.
         *
         * @private
         */
        async _sendPeerNotifications() {
            if (this.isNotifyPeersRPCInProgress) {
                return;
            }
            this.update({ isNotifyPeersRPCInProgress: true });
            await new Promise(resolve => setTimeout(resolve, this.peerNotificationWaitDelay));
            const peerNotifications = this.peerNotificationsToSend;
            try {
                await this.env.services.rpc({
                    route: '/mail/rtc/session/notify_call_members',
                    params: {
                        'peer_notifications': peerNotifications.map(peerNotification =>
                            [
                                peerNotification.senderId,
                                peerNotification.targetTokens,
                                JSON.stringify({
                                    event: peerNotification.event,
                                    channelId: peerNotification.channelId,
                                    payload: peerNotification.payload,
                                }),
                            ],
                        ),
                    },
                }, { shadow: true });
                if (!this.exists()) {
                    return;
                }
                this.update({ peerNotificationsToSend: unlink(peerNotifications) });
            } finally {
                if (this.exists()) {
                    this.update({ isNotifyPeersRPCInProgress: false });
                    if (this.peerNotificationsToSend.length > 0) {
                        this._sendPeerNotifications();
                    }
                }
            }
        }

        /**
         * Returns a string representation of a data channel for logging and
         * debugging purposes.
         *
         * @private
         * @param {RTCDataChannel} dataChannel
         * @returns string
         */
        _serializeRTCDataChannel(dataChannel) {
            const toLog = [
                "binaryType",
                "bufferedAmount",
                "bufferedAmountLowThreshold",
                "id",
                "label",
                "maxPacketLifeTime",
                "maxRetransmits",
                "negotiated",
                "ordered",
                "protocol",
                "readyState",
            ];
            return JSON.stringify(Object.fromEntries(toLog.map(p => [p, dataChannel[p]])));
        }

        /**
         * Updates the "isTalking" state of the current user and sets the
         * enabled state of its audio track accordingly.
         *
         * @private
         * @param {boolean} isTalking
         */
        async _setSoundBroadcast(isTalking) {
            if (!this.currentRtcSession) {
                return;
            }
            if (isTalking === this.currentRtcSession.isTalking) {
                return;
            }
            this.currentRtcSession.update({ isTalking });
            if (!this.currentRtcSession.isMuted) {
                await this._updateLocalAudioTrackEnabledState();
            }
        }

        /**
         * @private
         * @param {Object} trackOptions
         */
        async _toggleVideoBroadcast(trackOptions) {
            if (!this.channel) {
                return;
            }
            await this._toggleLocalVideoTrack(trackOptions);
            for (const [token, peerConnection] of Object.entries(this._peerConnections)) {
                await this._updateRemoteTrack(peerConnection, 'video', { token });
            }
            if (!this.currentRtcSession) {
                return;
            }
            this.currentRtcSession.updateAndBroadcast({
                isScreenSharingOn: !!this.sendDisplay,
                isCameraOn: !!this.sendUserVideo,
            });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {String} param0.type 'user-video' (eg: webcam) or 'display' (eg: screen sharing)
         * @param {boolean} [param0.force]
         */
        async _toggleLocalVideoTrack({ type, force }) {
            if (type === 'user-video') {
                const sendUserVideo = force !== undefined ? force : !this.sendUserVideo;
                await this._updateLocalVideoTrack(type, sendUserVideo);
            }
            if (type === 'display') {
                const sendDisplay = force !== undefined ? force : !this.sendDisplay;
                await this._updateLocalVideoTrack(type, sendDisplay);
            }
            if (!this.currentRtcSession) {
                return;
            }
            if (!this.videoTrack) {
                this.currentRtcSession.removeVideo();
            } else {
                this._updateExternalSessionTrack(this.videoTrack, this.currentRtcSession.peerToken);
            }
        }

        /**
         * Updates the mail.rtc_session associated to the token with a new track.
         *
         * @private
         * @param {Track} [track]
         * @param {String} token the token of video
         */
        _updateExternalSessionTrack(track, token) {
            const rtcSession = this.messaging.models['mail.rtc_session'].findFromIdentifyingData({ id: token });
            if (!rtcSession) {
                return;
            }
            const stream = new window.MediaStream();
            stream.addTrack(track);

            if (track.kind === 'audio') {
                rtcSession.setAudio({
                    audioStream: stream,
                    isMuted: false,
                    isTalking: false,
                });
            }
            if (track.kind === 'video') {
                rtcSession.update({
                    videoStream: stream,
                });
            }
        }

        /**
         * Sets the enabled property of the local audio track based on the
         * current session state. And notifies peers of the new audio state.
         *
         * @private
         */
        async _updateLocalAudioTrackEnabledState() {
            if (!this.audioTrack) {
                return;
            }
            this.audioTrack.enabled = !this.currentRtcSession.isMuted && this.currentRtcSession.isTalking;
            await this._notifyPeers(Object.keys(this._peerConnections), {
                event: 'trackChange',
                type: 'peerToPeer',
                payload: {
                    type: 'audio',
                    state: {
                        isTalking: this.currentRtcSession.isTalking && !this.currentRtcSession.isMuted,
                        isMuted: this.currentRtcSession.isMuted,
                        isDeaf: this.currentRtcSession.isDeaf,
                    },
                },
            });
        }

        /**
         * @private
         * @param {String} type 'user-video' or 'display'
         * @param {boolean} activateVideo true if we want to activate the video
         */
        async _updateLocalVideoTrack(type, activateVideo) {
            if (this.videoTrack) {
                this.videoTrack.stop();
            }
            this.update({
                sendDisplay: false,
                sendUserVideo: false,
                videoTrack: clear(),
            });
            let videoStream;
            if (!activateVideo) {
                if (type === 'display') {
                    this.messaging.soundEffects.screenSharing.play();
                }
                return;
            }
            try {
                if (type === 'user-video') {
                    videoStream = await browser.navigator.mediaDevices.getUserMedia({ video: this.videoConfig });
                }
                if (type === 'display') {
                    videoStream = await browser.navigator.mediaDevices.getDisplayMedia({ video: this.videoConfig });
                    this.messaging.soundEffects.screenSharing.play();
                }
            } catch (e) {
                this.env.services.notification.notify({
                    message: _.str.sprintf(
                        this.env._t(`"%s" requires "%s" access`),
                        window.location.host,
                        type === 'user-video' ? 'camera' : 'display',
                    ),
                    type: 'warning',
                });
                return;
            }
            const videoTrack = videoStream ? videoStream.getVideoTracks()[0] : undefined;
            if (videoTrack) {
                videoTrack.addEventListener('ended', async () => {
                    await this.async(() =>
                        this._toggleVideoBroadcast({ force: false, type })
                    );
                });
            }
            this.update({
                videoTrack,
                sendUserVideo: type === 'user-video' && !!videoTrack,
                sendDisplay: type === 'display' && !!videoTrack,
            });
        }

        /**
         * Updates the track that is broadcasted to the RTCPeerConnection.
         * This will start new transaction by triggering a negotiationneeded event
         * on the peerConnection given as parameter.
         *
         * negotiationneeded -> offer -> answer -> ...
         *
         * @private
         * @param {RTCPeerConnection} peerConnection
         * @param {String} trackKind
         * @param {Object} [param2]
         * @param {boolean} [param2.initTransceiver]
         * @param {String} [param2.token]
         */
        async _updateRemoteTrack(peerConnection, trackKind, { initTransceiver, token } = {}) {
            this._addLogEntry(token, `updating ${trackKind} transceiver`);
            const track = trackKind === 'audio' ? this.audioTrack : this.videoTrack;
            const fullDirection = track ? 'sendrecv' : 'recvonly';
            const limitedDirection = track ? 'sendonly' : 'inactive';
            let transceiverDirection = fullDirection;
            if (trackKind === 'video') {
                const focusedToken = this.messaging.focusedRtcSession && this.messaging.focusedRtcSession.peerToken;
                transceiverDirection = !focusedToken || focusedToken === token ? fullDirection : limitedDirection;
            }
            let transceiver;
            if (initTransceiver) {
                transceiver = peerConnection.addTransceiver(trackKind);
            } else {
                transceiver = this._getTransceiver(peerConnection, trackKind);
            }
            if (track) {
                try {
                    await transceiver.sender.replaceTrack(track);
                    transceiver.direction = transceiverDirection;
                } catch (e) {
                    // ignored, the track is probably already on the peerConnection.
                }
                return;
            }
            try {
                await transceiver.sender.replaceTrack(null);
                transceiver.direction = transceiverDirection;
            } catch (e) {
                // ignored, the transceiver is probably already removed
            }
            if (trackKind === 'video') {
                this._notifyPeers([token], {
                    event: 'trackChange',
                    type: 'peerToPeer',
                    payload: {
                        type: 'video',
                        state: { isSendingVideo: false },
                    },
                });
            }
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Event} ev
         */
        async _onBeforeUnload(ev) {
            if (this.channel) {
                await this.channel.performRpcLeaveCall();
            }
        }

        /**
         * @private
         * @param {String} state the new state of the connection
         * @param {String} token of the peer whose the connection changed
         */
        async _onConnectionStateChange(state, token) {
            this._addLogEntry(token, `connection state changed: ${state}`);
            switch (state) {
                case "closed":
                    this._removePeer(token);
                    break;
                case "failed":
                case "disconnected":
                    await this._recoverConnection(token, { delay: this.recoveryDelay, reason: `connection ${state}` });
                    break;
            }
        }

        /**
         * @private
         * @param {String} connectionState the new state of the connection
         * @param {String} token of the peer whose the connection changed
         */
        async _onICEConnectionStateChange(connectionState, token) {
            this._addLogEntry(token, `ICE connection state changed: ${connectionState}`, { state: connectionState });
            const rtcSession = this.messaging.models['mail.rtc_session'].findFromIdentifyingData({ id: token });
            if (!rtcSession) {
                return;
            }
            rtcSession.update({
                connectionState,
            });
            switch (connectionState) {
                case "closed":
                    this._removePeer(token);
                    break;
                case "failed":
                case "disconnected":
                    await this._recoverConnection(token, { delay: this.recoveryDelay, reason: `ice connection ${connectionState}` });
                    break;
            }
        }

        /**
         * @private
         * @param {keyboardEvent} ev
         */
        _onKeyDown(ev) {
            if (!this.channel) {
                return;
            }
            if (this.messaging.userSetting.rtcConfigurationMenu.isRegisteringKey) {
                return;
            }
            if (!this.messaging.userSetting.usePushToTalk || !this.messaging.userSetting.isPushToTalkKey(ev)) {
                return;
            }
            if (this._pushToTalkTimeoutId) {
                browser.clearTimeout(this._pushToTalkTimeoutId);
            }
            if (!this.currentRtcSession.isTalking && !this.currentRtcSession.isMuted) {
                this.messaging.soundEffects.pushToTalk.play({ volume: 0.3 });
            }
            this._setSoundBroadcast(true);
        }

        /**
         * @private
         * @param {keyboardEvent} ev
         */
        _onKeyUp(ev) {
            if (!this.channel) {
                return;
            }
            if (!this.messaging.userSetting.usePushToTalk || !this.messaging.userSetting.isPushToTalkKey(ev, { ignoreModifiers: true })) {
                return;
            }
            if (!this.currentRtcSession.isTalking) {
                return;
            }
            if (!this.currentRtcSession.isMuted) {
                this.messaging.soundEffects.pushToTalk.play({ volume: 0.3 });
            }
            this._pushToTalkTimeoutId = browser.setTimeout(
                () => {
                    this._setSoundBroadcast(false);
                },
                this.messaging.userSetting.voiceActiveDuration || 0,
            );
        }

    }
    Rtc.fields = {
        /**
         * audio MediaStreamTrack of the current user
         */
        audioTrack: attr(),
        /**
         * The channel that is hosting the current RTC call.
         */
        channel: one2one('mail.thread', {
            inverse: 'rtc',
        }),
        /**
         * String, peerToken of the current session used to identify him during the peer-to-peer transactions.
         */
        currentRtcSession: one2one('mail.rtc_session', {
            inverse: 'rtc',
        }),
        /**
         * ICE servers used by RTCPeerConnection to retrieve the public IP address (STUN)
         * or to relay packets when necessary (TURN).
         */
        iceServers: attr({
            default: [
                {
                    urls: [
                        'stun:stun1.l.google.com:19302',
                        'stun:stun2.l.google.com:19302',
                    ],
                },
            ],
        }),
        /**
         * list of connection states considered invalid, which means that
         * no action should be taken on such peerConnection.
         */
        invalidIceConnectionStates: attr({
            default: new Set(['disconnected', 'failed', 'closed']),
            readonly: true,
        }),
        /**
         * true if the browser supports webRTC
         */
        isClientRtcCompatible: attr({
            compute: '_computeIsClientRtcCompatible',
            default: true,
        }),
        isNotifyPeersRPCInProgress: attr({
            default: false,
        }),
        /**
         * Contains the logs of the current session by token.
         * { token: { name<String>, logs<Array> } }
         */
        logs: attr({
            default: {},
        }),
        peerNotificationsToSend: one2many('mail.rtc_peer_notification', {
            isCausal: true,
        }),
        /**
         * Determines the delay to wait (in ms) before sending peer
         * notifications to the server. Sending many notifications at once
         * significantly increase the connection time because the server can't
         * handle too many requests at once, but handles much faster one bigger
         * request, even with a delay. The delay should however not be too high.
         */
        peerNotificationWaitDelay: attr({
            default: 50,
        }),
        /**
         * How long to wait before considering a connection as needing recovery in ms.
         */
        recoveryTimeout: attr({
            default: 15000,
        }),
        /**
         * How long to wait before recovering a connection that has failed in ms.
         */
        recoveryDelay: attr({
            default: 3000,
        }),
        /**
         * True if we want to enable the video track of the current partner.
         */
        sendUserVideo: attr({
            default: false,
        }),
        /**
         * True if we want to enable the video track of the current partner.
         */
        sendDisplay: attr({
            default: false,
        }),
        /**
         * MediaTrackConstraints for the user video track.
         * Some browsers do not support all constraints, for example firefox
         * does not support aspectRatio. Those constraints will be ignored
         * unless specified as mandatory (see doc ConstrainDOMString).
         */
        videoConfig: attr({
            default: {
                aspectRatio: 16 / 9,
                frameRate: {
                    max: 30,
                },
            },
        }),
        /**
         * video MediaStreamTrack of the current user
         */
        videoTrack: attr(),
    };
    Rtc.identifyingFields = ['messaging'];
    Rtc.modelName = 'mail.rtc';

    return Rtc;
}

registerNewModel('mail.rtc', factory);
