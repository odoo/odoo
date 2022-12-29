/** @odoo-module */

import { browser } from "@web/core/browser/browser";

import { monitorAudio } from "./media_monitoring";
import { BlurManager } from "./blur_manager";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { reactive } from "@odoo/owl";

import { RtcSession } from "./rtc_session_model";
import { debounce } from "@web/core/utils/timing";
import { closeStream, createLocalId, onChange } from "../utils/misc";
import { registry } from "@web/core/registry";

const ORDERED_TRANSCEIVER_NAMES = ["audio", "video"];
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
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        this.notification = services.notification;
        this.rpc = services.rpc;
        /** @type {import("@mail/new/core/channel_member_service").ChannelMemberService} */
        this.channelMemberService = services["mail.channel.member"];
        /** @type {import("@mail/new/core/sound_effects_service").SoundEffects} */
        this.soundEffectsService = services["mail.sound_effects"];
        /** @type {import("@mail/new/core/user_settings_service").UserSettings} */
        this.userSettingsService = services["mail.user_settings"];
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
        /** @type {import("@mail/new/core/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
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
            videoTrack: undefined,
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
        });
        this.blur = undefined;
        this.ringingThreads = reactive([], () => this.onRingingThreadsChange());
        void this.ringingThreads.length;
        this.store.ringingThreads = this.ringingThreads;
        onChange(this.userSettingsService, "useBlur", () => {
            if (this.state.sendCamera) {
                this.toggleVideo("camera", true);
            }
        });
        onChange(this.userSettingsService, "edgeBlurAmount", () => {
            if (this.blurManager) {
                this.blurManager.edgeBlur = this.userSettingsService.edgeBlurAmount;
            }
        });
        onChange(this.userSettingsService, "backgroundBlurAmount", () => {
            if (this.blurManager) {
                this.blurManager.backgroundBlur = this.userSettingsService.backgroundBlurAmount;
            }
        });
        onChange(this.userSettingsService, "voiceActivationThreshold", async () => {
            await this.linkVoiceActivation();
        });
        onChange(this.userSettingsService, "usePushToTalk", async () => {
            await this.linkVoiceActivation();
        });
        onChange(this.userSettingsService, "audioInputDeviceId", async () => {
            if (this.state.selfSession) {
                await this.resetAudioTrack({ force: true });
            }
        });
        this.env.bus.addEventListener(
            "THREAD-SERVICE:UPDATE_RTC_SESSIONS",
            ({ detail: { commands = [], record, thread } }) => {
                if (record) {
                    const session = this.insertSession(record);
                    thread.rtcSessions[session.id] = session;
                }
                for (const command of commands) {
                    const sessionsData = command[1];
                    switch (command[0]) {
                        case "insert-and-unlink":
                            for (const rtcSessionData of sessionsData) {
                                this.deleteSession(rtcSessionData.id);
                            }
                            break;
                        case "insert":
                            for (const rtcSessionData of sessionsData) {
                                const session = this.insertSession(rtcSessionData);
                                thread.rtcSessions[session.id] = session;
                            }
                            break;
                    }
                }
            }
        );

        browser.addEventListener("keydown", (ev) => {
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
        });
        browser.addEventListener("keyup", (ev) => {
            if (
                !this.state.channel ||
                !this.userSettingsService.usePushToTalk ||
                !this.userSettingsService.isPushToTalkKey(ev, { ignoreModifiers: true }) ||
                !this.state.selfSession.isTalking
            ) {
                return;
            }
            if (!this.state.selfSession.isMute) {
                this.soundEffectsService.play("push-to-talk-off", { volume: 0.3 });
            }
            this.state.pttReleaseTimeout = browser.setTimeout(
                () => this.setTalking(false),
                this.userSettingsService.voiceActiveDuration || 0
            );
        });

        browser.addEventListener("beforeunload", async (ev) => {
            if (this.state.channel) {
                await this.rpcLeaveCall(this.state.channel);
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
     * Notifies the server and does the cleanup of the current call.
     */
    async leaveCall(channel = this.state.channel) {
        await this.rpcLeaveCall(channel);
        this.endCall(channel);
    }

    /**
     * @param {import("@mail/new/core/thread_model").Thread} [channel]
     */
    endCall(channel = this.state.channel) {
        channel.rtcInvitingSessionId = undefined;
        if (this.state.channel === channel) {
            this.clear();
            this.soundEffectsService.play("channel-leave");
        }
    }

    onRingingThreadsChange() {
        if (this.ringingThreads.length > 0) {
            this.soundEffectsService.play("incoming-call", { loop: true });
        } else {
            this.soundEffectsService.stop("incoming-call");
        }
    }

    async deafen() {
        await this.setDeaf(true);
        this.soundEffectsService.play("deafen");
    }

    async handleNotification(sessionId, content) {
        const { event, channelId, payload } = JSON.parse(content);
        const session = this.state.channel?.rtcSessions[sessionId];
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
                await this.updateRemote(session, "audio");
                await this.updateRemote(session, "video");

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
            case "trackChange": {
                const { isSelfMuted, isTalking, isSendingVideo, isDeaf } = payload.state;
                if (payload.type === "audio") {
                    if (!session.audioStream) {
                        return;
                    }
                    Object.assign(session, {
                        isSelfMuted,
                        isTalking,
                        isDeaf,
                    });
                }
                if (payload.type === "video" && isSendingVideo === false) {
                    /**
                     * Since WebRTC "unified plan", the local track is tied to the
                     * remote transceiver.sender and not the remote track. Therefore
                     * when the remote track is 'ended' the local track is not 'ended'
                     * but only 'muted'. This is why we do not stop the local track
                     * until the peer is completely removed.
                     */
                    session.videoStream = undefined;
                }
                break;
            }
        }
    }

    async mute() {
        await this.setMute(true);
        this.soundEffectsService.play("mute");
    }

    /**
     * @param {import("@mail/new/core/thread_model").Thread} channel
     * @param {Object} [param1={}]
     * @param {boolean} [param1.video]
     */
    async toggleCall(channel, { video } = {}) {
        if (this.state.hasPendingRequest) {
            return;
        }
        this.state.hasPendingRequest = true;
        const isActiveCall = Boolean(this.state.channel && this.state.channel === channel);
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
            event: `${window.moment().format("h:mm:ss")}: ${entry}`,
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
            await this.updateRemote(session, transceiverName, true);
        }
        this.state.outgoingSessions.add(session.id);
    }

    call() {
        if (!this.state.channel.rtcSessions) {
            return;
        }
        for (const session of Object.values(this.state.channel.rtcSessions)) {
            if (session.peerConnection || session.id === this.state.selfSession.id) {
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
            if (!this.state.channel.rtcSessions[session.id]) {
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
            this.updateStream(session, track, {
                mute: this.state.selfSession.isDeaf,
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
     * @param {import("@mail/new/core/thread_model").Thread}
     */
    async joinCall(channel, { video = false } = {}) {
        if (!IS_CLIENT_RTC_COMPATIBLE) {
            this.notification.add(_t("Your browser does not support webRTC."), { type: "warning" });
            return;
        }
        const { rtcSessions, iceServers, sessionId, invitedMembers } = await this.rpc(
            "/mail/rtc/channel/join_call",
            {
                channel_id: channel.id,
                check_rtc_session_ids: Object.values(channel.rtcSessions).map(
                    (session) => session.id
                ),
            },
            { silent: true }
        );
        // Initializing a new session implies closing the current session.
        this.clear();
        this.state.logs.clear();
        this.state.channel = channel;
        this.threadService.update(this.state.channel, {
            serverData: {
                rtcSessions,
                invitedMembers,
            },
        });
        this.state.selfSession = this.store.rtcSessions[sessionId];
        this.state.iceServers = iceServers || DEFAULT_ICE_SERVERS;
        this.state.logs.set("channelId", this.state.channel?.id);
        this.state.logs.set("selfSessionId", this.state.selfSession?.id);
        this.state.logs.set("hasTURN", hasTurn(this.state.iceServers));
        const channelProxy = reactive(this.state.channel, () => {
            if (channel !== this.state.channel) {
                throw new Error("channel has changed");
            }
            if (this.state.channel) {
                if (this.state.channel && !channelProxy.rtcSessions[this.state.selfSession.id]) {
                    // if the current RTC session is not in the channel sessions, this call is no longer valid.
                    this.endCall();
                    return;
                }
                for (const session of Object.values(this.state.channel.rtcSessions)) {
                    if (!channelProxy.rtcSessions[session.id]) {
                        this.log(session, "session removed from the server");
                        this.disconnect(session);
                    }
                }
            }
            void Object.keys(channelProxy.rtcSessions);
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
        this.state.channel.rtcInvitingSessionId = undefined;
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
            "/mail/channel/ping",
            {
                channel_id: this.state.channel.id,
                check_rtc_session_ids: Object.values(this.state.channel.rtcSessions).map(
                    (session) => session.id
                ),
                rtc_session_id: this.state.selfSession.id,
            },
            { silent: true }
        );
        if (this.state.channel) {
            const activeSessionsData = rtcSessions[0][1];
            for (const sessionData of activeSessionsData) {
                const session = this.insertSession(sessionData);
                this.state.channel.rtcSessions[session.id] = session;
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
        this.clearSession(session);
        browser.clearTimeout(this.state.recoverTimeouts.get(session.id));
        this.state.recoverTimeouts.delete(session.id);
        this.state.outgoingSessions.delete(session.id);
        this.log(session, "peer removed", { step: "peer removed" });
    }

    clear() {
        for (const session of Object.values(this.store.rtcSessions)) {
            this.disconnect(session);
        }
        for (const timeoutId of this.state.recoverTimeouts.values()) {
            clearTimeout(timeoutId);
        }
        this.state.recoverTimeouts.clear();
        this.state.updateAndBroadcastDebounce?.cancel();
        this.state.disconnectAudioMonitor?.();
        this.state.audioTrack?.stop();
        this.state.videoTrack?.stop();
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
            videoTrack: undefined,
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
        for (const session of Object.values(this.state.channel.rtcSessions)) {
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
                const sendCamera = force ?? !this.state.sendCamera;
                await this.setVideo(type, sendCamera);
                break;
            }
            case "screen": {
                const sendScreen = force ?? !this.state.sendScreen;
                await this.setVideo(type, sendScreen);
                break;
            }
        }
        if (this.state.selfSession) {
            if (!this.state.videoTrack) {
                this.removeVideoFromSession(this.state.selfSession);
            } else {
                this.updateStream(this.state.selfSession, this.state.videoTrack);
            }
        }
        for (const session of Object.values(this.state.channel.rtcSessions)) {
            if (session.id === this.state.selfSession.id) {
                continue;
            }
            await this.updateRemote(session, "video");
        }
        if (!this.state.selfSession) {
            return;
        }
        this.updateAndBroadcast({
            isScreenSharingOn: !!this.state.sendScreen,
            isCameraOn: !!this.state.sendCamera,
        });
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
        await this.notify(Object.values(this.state.channel.rtcSessions), "trackChange", {
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
    async setVideo(type, activateVideo = false) {
        this.state.sendScreen = false;
        this.state.sendCamera = false;
        if (this.blurManager) {
            this.blurManager.close();
            this.blurManager = undefined;
        }
        const stopVideo = () => {
            if (this.state.videoTrack) {
                this.state.videoTrack.stop();
            }
            this.state.videoTrack = undefined;
            closeStream(this.state.sourceCameraStream);
            this.state.sourceCameraStream = null;
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
                if (this.state.sourceCameraStream) {
                    sourceStream = this.state.sourceCameraStream;
                } else {
                    sourceStream = await browser.navigator.mediaDevices.getUserMedia({
                        video: VIDEO_CONFIG,
                    });
                }
            }
            if (type === "screen") {
                sourceStream = await browser.navigator.mediaDevices.getDisplayMedia({
                    video: VIDEO_CONFIG,
                });
                this.soundEffectsService.play("screen-sharing");
            }
        } catch {
            const str =
                type === "camera"
                    ? _t('%s" requires "camera" access')
                    : _t('%s" requires "screen recording" access');
            this.notification.add(sprintf(str, window.location.host), { type: "warning" });
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
                    sprintf(_t("%(name)s: %(message)s)"), {
                        name: _e.name,
                        message: _e.message,
                    }),
                    { type: "warning" }
                );
                this.userSettingsService.useBlur = false;
            }
        }
        const track = videoStream ? videoStream.getVideoTracks()[0] : undefined;
        if (track) {
            track.addEventListener("ended", async () => {
                await this.toggleVideo(type, false);
            });
        }
        // ensures that the previous stream is stopped before overwriting it
        if (this.state.sourceCameraStream && sourceStream.id !== this.state.sourceCameraStream.id) {
            closeStream(this.state.sourceCameraStream);
        }
        Object.assign(this.state, {
            sourceCameraStream: sourceStream,
            videoTrack: track,
            sendCamera: Boolean(type === "camera" && track),
            sendScreen: Boolean(type === "screen" && track),
        });
    }

    /**
     * Updates the track that is broadcasted to the RTCPeerConnection.
     * This will start new transaction by triggering a negotiationneeded event
     * on the peerConnection given as parameter.
     *
     * negotiationneeded -> offer -> answer -> ...
     */
    async updateRemote(session, trackKind, initTransceiver = false) {
        this.log(session, `updating ${trackKind} transceiver`);
        const track = trackKind === "audio" ? this.state.audioTrack : this.state.videoTrack;
        let transceiverDirection = track ? "sendrecv" : "recvonly";
        if (trackKind === "video") {
            transceiverDirection = this.getTransceiverDirection(session, Boolean(track));
        }
        let transceiver;
        if (initTransceiver) {
            transceiver = session.peerConnection.addTransceiver(trackKind);
        } else {
            transceiver = getTransceiver(session.peerConnection, trackKind);
        }
        if (track) {
            try {
                await transceiver.sender.replaceTrack(track);
                transceiver.direction = transceiverDirection;
            } catch {
                // ignored, the track is probably already on the peerConnection.
            }
            return;
        }
        try {
            await transceiver.sender.replaceTrack(null);
            transceiver.direction = transceiverDirection;
        } catch {
            // ignored, the transceiver is probably already removed
        }
        if (trackKind === "video") {
            this.notify([session], "trackChange", {
                type: "video",
                state: { isSendingVideo: false },
            });
        }
    }

    async resetAudioTrack({ force = false }) {
        if (this.state.audioTrack) {
            this.state.audioTrack.stop();
            this.state.audioTrack = undefined;
        }
        if (!this.state.channel.id) {
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
                    sprintf(_t('"%(hostname)s" requires microphone access'), {
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
            for (const session of Object.values(this.state.channel.rtcSessions)) {
                if (session.id === this.state.selfSession.id) {
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
     * @param {Object} data
     * @returns {RtcSession}
     */
    insertSession(data) {
        let session;
        if (this.store.rtcSessions[data.id]) {
            session = this.store.rtcSessions[data.id];
        } else {
            session = new RtcSession();
            session._store = this.store;
        }
        const { channelMember, ...remainingData } = data;
        for (const key in remainingData) {
            session[key] = remainingData[key];
        }
        if (channelMember?.channel) {
            session.channelId = channelMember.channel.id;
        }
        if (channelMember) {
            const channelMemberRecord = this.channelMemberService.insert(channelMember);
            session.channelMemberId = channelMemberRecord.id;
            if (channelMemberRecord.thread) {
                channelMemberRecord.thread.rtcSessions[session.id] = session;
            }
        }
        this.store.rtcSessions[session.id] = session;
        // return reactive version
        return this.store.rtcSessions[session.id];
    }

    /**
     * @param {import("@mail/new/rtc/rtc_session_model").id} id
     */
    deleteSession(id) {
        const session = this.store.rtcSessions[id];
        if (session) {
            delete this.store.threads[createLocalId("mail.channel", session.channelId)]
                ?.rtcSessions[id];
            this.clearSession(session);
        }
        delete this.store.rtcSessions[id];
    }

    /**
     * @param {RtcSession} session
     * @param {MediaStreamTrack} track
     * @param {Object} [parm1]
     * @param {boolean} [parm1.mute]
     */
    async updateStream(session, track, { mute } = {}) {
        const stream = new window.MediaStream();
        stream.addTrack(track);
        if (track.kind === "audio") {
            const audioElement = session.audioElement || new window.Audio();
            try {
                audioElement.srcObject = stream;
            } catch {
                session.isAudioInError = true;
            }
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
            try {
                await audioElement.play();
                session.isAudioInError = false;
            } catch (error) {
                if (typeof error === "object" && error.name === "NotAllowedError") {
                    // Ignored as some browsers may reject play() calls that do not
                    // originate from a user input.
                    return;
                }
                session.isAudioInError = true;
            }
        }
        if (track.kind === "video") {
            session.videoStream = stream;
        }
    }

    clearSession(session) {
        closeStream(session.audioStream);
        if (session.audioElement) {
            session.audioElement.pause();
            try {
                session.audioElement.srcObject = undefined;
            } catch {
                // ignore error during remove, the value will be overwritten at next usage anyway
            }
        }
        delete session.audioStream;
        delete session.connectionState;
        delete session.localCandidateType;
        delete session.remoteCandidateType;
        delete session.dataChannelState;
        delete session.packetsReceived;
        delete session.packetsSent;
        delete session.dtlsState;
        delete session.iceState;
        delete session.logStep;
        session.isAudioInError = false;
        session.isTalking = false;
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
            delete session.peerConnection;
        }
    }

    removeVideoFromSession(session) {
        closeStream(session.videoStream);
        session.videoStream = undefined;
    }

    updateVideoDownload(rtcSession, { viewCountIncrement }) {
        rtcSession.videoComponentCount += viewCountIncrement;
        if (!rtcSession.peerConnection) {
            return;
        }
        const transceivers = rtcSession.peerConnection.getTransceivers();
        const transceiver = transceivers[ORDERED_TRANSCEIVER_NAMES.indexOf("video")];
        if (!transceiver) {
            return;
        }
        transceiver.direction = this.getTransceiverDirection(
            rtcSession,
            Boolean(this.state.videoTrack)
        );
    }

    getTransceiverDirection(session, allowUpload = false) {
        if (session.videoComponentCount > 0) {
            return allowUpload ? "sendrecv" : "recvonly";
        } else {
            return allowUpload ? "sendonly" : "inactive";
        }
    }
}

export const rtcService = {
    dependencies: [
        "mail.channel.member",
        "mail.store",
        "notification",
        "rpc",
        "bus_service",
        "mail.sound_effects",
        "mail.user_settings",
        "mail.thread",
        "mail.persona",
    ],
    start(env, services) {
        const rtc = new Rtc(env, services);
        services["bus_service"].addEventListener("notification", (notifEvent) => {
            for (const notif of notifEvent.detail) {
                switch (notif.type) {
                    case "mail.channel.rtc.session/peer_notification":
                        {
                            const { sender, notifications } = notif.payload;
                            for (const content of notifications) {
                                rtc.handleNotification(sender, content);
                            }
                        }
                        break;
                    case "mail.channel.rtc.session/ended":
                        {
                            const { sessionId } = notif.payload;
                            if (rtc.state.selfSession?.id === sessionId) {
                                rtc.endCall();
                                services.notification.add(
                                    _t("Disconnected from the RTC call by the server"),
                                    { type: "warning" }
                                );
                            }
                        }
                        break;
                }
            }
        });
        // debugging. remove this
        window.rtc = rtc;
        return rtc;
    },
};

registry.category("services").add("mail.rtc", rtcService);
