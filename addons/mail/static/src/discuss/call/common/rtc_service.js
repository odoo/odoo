import { fields, Record } from "@mail/core/common/record";
import { BlurManager } from "@mail/discuss/call/common/blur_manager";
import { monitorAudio } from "@mail/utils/common/media_monitoring";
import { rpc } from "@web/core/network/rpc";
import { assignDefined, closeStream, onChange } from "@mail/utils/common/misc";
import { CallInfiniteMirroringWarning } from "@mail/discuss/call/common/call_infinite_mirroring_warning";

import { reactive, toRaw } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { debounce } from "@web/core/utils/timing";
import { loadBundle, loadJS } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";
import { url } from "@web/core/utils/urls";
import { isMobileOS } from "@web/core/browser/feature_detection";

let sequence = 1;
const getSequence = () => sequence++;

/**
 * @typedef {'audio' | 'camera' | 'screen' } streamType
 */

/**
 * @return {Promise<{ SfuClient: import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient, SFU_CLIENT_STATE: import("@mail/../lib/odoo_sfu/odoo_sfu").SFU_CLIENT_STATE }>}
 */
const loadSfuAssets = memoize(async () => await loadBundle("mail.assets_odoo_sfu"));

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

const SW_MESSAGE_TYPE = {
    POST_RTC_LOGS: "POST_RTC_LOGS",
};
export const CONNECTION_TYPES = { P2P: "p2p", SERVER: "server" };
const SCREEN_CONFIG = {
    width: { max: 1920 },
    height: { max: 1080 },
    aspectRatio: 16 / 9,
    frameRate: {
        max: 24,
    },
};

