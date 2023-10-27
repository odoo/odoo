/* @odoo-module */

import { BlurManager } from "@mail/discuss/call/common/blur_manager";
import { monitorAudio } from "@mail/discuss/call/common/media_monitoring";
import { closeStream, onChange } from "@mail/utils/common/misc";

import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";

const ORDERED_TRANSCEIVER_NAMES = ["audio", "screen", "camera"];
const PEER_NOTIFICATION_WAIT_DELAY = 50;
const RECOVERY_TIMEOUT = 15_000;
const RECOVERY_DELAY = 3_000;
const VIDEO_CONFIG = {
    aspectRatio: 16 / 9,
    frameRate: {
        max: 30,
    },
};
const INVALID_ICE_CONNECTION_STATES = new Set(["disconnected", "failed", "closed"]);
const IS_CLIENT_RTC_COMPATIBLE = Boolean(window.RTCPeerConnection && window.MediaStream);
const DEFAULT_ICE_SERVERS = [
    { urls: ["stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302"] },
];

let tmpId = 0;

/**
 * Returns a string representation of a data channel for logging and
 * debugging purposes.
 *
 * @param {RTCDataChannel} dataChannel
 * @returns string
 */
function serializeRTCDataChannel(data) {
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
    return JSON.stringify(Object.fromEntries(toLog.map((p) => [p, data[p]])));
}

/**
 * @param {RTCPeerConnection} peerConnection
 * @param {String} trackKind
 * @returns {RTCRtpTransceiver} the transceiver used for this trackKind.
 */
function getTransceiver(peerConnection, trackKind) {
    const transceivers = peerConnection.getTransceivers();
    return transceivers[ORDERED_TRANSCEIVER_NAMES.indexOf(trackKind)];
}

/**
 * @param {Array<RTCIceServer>} iceServers
 * @returns {Boolean}
 */
function hasTurn(iceServers) {
    return iceServers.some((server) => {
        let hasTurn = false;
        if (server.url) {
            hasTurn = server.url.startsWith("turn:");
        }
        if (server.urls) {
            if (Array.isArray(server.urls)) {
                hasTurn = server.urls.some((url) => url.startsWith("turn:")) || hasTurn;
            } else {
                hasTurn = server.urls.startsWith("turn:") || hasTurn;
            }
        }
        return hasTurn;
    });
}

export class Rtc {
    notifications = reactive(new Map());
    timeouts = new Map();

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.notification = services.notification;
        this.rpc = services.rpc;
        this.soundEffectsService = services["mail.sound_effects"];
        this.userSettingsService = services["mail.user_settings"];
        this.state = reactive({
            hasPendingRequest: false,
            selfSession: undefined,
            channel: undefined,
            iceServers: DEFAULT_ICE_SERVERS,
            logs: new Map(),
            sendCamera: false,
            sendScreen: false,
            updateAndBroadcastDebounce: undefined,
            isPendingNotify: false,
            notificationsToSend: new Map(),
            audioTrack: undefined,
            cameraTrack: undefined,
            screenTrack: undefined,
            /**
             * callback to properly end the audio monitoring.
             * If set it indicates that we are currently monitoring the local
             * audioTrack for the voice activation feature.
             */
            disconnectAudioMonitor: undefined,
            /**
             * Object { sessionId: timeoutId<Number> }
             * Contains the timeoutIds of the reconnection attempts.
             */
            recoverTimeouts: new Map(),
            /**
             * Set of sessionIds, used to track which calls are outgoing,
             * which is used when attempting to recover a failed peer connection by
             * inverting the call direction.
             */
            outgoingSessions: new Set(),
            pttReleaseTimeout: undefined,
            sourceCameraStream: null,
            sourceScreenStream: null,
        });
        this.blurManager = undefined;
        onChange(this.userSettingsService, "useBlur", () => {
            if (this.state.sendCamera) {
                this.toggleVideo("camera", true);
            }
        });
        onChange(this.userSettingsService, ["edgeBlurAmount", "backgroundBlurAmount"], () => {
            if (this.blurManager) {
                this.blurManager.edgeBlur = this.userSettingsService.edgeBlurAmount;
                this.blurManager.backgroundBlur = this.userSettingsService.backgroundBlurAmount;
            }
        });
        onChange(this.userSettingsService, ["voiceActivationThreshold", "usePushToTalk"], () =>
            this.linkVoiceActivation()
        );
        onChange(this.userSettingsService, "audioInputDeviceId", async () => {
            if (this.state.selfSession) {
                await this.resetAudioTrack({ force: true });
            }
        });
        this.env.bus.addEventListener("RTC-SERVICE:PLAY_MEDIA", () => {
            for (const session of this.state.channel.rtcSessions) {
                session.playAudio();
            }
        });
        browser.addEventListener(
            "keydown",
            (ev) => {
                if (
                    !this.state.channel ||
                    this.userSettingsService.isRegisteringKey ||
                    !this.userSettingsService.usePushToTalk ||
                    !this.userSettingsService.isPushToTalkKey(ev)
                ) {
                    return;
                }
                browser.clearTimeout(this.state.pttReleaseTimeout);
                if (!this.state.selfSession.isTalking && !this.state.selfSession.isMute) {
                    this.soundEffectsService.play("push-to-talk-on", { volume: 0.3 });
                }
                this.setTalking(true);
            },
            { capture: true }
        );
        browser.addEventListener(
            "keyup",
            (ev) => {
                if (
                    !this.state.channel ||
                    !this.userSettingsService.usePushToTalk ||
                    !this.userSettingsService.isPushToTalkKey(ev) ||
                    !this.state.selfSession.isTalking
                ) {
                    return;
                }
                this.state.pttReleaseTimeout = browser.setTimeout(() => {
                    this.setTalking(false);
                    if (!this.state.selfSession?.isMute) {
                        this.soundEffectsService.play("push-to-talk-off", { volume: 0.3 });
                    }
                }, Math.max(this.userSettingsService.voiceActiveDuration || 0, 200));
            },
            { capture: true }
        );

