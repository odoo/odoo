import { CallContextMenu } from "@mail/discuss/call/common/call_context_menu";
import { CallParticipantVideo } from "@mail/discuss/call/common/call_participant_video";
import { CONNECTION_TYPES } from "@mail/discuss/call/common/rtc_service";
import { TalkingAudioBars } from "@mail/discuss/call/common/talking_audio_bars";
import { useHover } from "@mail/utils/common/hooks";
import { extractAccentColor } from "@mail/utils/common/misc";
import { isEventHandled } from "@web/core/utils/misc";
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";

import {
    Component,
    onMounted,
    onWillUnmount,
    signal,
    types,
    useEffect,
    useListener,
    usePlugin,
    useProps,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

const HIDDEN_CONNECTION_STATES = new Set(["connected", "completed"]);

export class CallParticipantCard extends Component {
    static components = { CallParticipantVideo, CallContextMenu, Dropdown, TalkingAudioBars };
    static template = "discuss.CallParticipantCard";
    /** @type {import("models").Rtc} */
    rtc;
    root = signal.ref();

    debugMode = usePlugin(DebugModePlugin);

    setup() {
        super.setup();
        this.cardBgColor = signal();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.props = useProps({
            cardData: types.object({
                key: types.string(),
                member: types.instanceOf(this.store["discuss.channel.member"]).optional(),
                session: types.instanceOf(this.store["discuss.channel.rtc.session"]).optional(),
                type: types.selection(["camera", "screen"]).optional(),
                videoStream: types
                    .or([types.instanceOf(MediaStream), types.selection([false])])
                    .optional(),
            }),
            channel: types.instanceOf(this.store["discuss.channel"]),
            className: types.string(),
            compact: types.boolean().optional(),
            inset: types
                .function([
                    types.instanceOf(this.store["discuss.channel.rtc.session"]),
                    types.selection(["camera", "screen"]),
                ])
                .optional(),
            isSidebarItem: types.boolean().optional(),
            minimized: types.boolean().optional(),
        });
        this.ui = useService("ui");
        this.rootHover = useHover(this.root);
        this.contextMenuDropdownState = useDropdownState();
        this.isMobileOS = isMobileOS();
        this.dragPos = undefined;
        this.isDrag = false;
        this.parentBoundingRect = undefined;
        onMounted(async () => {
            const avatarUrl = this.channelMember?.avatarUrl;
            if (avatarUrl) {
                const { r, g, b } = await extractAccentColor(avatarUrl, 0.53);
                this.cardBgColor.set(`rgb(${r}, ${g}, ${b})`);
            }
            if (!this.rtcSession) {
                return;
            }
            this.rtc.updateVideoDownload(this.rtcSession, {
                viewCountIncrement: 1,
            });
        });
        onWillUnmount(() => {
            if (!this.rtcSession) {
                return;
            }
            this.rtc.updateVideoDownload(this.rtcSession, {
                viewCountIncrement: -1,
            });
        });
        useListener(browser, "fullscreenchange", () => this.onFullScreenChange());
        // Drive the talking glow on rAF, reading volume in render would re-render too often.
        useEffect(() => {
            if (!this.isTalking) {
                this.root()?.style.setProperty("--discuss-CallParticipantCard-talkingVolume", 0);
                return;
            }
            let frame;
            const update = () => {
                const volume = this.rtcSession?.talkingVolume ?? 0;
                const logScaledVolume = volume > 0 ? Math.log10(1 + volume * 9) : 0;
                this.root()?.style.setProperty(
                    "--discuss-CallParticipantCard-talkingVolume",
                    logScaledVolume
                );
                frame = browser.requestAnimationFrame(update);
            };
            // Defer the read so this effect tracks isTalking, not volume.
            frame = browser.requestAnimationFrame(update);
            return () => browser.cancelAnimationFrame(frame);
        });
    }

    get cardBgStyle() {
        return this.cardBgColor()
            ? `--discuss-CallParticipantCard-bgColor: ${this.cardBgColor()};`
            : "";
    }

    get isActiveCall() {
        return Boolean(this.props.channel.eq(this.rtc.channel));
    }

    get isContextMenuAvailable() {
        return (
            this.isOfActiveCall &&
            (this.rtcSession.notEq(this.rtc.selfSession) ||
                (this.debugMode.isActive() && this.rtc.connectionType === CONNECTION_TYPES.SERVER))
        );
    }

    get isRemoteVideo() {
        if (!this.rtcSession) {
            return false;
        }
        return (
            this.rtc.isRemote &&
            (this.rtcSession.is_screen_sharing_on || this.rtcSession.is_camera_on)
        );
    }

    get isSmall() {
        return Boolean(
            this.props.isSidebarItem || this.ui.isSmall || this.props.minimized || this.props.inset
        );
    }

    get window() {
        return this.env.pipWindow || window;
    }

    get showLiveLabel() {
        if (this.props.isSidebarItem) {
            return false;
        }
        if (this.props.cardData.type === "screen") {
            if (this.props.inset) {
                return true;
            } else {
                return (
                    !this.rtcSession.eq(this.rtcSession.channel.activeRtcSession) &&
                    !this.props.minimized
                );
            }
        }
        return false;
    }

    get showRemoteWarning() {
        return !this.props.minimized && !this.props.inset && this.isRemoteVideo;
    }

    get rtcSession() {
        return this.props.cardData.session;
    }

    get channelMember() {
        return this.rtcSession ? this.rtcSession.channel_member_id : this.props.cardData.member;
    }

    get isOfActiveCall() {
        return Boolean(this.rtcSession && this.rtcSession.channel?.eq(this.rtc.channel));
    }

    get showConnectionState() {
        if (
            !this.rtcSession ||
            !this.rtc.isHost ||
            !this.isOfActiveCall ||
            HIDDEN_CONNECTION_STATES.has(this.rtcSession.connectionState)
        ) {
            return false;
        }
        if (this.rtc.connectionType === CONNECTION_TYPES.SERVER) {
            return this.rtcSession.eq(this.rtc?.selfSession);
        } else {
            return this.rtcSession.notEq(this.rtc?.selfSession);
        }
    }

    get name() {
        return this.channelMember?.name;
    }

    get hasMediaError() {
        return (
            this.isOfActiveCall &&
            Boolean(this.rtcSession?.videoError || this.rtcSession?.audioError)
        );
    }

    get hasVideo() {
        return Boolean(this.props.cardData.videoStream);
    }

    get isTalking() {
        return Boolean(
            this.rtcSession && this.rtcSession.isActuallyTalking && !this.rtc.selfSession?.is_deaf
        );
    }

    get hasRaisingHand() {
        const screenStream = this.rtcSession.videoStreams.get("screen");
        return Boolean(
            this.rtcSession.raisingHand &&
                (!screenStream || screenStream !== this.props.cardData.videoStream)
        );
    }

    get isActiveRtcSession() {
        return this.rtcSession && this.rtcSession.eq(this.rtcSession.channel?.activeRtcSession);
    }

    get isPinned() {
        return this.rtcSession?.eq(this.rtcSession.channel?.pinnedRtcSession);
    }

    get isLocallyMuted() {
        return this.rtcSession?.isLocallyMuted;
    }

    async onClick(ev) {
        if (isEventHandled(ev, "CallParticipantCard.clickVolumeAnchor")) {
            return;
        }
        if (this.isDrag) {
            this.isDrag = false;
            return;
        }
        if (this.rtcSession) {
            if (!this.props.inset) {
                return;
            }
            const channel = this.rtcSession.channel;
            // The inset only swaps which stream of the spotlighted participant is shown (e.g.
            // screen ⇄ camera); it must not promote a different participant into the spotlight.
            if (this.rtcSession.notEq(channel.activeRtcSession)) {
                return;
            }
            this.rtcSession.mainVideoStreamType = this.props.cardData.type;
            const activeRtcSession = channel.activeRtcSession;
            const currentMainVideoType = this.rtcSession.mainVideoStreamType;
            channel.activeRtcSession = this.rtcSession;
            if (activeRtcSession) {
                this.props.inset(activeRtcSession, currentMainVideoType);
            }
            return;
        }
        await rpc("/mail/rtc/channel/cancel_call_invitation", {
            channel_id: this.props.channel.id,
            member_ids: [this.channelMember.id],
        });
    }

    async onClickReplay() {
        this.env.bus.trigger("RTC-SERVICE:PLAY_MEDIA");
    }

    onMouseDown() {
        if (!this.props.inset) {
            return;
        }
        const onMousemove = (ev) => this.drag(ev);
        const onMouseup = () => {
            const insetEl = this.root();
            const bottomOffset = this.env.inChatWindow ? this.window.innerHeight * 0.05 : 0; // 5vh in pixels
            if (parseInt(insetEl.style.left) < insetEl.parentNode.offsetWidth / 2) {
                insetEl.style.left = "1vh";
                insetEl.style.right = "";
            } else {
                insetEl.style.left = "";
                insetEl.style.right = "1vh";
            }
            if (
                parseInt(insetEl.style.top) <
                (insetEl.parentNode.offsetHeight - bottomOffset) / 2
            ) {
                insetEl.style.top = "1vh";
                insetEl.style.bottom = "";
            } else {
                insetEl.style.bottom = this.env.inChatWindow ? "5vh" : "1vh";
                insetEl.style.top = "unset";
            }
            this.dragPos = undefined;
            this.parentBoundingRect = undefined;
            document.removeEventListener("mouseup", onMouseup);
            document.removeEventListener("mousemove", onMousemove);
        };
        document.addEventListener("mouseup", onMouseup);
        document.addEventListener("mousemove", onMousemove);
    }

    onTouchMove(ev) {
        if (!this.props.inset) {
            return;
        }
        this.drag(ev);
    }

    drag(ev) {
        this.isDrag = true;
        const insetEl = this.root();
        const parent = insetEl.parentNode;
        const boundingRect =
            this.parentBoundingRect || (this.parentBoundingRect = parent.getBoundingClientRect());
        const bottomOffset = this.env.inChatWindow ? this.window.innerHeight * 0.05 : 0; // 5vh in pixels
        const clientX = Math.max((ev.clientX ?? ev.touches[0].clientX) - boundingRect.left, 0);
        const clientY = Math.max((ev.clientY ?? ev.touches[0].clientY) - boundingRect.top, 0);
        if (!this.dragPos) {
            this.dragPos = { posX: clientX, posY: clientY };
        }
        const dX = this.dragPos.posX - clientX;
        const dY = this.dragPos.posY - clientY;
        const widthOffset = parent.offsetWidth - insetEl.clientWidth;
        const heightOffset = parent.offsetHeight - insetEl.clientHeight - bottomOffset;
        this.dragPos.posX = Math.min(clientX, widthOffset);
        this.dragPos.posY = Math.min(clientY, heightOffset);
        insetEl.style.left = Math.min(Math.max(insetEl.offsetLeft - dX, 0), widthOffset) + "px";
        insetEl.style.top = Math.min(Math.max(insetEl.offsetTop - dY, 0), heightOffset) + "px";
    }

    onFullScreenChange() {
        if (!this.root()) {
            return;
        }
        this.root().style.left = "";
        this.root().style.top = "";
    }
}