const IS_CLIENT_RTC_COMPATIBLE = Boolean(window.RTCPeerConnection && window.MediaStream);
function GET_DEFAULT_ICE_SERVERS() {
    return [{ urls: ["stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302"] }];
}
export const CROSS_TAB_HOST_MESSAGE = {
    PING: "PING", // signals that the host is still active
    UPDATE_REMOTE: "UPDATE_REMOTE", // sent with updated state of the remote rtc sessions of the call
    CLOSE: "CLOSE", // sent when the host ends the call
    PIP_CHANGE: "PIP_CHANGE", // sent when the host changes the pip mode
};
export const CROSS_TAB_CLIENT_MESSAGE = {
    INIT: "INIT", // sent by a tab to signal its presence and receive a state update
    REQUEST_ACTION: "REQUEST_ACTION", // request that an action be executed by the host (mute, deaf,...)
    LEAVE: "LEAVE", // request the host to leave the call
    UPDATE_VOLUME: "UPDATE_VOLUME", // sent by a tab to signal a volume change
};
const PING_INTERVAL = 30_000;
const UNAVAILABLE_AS_REMOTE = _t("This action can only be done in the call tab.");
const CALL_FULLSCREEN_ID = Symbol("CALL_FULLSCREEN");

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
        const proms = [this.p2p.updateUpload(type, track)];
        if (this.sfu?.state === "connected") {
            proms.push(this.sfu.updateUpload(type, track));
        }
        await Promise.all(proms);
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
    notifications = reactive(new Map());
    /** @type {Map<string, number>} timeoutId by notificationId for call notifications */
    timeouts = new Map();
    /** @type {Map<number, number>} timeoutId by sessionId for download pausing delay */
    downloadTimeouts = new Map();
    /** @type {{urls: string[]}[]} */
    iceServers = fields.Attr(undefined, {
        compute() {
            return this.iceServers ? this.iceServers : GET_DEFAULT_ICE_SERVERS();
        },
    });
    /**
     * The RtcSession of the current user for the call hosted by this tab, this is only set if
     * the current tab is the cross-tab host (the tab that is maintaining the connections and streams).
     *
     * If you want a reference to the RtcSession of the call, regardless of where it is hosted,
     * as long as it is on the same browser, use `selfSession`.
     */
    localSession = fields.One("discuss.channel.rtc.session");
    /**
     * The RtcSession shared between tabs, this is set if any of the tabs of that browser is in a call.
     *
     * For most use cases, this is the RtcSession you want to use (to ensure cross-tab consistency),
     * unless you need to access actual connection data (connection stats, streams,...), which can only
     * be accessed from the tab that is hosting the call.
     */
    selfSession = fields.One("discuss.channel.rtc.session", {
        compute() {
            return (
                this.localSession ||
                this.store["discuss.channel.rtc.session"].get(this._remotelyHostedSessionId)
            );
        },
    });
    channel = fields.One("Thread", {
        compute() {
            if (this.state.channel) {
                return this.state.channel;
            }
            if (this._remotelyHostedChannelId) {
                return this.store.Thread.insert({
                    model: "discuss.channel",
                    id: this._remotelyHostedChannelId,
                });
            }
        },
        onUpdate() {
            if (!this.channel) {
                return;
            }
            this.store.Thread.getOrFetch({
                model: "discuss.channel",
                id: this.channel.id,
            });
        },
    });
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
    /** @type {AudioContext} AudioContext used to mix screen and mic audio */
    audioContext;
    // cross tab sync
    _broadcastChannel = new browser.BroadcastChannel("call_sync_state");
    _remotelyHostedSessionId;
    _remotelyHostedChannelId;
    _crossTabTimeoutId;
    /** @type {number} count of how many times the p2p service attempted a connection recovery */
    _p2pRecoveryCount = 0;
    upgradeConnectionDebounce = debounce(
        () => {
            this._upgradeConnection();
        },
        15000,
        { leading: true, trailing: false }
    );

    /**
     * Whether this tab serves as a remote for a call hosted on another tab.
     */
    get isRemote() {
        return Boolean(this._remotelyHostedChannelId);
    }
    /**
     * Whether the current tab is the host of the call.
     */
    get isHost() {
        return Boolean(this.localSession);
    }

    callActions = fields.Attr([], {
        compute() {
            return registry
                .category("discuss.call/actions")
                .getEntries()
                .filter(([key, action]) => action.condition({ rtc: this }))
                .map(([key, action]) => [key, action.isActive({ rtc: this }), action.isTracked]);
        },
        onUpdate() {
            for (const [key, isActive, isTracked] of this.callActions) {
                if (isActive === this.lastActions[key]) {
                    continue;
                }
                if (!isTracked) {
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
            logs: {},
            sendCamera: false,
            sendScreen: false,
            updateAndBroadcastDebounce: undefined,
            micAudioTrack: undefined,
            screenAudioTrack: undefined,
            audioTrack: undefined,
            cameraTrack: undefined,
            screenTrack: undefined,
            /**
             * callback to properly end the audio monitoring.
             * If set it indicates that we are currently monitoring the local
             * micAudioTrack for the voice activation feature.
             */
            disconnectAudioMonitor: undefined,
            pttReleaseTimeout: undefined,
            sourceCameraStream: null,
            sourceScreenStream: null,
            /**
             * Whether the network fell back to p2p mode in a SFU call.
             */
            fallbackMode: false,
            isPipMode: false,
            isFullscreen: false,
        });
        this.blurManager = undefined;
    }

    start() {
        const services = this.store.env.services;
        this.notification = services.notification;
        this.overlay = services.overlay;
        this.soundEffectsService = services["mail.sound_effects"];
        this.pttExtService = services["discuss.ptt_extension"];
        if (this._broadcastChannel) {
            this._broadcastChannel.onmessage = this._onBroadcastChannelMessage.bind(this);
            this._postToTabs({ type: CROSS_TAB_CLIENT_MESSAGE.INIT });
        }
        /**
         * @type {import("@mail/discuss/call/common/peer_to_peer").PeerToPeer}
         */
        this.p2pService = services["discuss.p2p"];
        onChange(this.store.settings, "useBlur", () => {
            if (this.state.sendCamera) {
                this.toggleVideo("camera", { force: true });
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
            if (this.localSession) {
                await this.resetMicAudioTrack({ force: true });
            }
        });
        onChange(this.store.settings, "audioOutputDeviceId", async () => {
            if (this.localSession) {
                await this.setOutputDevice(this.store.settings.audioOutputDeviceId);
            }
        });
        onChange(this.store.settings, "cameraInputDeviceId", async () => {
            if (this.localSession && this.state.cameraTrack) {
                await this.toggleVideo("camera", { force: true, refreshStream: true });
            }
        });
        this.store.env.bus.addEventListener("RTC-SERVICE:PLAY_MEDIA", () => {
            const channel = this.state.channel;
            if (!channel) {
                return;
            }
            for (const session of channel.rtc_session_ids) {
                session.playAudio();
            }
        });
        browser.addEventListener(
            "keydown",
            (ev) => {
                this.onKeyDown(ev);
            },
            { capture: true }
        );
        browser.addEventListener(
            "keyup",
            (ev) => {
                this.onKeyUp(ev);
            },
            { capture: true }
        );

        browser.addEventListener("pagehide", () => {
            if (this.state.channel) {
                const data = JSON.stringify({
                    params: { channel_id: this.state.channel.id, session_id: this.selfSession.id },
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
            if (!this.localSession || !this.state.channel) {
                return;
            }
            this._postToTabs({
                type: CROSS_TAB_HOST_MESSAGE.PING,
                hostedSessionId: this.localSession.id,
            });
            await this.ping();
            if (!this.localSession || !this.state.channel) {
                return;
            }
            this.call();
        }, PING_INTERVAL);
    }

    get displaySurface() {
        return this.state.sourceScreenStream?.getVideoTracks()[0]?.getSettings().displaySurface;
    }

    onKeyDown(ev) {
        if (!this.store.settings.isPushToTalkKey(ev)) {
            return;
        }
        this.onPushToTalk();
    }

    onKeyUp(ev) {
        if (
            !this.state.channel ||
            !this.store.settings.use_push_to_talk ||
            !this.store.settings.isPushToTalkKey(ev) ||
            !this.localSession.isTalking
        ) {
            return;
        }
        this.setPttReleaseTimeout();
    }

    showMirroringWarning() {
        this.state.screenTrack.enabled = false;
        const trackEndedFn = () => this.removeMirroringWarning?.();
        this.removeMirroringWarning = this.overlay.add(
            CallInfiniteMirroringWarning,
            {
                onClose: ({ stopScreensharing } = {}) => {
                    this.removeMirroringWarning({ stopScreensharing });
                },
            },
            {
                onRemove: ({ stopScreensharing } = {}) => {
                    if (stopScreensharing) {
                        this.toggleVideo("screen", false);
                    }
                    this.state.screenTrack?.removeEventListener("ended", trackEndedFn);
                    this.removeMirroringWarning = null;
                },
            }
        );
        this.state.screenTrack.addEventListener("ended", trackEndedFn, { once: true });
    }

    setPttReleaseTimeout(duration = 200) {
        this.state.pttReleaseTimeout = browser.setTimeout(() => {
            this.setTalking(false);
            if (!this.localSession?.isMute) {
                this.soundEffectsService.play("ptt-release");
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
        if (!this.localSession.isTalking && !this.localSession.isMute) {
            this.soundEffectsService.play("ptt-press");
        }
        this.setTalking(true);
    }

    async openPip(options) {
        if (this.isHost) {
            await this.pipService.openPip(options);
            return;
        }
        this.notification.add(UNAVAILABLE_AS_REMOTE, {
            type: "warning",
        });
    }

    closePip() {
        if (this.isHost) {
            this.pipService.closePip();
        } else {
            this._remoteAction({ pip: false });
        }
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
        await this.rpcLeaveCall(channel);
        this.endCall(channel);
        this.state.hasPendingRequest = false;
    }

    /**
     * @param {import("models").Thread} [channel]
     */
    endCall(channel = this.state.channel) {
        this._endHost();
        if (channel.selfMember) {
            channel.selfMember.rtc_inviting_session_id = undefined;
        }
        channel.activeRtcSession = undefined;
        if (channel.eq(this.state.channel)) {
            this.state.logs.end = new Date().toISOString();
            this.dumpLogs();
            this.pttExtService.unsubscribe();
            this.network?.disconnect();
            this.clear();
            this.soundEffectsService.play("call-leave");
        }
    }

    async deafen() {
        if (this.isRemote) {
            this._remoteAction({ is_deaf: true });
            return;
        }
        await this.setDeaf(true);
        this.soundEffectsService.play("earphone-off");
    }

    /**
     * @param {import("models").RtcSession} session
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

    setVolume(session, volume) {
        session.volume = volume;
        this.store.settings.saveVolumeSetting({
            guestId: session?.guest_id?.id,
            partnerId: session?.partner_id?.id,
            volume,
        });
        this._postToTabs({
            type: CROSS_TAB_CLIENT_MESSAGE.UPDATE_VOLUME,
            changes: { sessionId: session.id, volume },
        });
    }

    async mute() {
        if (this.isRemote) {
            this._remoteAction({ is_muted: true });
            return;
        }
        await this.setMute(true);
        this.soundEffectsService.play("mic-off");
    }

    async enterFullscreen() {
        const Call = registry.category("discuss.call/components").get("Call");
        await this.fullscreen.enter(Call, { id: CALL_FULLSCREEN_ID });
    }

    async exitFullscreen() {
        await this.fullscreen.exit(CALL_FULLSCREEN_ID);
    }

    /**
     * @param {import("models").Thread} channel
     * @param {Object} [initialState={}]
     * @param {boolean} [initialState.audio]
     * @param {boolean} [initialState.camera]
     */
    async toggleCall(channel, { audio = true, camera } = {}) {
        if (channel.id === this._remotelyHostedChannelId) {
            this._postToTabs({ type: CROSS_TAB_CLIENT_MESSAGE.LEAVE });
            this.clear();
            return;
        }
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
            await this.leaveCall(this.state.channel);
        }
        if (!isActiveCall) {
            await this.joinCall(channel, { audio, camera });
        }
    }

    async toggleCameraFacingMode() {
        this.store.settings.cameraFacingMode =
            this.store.settings.cameraFacingMode === "user" ? "environment" : "user";
        await this.toggleVideo("camera", { force: true, refreshStream: true });
    }

    async toggleDeafen() {
        if (this.selfSession.is_deaf) {
            await this.undeafen();
            if (this.selfSession.is_muted) {
                await this.unmute();
            }
        } else {
            await this.deafen();
        }
    }

    async toggleMicrophone() {
        if (this.selfSession.isMute) {
            if (this.selfSession.is_muted) {
                await this.unmute();
            }
            if (this.selfSession.is_deaf) {
                await this.undeafen();
            }
        } else {
            await this.mute();
        }
    }

    async undeafen() {
        if (this.isRemote) {
            this._remoteAction({ is_deaf: false });
            return;
        }
        await this.setDeaf(false);
        this.soundEffectsService.play("earphone-on");
    }

    async unmute() {
        if (this.isRemote) {
            this._remoteAction({ is_muted: false });
            return;
        }
        if (this.state.micAudioTrack) {
            await this.setMute(false);
        } else {
            await this.resetMicAudioTrack({ force: true });
        }
        this.soundEffectsService.play("mic-on");
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
        this.localSession.connectionState = "selecting network type";
        this.state.connectionType = CONNECTION_TYPES.P2P;
        this.network?.disconnect();
        // loading p2p in any case as we may need to receive peer-to-peer connections from users who failed to connect to the SFU.
        this.p2pService.connect(this.localSession.id, this.state.channel.id, {
            info: this.formatInfo(),
            iceServers: this.iceServers,
        });
        this.network = new Network(this.p2pService);
        this.updateUpload();
        if (this.serverInfo) {
            this.log(this.localSession, "loading sfu server", {
                step: "loading sfu server",
                serverInfo: toRaw(this.serverInfo),
            });
            this.localSession.connectionState = "loading SFU assets";
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
                this.log(this.localSession, "failed to load sfu server", {
                    error: e,
                    important: true,
                });
            }
            this.selfSession.connectionState = "initializing";
        } else {
            this.log(this.localSession, "no sfu server info, using peer-to-peer");
        }
        this.network.addEventListener("stateChange", this._handleSfuClientStateChange);
        this.network.addEventListener("update", this._handleNetworkUpdates);
        this.network.addEventListener("log", ({ detail: { id, level, message } }) => {
            const session = this.store["discuss.channel.rtc.session"].get(id);
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
     * Send an action to the host tab of the call
     *
     * @param {Object} changes
     */
    _remoteAction(changes) {
        this._postToTabs({
            type: CROSS_TAB_CLIENT_MESSAGE.REQUEST_ACTION,
            changes,
        });
    }

    _updateInfo() {
        if (!this.isHost) {
            return;
        }
        const info = toRaw(this.formatInfo());
        this.network?.updateInfo(info);
        this._updateRemoteTabs({ [this.localSession.id]: info });
    }

    _host() {
        this._remotelyHostedChannelId = undefined;
        this._remotelyHostedSessionId = this.localSession.id;
        this._updateRemoteTabs({ [this.localSession.id]: toRaw(this.formatInfo()) });
    }
    _endHost() {
        this._postToTabs({
            type: CROSS_TAB_HOST_MESSAGE.CLOSE,
            hostedSessionId: this._remotelyHostedSessionId,
        });
    }

    _updateRemoteTabs(changes) {
        this._postToTabs({
            type: CROSS_TAB_HOST_MESSAGE.UPDATE_REMOTE,
            hostedChannelId: this.state.channel.id,
            hostedSessionId: this.localSession.id,
            changes,
        });
    }

    _postToTabs(message) {
        if (!this._broadcastChannel) {
            this.log(this.selfSession, "broadcast channel not available");
            return;
        }
        try {
            this._broadcastChannel.postMessage(message);
        } catch (error) {
            this.log(this.selfSession, "failed to post message to broadcast channel", { error });
        }
    }

    _refreshCrossTabTimeout() {
        browser.clearTimeout(this._crossTabTimeoutId);
        this._crossTabTimeoutId = browser.setTimeout(() => {
            this.clear();
        }, PING_INTERVAL + 10_000);
    }

    async _onBroadcastChannelMessage({
        data: { type, hostedChannelId, hostedSessionId, changes },
    }) {
        switch (type) {
            case CROSS_TAB_HOST_MESSAGE.UPDATE_REMOTE:
                if (this.isHost) {
                    return;
                }
                this._remotelyHostedSessionId = hostedSessionId;
                this._remotelyHostedChannelId = hostedChannelId;
                this._refreshCrossTabTimeout();
                this.updateSessionInfo(changes);
                return;
            case CROSS_TAB_HOST_MESSAGE.CLOSE: {
                if (this._remotelyHostedSessionId !== hostedSessionId) {
                    return;
                }
                this.clear();
                return;
            }
            case CROSS_TAB_HOST_MESSAGE.PIP_CHANGE: {
                if (this.isHost) {
                    return;
                }
                this.state.isPipMode = changes.isPipMode;
                return;
            }
            case CROSS_TAB_HOST_MESSAGE.PING: {
                this._refreshCrossTabTimeout();
                return;
            }
            case CROSS_TAB_CLIENT_MESSAGE.INIT: {
                if (!this.isHost) {
                    return;
                }
                this._updateRemoteTabs({ [this.localSession.id]: toRaw(this.formatInfo()) });
                this._postToTabs({
                    type: CROSS_TAB_HOST_MESSAGE.PIP_CHANGE,
                    changes: { isPipMode: this.state.isPipMode },
                });
                return;
            }
            case CROSS_TAB_CLIENT_MESSAGE.REQUEST_ACTION: {
                if (!this.isHost) {
                    return;
                }
                await this._localAction(changes);
                this._updateRemoteTabs({ [this.localSession.id]: toRaw(this.formatInfo()) });
                return;
            }
            case CROSS_TAB_CLIENT_MESSAGE.LEAVE: {
                if (!this.isHost) {
                    return;
                }
                await this.leaveCall(this.channel);
                return;
            }
            case CROSS_TAB_CLIENT_MESSAGE.UPDATE_VOLUME: {
                const session = this.store["discuss.channel.rtc.session"].get(changes.sessionId);
                if (!session) {
                    return;
                }
                session.volume = changes.volume;
                return;
            }
        }
    }

    async _localAction(actions = {}) {
        const promises = [];
        for (const [key, value] of Object.entries(actions)) {
            switch (key) {
                case "is_muted":
                    if (value === this.localSession.is_muted) {
                        break;
                    }
                    promises.push(value ? this.mute() : this.unmute());
                    break;
                case "is_deaf":
                    if (value === this.localSession.is_deaf) {
                        break;
                    }
                    value ? promises.push(this.deafen()) : promises.push(this.undeafen());
                    break;
                case "raisingHand":
                    if (value === Boolean(this.localSession.raisingHand)) {
                        break;
                    }
                    promises.push(this.raiseHand(value));
                    break;
                case "pip":
                    if (value === this.state.isPipMode) {
                        break;
                    }
                    if (value) {
                        promises.push(this.openPip());
                    } else {
                        this.closePip();
                    }
                    break;
            }
        }
        await Promise.all(promises);
    }

    /**
     * @param {import("models").RtcSession} session
     * @param {String} entry
     * @param {Object} [param2]
     * @param {Error} [param2.error]
     * @param {String} [param2.step] current step of the flow
     * @param {String} [param2.state] current state of the connection
     * @param {Boolean} [param2.important] if the log is important and should be kept even if logRtc is disabled
     */
    log(session, entry, param2 = {}) {
        const { error, step, state, important, ...data } = param2;
        session.logStep = entry;
        if (!this.store.settings.logRtc && !important) {
            return;
        }
        console.debug(
            `%c${new Date().toLocaleString()} - [${entry}]`,
            "color: #e36f17; font-weight: bold;",
            toRaw(session)._raw,
            param2
        );
        if (!this.state.logs) {
            return;
        }
        let sessionEntry = this.state.logs.entriesBySessionId[session.id];
        if (!sessionEntry) {
            this.state.logs.entriesBySessionId[session.id] = sessionEntry = {
                step: "",
                state: "",
                logs: [],
            };
        }
        if (step) {
            sessionEntry.step = step;
        }
        if (state) {
            sessionEntry.state = state;
        }
        sessionEntry.logs.push({
            event: `${new Date().toISOString()}: ${entry}`,
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
                    const session = await this.store["discuss.channel.rtc.session"].getWhenReady(
                        senderId
                    );
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
                    const session = this.store["discuss.channel.rtc.session"].get(id);
                    if (!session) {
                        return;
                    }
                    session.connectionState = state;
                }
                return;
            case "disconnect":
                {
                    const { sessionId } = payload;
                    const session = this.store["discuss.channel.rtc.session"].get(sessionId);
                    if (!session) {
                        return;
                    }
                    this.disconnect(session);
                }
                return;
            case "info_change":
                this.updateSessionInfo(payload);
                return;
            case "track":
                {
                    const { sessionId, type, track, active, sequence } = payload;
                    const session = await this.store["discuss.channel.rtc.session"].getWhenReady(
                        sessionId
                    );
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
            case "recovery": {
                const { id } = payload;
                const session = this.store["discuss.channel.rtc.session"].get(id);
                if (
                    this.selfSession?.persona.main_user_id?.share !== false ||
                    this.serverInfo ||
                    this.state.fallbackMode ||
                    !session?.channel.eq(this.state.channel)
                ) {
                    return;
                }
                this._p2pRecoveryCount++;
                if (this._p2pRecoveryCount > 1 || !hasTurn(this.iceServers)) {
                    this.upgradeConnectionDebounce();
                }
            }
        }
    }

    async _handleSfuClientStateChange({ detail: { state, cause } }) {
        this.log(this.localSession, `connection state change: ${state}`, { state, cause });
        this.localSession.connectionState = state;
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
                        this.log(this.localSession, text, { important: true });
                        this._downgradeConnection();
                    }
                    this.notification.add(text, {
                        type: "warning",
                    });
                }
                return;
        }
    }

    async _upgradeConnection() {
        const channelId = this.state.channel?.id;
        if (this.serverInfo || this.state.fallbackMode || !channelId) {
            return;
        }
        await rpc(
            "/mail/rtc/channel/upgrade_connection",
            { channel_id: channelId },
            { silent: true }
        );
    }

    updateSessionInfo(payload) {
        if (!payload) {
            return;
        }
        if (this.isHost) {
            this._updateRemoteTabs(payload);
        }
        for (const [id, info] of Object.entries(payload)) {
            (async () => {
                const session = await this.store["discuss.channel.rtc.session"].getWhenReady(
                    Number(id)
                );
                if (!session || !this.channel) {
                    return;
                }
                // `isRaisingHand` is turned into the Date `raisingHand`
                this.setRemoteRaiseHand(session, info.isRaisingHand);
                delete info.isRaisingHand;
                assignDefined(session, {
                    is_muted: info.isSelfMuted ?? info.is_muted,
                    is_deaf: info.isDeaf ?? info.is_deaf,
                    isTalking: info.isTalking,
                    is_camera_on: info.isCameraOn ?? info.is_camera_on,
                    is_screen_sharing_on: info.isScreenSharingOn ?? info.is_screen_sharing_on,
                });
            })();
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
        if (this.state.channel.rtc_session_ids.length === 0) {
            return;
        }
        const sequence = getSequence();
        for (const session of this.state.channel.rtc_session_ids) {
            if (session.eq(this.localSession)) {
                continue;
            }
            this.p2pService.addPeer(session.id, { sequence });
        }
    }

    /**
     * @param {import("models").RtcSession} session
     * @param {MediaStreamTrack} track
     * @param {streamType} type
     * @param {boolean} active false if the track is muted/disabled
     */
    async handleRemoteTrack({ session, track, type, active = true }) {
        session.updateStreamState(type, active);
        await this.updateStream(session, track, {
            mute: this.localSession.is_deaf,
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
                check_rtc_session_ids: channel.rtc_session_ids.map((session) => session.id),
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
                if (!this.localSession) {
                    return;
                }
                await rpc(
                    "/mail/rtc/session/update_and_broadcast",
                    {
                        session_id: this.localSession.id,
                        values: pick(
                            this.localSession,
                            "is_camera_on",
                            "is_deaf",
                            "is_muted",
                            "is_screen_sharing_on"
                        ),
                    },
                    { silent: true }
                );
            },
            3000,
            { leading: true, trailing: true }
        );
        if (this.state.channel.selfMember) {
            this.state.channel.selfMember.rtc_inviting_session_id = undefined;
        }
        if (camera) {
            await this.toggleVideo("camera");
        }
        if (!this.selfSession) {
            return;
        }
        await this._initConnection();
        await this.resetMicAudioTrack({ force: audio });
        if (!this.state.channel?.id) {
            return;
        }
        this.soundEffectsService.play("call-join");
        this._host();
        this.cleanups.push(
            // only register the beforeunload event if there is a call as FireFox will not place
            // the pages with beforeunload listeners in the bfcache.
            subscribe(browser, "beforeunload", (event) => {
                event.preventDefault();
            })
        );
        this.channel?.focusAvailableVideo();
    }

    newLogs() {
        this.state.logs = {
            channelId: this.state.channel.id,
            selfSessionId: this.localSession.id,
            start: new Date().toISOString(),
            hasTurn: hasTurn(this.iceServers),
            entriesBySessionId: {},
        };
    }

    /**
     * @param {Object} [param0={}]
     * @param  {boolean} [param0.download=false] true if we want to download the logs
     */
    dumpLogs({ download = false } = {}) {
        const logs = [];
        if (this.state.logs) {
            logs.push({
                type: "timeline",
                entry: this.state.logs.start,
                value: toRaw(this.state.logs),
            });
        }
        if (this.state.channel) {
            logs.push(this.buildSnapshot());
        }
        if (logs.length || download) {
            browser.navigator.serviceWorker?.controller?.postMessage({
                name: SW_MESSAGE_TYPE.POST_RTC_LOGS,
                logs,
                download,
            });
        }
    }

    buildSnapshot() {
        const server = {};
        if (this.state.connectionType === CONNECTION_TYPES.SERVER) {
            server.info = toRaw(this.serverInfo);
            server.state = this.sfuClient?.state;
            server.errors = this.sfuClient?.errors.map((error) => error.message);
        }
        const sessions = this.state.channel.rtc_session_ids.map((session) => {
            const sessionInfo = {
                id: session.id,
                channelMemberId: session.channel_member_id?.id,
                state: session.connectionState,
                audioError: session.audioError,
                videoError: session.videoError,
                sfuConsumers: this.network?.getSfuConsumerStats(session.id),
            };
            if (session.eq(this.selfSession)) {
                sessionInfo.isSelf = true;
            }
            const audioEl = session.audioElement;
            if (audioEl) {
                sessionInfo.audio = {
                    state: audioEl.readyState,
                    muted: audioEl.muted,
                    paused: audioEl.paused,
                    networkState: audioEl.networkState,
                };
            }
            const peer = this.p2pService?.peers.get(session.id);
            if (peer) {
                sessionInfo.peer = {
                    id: peer.id,
                    state: peer.connection.connectionState,
                    iceState: peer.connection.iceConnectionState,
                };
            }
            return sessionInfo;
        });
        return {
            type: "snapshot",
            entry: new Date().toISOString(),
            value: {
                server,
                sessions,
                connectionType: this.state.connectionType,
                fallback: this.state.fallbackMode,
            },
        };
    }

    logSnapshot() {
        if (!this.state.channel) {
            // a snapshot out of a call would not collect any data
            return;
        }
        browser.navigator.serviceWorker?.controller?.postMessage({
            name: SW_MESSAGE_TYPE.POST_RTC_LOGS,
            logs: [this.buildSnapshot()],
        });
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
                check_rtc_session_ids: this.state.channel.rtc_session_ids.map(
                    (session) => session.id
                ),
                rtc_session_id: this.localSession.id,
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
            for (const session of this.state.channel.rtc_session_ids) {
                this.removeAudioFromSession(session);
                this.removeVideoFromSession(session);
                session.isTalking = false;
            }
        }
        this.exitFullscreen();
        this._remotelyHostedSessionId = undefined;
        this._remotelyHostedChannelId = undefined;
        browser.clearTimeout(this._crossTabTimeoutId);
        this.cleanups.splice(0).forEach((cleanup) => cleanup());
        browser.clearTimeout(this.sfuTimeout);
        this.sfuClient = undefined;
        this.network = undefined;
        this.audioContext?.close();
        this.audioContext = undefined;
        this._p2pRecoveryCount = 0;
        this.state.updateAndBroadcastDebounce?.cancel();
        this.state.disconnectAudioMonitor?.();
        this.state.micAudioTrack?.stop();
        this.state.screenAudioTrack?.stop();
        this.state.audioTrack?.stop();
        this.state.cameraTrack?.stop();
        this.state.screenTrack?.stop();
        this.state.fallbackMode = undefined;
        this.state.isPipMode = false;
        closeStream(this.state.sourceCameraStream);
        this.state.sourceCameraStream = null;
        closeStream(this.state.sourceScreenStream);
        this.state.sourceScreenStream = null;
        if (this.blurManager) {
            this.blurManager.close();
            this.blurManager = undefined;
        }
        this.update({
            localSession: undefined,
            serverInfo: undefined,
        });
        Object.assign(this.state, {
            updateAndBroadcastDebounce: undefined,
            connectionType: undefined,
            disconnectAudioMonitor: undefined,
            cameraTrack: undefined,
            screenTrack: undefined,
            screenAudioTrack: undefined,
            micAudioTrack: undefined,
            audioTrack: undefined,
            sendCamera: false,
            sendScreen: false,
            channel: undefined,
            fallbackMode: false,
        });
        this.pipService?.closePip();
    }

    /**
     * @param {Boolean} is_deaf
     */
    async setDeaf(is_deaf) {
        this.updateAndBroadcast({ is_deaf });
        for (const session of this.state.channel.rtc_session_ids) {
            if (!session.audioElement) {
                continue;
            }
            session.audioElement.muted = is_deaf;
        }
        await this.refreshMicAudioStatus();
    }

    async setOutputDevice(deviceId) {
        const promises = [];
        for (const session of this.state.channel.rtc_session_ids) {
            if (!session.audioElement) {
                continue;
            }
            promises.push(session.audioElement.setSinkId(deviceId));
        }
        await Promise.all(promises);
    }

    /**
     * @param {Boolean} is_muted
     */
    async setMute(is_muted) {
        this.updateAndBroadcast({ is_muted });
        await this.refreshMicAudioStatus();
    }

    /**
     * @param {Boolean} raise
     */
    async raiseHand(raise) {
        if (this.isRemote) {
            this._remoteAction({ raisingHand: raise });
            return;
        }
        if (!this.localSession || !this.state.channel) {
            return;
        }
        this.localSession.raisingHand = raise ? new Date() : undefined;
        await this._updateInfo();
    }

    /**
     * @param {boolean} isTalking
     */
    async setTalking(isTalking) {
        if (!this.localSession || isTalking === this.localSession.isTalking) {
            return;
        }
        this.localSession.isTalking = isTalking;
        if (!this.localSession.isMute) {
            this.pttExtService.notifyIsTalking(isTalking);
            await this.refreshMicAudioStatus();
        }
    }

    /**
     * @param {string} type
     * @param {Object} [param1]
     * @param {boolean} [param1.force]
     * @param {boolean} [param1.env]
     * @param {boolean} [param1.refreshStream]
     */
    async toggleVideo(type, options) {
        let force;
        let env;
        let refreshStream;
        if (typeof options === "boolean") {
            force = options;
        } else {
            force = options?.force;
            env = options?.env;
            refreshStream = options?.refreshStream;
        }
        if (this.isRemote) {
            this.notification.add(UNAVAILABLE_AS_REMOTE, {
                type: "warning",
            });
            return;
        }
        if (!this.state.channel?.id) {
            return;
        }
        switch (type) {
            case "camera": {
                const track = this.state.cameraTrack;
                const sendCamera = force ?? !this.state.sendCamera;
                this.state.sendCamera = false;
                await this.setVideo(track, type, { activateVideo: sendCamera, env, refreshStream });
                break;
            }
            case "screen": {
                const track = this.state.screenTrack;
                const sendScreen = force ?? !this.state.sendScreen;
                this.state.sendScreen = false;
                await this.setVideo(track, type, { activateVideo: sendScreen, env });
                break;
            }
        }
        if (this.localSession) {
            switch (type) {
                case "camera": {
                    this.removeVideoFromSession(this.localSession, {
                        type: "camera",
                        cleanup: false,
                    });
                    if (this.state.cameraTrack) {
                        this.updateStream(this.localSession, this.state.cameraTrack);
                    }
                    break;
                }
                case "screen": {
                    if (!this.state.screenTrack) {
                        this.removeVideoFromSession(this.localSession, {
                            type: "screen",
                            cleanup: false,
                        });
                    } else {
                        this.updateStream(this.localSession, this.state.screenTrack);
                    }
                    break;
                }
            }
        }
        const updatedTrack = type === "camera" ? this.state.cameraTrack : this.state.screenTrack;
        await this.network?.updateUpload(type, updatedTrack);
        if (!this.localSession) {
            return;
        }
        switch (type) {
            case "camera": {
                this.updateAndBroadcast({
                    is_camera_on: !!this.state.sendCamera,
                });
                break;
            }
            case "screen": {
                this.updateAndBroadcast({
                    is_screen_sharing_on: !!this.state.sendScreen,
                });
                break;
            }
        }
    }

    updateAndBroadcast(data) {
        this._updateRemoteTabs({ [this.localSession.id]: data });
        assignDefined(this.localSession, data);
        this.state.updateAndBroadcastDebounce?.();
    }

    /**
     * Sets the enabled property of the local microphone audio track based on the
     * current session state. And notifies peers of the new audio state.
     */
    async refreshMicAudioStatus() {
        if (!this.state.micAudioTrack) {
            return;
        }
        this.state.micAudioTrack.enabled = !this.localSession.isMute && this.localSession.isTalking;
        this._updateInfo();
    }

    /**
     * @param {String} type 'camera' or 'screen'
     * @param {Object} [param1] options
     * @param {Boolean} [param1.activateVideo=false] options
     * @param {Env} [param1.env]
     * @param {Boolean} [param1.refreshStream] whether we are requesting a new stream
     */
    async setVideo(track, type, options) {
        let activateVideo;
        let env;
        if (typeof options === "boolean") {
            activateVideo = options ?? false;
        } else {
            activateVideo = options?.activateVideo ?? false;
            env = options?.env;
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
            if (type === "camera" && this.blurManager) {
                this.blurManager.close();
                this.blurManager = undefined;
            }
            stopVideo();
            return;
        }
        let sourceStream;
        const sourceWindow = env?.pipWindow ?? browser;
        try {
            if (type === "camera") {
                if (this.state.sourceCameraStream && !options?.refreshStream) {
                    sourceStream = this.state.sourceCameraStream;
                } else {
                    closeStream(this.state.sourceCameraStream);
                    sourceStream = await sourceWindow.navigator.mediaDevices.getUserMedia({
                        video: this.store.settings.cameraConstraints,
                    });
                }
            }
            if (type === "screen") {
                if (this.state.sourceScreenStream) {
                    sourceStream = this.state.sourceScreenStream;
                } else {
                    sourceStream = await sourceWindow.navigator.mediaDevices.getDisplayMedia({
                        video: SCREEN_CONFIG,
                        audio: true,
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
        if (!this.selfSession) {
            closeStream(sourceStream);
            return;
        }
        let outputTrack = sourceStream ? sourceStream.getVideoTracks()[0] : undefined;
        const screenAudioTrack = sourceStream ? sourceStream.getAudioTracks()[0] : undefined;
        if (outputTrack) {
            outputTrack.addEventListener("ended", async () => {
                await this.toggleVideo(type, { force: false });
            });
            if (type === "camera" && isMobileOS()) {
                const settings = outputTrack.getSettings();
                if (settings?.facingMode) {
                    this.store.settings.cameraFacingMode = settings.facingMode;
                } else if (!this.store.settings.cameraFacingMode) {
                    this.store.settings.cameraFacingMode = "user";
                }
            }
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
                    isCameraSourceExternal: Boolean(sourceStream) && env?.pipWindow,
                });
                break;
            }
            case "screen": {
                Object.assign(this.state, {
                    sourceScreenStream: sourceStream,
                    screenTrack: outputTrack,
                    screenAudioTrack: screenAudioTrack,
                    sendScreen: Boolean(outputTrack),
                    isScreenSourceExternal: Boolean(sourceStream) && env?.pipWindow,
                });
                break;
            }
        }
        if (this.state.screenAudioTrack) {
            this.updateAudioTrack();
        }
    }

    async updateAudioTrack() {
        const { micAudioTrack, screenAudioTrack } = this.state;
        if (!micAudioTrack && !screenAudioTrack) {
            return;
        }
        if (micAudioTrack && screenAudioTrack) {
            await this.audioContext?.close();
            this.audioContext = undefined;
            this.audioContext = new AudioContext();
            const micSource = this.audioContext.createMediaStreamSource(
                new MediaStream([micAudioTrack])
            );
            const screenSource = this.audioContext.createMediaStreamSource(
                new MediaStream([screenAudioTrack])
            );
            const destination = this.audioContext.createMediaStreamDestination();
            micSource.connect(destination);
            screenSource.connect(destination);
            this.state.audioTrack = destination.stream.getAudioTracks()[0];
        } else {
            this.state.audioTrack = micAudioTrack ?? screenAudioTrack;
        }
        await this.network?.updateUpload("audio", this.state.audioTrack);
    }

    async resetMicAudioTrack({ force = false }) {
        this.state.micAudioTrack?.stop();
        this.state.micAudioTrack = undefined;
        this.state.audioTrack?.stop();
        this.state.audioTrack = undefined;
        if (!this.state.channel) {
            return;
        }
        if (this.localSession) {
            this.setMute(true);
        }
        if (force) {
            let micAudioTrack;
            try {
                const audioStream = await browser.navigator.mediaDevices.getUserMedia({
                    audio: this.store.settings.audioConstraints,
                });
                micAudioTrack = audioStream.getAudioTracks()[0];
                if (this.localSession) {
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
            if (!this.localSession) {
                // The getUserMedia promise could resolve when the call is ended
                // in which case the track is no longer relevant.
                micAudioTrack.stop();
                return;
            }
            micAudioTrack.addEventListener("ended", async () => {
                // this mostly happens when the user retracts microphone permission.
                await this.resetMicAudioTrack({ force: false });
                this.setMute(true);
            });
            micAudioTrack.enabled = !this.localSession.isMute && this.localSession.isTalking;
            this.state.micAudioTrack = micAudioTrack;
            this.linkVoiceActivationDebounce();
            this.updateAudioTrack();
        }
    }

    /**
     * Updates the way broadcast of the local audio track is handled,
     * attaches an audio monitor for voice activation if necessary.
     */
    async linkVoiceActivation() {
        this.state.disconnectAudioMonitor?.();
        if (!this.localSession) {
            return;
        }
        if (
            this.store.settings.use_push_to_talk ||
            !this.state.channel ||
            !this.state.micAudioTrack
        ) {
            this.localSession.isTalking = false;
            await this.refreshMicAudioStatus();
            return;
        }
        try {
            this.state.disconnectAudioMonitor = await monitorAudio(this.state.micAudioTrack, {
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
            this.localSession.isTalking = true;
        }
        await this.refreshMicAudioStatus();
    }

    /**
     * @param {import("models").id} id
     */
    deleteSession(id) {
        const session = this.store["discuss.channel.rtc.session"].get(id);
        if (session) {
            if (this.localSession && session.eq(this.localSession)) {
                this.log(this.localSession, "self session deleted, ending call", {
                    important: true,
                });
                this.endCall();
            }
            this.disconnect(session);
            session.delete();
        }
    }

    formatInfo() {
        this.localSession.is_camera_on = Boolean(this.state.cameraTrack);
        this.localSession.is_screen_sharing_on = Boolean(this.state.screenTrack);
        return this.localSession.info;
    }

    /**
     * @param {import("models").RtcSession} session
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
            session.is_muted = false;
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
            if (
                this.selfSession.videoStreams.size === 0 &&
                this.selfSession.eq(this.state.channel.activeRtcSession)
            ) {
                this.state.channel.activeRtcSession = undefined;
            }
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
     * @param {import("models").RtcSession} session
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
     * @param {import("models").RtcSession} session
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
     * @param {import("models").RtcSession} rtcSession
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
        "discuss.pip_service",
        "discuss.ptt_extension",
        "mail.fullscreen",
        "mail.sound_effects",
        "mail.store",
        "legacy_multi_tab",
        "notification",
        "presence",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        const store = env.services["mail.store"];
        const rtc = store.rtc;
        rtc.pipService = services["discuss.pip_service"];
        onChange(rtc.pipService.state, "active", () => {
            const isPipMode = rtc.pipService.state.active;
            if (!isPipMode) {
                rtc.channel?.openChatWindow();
            }
            rtc.state.isPipMode = isPipMode;
            rtc._postToTabs({
                type: CROSS_TAB_HOST_MESSAGE.PIP_CHANGE,
                changes: { isPipMode },
            });
        });
        rtc.fullscreen = services["mail.fullscreen"];
        onChange(rtc.fullscreen, "id", () => {
            const wasFullscreen = rtc.state.isFullscreen;
            rtc.state.isFullscreen = rtc.fullscreen.id === CALL_FULLSCREEN_ID;
            if (
                rtc.state.screenTrack &&
                rtc.displaySurface !== "browser" &&
                rtc.fullscreen.id === CALL_FULLSCREEN_ID
            ) {
                rtc.showMirroringWarning();
            } else if (!rtc.state.isFullscreen) {
                rtc.removeMirroringWarning?.();
                if (wasFullscreen && rtc.state.screenTrack) {
                    rtc.state.screenTrack.enabled = true;
                }
            }
        });
        rtc.p2pService = services["discuss.p2p"];
        rtc.p2pService.acceptOffer = async (id, sequence) => {
            const session = await store["discuss.channel.rtc.session"].getWhenReady(Number(id));
            /**
             * We only accept offers for new connections (higher sequence),
             * or offers that renegotiate an existing connection (same sequence).
             */
            return sequence >= session?.sequence;
        };
        services["bus_service"].subscribe(
            "discuss.channel.rtc.session/sfu_hot_swap",
            async ({ serverInfo }) => {
                if (!rtc.localSession) {
                    return;
                }
                if (rtc.serverInfo?.channelUUID === serverInfo.channelUUID) {
                    // we clear peers as inbound p2p connections may still be active
                    rtc.p2pService.removeALlPeers();
                    // no reason to swap if the server is the same, if at some point we want to force a swap
                    // there should be an explicit flag in the event payload.
                    return;
                }
                rtc.serverInfo = serverInfo;
                await rtc._initConnection();
            }
        );
        services["bus_service"].subscribe("discuss.channel.rtc.session/ended", ({ sessionId }) => {
            if (rtc.localSession?.id === sessionId) {
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
                if (channelId !== rtc.channel?.id) {
                    rtc.store.insert(data);
                }
            }
        );
        /**
         * Attempts to play RTC medias when a user shows signs of presence (interaction with the page) as
         * they cannot be played on windows that have not been interacted with.
         */
        services["presence"].bus.addEventListener(
            "presence",
            () => {
                env.bus.trigger("RTC-SERVICE:PLAY_MEDIA");
            },
            { once: true }
        );
        return rtc;
    },
};

registry.category("services").add("discuss.rtc", rtcService);
