import { onChange } from "@mail/utils/common/misc";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/**
 * @typedef {'camera' | 'screen' } VideoType
 */

/**
 * @typedef {'audio' | VideoType } StreamType
 */

/**
 * @typedef {object} DownloadStates
 * @property {boolean} [audio]
 * @property {boolean} [camera]
 * @property {boolean} [screen]
 */

/**
 * @typedef {Object<string, (import("@mail/discuss/call/common/rtc_session_model").ServerSessionInfo|import("@mail/discuss/call/common/rtc_session_model").SessionInfo)>} SessionInfoMap
 */

export const PTT_RELEASE_DURATION = 200;

export const CONNECTION_TYPES = {
    /** @type {"p2p"} */
    P2P: "p2p",
    /** @type {"server"} */
    SERVER: "server",
};

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
export const CALL_FULLSCREEN_ID = Symbol("CALL_FULLSCREEN");

/**
 * @typedef {Object} SessionSubLogError
 * @property {string} name
 * @property {string} message
 * @property {string} [stack]
 */
/**
 * @typedef {Object} SessionSubLog
 * @property {string} event
 * @property {SessionSubLogError} [error]
 */
/**
 * @typedef {Object} SessionLog
 * @property {string} step
 * @property {string} state
 * @property {SessionSubLog[]} logs
 * @property {boolean} important
 * @property {string} [cause]
 * @property {string} [serverInfo]
 * @property {string} [level]
 */
/**
 * @typedef {Object} RtcLog
 * @property {Number} channelId
 * @property {Number} selfSessionId
 * @property {string} start
 * @property {string} [end]
 * @property {boolean} hasTurn
 * @property {Object<number, SessionLog>} entriesBySessionId
 */

export const rtcService = {
    dependencies: [
        "bus_service",
        "discuss.p2p",
        "discuss.pip_service",
        "discuss.ptt_extension",
        "mail.fullscreen",
        "mail.sound_effects",
        "mail.store",
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
            rtc.isPipMode = isPipMode;
            rtc._postToTabs({
                type: CROSS_TAB_HOST_MESSAGE.PIP_CHANGE,
                changes: { isPipMode },
            });
        });
        rtc.fullscreen = services["mail.fullscreen"];
        onChange(rtc.fullscreen, "id", () => {
            const wasFullscreen = rtc.isFullscreen;
            rtc.isFullscreen = rtc.fullscreen.id === CALL_FULLSCREEN_ID;
            if (
                rtc.screenTrack &&
                rtc.displaySurface !== "browser" &&
                rtc.fullscreen.id === CALL_FULLSCREEN_ID
            ) {
                rtc.showMirroringWarning();
            } else if (!rtc.isFullscreen) {
                rtc.removeMirroringWarning?.();
                if (wasFullscreen && rtc.screenTrack) {
                    rtc.screenTrack.enabled = true;
                }
            }
        });
        browser.navigator.permissions?.query({ name: "microphone" }).then((status) => {
            rtc.microphonePermission = status.state;
            status.onchange = () => (rtc.microphonePermission = status.state);
        });
        browser.navigator.permissions?.query({ name: "camera" }).then((status) => {
            rtc.cameraPermission = status.state;
            status.onchange = () => (rtc.cameraPermission = status.state);
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
                rtc.notifyServerDisconnect();
                rtc.endCall();
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