        browser.addEventListener("pagehide", () => {
            if (this.state.channel) {
                const data = JSON.stringify({
                    params: { channel_id: this.state.channel.id },
                });
                const blob = new Blob([data], { type: "application/json" });
                // using sendBeacon allows sending a post request even when the
                // browser prevents async requests from firing when the browser
                // is closed. Alternatives like synchronous XHR are not reliable.
                browser.navigator.sendBeacon("/mail/rtc/channel/leave_call", blob);
            }
        });
        /**
         * Call all sessions for which no peerConnection is established at
         * a regular interval to try to recover any connection that failed
         * to start.
         *
         * This is distinct from this.recover which tries to restores
         * connection that were established but failed or timed out.
         */
        browser.setInterval(async () => {
            if (!this.state.selfSession || !this.state.channel) {
                return;
            }
            await this.ping();
            if (!this.state.selfSession || !this.state.channel) {
                return;
            }
            this.call();
        }, 30_000);
    }

    /**
     * @param {Object} param0
     * @param {any} param0.id
     * @param {string} param0.text
     * @param {number} [param0.delay]
     */
    addCallNotification({ id, text, delay = 3000 }) {
        if (this.notifications.has(id)) {
            return;
        }
        this.notifications.set(id, { id, text });
        this.timeouts.set(
            id,
            browser.setTimeout(() => {
                this.notifications.delete(id);
                this.timeouts.delete(id);
            }, delay)
        );
    }

    /**
     * @param {any} id
     */
    removeCallNotification(id) {
        browser.clearTimeout(this.timeouts.get(id));
        this.notifications.delete(id);
        this.timeouts.delete(id);
    }

    /**
     * Notifies the server and does the cleanup of the current call.
     */
    async leaveCall(channel = this.state.channel) {
        await this.rpcLeaveCall(channel);
        this.endCall(channel);
    }

    /**
     * @param {import("models").Thread} [channel]
     */
    endCall(channel = this.state.channel) {
        channel.rtcInvitingSession = undefined;
        channel.activeRtcSession = undefined;
        if (channel.eq(this.state.channel)) {
            this.clear();
            this.soundEffectsService.play("channel-leave");
        }
    }

    async deafen() {
        await this.setDeaf(true);
        this.soundEffectsService.play("deafen");
    }

    async handleNotification(sessionId, content) {
        const { event, channelId, payload } = JSON.parse(content);
        const session = this.state.channel?.rtcSessions.find((session) => session.id === sessionId);
        if (
            !session ||
            !IS_CLIENT_RTC_COMPATIBLE ||
            (!session.peerConnection &&
                (!channelId || !this.state.channel || channelId !== this.state.channel.id))
        ) {
            return;
        }
        switch (event) {
            case "offer": {
                this.log(session, `received notification: ${event}`, {
                    step: "received offer",
                });
                const peerConnection = session.peerConnection || this.createConnection(session);
                if (
                    !peerConnection ||
                    INVALID_ICE_CONNECTION_STATES.has(peerConnection.iceConnectionState) ||
                    peerConnection.signalingState === "have-remote-offer"
                ) {
                    return;
                }
                const description = new window.RTCSessionDescription(payload.sdp);
                try {
                    await peerConnection.setRemoteDescription(description);
                } catch (e) {
                    this.log(session, "offer handling: failed at setting remoteDescription", {
                        error: e,
                    });
                    return;
                }
                if (peerConnection.getTransceivers().length === 0) {
                    for (const trackKind of ORDERED_TRANSCEIVER_NAMES) {
                        const type = ["screen", "camera"].includes(trackKind) ? "video" : trackKind;
                        peerConnection.addTransceiver(type);
                    }
                }
                for (const transceiverName of ORDERED_TRANSCEIVER_NAMES) {
                    await this.updateRemote(session, transceiverName);
                }

                let answer;
                try {
                    answer = await peerConnection.createAnswer();
                } catch (e) {
                    this.log(session, "offer handling: failed at creating answer", {
                        error: e,
                    });
                    return;
                }
                try {
                    await peerConnection.setLocalDescription(answer);
                } catch (e) {
                    this.log(session, "offer handling: failed at setting localDescription", {
                        error: e,
                    });
                    return;
                }

                this.log(session, "sending notification: answer", {
                    step: "sending answer",
                });
                await this.notify([session], "answer", {
                    sdp: peerConnection.localDescription,
                });
                this.recover(session, RECOVERY_TIMEOUT, "standard answer timeout");
                break;
            }
            case "answer": {
                this.log(session, `received notification: ${event}`, {
                    step: "received answer",
                });
                const peerConnection = session.peerConnection;
                if (
                    !peerConnection ||
                    INVALID_ICE_CONNECTION_STATES.has(peerConnection.iceConnectionState) ||
                    peerConnection.signalingState === "stable" ||
                    peerConnection.signalingState === "have-remote-offer"
                ) {
                    return;
                }
                const description = new window.RTCSessionDescription(payload.sdp);
                try {
                    await peerConnection.setRemoteDescription(description);
                } catch (e) {
                    this.log(session, "answer handling: Failed at setting remoteDescription", {
                        error: e,
                    });
                    // ignored the transaction may have been resolved by another concurrent offer.
                }
                break;
            }
            case "ice-candidate": {
                const peerConnection = session.peerConnection;
                if (
                    !peerConnection ||
                    INVALID_ICE_CONNECTION_STATES.has(peerConnection.iceConnectionState)
                ) {
                    return;
                }
                const rtcIceCandidate = new window.RTCIceCandidate(payload.candidate);
                try {
                    await peerConnection.addIceCandidate(rtcIceCandidate);
                } catch (error) {
                    this.log(
                        session,
                        "ICE candidate handling: failed at adding the candidate to the connection",
                        { error }
                    );
                    this.recover(session, RECOVERY_TIMEOUT, "failed at adding ice candidate");
                }
                break;
            }
            case "disconnect":
                this.log(session, `received notification: ${event}`, {
                    step: " peer cleanly disconnected ",
                });
                this.disconnect(session);
                break;
            case "raise_hand":
                Object.assign(session, {
                    raisingHand: payload.active ? new Date() : undefined,
                });
                // eslint-disable-next-line no-case-declarations
                const notificationId = "raise_hand_" + session.id;
                if (session.raisingHand) {
                    this.addCallNotification({
                        id: notificationId,
                        text: _t("%s raised a hand", session.name),
                    });
                } else {
                    this.removeCallNotification(notificationId);
                }
                break;
            case "trackChange": {
                if (payload.type === "audio") {
                    const { isSelfMuted, isTalking, isDeaf } = payload.state;
                    if (!session.audioStream) {
                        return;
                    }
                    Object.assign(session, {
                        isSelfMuted,
                        isTalking,
                        isDeaf,
                    });
                    return;
                }
                /**
                 * Since WebRTC "unified plan", the local track is tied to the
                 * remote transceiver.sender and not the remote track. Therefore
                 * when the remote track is 'ended' the local track is not 'ended'
                 * but only 'muted'. This is why we do not stop the local track
                 * until the peer is completely removed.
                 */
                this.updateActiveSession(session, payload.type);
                session.videoStreams.delete(payload.type);
                session.updateStreamState(payload.type, false);
                break;
            }
        }
    }

    async mute() {
        await this.setMute(true);
        this.soundEffectsService.play("mute");
    }

    /**
     * @param {import("models").Thread} channel
     * @param {Object} [param1={}]
     * @param {boolean} [param1.video]
     */
    async toggleCall(channel, { video } = {}) {
        if (this.state.hasPendingRequest) {
            return;
        }
        this.state.hasPendingRequest = true;
        const isActiveCall = channel.eq(this.state.channel);
        if (this.state.channel) {
            await this.leaveCall(this.state.channel);
        }
        if (!isActiveCall) {
            await this.joinCall(channel, { video });
        }
        this.state.hasPendingRequest = false;
    }

    async toggleMicrophone() {
        if (this.state.selfSession.isMute) {
            await this.unmute();
        } else {
            await this.mute();
        }
    }

    async undeafen() {
        await this.setDeaf(false);
        this.soundEffectsService.play("undeafen");
    }

    async unmute() {
        if (this.state.audioTrack) {
            await this.setMute(false);
        } else {
            await this.resetAudioTrack({ force: true });
        }
        this.soundEffectsService.play("unmute");
    }

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @param {RtcSession} session
     * @param {String} entry
     * @param {Object} [param2]
     * @param {Error} [param2.error]
     * @param {String} [param2.step] current step of the flow
     * @param {String} [param2.state] current state of the connection
     */
    log(session, entry, { error, step, state, ...data } = {}) {
        session.logStep = entry;
        if (!this.userSettingsService.logRtc) {
            return;
        }
        if (!this.state.logs.has(session.id)) {
            this.state.logs.set(session.id, { step: "", state: "", logs: [] });
        }
        if (step) {
            this.state.logs.get(session.id).step = step;
        }
        if (state) {
            this.state.logs.get(session.id).state = state;
        }
        const trace = window.Error().stack || "";
        this.state.logs.get(session.id).logs.push({
            event: `${luxon.DateTime.now().toFormat("HH:mm:ss")}: ${entry}`,
            error: error && {
                name: error.name,
                message: error.message,
                stack: error.stack && error.stack.split("\n"),
            },
            trace: trace.split("\n"),
            ...data,
        });
    }

    async connect(session) {
        this.createConnection(session);
        for (const transceiverName of ORDERED_TRANSCEIVER_NAMES) {
            await this.updateRemote(session, transceiverName);
        }
        this.state.outgoingSessions.add(session.id);
    }

    call() {
        if (this.state.channel.rtcSessions.length === 0) {
            return;
        }
        for (const session of this.state.channel.rtcSessions) {
            if (session.peerConnection || session.eq(this.state.selfSession)) {
                continue;
            }
            this.log(session, "init call", { step: "init call" });
            this.connect(session);
        }
    }

    createConnection(session) {
        const peerConnection = new window.RTCPeerConnection({ iceServers: this.state.iceServers });
        this.log(session, "RTCPeerConnection created", {
            step: "peer connection created",
        });
        peerConnection.onicecandidate = async (event) => {
            if (!event.candidate) {
                return;
            }
            await this.notify([session], "ice-candidate", {
                candidate: event.candidate,
            });
        };
        peerConnection.oniceconnectionstatechange = async (event) => {
            this.log(
                session,
                `ICE connection state changed: ${peerConnection.iceConnectionState}`,
                {
                    state: peerConnection.iceConnectionState,
                }
            );
            if (!this.state.channel.rtcSessions.some((s) => s.id === session.id)) {
                return;
            }
            session.connectionState = peerConnection.iceConnectionState;
            switch (peerConnection.iceConnectionState) {
                case "closed":
                    this.disconnect(session);
                    break;
                case "failed":
                case "disconnected":
                    await this.recover(
                        session,
                        RECOVERY_DELAY,
                        `ice connection ${peerConnection.iceConnectionState}`
                    );
                    break;
            }
        };
        peerConnection.onicegatheringstatechange = (event) => {
            this.log(session, `ICE gathering state changed: ${peerConnection.iceGatheringState}`);
        };
        peerConnection.onconnectionstatechange = async (event) => {
            this.log(session, `connection state changed: ${peerConnection.connectionState}`);
            switch (peerConnection.connectionState) {
                case "closed":
                    this.disconnect(session);
                    break;
                case "failed":
                case "disconnected":
                    await this.recover(
                        session,
                        RECOVERY_DELAY,
                        `connection ${peerConnection.connectionState}`
                    );
                    break;
            }
        };
        peerConnection.onicecandidateerror = async (error) => {
            this.log(session, "ice candidate error");
            this.recover(session, RECOVERY_TIMEOUT, "ice candidate error");
        };
        peerConnection.onnegotiationneeded = async (event) => {
            const offer = await peerConnection.createOffer();
            try {
                await peerConnection.setLocalDescription(offer);
            } catch (error) {
                // Possibly already have a remote offer here: cannot set local description
                this.log(session, "couldn't setLocalDescription", { error });
                return;
            }
            this.log(session, "sending notification: offer", {
                step: "sending offer",
            });
            await this.notify([session], "offer", {
                sdp: peerConnection.localDescription,
            });
        };
        peerConnection.ontrack = ({ transceiver, track }) => {
            this.log(session, `received ${track.kind} track`);
            this.handleRemoteTrack({
                session,
                track,
                type: this.getTransceiverType(session.peerConnection, transceiver),
            });
        };
        const dataChannel = peerConnection.createDataChannel("notifications", {
            negotiated: true,
            id: 1,
        });
        dataChannel.onmessage = (event) => {
            this.handleNotification(session.id, event.data);
        };
        dataChannel.onopen = async () => {
            /**
             * FIXME? it appears that the track yielded by the peerConnection's 'ontrack' event is always enabled,
             * even when it is disabled on the sender-side.
             */
            try {
                await this.notify([session], "trackChange", {
                    type: "audio",
                    state: {
                        isTalking: this.state.selfSession.isTalking,
                        isSelfMuted: this.state.selfSession.isSelfMuted,
                    },
                });
                await this.notify([session], "raise_hand", {
                    active: Boolean(this.state.selfSession.raisingHand),
                });
            } catch (e) {
                if (!(e instanceof DOMException) || e.name !== "OperationError") {
                    throw e;
                }
                this.log(
                    session,
                    `failed to send on datachannel; dataChannelInfo: ${serializeRTCDataChannel(
                        dataChannel
                    )}`,
                    { error: e }
                );
            }
        };
        Object.assign(session, {
            peerConnection,
            dataChannel,
            connectionState: "connecting",
        });
        return peerConnection;
    }

    /**
     * @param {import("@mail/discuss/call/common/rtc_session_model").RtcSession} session
     * @param {MediaStreamTrack} track
     * @param {"audio" | "screen" | "camera"} type
     * @param {boolean} active false if the track is muted/disabled
     */
    async handleRemoteTrack({ session, track, type, active = true }) {
        session.updateStreamState(type, active);
        await this.updateStream(session, track, {
            mute: this.state.selfSession.isDeaf,
            videoType: type,
        });
        this.updateActiveSession(session, type, { addVideo: true });
    }

    /**
     * @param {RTCPeerConnection} peerConnection
     * @param {RTCRtpTransceiver} transceiver
     */
    getTransceiverType(peerConnection, transceiver) {
        const transceivers = peerConnection.getTransceivers();
        return ORDERED_TRANSCEIVER_NAMES[transceivers.indexOf(transceiver)];
    }

    /**
     * @param {import("models").Thread}
     */
    async joinCall(channel, { video = false } = {}) {
        if (!IS_CLIENT_RTC_COMPATIBLE) {
            this.notification.add(_t("Your browser does not support webRTC."), { type: "warning" });
            return;
        }
        const { rtcSessions, iceServers, sessionId } = await this.rpc(
            "/mail/rtc/channel/join_call",
            {
                channel_id: channel.id,
                check_rtc_session_ids: channel.rtcSessions.map((session) => session.id),
            },
            { silent: true }
        );
        // Initializing a new session implies closing the current session.
        this.clear();
        this.state.logs.clear();
        this.state.channel = channel;
        this.state.channel.rtcSessions = rtcSessions;
        this.state.selfSession = this.store.RtcSession.get(sessionId);
        this.state.iceServers = iceServers || DEFAULT_ICE_SERVERS;
        this.state.logs.set("channelId", this.state.channel?.id);
        this.state.logs.set("selfSessionId", this.state.selfSession?.id);
        this.state.logs.set("hasTURN", hasTurn(this.state.iceServers));
        const channelProxy = reactive(this.state.channel, () => {
            if (channel.notEq(this.state.channel)) {
                throw new Error("channel has changed");
            }
            if (this.state.channel) {
                if (this.state.channel && this.state.selfSession.notIn(channelProxy.rtcSessions)) {
                    // if the current RTC session is not in the channel sessions, this call is no longer valid.
                    this.endCall();
                    return;
                }
                for (const session of this.state.channel.rtcSessions) {
                    if (session.notIn(channelProxy.rtcSessions)) {
                        this.log(session, "session removed from the server");
                        this.disconnect(session);
                    }
                }
            }
            void channelProxy.rtcSessions.map((s) => s);
        });
        this.state.updateAndBroadcastDebounce = debounce(
            async () => {
                if (!this.state.selfSession) {
                    return;
                }
                await this.rpc(
                    "/mail/rtc/session/update_and_broadcast",
                    {
                        session_id: this.state.selfSession.id,
                        values: {
                            is_camera_on: this.state.selfSession.isCameraOn,
                            is_deaf: this.state.selfSession.isDeaf,
                            is_muted: this.state.selfSession.isSelfMuted,
                            is_screen_sharing_on: this.state.selfSession.isScreenSharingOn,
                        },
                    },
                    { silent: true }
                );
            },
            3000,
            true
        );
        this.state.channel.rtcInvitingSession = undefined;
        this.call();
        this.soundEffectsService.play("channel-join");
        await this.resetAudioTrack({ force: true });
        if (video) {
            await this.toggleVideo("camera");
        }
    }

    /**
     * @param {RtcSession[]} sessions
     * @param {String} event
     * @param {Object} [payload]
     */
    async notify(sessions, event, payload) {
        if (!sessions.length || !this.state.channel.id || !this.state.selfSession) {
            return;
        }
        if (event === "trackChange") {
            // p2p
            for (const session of sessions) {
                if (!session?.dataChannel || session?.dataChannel.readyState !== "open") {
                    continue;
                }
                session.dataChannel.send(
                    JSON.stringify({
                        event,
                        channelId: this.state.channel.id,
                        payload,
                    })
                );
            }
        } else {
            // server
            this.state.notificationsToSend.set(++tmpId, {
                channelId: this.state.channel.id,
                event,
                payload,
                sender: this.state.selfSession,
                sessions,
            });
            await this.sendNotifications();
        }
    }

    async rpcLeaveCall(channel) {
        await this.rpc(
            "/mail/rtc/channel/leave_call",
            {
                channel_id: channel.id,
            },
            { silent: true }
        );
    }

    async ping() {
        const { rtcSessions } = await this.rpc(
            "/discuss/channel/ping",
            {
                channel_id: this.state.channel.id,
                check_rtc_session_ids: this.state.channel.rtcSessions.map((session) => session.id),
                rtc_session_id: this.state.selfSession.id,
            },
            { silent: true }
        );
        if (this.state.channel && rtcSessions) {
            const activeSessionsData = rtcSessions[0][1];
            for (const sessionData of activeSessionsData) {
                this.state.channel.rtcSessions.add(sessionData);
            }
            const outdatedSessionsData = rtcSessions[1][1];
            for (const sessionData of outdatedSessionsData) {
                this.deleteSession(sessionData);
            }
        }
    }

    /**
     * @param {number} [delay] in ms
     */
    recover(session, delay = 0, reason = "") {
        if (this.state.recoverTimeouts.get(session.id)) {
            return;
        }
        this.state.recoverTimeouts.set(
            session.id,
            browser.setTimeout(async () => {
                this.state.recoverTimeouts.delete(session.id);
                const peerConnection = session.peerConnection;
                if (
                    !peerConnection ||
                    !this.state.channel.id ||
                    this.state.outgoingSessions.has(session.id) ||
                    peerConnection.iceConnectionState === "connected"
                ) {
                    return;
                }
                if (this.userSettingsService.logRtc) {
                    let stats;
                    try {
                        const iterableStats = await peerConnection.getStats();
                        stats = iterableStats && [...iterableStats.values()];
                    } catch {
                        // ignore
                    }
                    this.log(
                        session,
                        `calling back to recover "${peerConnection.iceConnectionState}" connection`,
                        { reason, stats }
                    );
                }
                await this.notify([session], "disconnect");
                this.disconnect(session);
                this.connect(session);
            }, delay)
        );
    }

    disconnect(session) {
        this.removeCallNotification("raise_hand_" + session.id);
        closeStream(session.audioStream);
        if (session.audioElement) {
            session.audioElement.pause();
            try {
                session.audioElement.srcObject = undefined;
            } catch {
                // ignore error during remove, the value will be overwritten at next usage anyway
            }
        }
        session.audioStream = undefined;
        session.connectionState = undefined;
        session.localCandidateType = undefined;
        session.remoteCandidateType = undefined;
        session.dataChannelState = undefined;
        session.packetsReceived = undefined;
        session.packetsSent = undefined;
        session.dtlsState = undefined;
        session.iceState = undefined;
        session.raisingHand = undefined;
        session.logStep = undefined;
        session.audioError = undefined;
        session.videoError = undefined;
        session.isTalking = false;
        session.mainVideoStreamType = undefined;
        this.removeVideoFromSession(session);
        session.dataChannel?.close();
        delete session.dataChannel;
        const peerConnection = session.peerConnection;
        if (peerConnection) {
            const RTCRtpSenders = peerConnection.getSenders();
            for (const sender of RTCRtpSenders) {
                try {
                    peerConnection.removeTrack(sender);
                } catch {
                    // ignore error
                }
            }
            for (const transceiver of peerConnection.getTransceivers()) {
                try {
                    transceiver.stop();
                } catch {
                    // transceiver may already be stopped by the remote.
                }
            }
            peerConnection.close();
            session.peerConnection = undefined;
        }
        browser.clearTimeout(this.state.recoverTimeouts.get(session.id));
        this.state.recoverTimeouts.delete(session.id);
        this.state.outgoingSessions.delete(session.id);
        this.log(session, "peer removed", { step: "peer removed" });
    }

    clear() {
        for (const session of Object.values(this.store.RtcSession.records)) {
            this.disconnect(session);
        }
        for (const timeoutId of this.state.recoverTimeouts.values()) {
            clearTimeout(timeoutId);
        }
        this.state.recoverTimeouts.clear();
        this.state.updateAndBroadcastDebounce?.cancel();
        this.state.disconnectAudioMonitor?.();
        this.state.audioTrack?.stop();
        this.state.cameraTrack?.stop();
        this.state.screenTrack?.stop();
        this.state.notificationsToSend.clear();
        closeStream(this.state.sourceCameraStream);
        this.state.sourceCameraStream = null;
        if (this.blurManager) {
            this.blurManager.close();
            this.blurManager = undefined;
        }
        Object.assign(this.state, {
            updateAndBroadcastDebounce: undefined,
            disconnectAudioMonitor: undefined,
            outgoingSessions: new Set(),
            cameraTrack: undefined,
            screenTrack: undefined,
            audioTrack: undefined,
            selfSession: undefined,
            sendCamera: false,
            sendScreen: false,
            channel: undefined,
        });
    }

    async sendNotifications() {
        if (this.state.isPendingNotify) {
            return;
        }
        this.state.isPendingNotify = true;
        await new Promise((resolve) => setTimeout(resolve, PEER_NOTIFICATION_WAIT_DELAY));
        const ids = [];
        const notifications = [];
        this.state.notificationsToSend.forEach((notification, id) => {
            ids.push(id);
            notifications.push([
                notification.sender.id,
                notification.sessions.map((session) => session.id),
                JSON.stringify({
                    event: notification.event,
                    channelId: notification.channelId,
                    payload: notification.payload,
                }),
            ]);
        });
        try {
            await this.rpc(
                "/mail/rtc/session/notify_call_members",
                {
                    peer_notifications: notifications,
                },
                { silent: true }
            );
            for (const id of ids) {
                this.state.notificationsToSend.delete(id);
            }
        } finally {
            this.state.isPendingNotify = false;
            if (this.state.notificationsToSend.size > 0) {
                this.sendNotifications();
            }
        }
    }

    /**
     * @param {Boolean} isDeaf
     */
    async setDeaf(isDeaf) {
        this.updateAndBroadcast({ isDeaf });
        for (const session of this.state.channel.rtcSessions) {
            if (!session.audioElement) {
                continue;
            }
            session.audioElement.muted = isDeaf;
        }
        await this.refreshAudioStatus();
    }

    /**
     * @param {Boolean} isSelfMuted
     */
    async setMute(isSelfMuted) {
        this.updateAndBroadcast({ isSelfMuted });
        await this.refreshAudioStatus();
    }

    /**
     * @param {Boolean} raise
     */
    async raiseHand(raise) {
        if (!this.state.selfSession || !this.state.channel) {
            return;
        }
        this.state.selfSession.raisingHand = raise ? new Date() : undefined;
        await this.notify(this.state.channel.rtcSessions, "raise_hand", {
            active: this.state.selfSession.raisingHand,
        });
    }

    /**
     * @param {boolean} isTalking
     */
    async setTalking(isTalking) {
        if (!this.state.selfSession || isTalking === this.state.selfSession.isTalking) {
            return;
        }
        this.state.selfSession.isTalking = isTalking;
        if (!this.state.selfSession.isMute) {
            await this.refreshAudioStatus();
        }
    }

    /**
     * @param {string} type
     * @param {boolean} [force]
     */
    async toggleVideo(type, force) {
        if (!this.state.channel.id) {
            return;
        }
        switch (type) {
            case "camera": {
                const track = this.state.cameraTrack;
                const sendCamera = force ?? !this.state.sendCamera;
                this.state.sendCamera = false;
                await this.setVideo(track, type, sendCamera);
                break;
            }
            case "screen": {
                const track = this.state.screenTrack;
                const sendScreen = force ?? !this.state.sendScreen;
                this.state.sendScreen = false;
                await this.setVideo(track, type, sendScreen);
                break;
            }
        }
        if (this.state.selfSession) {
            switch (type) {
                case "camera": {
                    this.removeVideoFromSession(this.state.selfSession, "camera");
                    if (this.state.cameraTrack) {
                        this.updateStream(this.state.selfSession, this.state.cameraTrack);
                    }
                    break;
                }
                case "screen": {
                    if (!this.state.screenTrack) {
                        this.removeVideoFromSession(this.state.selfSession, "screen");
                    } else {
                        this.updateStream(this.state.selfSession, this.state.screenTrack);
                    }
                    break;
                }
            }
        }
        for (const session of this.state.channel.rtcSessions) {
            if (session.eq(this.state.selfSession)) {
                continue;
            }
            await this.updateRemote(session, type);
        }
        if (!this.state.selfSession) {
            return;
        }
        switch (type) {
            case "camera": {
                this.updateAndBroadcast({
                    isCameraOn: !!this.state.sendCamera,
                });
                break;
            }
            case "screen": {
                this.updateAndBroadcast({
                    isScreenSharingOn: !!this.state.sendScreen,
                });
                break;
            }
        }
    }

    updateAndBroadcast(data) {
        const session = this.state.selfSession;
        Object.assign(session, data);
        this.state.updateAndBroadcastDebounce?.();
    }

    /**
     * Sets the enabled property of the local audio track based on the
     * current session state. And notifies peers of the new audio state.
     */
    async refreshAudioStatus() {
        if (!this.state.audioTrack) {
            return;
        }
        this.state.audioTrack.enabled =
            !this.state.selfSession.isMute && this.state.selfSession.isTalking;
        await this.notify(this.state.channel.rtcSessions, "trackChange", {
            type: "audio",
            state: {
                isTalking: this.state.selfSession.isTalking && !this.state.selfSession.isSelfMuted,
                isSelfMuted: this.state.selfSession.isSelfMuted,
                isDeaf: this.state.selfSession.isDeaf,
            },
        });
    }

    /**
     * @param {String} type 'camera' or 'screen'
     */
    async setVideo(track, type, activateVideo = false) {
        if (this.blurManager) {
            this.blurManager.close();
            this.blurManager = undefined;
        }
        const stopVideo = () => {
            if (track) {
                track.stop();
            }
            switch (type) {
                case "camera": {
                    this.state.cameraTrack = undefined;
                    closeStream(this.state.sourceCameraStream);
                    this.state.sourceCameraStream = null;
                    break;
                }
                case "screen": {
                    this.state.screenTrack = undefined;
                    closeStream(this.state.sourceScreenStream);
                    this.state.sourceScreenStream = null;
                    break;
                }
            }
        };
        if (!activateVideo) {
            if (type === "screen") {
                this.soundEffectsService.play("screen-sharing");
            }
            stopVideo();
            return;
        }
        let sourceStream;
        try {
            if (type === "camera") {
                if (this.state.sourceCameraStream && this.state.sendCamera) {
                    sourceStream = this.state.sourceCameraStream;
                } else {
                    sourceStream = await browser.navigator.mediaDevices.getUserMedia({
                        video: VIDEO_CONFIG,
                    });
                }
            }
            if (type === "screen") {
                if (this.state.sourceScreenStream && this.state.sendScreen) {
                    sourceStream = this.state.sourceScreenStream;
                } else {
                    sourceStream = await browser.navigator.mediaDevices.getDisplayMedia({
                        video: VIDEO_CONFIG,
                    });
                }
                this.soundEffectsService.play("screen-sharing");
            }
        } catch {
            const str =
                type === "camera"
                    ? _t('%s" requires "camera" access', window.location.host)
                    : _t('%s" requires "screen recording" access', window.location.host);
            this.notification.add(str, { type: "warning" });
            stopVideo();
            return;
        }
        let videoStream = sourceStream;
        if (this.userSettingsService.useBlur && type === "camera") {
            try {
                this.blurManager = new BlurManager(sourceStream, {
                    backgroundBlur: this.userSettingsService.backgroundBlurAmount,
                    edgeBlur: this.userSettingsService.edgeBlurAmount,
                });
                videoStream = await this.blurManager.stream;
            } catch (_e) {
                this.notification.add(
                    _t("%(name)s: %(message)s)", { name: _e.name, message: _e.message }),
                    { type: "warning" }
                );
                this.userSettingsService.useBlur = false;
            }
        }
        track = videoStream ? videoStream.getVideoTracks()[0] : undefined;
        if (track) {
            track.addEventListener("ended", async () => {
                await this.toggleVideo(type, false);
            });
        }
        switch (type) {
            case "camera": {
                Object.assign(this.state, {
                    sourceCameraStream: sourceStream,
                    cameraTrack: track,
                    sendCamera: Boolean(type === "camera" && track),
                });
                break;
            }
            case "screen": {
                Object.assign(this.state, {
                    sourceScreenStream: sourceStream,
                    screenTrack: track,
                    sendScreen: Boolean(type === "screen" && track),
                });
                break;
            }
        }
    }

    /**
     * Updates the track that is broadcasted to the RTCPeerConnection.
     * This will start new transaction by triggering a negotiationneeded event
     * on the peerConnection given as parameter.
     *
     * negotiationneeded -> offer -> answer -> ...
     */
    async updateRemote(session, trackKind) {
        this.log(session, `updating ${trackKind} transceiver`);
        let track;
        switch (trackKind) {
            case "audio": {
                track = this.state.audioTrack;
                break;
            }
            case "camera": {
                track = this.state.cameraTrack;
                break;
            }
            case "screen": {
                track = this.state.screenTrack;
                break;
            }
        }
        let transceiverDirection = track ? "sendrecv" : "recvonly";
        if (trackKind !== "audio") {
            transceiverDirection = this.getTransceiverDirection(session, Boolean(track));
        }
        const transceiver = getTransceiver(session.peerConnection, trackKind);
        try {
            await transceiver.sender.replaceTrack(track || null);
            transceiver.direction = transceiverDirection;
        } catch {
            this.log(session, `failed to update ${trackKind} transceiver`);
        }
        if (!track && trackKind !== "audio") {
            this.notify([session], "trackChange", {
                type: this.getTransceiverType(session.peerConnection, transceiver),
            });
        }
    }

    async resetAudioTrack({ force = false }) {
        if (this.state.audioTrack) {
            this.state.audioTrack.stop();
            this.state.audioTrack = undefined;
        }
        if (!this.state.channel) {
            return;
        }
        if (force) {
            let audioTrack;
            try {
                const audioStream = await browser.navigator.mediaDevices.getUserMedia({
                    audio: this.userSettingsService.audioConstraints,
                });
                audioTrack = audioStream.getAudioTracks()[0];
            } catch {
                this.notification.add(
                    _t('"%(hostname)s" requires microphone access', {
                        hostname: window.location.host,
                    }),
                    { type: "warning" }
                );
                if (this.state.selfSession) {
                    this.updateAndBroadcast({ isSelfMuted: true });
                }
                return;
            }
            if (!this.state.selfSession) {
                // The getUserMedia promise could resolve when the call is ended
                // in which case the track is no longer relevant.
                audioTrack.stop();
                return;
            }
            audioTrack.addEventListener("ended", async () => {
                // this mostly happens when the user retracts microphone permission.
                await this.resetAudioTrack({ force: false });
                this.updateAndBroadcast({ isSelfMuted: true });
                await this.refreshAudioStatus();
            });
            this.updateAndBroadcast({ isSelfMuted: false });
            audioTrack.enabled = !this.state.selfSession.isMute && this.state.selfSession.isTalking;
            this.state.audioTrack = audioTrack;
            await this.linkVoiceActivation();
            for (const session of this.state.channel.rtcSessions) {
                if (session.eq(this.state.selfSession)) {
                    continue;
                }
                await this.updateRemote(session, "audio");
            }
        }
    }

    /**
     * Updates the way broadcast of the local audio track is handled,
     * attaches an audio monitor for voice activation if necessary.
     */
    async linkVoiceActivation() {
        this.state.disconnectAudioMonitor?.();
        if (!this.state.selfSession) {
            return;
        }
        if (
            this.userSettingsService.usePushToTalk ||
            !this.state.channel ||
            !this.state.audioTrack
        ) {
            this.state.selfSession.isTalking = false;
            await this.refreshAudioStatus();
            return;
        }
        try {
            this.state.disconnectAudioMonitor = await monitorAudio(this.state.audioTrack, {
                onThreshold: async (isAboveThreshold) => {
                    this.setTalking(isAboveThreshold);
                },
                volumeThreshold: this.userSettingsService.voiceActivationThreshold,
            });
        } catch {
            /**
             * The browser is probably missing audioContext,
             * in that case, voice activation is not enabled
             * and the microphone is always 'on'.
             */
            this.notification.add(_t("Your browser does not support voice activation"), {
                type: "warning",
            });
            this.state.selfSession.isTalking = true;
        }
        await this.refreshAudioStatus();
    }

    /**
     * @param {import("models").id} id
     */
    deleteSession(id) {
        const session = this.store.RtcSession.get(id);
        if (session) {
            if (this.state.selfSession && session.eq(this.state.selfSession)) {
                this.endCall();
            }
            this.disconnect(session);
            session.delete();
        }
    }

    /**
     * @param {RtcSession} session
     * @param {MediaStreamTrack} track
     * @param {Object} [parm1]
     * @param {boolean} [parm1.mute]
     * @param {"camera"|"screen"} [parm1.videoType]
     */
    async updateStream(session, track, { mute, videoType } = {}) {
        const stream = new window.MediaStream();
        stream.addTrack(track);
        if (track.kind === "audio") {
            const audioElement = session.audioElement || new window.Audio();
            audioElement.srcObject = stream;
            audioElement.load();
            audioElement.muted = mute;
            audioElement.volume = this.userSettingsService.getVolume(session);
            // Using both autoplay and play() as safari may prevent play() outside of user interactions
            // while some browsers may not support or block autoplay.
            audioElement.autoplay = true;
            session.audioElement = audioElement;
            session.audioStream = stream;
            session.isSelfMuted = false;
            session.isTalking = false;
            await session.playAudio();
        }
        if (track.kind === "video") {
            videoType = videoType
                ? videoType
                : track.id === this.state.cameraTrack?.id
                ? "camera"
                : "screen";
            session.videoStreams.set(videoType, stream);
            this.updateActiveSession(session, videoType, { addVideo: true });
        }
    }

    /**
     * @param {RtcSession} session
     * @param {String} [videoType]
     */
    removeVideoFromSession(session, videoType = false) {
        if (videoType) {
            this.updateActiveSession(session, videoType);
            closeStream(session.videoStreams.get(videoType));
            session.videoStreams.delete(videoType);
        } else {
            for (const stream of session.videoStreams.values()) {
                closeStream(stream);
            }
            session.videoStreams.clear();
        }
    }

    /**
     * @param {RtcSession} session
     * @param {"screen"|"camera"} [videoType]
     * @param {Object} [parm2]
     * @param {boolean} [parm2.addVideo]
     */
    updateActiveSession(session, videoType, { addVideo = false } = {}) {
        const activeRtcSession = this.state.channel.activeRtcSession;
        if (addVideo) {
            if (videoType === "screen") {
                this.state.channel.activeRtcSession = session;
                session.mainVideoStreamType = videoType;
                return;
            }
            if (activeRtcSession && session.hasVideo && !session.isMainVideoStreamActive) {
                session.mainVideoStreamType = videoType;
            }
            return;
        }
        if (!activeRtcSession || activeRtcSession.notEq(session)) {
            return;
        }
        if (activeRtcSession.isMainVideoStreamActive) {
            if (videoType === session.mainVideoStreamType) {
                if (videoType === "screen") {
                    this.state.channel.activeRtcSession = undefined;
                } else {
                    session.mainVideoStreamType = "screen";
                }
            }
        }
    }

    updateVideoDownload(rtcSession, { viewCountIncrement }) {
        rtcSession.videoComponentCount += viewCountIncrement;
        if (!rtcSession.peerConnection) {
            return;
        }
        const transceivers = rtcSession.peerConnection.getTransceivers();
        const cameraTransceiver = transceivers[ORDERED_TRANSCEIVER_NAMES.indexOf("camera")];
        const screenTransceiver = transceivers[ORDERED_TRANSCEIVER_NAMES.indexOf("screen")];
        if (cameraTransceiver) {
            cameraTransceiver.direction = this.getTransceiverDirection(
                rtcSession,
                Boolean(this.state.cameraTrack)
            );
        }
        if (screenTransceiver) {
            screenTransceiver.direction = this.getTransceiverDirection(
                rtcSession,
                Boolean(this.state.screenTrack)
            );
        }
    }

    getTransceiverDirection(session, allowUpload = false) {
        if (session.videoComponentCount > 0) {
            return allowUpload ? "sendrecv" : "recvonly";
        } else {
            return allowUpload ? "sendonly" : "inactive";
        }
    }

    updateRtcSessions(channelId, sessionsData) {
        const channel = this.store.Thread.get({ model: "discuss.channel", id: channelId });
        if (!channel) {
            return;
        }
        const oldCount = channel.rtcSessions.length;
        channel.rtcSessions = sessionsData;
        if (channel.rtcSessions.length > oldCount) {
            this.soundEffectsService.play("channel-join");
        } else if (channel.rtcSessions.length < oldCount) {
            this.soundEffectsService.play("member-leave");
        }
    }
}

