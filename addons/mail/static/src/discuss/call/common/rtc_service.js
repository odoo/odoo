import { Record } from "@mail/core/common/record";
import { BlurManager } from "@mail/discuss/call/common/blur_manager";
import { monitorAudio } from "@mail/discuss/call/common/media_monitoring";
import { rpc } from "@web/core/network/rpc";
import { closeStream, onChange } from "@mail/utils/common/misc";

import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { loadBundle, loadJS } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";
import { url } from "@web/core/utils/urls";
import { callActionsRegistry } from "./call_actions";

let sequence = 1;
const getSequence = () => {
    return sequence++;
};

/**
 *
 * @param {EventTarget} target
 * @param {string} event
 * @param {Function} f event listener callback
 * @return {Function} unsubscribe function
 */
function subscribe(target, event, f) {
    target.addEventListener(event, f);
    return () => target.removeEventListener(event, f);
}

/**
 * @typedef {'audio' | 'camera' | 'screen' } streamType
 */

/**
 * @return {Promise<{ SfuClient: import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient, SFU_CLIENT_STATE: import("@mail/../lib/odoo_sfu/odoo_sfu").SFU_CLIENT_STATE }>}
 */
const loadSfuAssets = memoize(async () => await loadBundle("mail.assets_odoo_sfu"));

