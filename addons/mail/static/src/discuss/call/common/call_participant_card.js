import { CallContextMenu } from "@mail/discuss/call/common/call_context_menu";
import { CallParticipantVideo } from "@mail/discuss/call/common/call_participant_video";
import { CONNECTION_TYPES } from "@mail/discuss/call/common/rtc_service";
import { useHover } from "@mail/utils/common/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";
import { browser } from "@web/core/browser/browser";

import {
    Component,
    onMounted,
    onWillUnmount,
    useRef,
    useState,
    useExternalListener,
} from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

const HIDDEN_CONNECTION_STATES = new Set([undefined, "connected", "completed"]);

export class CallParticipantCard extends Component {
    static props = ["className", "cardData", "thread", "minimized?", "inset?"];
    static components = { CallParticipantVideo };
    static template = "discuss.CallParticipantCard";

    setup() {
        super.setup();
        this.contextMenuAnchorRef = useRef("contextMenuAnchor");
        this.root = useRef("root");
        this.popover = usePopover(CallContextMenu);
        this.rtc = useState(useService("discuss.rtc"));
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.rootHover = useHover("root");
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
        if (!this.rtcSession) {
            return false;
        }
        return (
            !this.rtcSession.eq(this.rtc.selfSession) ||
            (this.env.debug && this.rtc.state.connectionType === CONNECTION_TYPES.SERVER)
        );
    }

    get rtcSession() {
        return this.props.cardData.session;
    }

    get channelMember() {
        return this.rtcSession ? this.rtcSession.channelMember : this.props.cardData.member;
    }

    get isOfActiveCall() {
        return Boolean(this.rtcSession && this.rtcSession.channel?.eq(this.rtc.state.channel));
    }

    get showConnectionState() {
        if (
            !this.rtcSession ||
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

    /**
     * @deprecated use `showConnectionState` instead
     */
    get showServerState() {
        return false;
    }

    get name() {
        return this.channelMember?.persona.name;
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
        return Boolean(this.rtcSession && this.rtcSession.isActuallyTalking);
    }

    get hasRaisingHand() {
        const screenStream = this.rtcSession.videoStreams.get("screen");
        return Boolean(
            this.rtcSession.raisingHand &&
                (!screenStream || screenStream !== this.props.cardData.videoStream)
        );
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
            const channel = this.rtcSession.channel;
            this.rtcSession.mainVideoStreamType = this.props.cardData.type;
            if (this.rtcSession.eq(channel.activeRtcSession) && !this.props.inset) {
                channel.activeRtcSession = undefined;
                this.rtcSession.mainVideoStreamType = undefined;
            } else {
                const activeRtcSession = channel.activeRtcSession;
                const currentMainVideoType = this.rtcSession.mainVideoStreamType;
                channel.activeRtcSession = this.rtcSession;
                if (this.props.inset && activeRtcSession) {
                    this.props.inset(activeRtcSession, currentMainVideoType);
                }
            }
            return;
        }
        await rpc("/mail/rtc/channel/cancel_call_invitation", {
            channel_id: this.props.thread.id,
            member_ids: [this.channelMember.id],
        });
    }

    async onClickReplay() {
        this.env.bus.trigger("RTC-SERVICE:PLAY_MEDIA");
    }

    /**
     * @param {Event} ev
     */
    onContextMenu(ev) {
        ev.preventDefault();
        markEventHandled(ev, "CallParticipantCard.clickVolumeAnchor");
        if (this.popover.isOpen) {
            this.popover.close();
            return;
        }
        if (!this.contextMenuAnchorRef?.el) {
            return;
        }
        this.popover.open(this.contextMenuAnchorRef.el, {
            rtcSession: this.rtcSession,
        });
    }

    onMouseDown() {
        if (!this.props.inset) {
            return;
        }
        const onMousemove = (ev) => this.drag(ev);
        const onMouseup = () => {
            const insetEl = this.root.el;
            const bottomOffset = this.env.inChatWindow ? window.innerHeight * 0.05 : 0; // 5vh in pixels
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
        const insetEl = this.root.el;
        const parent = insetEl.parentNode;
        const boundingRect =
            this.parentBoundingRect || (this.parentBoundingRect = parent.getBoundingClientRect());
        const bottomOffset = this.env.inChatWindow ? window.innerHeight * 0.05 : 0; // 5vh in pixels
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
        this.root.el.style = "left:''; top:''";
    }
}