export const rtcService = {
    dependencies: [
        "bus_service",
        "mail.sound_effects",
        "mail.store",
        "mail.user_settings",
        "notification",
        "rpc",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const rtc = new Rtc(env, services);
        services["bus_service"].subscribe(
            "discuss.channel.rtc.session/peer_notification",
            ({ sender, notifications }) => {
                for (const content of notifications) {
                    rtc.handleNotification(sender, content);
                }
            }
        );
        services["bus_service"].subscribe("discuss.channel.rtc.session/ended", ({ sessionId }) => {
            if (rtc.state.selfSession?.id === sessionId) {
                rtc.endCall();
                services.notification.add(_t("Disconnected from the RTC call by the server"), {
                    type: "warning",
                });
            }
        });
        services["bus_service"].subscribe(
            "discuss.channel/rtc_sessions_update",
            ({ id, rtcSessions }) => {
                rtc.updateRtcSessions(id, rtcSessions);
            }
        );
        services["bus_service"].subscribe("discuss.channel/joined", ({ channel }) => {
            rtc.updateRtcSessions(channel.id, channel.rtcSessions);
        });
        services["bus_service"].subscribe("res.users.settings.volumes", (payload) => {
            if (payload) {
                services["mail.user_settings"].setVolumes(payload);
            }
        });
        services["bus_service"].subscribe(
            "discuss.channel.rtc.session/update_and_broadcast",
            (payload) => {
                const { data, channelId } = payload;
                /**
                 * If this event comes from the channel of the current call, information is shared in real time
                 * through the peer to peer connection. So we do not use this less accurate broadcast.
                 */
                if (channelId !== rtc.state.channel?.id) {
                    rtc.store.RtcSession.insert(data);
                }
            }
        );
        return rtc;
    },
};

registry.category("services").add("discuss.rtc", rtcService);