export const CONNECTION_TYPES = { P2P: "p2p", SERVER: "server" };
const SCREEN_CONFIG = {
    width: { max: 1920 },
    height: { max: 1080 },
    aspectRatio: 16 / 9,
    frameRate: {
        max: 24,
    },
};
const CAMERA_CONFIG = {
    width: 1280,
};
const IS_CLIENT_RTC_COMPATIBLE = Boolean(window.RTCPeerConnection && window.MediaStream);
function GET_DEFAULT_ICE_SERVERS() {
    return [{ urls: ["stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302"] }];
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

/**
 * Allows to use both peer to peer and SFU connections simultaneously, which makes it possible to
 * establish a connection with other call participants with the SFU when possible, and still handle
 * peer-to-peer for the participants who did not manage to establish a SFU connection.
 */
class Network {
    /** @type {import("@mail/discuss/call/common/peer_to_peer").PeerToPeer} */
    p2p;
    /** @type {import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient} */
    sfu;
    /** @type {[{ name: string, f: EventListener }]} */
    _listeners = [];
    /**
     * @param {import("@mail/discuss/call/common/peer_to_peer").PeerToPeer} p2p
     * @param {import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient} [sfu]
     */
    constructor(p2p, sfu) {
        this.p2p = p2p;
        this.sfu = sfu;
    }

    getSfuConsumerStats(sessionId) {
        const consumers = this.sfu?._consumers.get(sessionId);
        if (!consumers) {
            return [];
        }
        return Object.entries(consumers).map(([type, consumer]) => {
            let state = "active";
            if (!consumer) {
                state = "no consumer";
            } else if (consumer.closed) {
                state = "closed";
            } else if (consumer.paused) {
                state = "paused";
            } else if (!consumer.track) {
                state = "no track";
            } else if (!consumer.track.enabled) {
                state = "track disabled";
            } else if (consumer.track.muted) {
                state = "track muted";
            }
            return { type, state };
        });
    }

    /**
     * add a SFU to the network.
     * @param {import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient} sfu
     */
    addSfu(sfu) {
        if (this.sfu) {
            this.sfu.disconnect();
        }
        this.sfu = sfu;
    }
    removeSfu() {
        if (!this.sfu) {
            return;
        }
        for (const { name, f } of this._listeners) {
            this.sfu.removeEventListener(name, f);
        }
        this.sfu.disconnect();
    }
    /**
     * @param {string} name
     * @param {function} f
     * @override
     */
    addEventListener(name, f) {
        this._listeners.push({ name, f });
        this.p2p.addEventListener(name, f);
        this.sfu?.addEventListener(name, f);
    }
    /**
     * @param {streamType} type
     * @param {MediaStreamTrack | null} track track to be sent to the other call participants,
     * not setting it will remove the track from the server
     */
    async updateUpload(type, track) {
        await Promise.all([
            this.p2p.updateUpload(type, track),
            this.sfu?.updateUpload(type, track),
        ]);
    }
    /**
     * Stop or resume the consumption of tracks from the other call participants.
     *
     * @param {number} sessionId
     * @param {Object<[streamType, boolean]>} states e.g: { audio: true, camera: false }
     */
    updateDownload(sessionId, states) {
        this.p2p.updateDownload(sessionId, states);
        this.sfu?.updateDownload(sessionId, states);
    }
    /**
     * Updates the server with the info of the session (isTalking, isCameraOn,...) so that it can broadcast it to the
     * other call participants.
     *
     * @param {import("#src/models/session.js").SessionInfo} info
     * @param {Object} [options] see documentation of respective classes
     */
    updateInfo(info, options = {}) {
        this.p2p.updateInfo(info, options);
        this.sfu?.updateInfo(info, options);
    }
    disconnect() {
        for (const { name, f } of this._listeners.splice(0)) {
            this.p2p.removeEventListener(name, f);
            this.sfu?.removeEventListener(name, f);
        }
        this.p2p.disconnect();
        this.sfu?.disconnect();
    }
}

export class Rtc extends Record {
    /** @returns {import("models").Rtc} */
    static get(data) {
        return super.get(...arguments);
    }
    /** @returns {import("models").Rtc} */
    static insert(data) {
        return super.insert(...arguments);
    }

    notifications = reactive(new Map());
    /** @type {Map<string, number>} timeoutId by notificationId for call notifications */
    timeouts = new Map();
    /** @type {Map<number, number>} timeoutId by sessionId for download pausing delay */
    downloadTimeouts = new Map();
    /** @type {{urls: string[]}[]} */
    iceServers = Record.attr(undefined, {
        compute() {
            return this.iceServers ? this.iceServers : GET_DEFAULT_ICE_SERVERS();
        },
    });
    selfSession = Record.one("RtcSession");
    serverInfo;
    /**
     * @type {Network}
     */
    network;
    /** @type {import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient} */
    sfuClient = undefined;

    /** @type {Object<string, boolean>} The keys are action names and the values are booleans indicating whether each action is active */
    lastActions = {};
    /** @type {Array<string>} Array of action names representing the stack of currently active actions */
    actionsStack = [];
    /** @type {string|undefined} String representing the last call action activated, or undefined if none are */
    lastSelfCallAction = undefined;
    /** callbacks to be called when cleaning the state up after a call */
    cleanups = [];
    /** @type {number} */
    sfuTimeout;

    callActions = Record.attr([], {
        compute() {
            return callActionsRegistry
                .getEntries()
                .filter(([key, action]) => action.condition({ rtc: this }))
                .map(([key, action]) => [key, action.isActive({ rtc: this })]);
        },
        onUpdate() {
            for (const [key, isActive] of this.callActions) {
                if (isActive === this.lastActions[key]) {
                    continue;
                }
                if (isActive) {
                    if (!this.actionsStack.includes(key)) {
                        this.actionsStack.unshift(key);
                    }
                } else {
                    this.actionsStack.splice(this.actionsStack.indexOf(key), 1);
                }
            }

            this.lastSelfCallAction = this.actionsStack[0];

            this.lastActions = Object.fromEntries(this.callActions);
        },
    });

    setup() {
        this.linkVoiceActivationDebounce = debounce(this.linkVoiceActivation, 500);
        this.state = reactive({
            connectionType: undefined,
            hasPendingRequest: false,
            channel: undefined,
            globalLogs: {},
            logs: new Map(), // deprecated
            sendCamera: false,
            sendScreen: false,
            updateAndBroadcastDebounce: undefined,
            audioTrack: undefined,
            cameraTrack: undefined,
            screenTrack: undefined,
            /**
             * callback to properly end the audio monitoring.
             * If set it indicates that we are currently monitoring the local
             * audioTrack for the voice activation feature.
             */
            disconnectAudioMonitor: undefined,
            pttReleaseTimeout: undefined,
            sourceCameraStream: null,
            sourceScreenStream: null,
            /**
             * Whether the network fell back to p2p mode in a SFU call.
             */
            fallbackMode: false,
        });
        this.blurManager = undefined;
    }

    start() {
        const services = this.store.env.services;
        this.notification = services.notification;
        this.soundEffectsService = services["mail.sound_effects"];
        this.pttExtService = services["discuss.ptt_extension"];
        /**
         * @type {import("@mail/discuss/call/common/peer_to_peer").PeerToPeer}
         */
        this.p2pService = services["discuss.p2p"];
        onChange(this.store.settings, "useBlur", () => {
            if (this.state.sendCamera) {
                this.toggleVideo("camera", true);
            }
        });
        onChange(this.store.settings, ["edgeBlurAmount", "backgroundBlurAmount"], () => {
            if (this.blurManager) {
                this.blurManager.edgeBlur = this.store.settings.edgeBlurAmount;
                this.blurManager.backgroundBlur = this.store.settings.backgroundBlurAmount;
            }
        });
        onChange(this.store.settings, ["voiceActivationThreshold", "use_push_to_talk"], () => {
            this.linkVoiceActivationDebounce();
        });
        onChange(this.store.settings, "audioInputDeviceId", async () => {
            if (this.selfSession) {
                await this.resetAudioTrack({ force: true });
            }
        });
        this.store.env.bus.addEventListener("RTC-SERVICE:PLAY_MEDIA", () => {
            for (const session of this.state.channel.rtcSessions) {
                session.playAudio();
            }
        });
        browser.addEventListener(
            "keydown",
            (ev) => {
                if (!this.store.settings.isPushToTalkKey(ev)) {
                    return;
                }
                this.onPushToTalk();
            },
            { capture: true }
        );
        browser.addEventListener(
            "keyup",
            (ev) => {
                if (
                    !this.state.channel ||
                    !this.store.settings.use_push_to_talk ||
                    !this.store.settings.isPushToTalkKey(ev) ||
                    !this.selfSession.isTalking
                ) {
                    return;
                }
                this.setPttReleaseTimeout();
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
                this.sfuClient?.disconnect();
            }
        });
        /**
         * Call all sessions for which no peerConnection is established at
         * a regular interval to try to recover any connection that failed
         * to start.
         *
         * This is distinct from this.recover which tries to restore
         * connections that were established but failed or timed out.
         */
        browser.setInterval(async () => {
            if (!this.selfSession || !this.state.channel) {
                return;
            }
            await this.ping();
            if (!this.selfSession || !this.state.channel) {
                return;
            }
            this.call();
        }, 30_000);
    }

    setPttReleaseTimeout(duration = 200) {
        this.state.pttReleaseTimeout = browser.setTimeout(() => {
            this.setTalking(false);
            if (!this.selfSession?.isMute) {
                this.soundEffectsService.play("push-to-talk-off");
            }
        }, Math.max(this.store.settings.voice_active_duration || 0, duration));
    }

    onPushToTalk() {
        if (
            !this.state.channel ||
            this.store.settings.isRegisteringKey ||
            !this.store.settings.use_push_to_talk
        ) {
            return;
        }
        browser.clearTimeout(this.state.pttReleaseTimeout);
        if (!this.selfSession.isTalking && !this.selfSession.isMute) {
            this.soundEffectsService.play("push-to-talk-on");
        }
        this.setTalking(true);
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
        this.state.hasPendingRequest = true;
        this.logSnapshot();
        await this.rpcLeaveCall(channel);
        this.endCall(channel);
        this.state.hasPendingRequest = false;
    }

    /**
     * @param {import("models").Thread} [channel]
     */
    endCall(channel = this.state.channel) {
        channel.rtcInvitingSession = undefined;
        channel.activeRtcSession = undefined;
        if (channel.eq(this.state.channel)) {
            this.pttExtService.unsubscribe();
            this.network?.disconnect();
            this.clear();
            this.soundEffectsService.play("channel-leave");
        }
    }

    async deafen() {
        await this.setDeaf(true);
        this.soundEffectsService.play("deafen");
    }

    /**
     * @param {import("@mail/discuss/call/common/rtc_session_model").RtcSession} session
     * @param {boolean} active
     */
    setRemoteRaiseHand(session, active) {
        if (Boolean(session.raisingHand) === active) {
            return;
        }
        Object.assign(session, {
            raisingHand: active ? new Date() : undefined,
        });
        const notificationId = "raise_hand_" + session.id;
        if (session.raisingHand) {
            this.addCallNotification({
                id: notificationId,
                text: _t("%s raised their hand", session.name),
            });
        } else {
            this.removeCallNotification(notificationId);
        }
    }

    async mute() {
        await this.setMute(true);
        this.soundEffectsService.play("mute");
    }

    /**
     * @param {import("models").Thread} channel
     * @param {Object} [initialState={}]
     * @param {boolean} [initialState.audio]
     * @param {{ exit: () => {} }} [initialState.fullscreen] if set, the call view is using fullscreen.
     *   Providing fullscreen object allows to exit on call leave.
     * @param {boolean} [initialState.camera]
     */
    async toggleCall(channel, { audio = true, fullscreen, camera } = {}) {
        await Promise.resolve(() =>
            loadJS(url("/mail/static/lib/selfie_segmentation/selfie_segmentation.js")).catch(
                () => {}
            )
        );
        if (this.state.hasPendingRequest) {
            return;
        }
        const isActiveCall = channel.eq(this.state.channel);
        if (this.state.channel) {
            fullscreen?.exit();
            await this.leaveCall(this.state.channel);
        }
        if (!isActiveCall) {
            await this.joinCall(channel, { audio, camera });
        }
    }

    async toggleMicrophone() {
        if (this.selfSession.isMute) {
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

    async _loadSfu() {
        const load = async () => {
            await loadSfuAssets();
            const sfuModule = odoo.loader.modules.get("@mail/../lib/odoo_sfu/odoo_sfu");
            this.SFU_CLIENT_STATE = sfuModule.SFU_CLIENT_STATE;
            this.sfuClient = new sfuModule.SfuClient();
        };
        try {
            await load();
        } catch {
            // trying again with a delay in case of race condition with the asset loading.
            await new Promise((resolve, reject) => {
                browser.setTimeout(async () => {
                    try {
                        await load();
                    } catch (error) {
                        reject(error);
                    }
                    resolve();
                }, 1000);
            });
        }
    }

    updateUpload() {
        this.network?.updateUpload("audio", this.state.audioTrack);
        this.network?.updateUpload("camera", this.state.cameraTrack);
        this.network?.updateUpload("screen", this.state.screenTrack);
    }

    async _initConnection() {
        this.selfSession.connectionState = "selecting network type";
        this.state.connectionType = CONNECTION_TYPES.P2P;
        this.network?.disconnect();
        // loading p2p in any case as we may need to receive peer-to-peer connections from users who failed to connect to the SFU.
        this.p2pService.connect(this.selfSession.id, this.state.channel.id, {
            info: this.formatInfo(),
            iceServers: this.iceServers,
        });
        this.network = new Network(this.p2pService);
        this.updateUpload();
        if (this.serverInfo) {
            this.log(this.selfSession, "loading sfu server", {
                step: "loading sfu server",
                serverInfo: this.serverInfo,
            });
            this.selfSession.connectionState = "loading SFU assets";
            try {
                await this._loadSfu();
                this.state.connectionType = CONNECTION_TYPES.SERVER;
                if (this.network) {
                    this.network.addSfu(this.sfuClient);
                } else {
                    return; // the call may be ended by the time the sfu is loaded
                }
            } catch (e) {
                this.state.fallbackMode = true;
                this.notification.add(
                    _t("Failed to load the SFU server, falling back to peer-to-peer"),
                    {
                        type: "warning",
                    }
                );
                this.log(this.selfSession, "failed to load sfu server", {
                    error: e,
                    important: true,
                });
            }
            this.selfSession.connectionState = "initializing";
        } else {
            this.log(this.selfSession, "no sfu server info, using peer-to-peer");
        }
        this.network.addEventListener("stateChange", this._handleSfuClientStateChange);
        this.network.addEventListener("update", this._handleNetworkUpdates);
        this.network.addEventListener("log", ({ detail: { id, level, message } }) => {
            const session = this.store.RtcSession.get(id);
            if (session) {
                this.log(session, message, { step: "p2p", level, important: true });
            }
        });
        if (this.state.channel) {
            await this.call();
            this.updateUpload();
        }
    }

    /**
     * @param {RtcSession} session
     * @param {String} entry
     * @param {Object} [param2]
     * @param {Error} [param2.error]
     * @param {String} [param2.step] current step of the flow
     * @param {String} [param2.state] current state of the connection
     * @param {Boolean} [param2.important] if the log is important and should be kept even if logRtc is disabled
     */
    log(session, entry, { error, step, state, important, ...data } = {}) {
        session.logStep = entry;
        if (!this.store.settings.logRtc && !important) {
            return;
        }
        let sessionEntry = this.state.logs[session.id];
        if (!sessionEntry) {
            this.state.logs[session.id] = sessionEntry = { step: "", state: "", logs: [] };
        }
        if (step) {
            sessionEntry.step = step;
        }
        if (state) {
            sessionEntry.state = state;
        }
        sessionEntry.logs.push({
            event: `${luxon.DateTime.now().toFormat("HH:mm:ss")}: ${entry}`,
            error: error && {
                name: error.name,
                message: error.message,
                stack: error.stack && error.stack.split("\n"),
            },
            ...data,
        });
    }

    /**
     * @param {CustomEvent} param0
     * @param {Object} param0.detail
     * @param {String} param0.detail.name
     * @param {any} param0.detail.payload
     */
    async _handleNetworkUpdates({ detail: { name, payload } }) {
        if (!this.state.channel) {
            return;
        }
        switch (name) {
            case "broadcast":
                {
                    const {
                        senderId,
                        message: { sequence },
                    } = payload;
                    if (!sequence) {
                        return;
                    }
                    const session = await this.store.RtcSession.getWhenReady(senderId);
                    if (!session) {
                        return;
                    }
                    if (!session.sequence || session.sequence < sequence) {
                        session.sequence = sequence;
                    }
                }
                return;
            case "connection_change":
                {
                    const { id, state } = payload;
                    const session = this.store.RtcSession.get(id);
                    if (!session) {
                        return;
                    }
                    session.connectionState = state;
                }
                return;
            case "disconnect":
                {
                    const { sessionId } = payload;
                    const session = this.store.RtcSession.get(sessionId);
                    if (!session) {
                        return;
                    }
                    this.disconnect(session);
                }
                return;
            case "info_change":
                if (!payload) {
                    return;
                }
                for (const [id, info] of Object.entries(payload)) {
                    const session = await this.store.RtcSession.getWhenReady(Number(id));
                    if (!session || !this.state.channel) {
                        return;
                    }
                    // `isRaisingHand` is turned into the Date `raisingHand`
                    this.setRemoteRaiseHand(session, info.isRaisingHand);
                    delete info.isRaisingHand;
                    Object.assign(session, info);
                }
                return;
            case "track":
                {
                    const { sessionId, type, track, active, sequence } = payload;
                    const session = await this.store.RtcSession.getWhenReady(sessionId);
                    if (!session || !this.state.channel) {
                        this.log(
                            this.selfSession,
                            `track received for unknown session ${sessionId} (${this.state.connectionType})`
                        );
                        return;
                    }
                    if (sequence && sequence < session.sequence) {
                        this.log(
                            session,
                            `track received for old sequence ${sequence} (${this.state.connectionType})`
                        );
                        return;
                    }
                    this.log(session, `${type} track received (${this.state.connectionType})`);
                    try {
                        await this.handleRemoteTrack({ session, track, type, active });
                    } catch {
                        // ignored, the session may be closing.
                        // this can happen when you join a call from another tab in which you have another session.
                    }
                    // makes sure we are not downloading a video that is not displayed
                    setTimeout(() => {
                        this.updateVideoDownload(session);
                    }, 2000);
                }
                return;
        }
    }

    _handleSfuClientStateChange({ detail: { state, cause } }) {
        this.log(this.selfSession, `sfu state change: ${state}. cause: ${cause}`, { state });
        this.selfSession.connectionState = state;
        switch (state) {
            case this.SFU_CLIENT_STATE.AUTHENTICATED:
                // if we are hot-swapping connection type, we clear the p2p as late as possible
                this.p2pService.removeALlPeers();
                this.sfuClient.broadcast({ sequence: getSequence() });
                break;
            case this.SFU_CLIENT_STATE.CONNECTED:
                browser.clearTimeout(this.sfuTimeout);
                this.sfuClient.updateInfo(this.formatInfo(), {
                    needRefresh: true, // asks the server to send the info from all the channel
                });
                this.sfuClient.updateUpload("audio", this.state.audioTrack);
                this.sfuClient.updateUpload("camera", this.state.cameraTrack);
                this.sfuClient.updateUpload("screen", this.state.screenTrack);
                return;
            case this.SFU_CLIENT_STATE.CLOSED:
                {
                    if (!this.state.channel) {
                        return;
                    }
                    let text;
                    if (cause === "full") {
                        text = _t("Channel full");
                        this.leaveCall();
                    } else {
                        text = _t(
                            "Connection to SFU server closed by the server, falling back to peer-to-peer"
                        );
                        this.log(this.selfSession, text, { important: true });
                        this._downgradeConnection();
                    }
                    this.notification.add(text, {
                        type: "warning",
                    });
                }
                return;
        }
    }

    async _downgradeConnection() {
        this.serverInfo = undefined;
        this.state.fallbackMode = true;
        this.state.connectionType = CONNECTION_TYPES.P2P;
        this.network.removeSfu();
        await this.call();
        this.updateUpload();
    }

    /**
     *
     * @param {Object} [param0={}]
     * @param {boolean} [param0.asFallback=false] whether the call is made as a fallback to the SFU, in which case
     * p2p connections are offered more eagerly as other participants may not offer them if their primary connection
     * type is SFU.
     * @return {Promise<void>}
     */
    async call({ asFallback = false } = {}) {
        if (asFallback && !this.state.fallbackMode) {
            return;
        }
        if (this.state.connectionType === CONNECTION_TYPES.SERVER) {
            if (this.sfuClient.state === this.SFU_CLIENT_STATE.DISCONNECTED) {
                browser.clearTimeout(this.sfuTimeout);
                this.sfuTimeout = browser.setTimeout(() => {
                    this.log(this.selfSession, "sfu connection timeout", { important: true });
                    this._downgradeConnection();
                }, 10000);
                await this.sfuClient.connect(this.serverInfo.url, this.serverInfo.jsonWebToken, {
                    channelUUID: this.serverInfo.channelUUID,
                    iceServers: this.iceServers,
                });
            }
            return;
        }
        if (this.state.channel.rtcSessions.length === 0) {
            return;
        }
        const sequence = getSequence();
        for (const session of this.state.channel.rtcSessions) {
            if (session.eq(this.selfSession)) {
                continue;
            }
            this.log(session, "init call", { step: "init call" });
            this.p2pService.addPeer(session.id, { sequence });
        }
    }

    /**
     * @param {import("@mail/discuss/call/common/rtc_session_model").RtcSession} session
     * @param {MediaStreamTrack} track
     * @param {streamType} type
     * @param {boolean} active false if the track is muted/disabled
     */
    async handleRemoteTrack({ session, track, type, active = true }) {
        session.updateStreamState(type, active);
        await this.updateStream(session, track, {
            mute: this.selfSession.isDeaf,
            videoType: type,
        });
        this.updateActiveSession(session, type, { addVideo: true });
    }

    /**
     * @param {import("models").Thread} channel
     * @param {object} [initialState]
     * @param {boolean} [initialState.audio] whether to request and use the user audio input (microphone) at start
     * @param {boolean} [initialState.camera] whether to request and use the user video input (camera) at start
     */
    async joinCall(channel, { audio = true, camera = false } = {}) {
        if (!IS_CLIENT_RTC_COMPATIBLE) {
            this.notification.add(_t("Your browser does not support webRTC."), { type: "warning" });
            return;
        }
        this.pttExtService.subscribe();
        this.state.hasPendingRequest = true;
        const data = await rpc(
            "/mail/rtc/channel/join_call",
            {
                camera,
                channel_id: channel.id,
                check_rtc_session_ids: channel.rtcSessions.map((session) => session.id),
            },
            { silent: true }
        );
        this.state.hasPendingRequest = false;
        // Initializing a new session implies closing the current session.
        this.clear();
        this.state.channel = channel;
        this.store.insert(data);
        this.newLogs();
        this.state.updateAndBroadcastDebounce = debounce(
            async () => {
                if (!this.selfSession) {
                    return;
                }
                await rpc(
                    "/mail/rtc/session/update_and_broadcast",
                    {
                        session_id: this.selfSession.id,
                        values: {
                            is_camera_on: this.selfSession.isCameraOn,
                            is_deaf: this.selfSession.isDeaf,
                            is_muted: this.selfSession.isSelfMuted,
                            is_screen_sharing_on: this.selfSession.isScreenSharingOn,
                        },
                    },
                    { silent: true }
                );
            },
            3000,
            { leading: true, trailing: true }
        );
        this.state.channel.rtcInvitingSession = undefined;
        if (camera) {
            await this.toggleVideo("camera");
        }
        await this._initConnection();
        await this.resetAudioTrack({ force: audio });
        if (!this.state.channel?.id) {
            return;
        }
        this.soundEffectsService.play("channel-join");
        this.cleanups.push(
            // only register the beforeunload event if there is a call as FireFox will not place
            // the pages with beforeunload listeners in the bfcache.
            subscribe(browser, "beforeunload", (event) => {
                event.preventDefault();
            })
        );
    }

    newLogs() {
        const date = luxon.DateTime.now().toFormat("yyyy-MM-dd-HH:mm:ss");
        const id = `c:${this.state.channel.id}-s:${this.selfSession.id}-d:${date}`;
        this.state.logs = this.state.globalLogs[id] = {};
        this.state.logs["hasTurn"] = hasTurn(this.iceServers);
    }

    logSnapshot() {
        const peers = [];
        this.p2pService?.peers.forEach((peer) => {
            peers.push({
                id: peer.id,
                state: peer.connection.connectionState,
                iceState: peer.connection.iceConnectionState,
            });
        });
        const server = {};
        if (this.state.connectionType === CONNECTION_TYPES.SERVER) {
            server.info = this.serverInfo;
            server.state = this.sfuClient?.state;
            server.consumersStats = this.state.channel.rtcSessions.map((session) =>
                this.network.getSfuConsumerStats(session.id)
            );
            server.errors = this.sfuClient?.errors.map((error) => error.message);
        }
        this.state.globalLogs[`snapshot-${luxon.DateTime.now().toFormat("yyyy-MM-dd-HH-mm-ss")}`] =
            {
                peers,
                server,
                connectionType: this.state.connectionType,
            };
    }

    async rpcLeaveCall(channel) {
        await rpc(
            "/mail/rtc/channel/leave_call",
            {
                channel_id: channel.id,
            },
            { silent: true }
        );
    }

    async ping() {
        const data = await rpc(
            "/discuss/channel/ping",
            {
                channel_id: this.state.channel.id,
                check_rtc_session_ids: this.state.channel.rtcSessions.map((session) => session.id),
                rtc_session_id: this.selfSession.id,
            },
            { silent: true }
        );
        this.store.insert(data);
    }

    disconnect(session) {
        const downloadTimeout = this.downloadTimeouts.get(session.id);
        if (downloadTimeout) {
            clearTimeout(downloadTimeout);
            this.downloadTimeouts.delete(session.id);
        }
        this.removeCallNotification("raise_hand_" + session.id);
        session.raisingHand = undefined;
        session.logStep = undefined;
        session.audioError = undefined;
        session.videoError = undefined;
        session.connectionState = undefined;
        session.isTalking = false;
        session.mainVideoStreamType = undefined;
        this.removeAudioFromSession(session);
        this.removeVideoFromSession(session);
        this.p2pService?.removePeer(session.id);
        this.log(session, "peer removed", { step: "peer removed" });
    }

    clear() {
        if (this.state.channel) {
            for (const session of this.state.channel.rtcSessions) {
                this.removeAudioFromSession(session);
                this.removeVideoFromSession(session);
                session.isTalking = false;
            }
            this.cleanups.splice(0).forEach((cleanup) => cleanup());
        }
        browser.clearTimeout(this.sfuTimeout);
        this.sfuClient = undefined;
        this.network = undefined;
        this.state.updateAndBroadcastDebounce?.cancel();
        this.state.disconnectAudioMonitor?.();
        this.state.audioTrack?.stop();
        this.state.cameraTrack?.stop();
        this.state.screenTrack?.stop();
        this.state.fallbackMode = undefined;
        closeStream(this.state.sourceCameraStream);
        this.state.sourceCameraStream = null;
        closeStream(this.state.sourceScreenStream);
        this.state.sourceScreenStream = null;
        if (this.blurManager) {
            this.blurManager.close();
            this.blurManager = undefined;
        }
        this.update({
            selfSession: undefined,
            serverInfo: undefined,
        });
        Object.assign(this.state, {
            updateAndBroadcastDebounce: undefined,
            connectionType: undefined,
            disconnectAudioMonitor: undefined,
            cameraTrack: undefined,
            screenTrack: undefined,
            audioTrack: undefined,
            sendCamera: false,
            sendScreen: false,
            channel: undefined,
            fallbackMode: false,
        });
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
        if (!this.selfSession || !this.state.channel) {
            return;
        }
        this.selfSession.raisingHand = raise ? new Date() : undefined;
        await this.network?.updateInfo(this.formatInfo());
    }

    /**
     * @param {boolean} isTalking
     */
    async setTalking(isTalking) {
        if (!this.selfSession || isTalking === this.selfSession.isTalking) {
            return;
        }
        this.selfSession.isTalking = isTalking;
        if (!this.selfSession.isMute) {
            this.pttExtService.notifyIsTalking(isTalking);
            await this.refreshAudioStatus();
        }
    }

    /**
     * @param {string} type
     * @param {boolean} [force]
     */
    async toggleVideo(type, force) {
        if (!this.state.channel?.id) {
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
        if (this.selfSession) {
            switch (type) {
                case "camera": {
                    this.removeVideoFromSession(this.selfSession, {
                        type: "camera",
                        cleanup: false,
                    });
                    if (this.state.cameraTrack) {
                        this.updateStream(this.selfSession, this.state.cameraTrack);
                    }
                    break;
                }
                case "screen": {
                    if (!this.state.screenTrack) {
                        this.removeVideoFromSession(this.selfSession, {
                            type: "screen",
                            cleanup: false,
                        });
                    } else {
                        this.updateStream(this.selfSession, this.state.screenTrack);
                    }
                    break;
                }
            }
        }
        const updatedTrack = type === "camera" ? this.state.cameraTrack : this.state.screenTrack;
        await this.network?.updateUpload(type, updatedTrack);
        if (!this.selfSession) {
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
        const session = this.selfSession;
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
        this.state.audioTrack.enabled = !this.selfSession.isMute && this.selfSession.isTalking;
        this.network?.updateInfo(this.formatInfo());
    }

    /**
     * @param {String} type 'camera' or 'screen'
     */
    async setVideo(track, type, activateVideo = false) {
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
            if (type === "camera" && this.blurManager) {
                this.blurManager.close();
                this.blurManager = undefined;
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
                        video: CAMERA_CONFIG,
                    });
                }
            }
            if (type === "screen") {
                if (this.state.sourceScreenStream) {
                    sourceStream = this.state.sourceScreenStream;
                } else {
                    sourceStream = await browser.navigator.mediaDevices.getDisplayMedia({
                        video: SCREEN_CONFIG,
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
        let outputTrack = sourceStream ? sourceStream.getVideoTracks()[0] : undefined;
        if (outputTrack) {
            outputTrack.addEventListener("ended", async () => {
                await this.toggleVideo(type, false);
            });
        }
        if (this.store.settings.useBlur && type === "camera") {
            try {
                this.blurManager?.close();
                this.blurManager = new BlurManager(sourceStream, {
                    backgroundBlur: this.store.settings.backgroundBlurAmount,
                    edgeBlur: this.store.settings.edgeBlurAmount,
                });
                const bluredStream = await this.blurManager.stream;
                outputTrack = bluredStream.getVideoTracks()[0];
            } catch (_e) {
                this.notification.add(
                    _t("%(name)s: %(message)s)", { name: _e.name, message: _e.message }),
                    { type: "warning" }
                );
                this.store.settings.useBlur = false;
            }
        }
        switch (type) {
            case "camera": {
                Object.assign(this.state, {
                    sourceCameraStream: sourceStream,
                    cameraTrack: outputTrack,
                    sendCamera: Boolean(outputTrack),
                });
                break;
            }
            case "screen": {
                Object.assign(this.state, {
                    sourceScreenStream: sourceStream,
                    screenTrack: outputTrack,
                    sendScreen: Boolean(outputTrack),
                });
                break;
            }
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
        if (this.selfSession) {
            this.setMute(true);
        }
        if (force) {
            let audioTrack;
            try {
                const audioStream = await browser.navigator.mediaDevices.getUserMedia({
                    audio: this.store.settings.audioConstraints,
                });
                audioTrack = audioStream.getAudioTracks()[0];
                if (this.selfSession) {
                    this.setMute(false);
                }
            } catch {
                this.notification.add(
                    _t('"%(hostname)s" requires microphone access', {
                        hostname: window.location.host,
                    }),
                    { type: "warning" }
                );
                return;
            }
            if (!this.selfSession) {
                // The getUserMedia promise could resolve when the call is ended
                // in which case the track is no longer relevant.
                audioTrack.stop();
                return;
            }
            audioTrack.addEventListener("ended", async () => {
                // this mostly happens when the user retracts microphone permission.
                await this.resetAudioTrack({ force: false });
                this.setMute(true);
            });
            audioTrack.enabled = !this.selfSession.isMute && this.selfSession.isTalking;
            this.state.audioTrack = audioTrack;
            this.linkVoiceActivationDebounce();
            await this.network?.updateUpload("audio", this.state.audioTrack);
        }
    }

    /**
     * Updates the way broadcast of the local audio track is handled,
     * attaches an audio monitor for voice activation if necessary.
     */
    async linkVoiceActivation() {
        this.state.disconnectAudioMonitor?.();
        if (!this.selfSession) {
            return;
        }
        if (this.store.settings.use_push_to_talk || !this.state.channel || !this.state.audioTrack) {
            this.selfSession.isTalking = false;
            await this.refreshAudioStatus();
            return;
        }
        try {
            this.state.disconnectAudioMonitor = await monitorAudio(this.state.audioTrack, {
                onThreshold: async (isAboveThreshold) => {
                    this.setTalking(isAboveThreshold);
                },
                volumeThreshold: this.store.settings.voiceActivationThreshold,
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
            this.selfSession.isTalking = true;
        }
        await this.refreshAudioStatus();
    }

    /**
     * @param {import("models").id} id
     */
    deleteSession(id) {
        const session = this.store.RtcSession.get(id);
        if (session) {
            if (this.selfSession && session.eq(this.selfSession)) {
                this.log(this.selfSession, "self session deleted, ending call", {
                    important: true,
                });
                this.endCall();
            }
            this.disconnect(session);
            session.delete();
        }
    }

    formatInfo() {
        this.selfSession.isCameraOn = Boolean(this.state.cameraTrack);
        this.selfSession.isScreenSharingOn = Boolean(this.state.screenTrack);
        return this.selfSession.info;
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
            audioElement.volume = this.store.settings.getVolume(session);
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
     * @param {import("models").RtcSession} session
     * @param {Object} [param1]
     * @param {String} [param1.type]
     * @param {boolean} [param1.cleanup]
     */
    removeVideoFromSession(session, { type, cleanup = true } = {}) {
        if (type) {
            this.updateActiveSession(session, type);
            if (cleanup) {
                closeStream(session.videoStreams.get(type));
            }
            session.videoStreams.delete(type);
        } else {
            if (cleanup) {
                for (const stream of session.videoStreams.values()) {
                    closeStream(stream);
                }
            }
            session.videoStreams.clear();
        }
    }
    /**
     * @param {RtcSession} session
     */
    removeAudioFromSession(session) {
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
                    session.mainVideoStreamType = "camera";
                } else if (
                    this.actionsStack.includes("camera-on") &&
                    this.actionsStack.includes("share-screen")
                ) {
                    session.mainVideoStreamType = "screen";
                }
            }
        }
    }

    /**
     * @param {import("@mail/discuss/call/common/rtc_session_model").RtcSession} rtcSession
     * @param {Object} [param1]
     * @param {number} [param1.viewCountIncrement=0] negative value to decrement
     */
    updateVideoDownload(rtcSession, { viewCountIncrement = 0 } = {}) {
        rtcSession.videoComponentCount += viewCountIncrement;
        const downloadTimeout = this.downloadTimeouts.get(rtcSession.id);
        if (downloadTimeout) {
            this.downloadTimeouts.delete(rtcSession.id);
            browser.clearTimeout(downloadTimeout);
        }
        if (rtcSession.videoComponentCount > 0) {
            this.network?.updateDownload(rtcSession.id, {
                camera: true,
                screen: true,
            });
        } else {
            /**
             * We wait a bit before pausing a download to avoid flickering, if the user stops downloading and starts again
             * soon after, it is not worth pausing the download.
             */
            this.downloadTimeouts.set(
                rtcSession.id,
                browser.setTimeout(() => {
                    this.downloadTimeouts.delete(rtcSession.id);
                    this.network?.updateDownload(rtcSession.id, {
                        camera: false,
                        screen: false,
                    });
                }, 1000)
            );
        }
    }
}

Rtc.register();

export const rtcService = {
    dependencies: [
        "bus_service",
        "discuss.p2p",
        "discuss.ptt_extension",
        "mail.sound_effects",
        "mail.store",
        "notification",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const store = env.services["mail.store"];
        const rtc = store.rtc;
        rtc.p2pService = services["discuss.p2p"];
        rtc.p2pService.acceptOffer = async (id, sequence) => {
            const session = await store.RtcSession.getWhenReady(Number(id));
            /**
             * We only accept offers for new connections (higher sequence),
             * or offers that renegotiate an existing connection (same sequence).
             */
            return sequence >= session?.sequence;
        };
        services["bus_service"].subscribe(
            "discuss.channel.rtc.session/sfu_hot_swap",
            async ({ serverInfo }) => {
                if (!rtc.selfSession) {
                    return;
                }
                if (rtc.serverInfo?.channelUUID === serverInfo.channelUUID) {
                    // no reason to swap if the server is the same, if at some point we want to force a swap
                    // there should be an explicit flag in the event payload.
                    return;
                }
                rtc.serverInfo = serverInfo;
                await rtc._initConnection();
            }
        );
        services["bus_service"].subscribe("discuss.channel.rtc.session/ended", ({ sessionId }) => {
            if (rtc.selfSession?.id === sessionId) {
                rtc.endCall();
                services.notification.add(_t("Disconnected from the RTC call by the server"), {
                    type: "warning",
                });
            }
        });
        services["bus_service"].subscribe("res.users.settings.volumes", (payload) => {
            if (payload) {
                rtc.store.Volume.insert(payload);
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
                    rtc.store.insert(data);
                }
            }
        );
        return rtc;
    },
};

registry.category("services").add("discuss.rtc", rtcService);
