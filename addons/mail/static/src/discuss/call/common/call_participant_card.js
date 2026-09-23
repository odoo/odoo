// @ts-check
/** @odoo-module native */
import { CallContextMenu } from "@mail/discuss/call/common/call_context_menu";
import { CallDropdown } from "@mail/discuss/call/common/call_dropdown";
import { CallParticipantVideo } from "@mail/discuss/call/common/call_participant_video";
import { CONNECTION_TYPES } from "@mail/discuss/call/common/rtc_service";
import { useHover } from "@mail/utils/common/hooks";
import {
    Component,
    onMounted,
    onWillUnmount,
    useExternalListener,
    useRef,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { isEventHandled } from "@web/core/utils/dom/events";
import { useService } from "@web/core/utils/hooks";

const log = makeLogger("mail.rtc.ui");
/** @type {Set<string>} */
const HIDDEN_CONNECTION_STATES = new Set(["connected", "completed"]);

export class CallParticipantCard extends Component {
    static props = [
        "className",
        "cardData",
        "thread",
        "minimized?",
        "inset?",
        "isSidebarItem?",
        "compact?",
    ];
    static components = { CallParticipantVideo, CallContextMenu, CallDropdown };
    static template = "discuss.CallParticipantCard";

    setup() {
        super.setup();
        this.contextMenuAnchorRef = useRef("contextMenuAnchor");
        this.root = useRef("root");
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rootHover = useHover("root");
        this.resumeStreamHover = useHover("resumeStream");
        this.isMobileOS = isMobileOS();
        this.dragPos = undefined;
        this.isDrag = false;
        this.parentBoundingRect = undefined;
        onMounted(() => {
            if (!this.rtcSession) {
                return;
            }
            this.rtc.updateVideoDownload(this.rtcSession, {
                viewCountIncrement: 1,
            });
        });
        onWillUnmount(() => {
            this._removeDragListeners?.();
            if (!this.rtcSession) {
                return;
            }
            this.rtc.updateVideoDownload(this.rtcSession, {
                viewCountIncrement: -1,
            });
        });
        useExternalListener(browser, "fullscreenchange", this.onFullScreenChange);
    }

    get isContextMenuAvailable() {
        return (
            this.isOfActiveCall &&
            (this.rtcSession.notEq(this.rtc.selfSession) ||
                (this.env.debug &&
                    this.rtc.state.connectionType === CONNECTION_TYPES.SERVER))
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
            this.props.isSidebarItem ||
            this.ui.isSmall ||
            this.props.minimized ||
            this.props.inset,
        );
    }

    get window() {
        return this.env.pipWindow || window;
    }

    get showPausedScreenStream() {
        return Boolean(
            !this.props.isSidebarItem &&
            this.props.cardData.type === "screen" &&
            this.rtcSession?.eq(this.rtc.localSession) &&
            this.rtc.state.screenTrack &&
            !this.rtc.state.screenTrack.enabled,
        );
    }

    resumeScreenStream() {
        if (this.rtc.state.screenTrack) {
            this.rtc.state.screenTrack.enabled = true;
        }
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
        return this.rtcSession
            ? this.rtcSession.channel_member_id
            : this.props.cardData.member;
    }

    get isOfActiveCall() {
        return Boolean(
            this.rtcSession && this.rtcSession.channel?.eq(this.rtc.channel),
        );
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
        if (this.rtc.state.connectionType === CONNECTION_TYPES.SERVER) {
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
            this.rtcSession &&
            this.rtcSession.isActuallyTalking &&
            !this.rtc.selfSession?.is_deaf,
        );
    }

    get hasRaisingHand() {
        const screenStream = this.rtcSession.videoStreams.get("screen");
        return Boolean(
            this.rtcSession.raisingHand &&
            (!screenStream || screenStream !== this.props.cardData.videoStream),
        );
    }

    get isActiveRtcSession() {
        return (
            this.rtcSession &&
            this.rtcSession.eq(this.rtcSession.channel?.activeRtcSession)
        );
    }

    /** @param {MouseEvent} ev */
    async onClick(ev) {
        if (isEventHandled(ev, "CallParticipantCard.clickVolumeAnchor")) {
            return;
        }
        if (this.isDrag) {
            this.isDrag = false;
            return;
        }
        if (this.rtcSession) {
            const channel = this.rtcSession.channel;
            log.logic("onClick card", () => ({
                session: this.rtcSession.id,
                type: this.props.cardData.type,
                wasActive: this.rtcSession.eq(channel.activeRtcSession),
                inset: Boolean(this.props.inset),
            }));
            this.rtcSession.mainVideoStreamType = this.props.cardData.type;
            if (this.rtcSession.eq(channel.activeRtcSession) && !this.props.inset) {
                channel.activeRtcSession = undefined;
                this.rtcSession.mainVideoStreamType = undefined;
            } else {
                channel.activeRtcSession = this.rtcSession;
            }
            return;
        }
        log.logic("cancel call invitation", () => ({
            thread: this.props.thread.localId,
            memberId: this.channelMember.id,
        }));
        await rpc("/mail/rtc/channel/cancel_call_invitation", {
            channel_id: this.props.thread.id,
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
        this._removeDragListeners?.();
        const onMousemove = /** @param {MouseEvent} ev */ (ev) => this.drag(ev);
        const onMouseup = () => {
            const insetEl = this.root.el;
            if (insetEl) {
                const bottomOffset = this.env.inChatWindow
                    ? this.window.innerHeight * 0.05
                    : 0;
                if (
                    parseInt(insetEl.style.left) <
                    insetEl.parentElement.offsetWidth / 2
                ) {
                    insetEl.style.left = "1vh";
                    insetEl.style.right = "";
                } else {
                    insetEl.style.left = "";
                    insetEl.style.right = "1vh";
                }
                if (
                    parseInt(insetEl.style.top) <
                    (insetEl.parentElement.offsetHeight - bottomOffset) / 2
                ) {
                    insetEl.style.top = "1vh";
                    insetEl.style.bottom = "";
                } else {
                    insetEl.style.bottom = this.env.inChatWindow ? "5vh" : "1vh";
                    insetEl.style.top = "unset";
                }
            }
            this.dragPos = undefined;
            this.parentBoundingRect = undefined;
            this._removeDragListeners();
        };
        this._removeDragListeners = () => {
            document.removeEventListener("mouseup", onMouseup);
            document.removeEventListener("mousemove", onMousemove);
            this._removeDragListeners = undefined;
        };
        document.addEventListener("mouseup", onMouseup);
        document.addEventListener("mousemove", onMousemove);
    }

    /** @param {TouchEvent} ev */
    onTouchMove(ev) {
        if (!this.props.inset) {
            return;
        }
        this.drag(ev);
    }

    /** @param {MouseEvent|TouchEvent} ev */
    drag(ev) {
        const insetEl = this.root.el;
        if (!insetEl) {
            this._removeDragListeners?.();
            return;
        }
        this.isDrag = true;
        const parent = insetEl.parentElement;
        const boundingRect =
            this.parentBoundingRect ||
            (this.parentBoundingRect = parent.getBoundingClientRect());
        const bottomOffset = this.env.inChatWindow ? this.window.innerHeight * 0.05 : 0;
        const clientX = Math.max(
            ("touches" in ev ? ev.touches[0].clientX : ev.clientX) - boundingRect.left,
            0,
        );
        const clientY = Math.max(
            ("touches" in ev ? ev.touches[0].clientY : ev.clientY) - boundingRect.top,
            0,
        );
        if (!this.dragPos) {
            this.dragPos = { posX: clientX, posY: clientY };
        }
        const dX = this.dragPos.posX - clientX;
        const dY = this.dragPos.posY - clientY;
        const widthOffset = parent.offsetWidth - insetEl.clientWidth;
        const heightOffset = parent.offsetHeight - insetEl.clientHeight - bottomOffset;
        this.dragPos.posX = Math.min(clientX, widthOffset);
        this.dragPos.posY = Math.min(clientY, heightOffset);
        insetEl.style.left =
            Math.min(Math.max(insetEl.offsetLeft - dX, 0), widthOffset) + "px";
        insetEl.style.top =
            Math.min(Math.max(insetEl.offsetTop - dY, 0), heightOffset) + "px";
    }

    onFullScreenChange() {
        if (this.root.el) {
            this.root.el.style.left = "";
            this.root.el.style.top = "";
        }
    }
}
