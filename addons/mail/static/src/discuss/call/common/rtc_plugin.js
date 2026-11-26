import { BusPlugin } from "@bus/services/bus_plugin";
import { PresencePlugin } from "@bus/services/presence_plugin";
import { MailFullscreenPlugin } from "@mail/core/common/mail_fullscreen";
import { StorePlugin } from "@mail/core/common/store_plugin";
import { CallInvitationsPlugin } from "@mail/discuss/call/common/call_invitations";
import { DiscussP2PPlugin } from "@mail/discuss/call/common/discuss_p2p_plugin";
import { PipPlugin } from "@mail/discuss/call/common/pip_plugin";
import { PttExtensionPlugin } from "@mail/discuss/call/common/ptt_extension_plugin";
import {
    CALL_FULLSCREEN_ID,
    CROSS_TAB_HOST_MESSAGE,
    VIEW_TO_RESTORE,
} from "@mail/discuss/call/common/rtc_model";

import { onWillDestroy, Plugin, useListener, usePlugin } from "@odoo/owl";

import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { services } from "@web/core/services";

/** Wires the `Rtc` record of the store (`store.rtc`) to the plugins and bus events it needs. */
export class RtcPlugin extends Plugin {
    /** Starts after StorePlugin, whose `rtc` record it wires. */
    static sequence = 120;

    #bus = usePlugin(BusPlugin);
    #presence = usePlugin(PresencePlugin);
    #store = usePlugin(StorePlugin);
    #rtc = this.#store.rtc;

    setup() {
        usePlugin(CallInvitationsPlugin);
        this.#rtc.dialog = usePlugin(DialogPlugin);
        this.#rtc.fullscreen = usePlugin(MailFullscreenPlugin);
        this.#rtc.p2pService = usePlugin(DiscussP2PPlugin).p2p;
        this.#rtc.pip = usePlugin(PipPlugin);
        this.#rtc.pttExtService = usePlugin(PttExtensionPlugin);
        this.#rtc.onChange(
            () => [this.#rtc.pip.isActive()],
            function onChangePipMode(isPipMode) {
                if (!isPipMode) {
                    if (this.viewToRestore !== VIEW_TO_RESTORE.NONE && this.channel) {
                        this.enterFullscreen();
                    }
                    this.viewToRestore = VIEW_TO_RESTORE.NONE;
                    this.channel?.openChatWindow();
                }
                this.isPipMode = isPipMode;
                this._postToTabs({
                    type: CROSS_TAB_HOST_MESSAGE.PIP_CHANGE,
                    changes: { isPipMode },
                });
            },
            { immediate: true, initialRun: false }
        );
        this.#rtc.onChange(
            () => [this.#store.meetingViewOpened],
            function onChangeMeetingViewOpened(meetingViewOpened) {
                if (!meetingViewOpened) {
                    this.channel?.resetCallFocus();
                }
            },
            { immediate: true, initialRun: false }
        );
        this.#rtc.onChange(
            () => [this.#rtc.fullscreen.id()],
            function onChangeFullscreen(fullscreenId) {
                const wasFullscreen = this.isFullscreen;
                this.isFullscreen = fullscreenId === CALL_FULLSCREEN_ID;
                if (
                    this.screenTrack &&
                    this.displaySurface !== "browser" &&
                    fullscreenId === CALL_FULLSCREEN_ID
                ) {
                    this.setScreenTrackPaused(true);
                } else if (!this.isFullscreen) {
                    if (wasFullscreen && this.screenTrack) {
                        this.setScreenTrackPaused(false);
                    }
                }
            },
            { immediate: true, initialRun: false }
        );
        this.#rtc.mediaPermissionsPromise = Promise.all([
            window.navigator.permissions
                ?.query({ name: "microphone" })
                .then((status) => {
                    this.#rtc.microphonePermission = status.state;
                    status.onchange = () => (this.#rtc.microphonePermission = status.state);
                })
                .catch(() => {}),
            window.navigator.permissions
                ?.query({ name: "camera" })
                .then((status) => {
                    this.#rtc.cameraPermission = status.state;
                    status.onchange = () => (this.#rtc.cameraPermission = status.state);
                })
                .catch(() => {}),
        ]);
        this.#rtc.p2pService.acceptOffer = async (id, sequence) => {
            const session = await this.#store["discuss.channel.rtc.session"].getWhenReady(
                Number(id)
            );
            /**
             * We only accept offers for new connections (higher sequence),
             * or offers that renegotiate an existing connection (same sequence).
             */
            return sequence >= session?.sequence;
        };
        const unsubscribeHotSwap = this.#bus.subscribe(
            "discuss.channel.rtc.session/sfu_hot_swap",
            async ({ serverInfo }) => {
                if (!this.#rtc.localSession) {
                    return;
                }
                if (this.#rtc.serverInfo?.channelUUID === serverInfo.channelUUID) {
                    // we clear peers as inbound p2p connections may still be active
                    this.#rtc.p2pService.removeALlPeers();
                    // no reason to swap if the server is the same, if at some point we want to force a swap
                    // there should be an explicit flag in the event payload.
                    return;
                }
                this.#rtc.serverInfo = serverInfo;
                await this.#rtc._initConnection();
            }
        );
        const unsubscribeEnded = this.#bus.subscribe(
            "discuss.channel.rtc.session/ended",
            ({ sessionId }) => {
                if (this.#rtc.localSession?.id === sessionId) {
                    this.#rtc.notifyServerDisconnect();
                    this.#rtc.endCall();
                }
            }
        );
        const unsubscribeUpdate = this.#bus.subscribe(
            "discuss.channel.rtc.session/update_and_broadcast",
            (payload) => {
                const { store_data, channelId } = payload;
                /**
                 * If this event comes from the channel of the current call, information is shared in real time
                 * through the peer to peer connection. So we do not use this less accurate broadcast.
                 */
                if (channelId !== this.#rtc.channel?.id) {
                    this.#store.insert(store_data);
                }
            }
        );
        /**
         * Attempts to play RTC medias when a user shows signs of presence (interaction with the page) as
         * they cannot be played on windows that have not been interacted with.
         */
        useListener(
            this.#presence.bus,
            "presence",
            () => this.#store.env.bus.trigger("RTC:PLAY_MEDIA"),
            { once: true }
        );
        onWillDestroy(() => {
            unsubscribeHotSwap();
            unsubscribeEnded();
            unsubscribeUpdate();
        });
    }
}

services.add(RtcPlugin);
