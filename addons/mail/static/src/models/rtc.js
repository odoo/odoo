/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert, unlink } from '@mail/model/model_field_command';
import { monitorAudio } from '@mail/utils/media_monitoring';
import { sprintf } from '@web/core/utils/strings';

const getRTCPeerNotificationNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

registerModel({
    name: 'Rtc',
    lifecycleHooks: {
        _created() {
            browser.addEventListener('keydown', this._onKeyDown);
            browser.addEventListener('keyup', this._onKeyUp);
            // Disconnects the RTC session if the page is closed or reloaded.
            browser.addEventListener('beforeunload', this._onBeforeUnload);
        },
        async _willDelete() {
            browser.removeEventListener('beforeunload', this._onBeforeUnload);
            browser.removeEventListener('keydown', this._onKeyDown);
            browser.removeEventListener('keyup', this._onKeyUp);
            this.messaging.browser.clearInterval(this.pingInterval);
        },
    },
    recordMethods: {
        async deafen() {
            await this._setDeafState(true);
            this.messaging.soundEffects.deafen.play();
        },
        /**
         * Removes and disconnects all the peerConnections that are not current members of the call.
         *
         * @param {RtcSession[]} currentSessions list of sessions of this call.
         */
        async filterCallees(currentSessions) {
            const currentSessionsTokens = new Set(currentSessions.map(session => session.id));
            for (const rtcSession of this.connectedRtcSessions) {
                if (!currentSessionsTokens.has(rtcSession.id)) {
                    this._addLogEntry(rtcSession.id, 'session removed from the server');
                    this._removePeer(rtcSession.id);
                }
            }
            if (this.channel && this.currentRtcSession && !currentSessionsTokens.has(this.currentRtcSession.id)) {
                // if the current RTC session is not in the channel sessions, this call is no longer valid.
                this.channel.endCall();
            }
        },
        /**
         * @param {number} sender id of the session that sent the notification
         * @param {String} content JSON
         */
        async handleNotification(sender, content) {
            const { event, channelId, payload } = JSON.parse(content);
            const rtcSession = this.messaging.models['RtcSession'].findFromIdentifyingData({ id: sender });
            if (!rtcSession || rtcSession.channel !== this.channel) {
                // does handle notifications targeting a different session
                return;
            }
            if (!this.messaging.device.hasRtcSupport) {
                return;
            }
            if (!rtcSession.rtcPeerConnection && (!channelId || !this.channel || channelId !== this.channel.id)) {
                return;
            }
            switch (event) {
                case "offer":
                    this._addLogEntry(sender, `received notification: ${event}`, { step: 'received offer' });
                    await this._handleRtcTransactionOffer(rtcSession, payload);
                    break;
                case "answer":
                    this._addLogEntry(sender, `received notification: ${event}`, { step: 'received answer' });
                    await this._handleRtcTransactionAnswer(rtcSession, payload);
                    break;
                case "ice-candidate":
                    await this._handleRtcTransactionICECandidate(rtcSession, payload);
                    break;
                case "disconnect":
                    this._addLogEntry(sender, `received notification: ${event}`, { step: ' peer cleanly disconnected ' });
                    this._removePeer(rtcSession.id);
                    break;
                case 'trackChange':
                    this._handleTrackChange(rtcSession, payload);
                    break;
            }
        },
        /**
         * @param {Object} param0
         * @param {string} param0.currentSessionId the Id of the 'RtcSession'
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
        },
        async mute() {
            await this._setMuteState(true);
            this.messaging.soundEffects.mute.play();
        },
        /**
         * @param {number[]} targetToken
         * @param {Object} param1
         * @param {String} param1.event
         * @param {Object} [param1.payload]
         * @param {String} [param1.type] 'server' or 'peerToPeer',
         *                 'peerToPeer' requires an active RTCPeerConnection
         */
        async notifyPeers(targetTokens, { event, payload, type = 'server' }) {
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
                    const rtcSession = this.messaging.models['RtcSession'].findFromIdentifyingData({ id: token });
                    if (!rtcSession) {
                        continue;
                    }
                    const rtcDataChannel = rtcSession.rtcDataChannel;
                    if (!rtcDataChannel || rtcDataChannel.dataChannel.readyState !== 'open') {
                        continue;
                    }
                    rtcDataChannel.dataChannel.send(JSON.stringify({
                        event,
                        channelId: this.channel.id,
                        payload,
                    }));
                }
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickActivityNoticeButton(ev) {
            this.channel.open();
        },
        /**
         * Resets the state of the model and cleanly ends all connections and
         * streams.
         */
        reset() {
            for (const rtcSession of this.connectedRtcSessions) {
                this._removePeer(rtcSession.id);
                rtcSession.update({ rtcPeerConnection: clear() });
            }

            if (this.disconnectAudioMonitor) {
                this.disconnectAudioMonitor()
            }
            this.audioTrack && this.audioTrack.stop();
            this.videoTrack && this.videoTrack.stop();

            for (const rtcSession of this.messaging.models['RtcSession'].all()) {
                this.messaging.browser.clearTimeout(rtcSession.connectionRecoveryTimeout);
                rtcSession.update({
                    connectionRecoveryTimeout: clear(),
                    isCurrentUserInitiatorOfConnectionOffer: clear(),
                    rtcDataChannel: clear(),
                });
            }
            this.update({
                blurManager: clear(),
                currentRtcSession: clear(),
                disconnectAudioMonitor: clear(),
                logs: clear(),
                sendUserVideo: clear(),
                sendDisplay: clear(),
                sourceVideoStream: clear(),
                videoTrack: clear(),
                audioTrack: clear(),
            });
        },
        /**
         * Mutes and unmutes the microphone, will not unmute if deaf.
         *
         */
        async toggleMicrophone() {
            if (this.currentRtcSession.isMute) {
                await this.unmute();
            } else {
                await this.mute();
            }
        },
        /**
         * toggles screen broadcasting to peers.
         */
        async toggleScreenShare() {
            this._toggleVideoBroadcast({ type: 'display' });
        },
        /**
         * Toggles user video (eg: webcam) broadcasting to peers.
         */
        async toggleUserVideo({ force } = {}) {
            this._toggleVideoBroadcast({ type: 'user-video', force });
        },
        async undeafen() {
            await this._setDeafState(false);
            this.messaging.soundEffects.undeafen.play();
        },
        async unmute() {
            if (this.audioTrack) {
                await this._setMuteState(false);
            } else {
                // if we don't have an audioTrack, we try to request it again
                await this.updateLocalAudioTrack(true);
            }
            this.messaging.soundEffects.unmute.play();
        },
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
                } catch (_e) {
                    this.messaging.notify({
                        message: sprintf(
                            this.env._t(`"%s" requires microphone access`),
                            window.location.host,
                        ),
                        type: 'warning',
                    });
                    if (this.currentRtcSession) {
                        this.currentRtcSession.updateAndBroadcast({ isSelfMuted: true });
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
                    await this.updateLocalAudioTrack(false);
                    if (!this.exists()) {
                        return;
                    }
                    this.currentRtcSession.updateAndBroadcast({ isSelfMuted: true });
                    await this._updateLocalAudioTrackEnabledState();
                });
                this.currentRtcSession.updateAndBroadcast({ isSelfMuted: false });
                audioTrack.enabled = !this.currentRtcSession.isMute && this.currentRtcSession.isTalking;
                this.update({ audioTrack });
                await this.updateVoiceActivation();
                if (!this.exists()) {
                    return;
                }
                for (const rtcSession of this.connectedRtcSessions) {
                    await rtcSession.updateRemoteTrack('audio');
                }
            }
        },
        /**
         * @param {MediaTrackConstraints Object} constraints
         */
        updateVideoConfig(constraints) {
            const videoConfig = Object.assign(this.videoConfig, constraints);
            this.update({ videoConfig });
            this.videoTrack && this.videoTrack.applyConstraints(this.videoConfig);
        },
        /**
         * Updates the way broadcast of the local audio track is handled,
         * attaches an audio monitor for voice activation if necessary.
         */
        async updateVoiceActivation() {
            if (this.disconnectAudioMonitor) {
                this.disconnectAudioMonitor();
            }
            if (!this.currentRtcSession) {
                return;
            }
            if (this.messaging.userSetting.usePushToTalk || !this.channel || !this.audioTrack) {
                this.currentRtcSession.update({ isTalking: false });
                await this._updateLocalAudioTrackEnabledState();
                return;
            }
            try {
                this.update({
                    disconnectAudioMonitor: await monitorAudio(
                        this.audioTrack,
                        {
                            onThreshold: this._onThresholdAudioMonitor,
                            volumeThreshold: this.messaging.userSetting.voiceActivationThreshold,
                        },
                    ),
                });
            } catch (_e) {
                /**
                 * The browser is probably missing audioContext,
                 * in that case, voice activation is not enabled
                 * and the microphone is always 'on'.
                 */
                this.messaging.notify({
                    message: this.env._t("Your browser does not support voice activation"),
                    type: 'warning',
                });
                this.currentRtcSession.update({ isTalking: true });
            }
            await this._updateLocalAudioTrackEnabledState();
        },
        /**
         * @private
         * @param {String} token
         * @param {String} entry
         * @param {Object} [param2]
         * @param {Error} [param2.error]
         * @param {String} [param2.step] current step of the flow
         * @param {String} [param2.state] current state of the connection
         */
        _addLogEntry(token, entry, { error, step, state, ...data } = {}) {
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
                ...data,
            });
            if (step) {
                this.logs[token].step = step;
            }
            if (state) {
                this.logs[token].state = state;
            }
        },
        /**
         * @private
         * @param {RtcSession} rtcSession
         */
        async _callPeer(rtcSession) {
            this._createPeerConnection(rtcSession);
            for (const trackKind of this.orderedTransceiverNames) {
                await rtcSession.updateRemoteTrack(trackKind, { initTransceiver: true });
            }
            rtcSession.update({ isCurrentUserInitiatorOfConnectionOffer: true });
        },
        /**
         * Call all the sessions that do not have an already initialized peerConnection.
         *
         * @private
         */
        _callSessions() {
            if (!this.channel.rtcSessions) {
                return;
            }
            for (const rtcSession of this.channel.rtcSessions) {
                if (rtcSession.rtcPeerConnection && rtcSession.rtcPeerConnection.peerConnection) {
                    continue;
                }
                if (rtcSession === this.currentRtcSession) {
                    continue;
                }
                rtcSession.update({
                    connectionState: 'Not connected: sending initial RTC offer',
                });
                this._addLogEntry(rtcSession.id, 'init call', { step: 'init call' });
                this._callPeer(rtcSession);
            }
        },

        /**
         * Creates and setup a RTCPeerConnection.
         *
         * @private
         * @param {RtcSession} rtcSession
         * @returns {RtcSession}
         */
        _createPeerConnection(rtcSession) {
            const peerConnection = new window.RTCPeerConnection({ iceServers: this.iceServers });
            this._addLogEntry(rtcSession.id, `RTCPeerConnection created`, { step: 'peer connection created' });
            peerConnection.onicecandidate = async (event) => {
                if (!event.candidate) {
                    return;
                }
                await this.notifyPeers([rtcSession.id], {
                    event: 'ice-candidate',
                    payload: { candidate: event.candidate },
                });
            };
            peerConnection.oniceconnectionstatechange = (event) => {
                this._onICEConnectionStateChange(peerConnection.iceConnectionState, rtcSession);
            };
            peerConnection.onconnectionstatechange = (event) => {
                this._onConnectionStateChange(peerConnection.connectionState, rtcSession);
            };
            peerConnection.onicecandidateerror = async (error) => {
                this._addLogEntry(rtcSession.id, `ice candidate error`);
                this._recoverConnection(rtcSession, { delay: this.recoveryTimeout, reason: 'ice candidate error' });
            };
            peerConnection.onnegotiationneeded = async (event) => {
                const offer = await peerConnection.createOffer();
                try {
                    await peerConnection.setLocalDescription(offer);
                } catch (e) {
                    // Possibly already have a remote offer here: cannot set local description
                    this._addLogEntry(rtcSession.id, `couldn't setLocalDescription`, { error: e });
                    return;
                }
                this._addLogEntry(rtcSession.id, `sending notification: offer`, { step: 'sending offer' });
                await this.notifyPeers([rtcSession.id], {
                    event: 'offer',
                    payload: { sdp: peerConnection.localDescription },
                });
            };
            peerConnection.ontrack = ({ transceiver, track }) => {
                this._addLogEntry(rtcSession.id, `received ${track.kind} track`);
                rtcSession.updateStream(track);
            };
            const dataChannel = peerConnection.createDataChannel("notifications", { negotiated: true, id: 1 });
            dataChannel.onmessage = (event) => {
                this.handleNotification(rtcSession.id, event.data);
            };
            dataChannel.onopen = async () => {
                /**
                 * FIXME? it appears that the track yielded by the peerConnection's 'ontrack' event is always enabled,
                 * even when it is disabled on the sender-side.
                 */
                try {
                    await this.notifyPeers([rtcSession.id], {
                        event: 'trackChange',
                        type: 'peerToPeer',
                        payload: {
                            type: 'audio',
                            state: {
                                isTalking: this.audioTrack && this.audioTrack.enabled,
                                isSelfMuted: this.currentRtcSession.isSelfMuted,
                            },
                        },
                    });
                } catch (e) {
                    if (!(e instanceof DOMException) || e.name !== "OperationError") {
                        throw e;
                    }
                    this._addLogEntry(rtcSession.id, `failed to send on datachannel; dataChannelInfo: ${this._serializeRTCDataChannel(dataChannel)}`, { error: e });
                }
            };
            rtcSession.update({ rtcPeerConnection: { peerConnection } });
            this.messaging.models['RtcDataChannel'].insert({
                dataChannel,
                rtcSession,
            });
            return rtcSession;
        },
        /**
         * @private
         * @param {RtcSession} rtcSession
         * @param {Object} param1
         * @param {Object} param1.sdp Session Description Protocol
         */
        async _handleRtcTransactionAnswer(rtcSession, { sdp }) {
            const rtcPeerConnection = rtcSession.rtcPeerConnection;
            if (
                !rtcPeerConnection ||
                this.invalidIceConnectionStates.has(rtcPeerConnection.peerConnection.iceConnectionState) ||
                rtcPeerConnection.peerConnection.signalingState === 'stable'
            ) {
                return;
            }
            if (rtcPeerConnection.peerConnection.signalingState === 'have-remote-offer') {
                // we already have an offer
                return;
            }
            const rtcSessionDescription = new window.RTCSessionDescription(sdp);
            try {
                await rtcPeerConnection.peerConnection.setRemoteDescription(rtcSessionDescription);
            } catch (e) {
                this._addLogEntry(rtcSession.id, 'answer handling: Failed at setting remoteDescription', { error: e });
                // ignored the transaction may have been resolved by another concurrent offer.
            }
        },
        /**
         * @private
         * @param {RtcSession} rtcSession
         * @param {Object} param1
         * @param {Object} param1.candidate RTCIceCandidateInit
         */
        async _handleRtcTransactionICECandidate(rtcSession, { candidate }) {
            const rtcPeerConnection = rtcSession.rtcPeerConnection;
            if (!rtcPeerConnection || this.invalidIceConnectionStates.has(rtcPeerConnection.peerConnection.iceConnectionState)) {
                return;
            }
            const rtcIceCandidate = new window.RTCIceCandidate(candidate);
            try {
                await rtcPeerConnection.peerConnection.addIceCandidate(rtcIceCandidate);
            } catch (error) {
                this._addLogEntry(rtcSession.id, 'ICE candidate handling: failed at adding the candidate to the connection', { error });
                this._recoverConnection(rtcSession, { delay: this.recoveryTimeout, reason: 'failed at adding ice candidate' });
            }
        },
        /**
         * @private
         * @param {RtcSession} rtcSession
         * @param {Object} param1
         * @param {Object} param1.sdp Session Description Protocol
         */
        async _handleRtcTransactionOffer(rtcSession, { sdp }) {
            if (!rtcSession.rtcPeerConnection) {
                this._createPeerConnection(rtcSession)
            }
            if (!rtcSession.rtcPeerConnection || this.invalidIceConnectionStates.has(rtcSession.rtcPeerConnection.peerConnection.iceConnectionState)) {
                return;
            }
            if (rtcSession.rtcPeerConnection.peerConnection.signalingState === 'have-remote-offer') {
                // we already have an offer
                return;
            }
            const rtcSessionDescription = new window.RTCSessionDescription(sdp);
            try {
                await rtcSession.rtcPeerConnection.peerConnection.setRemoteDescription(rtcSessionDescription);
            } catch (e) {
                this._addLogEntry(rtcSession.id, 'offer handling: failed at setting remoteDescription', { error: e });
                return;
            }
            await rtcSession.updateRemoteTrack('audio');
            await rtcSession.updateRemoteTrack('video');

            let answer;
            try {
                answer = await rtcSession.rtcPeerConnection.peerConnection.createAnswer();
            } catch (e) {
                this._addLogEntry(rtcSession.id, 'offer handling: failed at creating answer', { error: e });
                return;
            }
            try {
                await rtcSession.rtcPeerConnection.peerConnection.setLocalDescription(answer);
            } catch (e) {
                this._addLogEntry(rtcSession.id, 'offer handling: failed at setting localDescription', { error: e });
                return;
            }

            this._addLogEntry(rtcSession.id, `sending notification: answer`, { step: 'sending answer' });
            await this.notifyPeers([rtcSession.id], {
                event: 'answer',
                payload: { sdp: rtcSession.rtcPeerConnection.peerConnection.localDescription },
            });
            this._recoverConnection(rtcSession, { delay: this.recoveryTimeout, reason: 'standard answer timeout' });
        },
        /**
         * @private
         * @param {RtcSession} rtcSession
         * @param {Object} param1
         * @param {String} param1.type 'audio' or 'video'
         * @param {Object} param1.state
         */
        _handleTrackChange(rtcSession, { type, state }) {
            const { isSelfMuted, isTalking, isSendingVideo, isDeaf } = state;
            if (type === 'audio') {
                if (!rtcSession.audioStream) {
                    return;
                }
                rtcSession.update({
                    isSelfMuted,
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
        },
        /**
         * @param {RtcSession} rtcSession
         * @param {string} [reason]
         */
        async _onRecoverConnectionTimeout(rtcSession, reason) {
            rtcSession.update({ connectionRecoveryTimeout: clear() });
            const rtcPeerConnection = rtcSession.rtcPeerConnection;
            if (!rtcPeerConnection || !this.channel) {
                return;
            }
            if (rtcSession.isCurrentUserInitiatorOfConnectionOffer) {
                return;
            }
            if (rtcPeerConnection.peerConnection.iceConnectionState === 'connected') {
                return;
            }
            this._addLogEntry(rtcSession.id, `calling back to recover ${rtcPeerConnection.peerConnection.iceConnectionState} connection, reason: ${reason}`);
            if (this.modelManager.isDebug) {
                let stats;
                try {
                    const peerConnectionStats = await rtcPeerConnection.peerConnection.getStats();
                    stats = peerConnectionStats && [...peerConnectionStats.values()];
                } catch (_e) {
                    // ignore
                }
                this._addLogEntry(
                    rtcSession.id,
                    `calling back to recover "${rtcPeerConnection.peerConnection.iceConnectionState}" connection`,
                    { reason, stats }
                );
            }
            await this.notifyPeers([rtcSession.id], {
                event: 'disconnect',
            });
            this._removePeer(rtcSession.id);
            this._callPeer(rtcSession);
        },
        /**
         * Pings the server to ensure this session is kept alive.
         */
        async _pingServer() {
            const channel = this.channel;
            const { rtcSessions } = await this.messaging.rpc({
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
        },
        /**
         * Attempts a connection recovery by closing and restarting the call
         * from the receiving end.
         *
         * @private
         * @param {RtcSession} rtcSession
         * @param {Object} [param1]
         * @param {number} [param1.delay] in ms
         * @param {string} [param1.reason]
         */
        _recoverConnection(rtcSession, { delay = 0, reason = '' } = {}) {
            if (rtcSession.connectionRecoveryTimeout) {
                return;
            }
            rtcSession.update({
                connectionRecoveryTimeout: this.messaging.browser.setTimeout(
                    this._onRecoverConnectionTimeout.bind(this, rtcSession, reason),
                    delay,
                ),
            });
        },
        /**
         * Cleans up a peer by closing all its associated content and the connection.
         *
         * @private
         * @param {number} sessionId
         */
        _removePeer(sessionId) {
            const rtcSession = this.messaging.models['RtcSession'].findFromIdentifyingData({ id: sessionId });
            if (rtcSession) {
                rtcSession.reset();
                const rtcDataChannel = rtcSession.rtcDataChannel;
                if (rtcDataChannel) {
                    rtcDataChannel.delete();
                }
            }
            const rtcPeerConnection = rtcSession.rtcPeerConnection;
            if (rtcPeerConnection) {
                this._removeRemoteTracks(rtcPeerConnection.peerConnection);
                rtcPeerConnection.delete();
            }
            this.messaging.models['RtcSession'].insert({
                id: sessionId,
                isCurrentUserInitiatorOfConnectionOffer: clear(),
            });
            this._addLogEntry(sessionId, 'peer removed', { step: 'peer removed' });
        },
        /**
         * Terminates the Transceivers of the peer connection.
         *
         * @private
         * @param {web.RTCPeerConnection} peerConnection
         */
        _removeRemoteTracks(peerConnection) {
            const RTCRtpSenders = peerConnection.getSenders();
            for (const sender of RTCRtpSenders) {
                try {
                    peerConnection.removeTrack(sender);
                } catch (_e) {
                    // ignore error
                }
            }
            for (const transceiver of peerConnection.getTransceivers()) {
                try {
                    transceiver.stop();
                } catch (_e) {
                    // transceiver may already be stopped by the remote.
                }
            }
        },
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
                await this.messaging.rpc({
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
        },
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
        },
        /**
         * @param {Boolean} isDeaf
         */
        async _setDeafState(isDeaf) {
            this.currentRtcSession.updateAndBroadcast({ isDeaf });
            for (const session of this.messaging.models['RtcSession'].all()) {
                if (!session.audioElement) {
                    continue;
                }
                session.audioElement.muted = isDeaf;
            }
            await this._updateLocalAudioTrackEnabledState();
        },
        /**
         * @param {Boolean} isSelfMuted
         */
        async _setMuteState(isSelfMuted) {
            this.currentRtcSession.updateAndBroadcast({ isSelfMuted });
            await this._updateLocalAudioTrackEnabledState();
        },
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
            if (!this.currentRtcSession.isMute) {
                await this._updateLocalAudioTrackEnabledState();
            }
        },
        /**
         * @private
         * @param {Object} trackOptions
         */
        async _toggleVideoBroadcast(trackOptions) {
            if (!this.channel) {
                return;
            }
            await this._toggleLocalVideoTrack(trackOptions);
            for (const rtcSession of this.connectedRtcSessions) {
                await rtcSession.updateRemoteTrack('video');
            }
            if (!this.currentRtcSession) {
                return;
            }
            this.currentRtcSession.updateAndBroadcast({
                isScreenSharingOn: !!this.sendDisplay,
                isCameraOn: !!this.sendUserVideo,
            });
        },
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
                this.currentRtcSession.updateStream(this.videoTrack);
            }
        },
        /**
         * Sets the enabled property of the local audio track and notifies
         * peers of the new state.
         *
         * @private
         */
        async _updateLocalAudioTrackEnabledState() {
            if (!this.audioTrack) {
                return;
            }
            this.audioTrack.enabled = !this.currentRtcSession.isMute && this.currentRtcSession.isTalking;
            await this.notifyPeers(this.connectedRtcSessions.map(rtcSession => rtcSession.id), {
                event: 'trackChange',
                type: 'peerToPeer',
                payload: {
                    type: 'audio',
                    state: {
                        isTalking: this.audioTrack.enabled,
                        isSelfMuted: this.currentRtcSession.isSelfMuted,
                        isDeaf: this.currentRtcSession.isDeaf,
                    },
                },
            });
        },
        /**
         * @private
         * @param {String} type 'user-video' or 'display'
         * @param {boolean} activateVideo true if we want to activate the video
         */
        async _updateLocalVideoTrack(type, activateVideo) {
            this.update({
                sendDisplay: false,
                sendUserVideo: false,
            });
            const stopVideo = () => {
                if (this.videoTrack) {
                    this.videoTrack.stop();
                }
                this.update({
                    sourceVideoStream: clear(),
                    videoTrack: clear(),
                });
            };
            if (!activateVideo) {
                if (this.blurManager) {
                    this.blurManager.update({
                        srcStream: clear(),
                    });
                }
                if (type === 'display') {
                    this.messaging.soundEffects.screenSharing.play();
                }
                stopVideo();
                return;
            }
            let sourceWebMediaStream;
            try {
                if (type === 'user-video') {
                    if (this.blurManager && this.blurManager.srcStream) {
                        sourceWebMediaStream = this.blurManager.srcStream.webMediaStream;
                    } else {
                        sourceWebMediaStream = await browser.navigator.mediaDevices.getUserMedia({ video: this.videoConfig });
                    }
                }
                if (type === 'display') {
                    sourceWebMediaStream = await browser.navigator.mediaDevices.getDisplayMedia({ video: this.videoConfig });
                    this.messaging.soundEffects.screenSharing.play();
                }
            } catch (_e) {
                this.messaging.notify({
                    message: sprintf(
                        this.env._t(`"%s" requires "%s" access`),
                        window.location.host,
                        type === 'user-video' ? 'camera' : 'display',
                    ),
                    type: 'warning',
                });
                stopVideo();
                return;
            }
            let videoStream = sourceWebMediaStream;
            if (this.messaging.userSetting.useBlur && type === 'user-video') {
                try {
                    this.update({ blurManager: { srcStream: { webMediaStream: sourceWebMediaStream, id: sourceWebMediaStream.id } }, });
                    const mediaStream = await this.blurManager.stream;
                    videoStream = mediaStream.webMediaStream;
                } catch (_e) {
                    this.messaging.notify({
                        message: sprintf(
                            this.env._t('To %(name)s: %(message)s)'), {
                                name: _e.name,
                                message: _e.message,
                            },
                        ),
                        type: 'warning',
                    });
                    this.messaging.userSetting.update({ useBlur: false });
                }
            }
            const videoTrack = videoStream ? videoStream.getVideoTracks()[0] : undefined;
            if (videoTrack) {
                videoTrack.addEventListener('ended', async () => {
                    await this._toggleVideoBroadcast({ force: false, type });
                });
            }
            this.update({
                sourceVideoStream: { webMediaStream: sourceWebMediaStream, id: sourceWebMediaStream.id },
                videoTrack,
                sendUserVideo: type === 'user-video' && !!videoTrack,
                sendDisplay: type === 'display' && !!videoTrack,
            });
        },
        /**
         * @private
         * @param {Event} ev
         */
        async _onBeforeUnload(ev) {
            if (this.channel) {
                await this.channel.performRpcLeaveCall();
            }
        },
        /**
         * @private
         * @param {String} state the new state of the connection
         * @param {RtcSession} rtcSession of the peer whose the connection changed
         */
        async _onConnectionStateChange(state, rtcSession) {
            this._addLogEntry(rtcSession.id, `connection state changed: ${state}`);
            switch (state) {
                case "closed":
                    this._removePeer(rtcSession.id);
                    break;
                case "failed":
                case "disconnected":
                    await this._recoverConnection(rtcSession, { delay: this.recoveryDelay, reason: `connection ${state}` });
                    break;
            }
        },
        /**
         * @private
         * @param {String} connectionState the new state of the connection
         * @param {RtcSession} rtcSession id of the rtcSession of the peer whose the connection changed
         */
        async _onICEConnectionStateChange(connectionState, rtcSession) {
            this._addLogEntry(rtcSession.id, `ICE connection state changed: ${connectionState}`, { state: connectionState });
            if (!rtcSession) {
                return;
            }
            rtcSession.update({
                connectionState,
            });
            switch (connectionState) {
                case "connected":
                    rtcSession.updateConnectionTypes();
                    break;
                case "closed":
                    this._removePeer(rtcSession.id);
                    break;
                case "failed":
                case "disconnected":
                    await this._recoverConnection(rtcSession, { delay: this.recoveryDelay, reason: `ice connection ${connectionState}` });
                    break;
            }
        },
        /**
         * @private
         * @param {keyboardEvent} ev
         */
        _onKeyDown(ev) {
            if (!this.channel) {
                return;
            }
            if (!this.messaging.userSetting.usePushToTalk || !this.messaging.userSetting.isPushToTalkKey(ev)) {
                return;
            }
            if (this.currentRtcSession.isMute) {
                return;
            }
            if (this.messaging.userSetting.isRegisteringKey) {
                return;
            }
            this.messaging.browser.clearTimeout(this.pushToTalkTimeout);
            if (!this.currentRtcSession.isTalking) {
                this.messaging.soundEffects.pushToTalkOn.play();
                this._setSoundBroadcast(true);
            }
        },
        /**
         * @private
         * @param {keyboardEvent} ev
         */
        _onKeyUp(ev) {
            if (!this.channel) {
                return;
            }
            if (!this.messaging.userSetting.usePushToTalk || !this.messaging.userSetting.isPushToTalkKey(ev)) {
                return;
            }
            if (!this.currentRtcSession.isTalking) {
                return;
            }
            if (!this.currentRtcSession.isMute) {
                this.messaging.soundEffects.pushToTalkOff.play();
            }
            this.update({
                pushToTalkTimeout: this.messaging.browser.setTimeout(
                    this._onPushToTalkTimeout,
                    this.messaging.userSetting.voiceActiveDuration,
                ),
            });
        },
        /**
         * @private
         */
        _onPushToTalkTimeout() {
            this.update({ pushToTalkTimeout: clear() });
            this._setSoundBroadcast(false);
        },
        /**
         * @private
         */
        async _onPingInterval() {
            if (!this.currentRtcSession || !this.channel) {
                return;
            }
            await this._pingServer();
            if (!this.currentRtcSession || !this.channel) {
                return;
            }
            this._callSessions();
        },
        /**
         * @private
         * @param {boolean} isAboveThreshold
         */
        _onThresholdAudioMonitor(isAboveThreshold) {
            this._setSoundBroadcast(isAboveThreshold);
        },
    },
    fields: {
        /**
         * audio MediaStreamTrack of the current user
         */
        audioTrack: attr(),
        blurManager: one('BlurManager', {
            inverse: 'rtc',
        }),
        /**
         * The channel that is hosting the current RTC call.
         */
        channel: one('Thread', {
            inverse: 'rtc',
        }),
        /**
         * Contains the RTC Session that are connected.
         * Connected RTC Sessions have rtcPeerConnection set.
         */
        connectedRtcSessions: many('RtcSession', {
            inverse: 'rtcAsConnectedSession',
        }),
        /**
         * String, peerToken of the current session used to identify them during the peer-to-peer transactions.
         */
        currentRtcSession: one('RtcSession', {
            inverse: 'rtcAsCurrentSession',
        }),
        /**
         * callback to properly end the audio monitoring.
         * If set it indicates that we are currently monitoring the local
         * audioTrack for the voice activation feature.
         */
        disconnectAudioMonitor: attr(),
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
        /**
         * List of transceivers in ordered for consistent insertion and retrieval order, relevant for
         * RTCPeerConnection.getTransceivers which returns transceivers in insertion order as per webRTC specifications.
         */
        orderedTransceiverNames: attr({
            default: ['audio', 'video'],
            readonly: true,
            required: true,
        }),
        peerNotificationsToSend: many('RtcPeerNotification', {
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
         * Interval to regularly ping and connect to RTC sessions.
         *
         * - Ping is to update rtc sessions of the channel, i.e. add or remove rtc sessions.
         *   This also deals with possible race conditions that could make us unaware of some sessions.
         * - Connect to RTC sessions for which no peerConnection is established, to try to recover any
         *   connection that failed to start.
         *   This is distinct from this._recoverConnection which tries to restores connection that were
         *   established but failed or timed out.
         */
        pingInterval: attr({
            compute() {
                return this.messaging.browser.setInterval(this._onPingInterval, 30000); // 30 seconds
            },
        }),
        /**
         * The protocols for each RTC ICE candidate types.
         */
        protocolsByCandidateTypes: attr({
            default: {
                'host': "HOST",
                'srflx': "STUN",
                'prflx': "STUN",
                'relay': "TURN",
            },
            readonly: true,
            required: true,
        }),
        /**
         *  timeoutId for the push to talk release delay.
         */
        pushToTalkTimeout: attr(),
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
        callSystrayMenu: one('CallSystrayMenu', {
            default: {},
            inverse: 'rtc',
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
         * Ensures that we always have a single source stream and that replacing it will properly terminate its tracks.
         */
        sourceVideoStream: one('MediaStream', {
            isCausal: true,
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
    },
});
