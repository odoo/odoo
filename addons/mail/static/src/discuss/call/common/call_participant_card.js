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
    static props = ["className", "cardData", "thread", "minimized?", "inset?", "isSidebarItem?"];
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
        this.state = useState({ drag: false, dragPos: undefined });
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

    get isRemoteVideo() {
        if (!this.rtcSession) {
            return false;
        }
        return (
            this.rtc.isRemote &&
            (this.rtcSession.is_screen_sharing_on || this.rtcSession.is_camera_on)
        );
    }

    get showLiveLabel() {
        if (this.props.isSidebarItem) {
            return false;
        }
        return (
            this.isRemoteVideo ||
            (this.rtcSession?.is_screen_sharing_on && !this.props.minimized && !this.isOfActiveCall)
        );
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

    get showServerState() {
        return Boolean(
            this.rtcSession.channel_member_id?.persona.eq(this.store.self) &&
                this.rtc.state.serverState &&
                this.rtc.state.serverState !== "connected"
        );
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
        if (this.state.drag) {
            this.state.drag = false;
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
            if (parseInt(insetEl.style.left) < insetEl.parentNode.offsetWidth / 2) {
                insetEl.style.left = "1vh";
                insetEl.style.right = "";
            } else {
                insetEl.style.left = "";
                insetEl.style.right = "1vh";
            }
            if (parseInt(insetEl.style.top) < insetEl.parentNode.offsetHeight / 2) {
                insetEl.style.top = "1vh";
                insetEl.style.bottom = "";
            } else {
                insetEl.style.bottom = "1vh";
                insetEl.style.top = "";
            }
            document.removeEventListener("mouseup", onMouseup);
            document.removeEventListener("mousemove", onMousemove);
        };
        document.addEventListener("mouseup", onMouseup);
        document.addEventListener("mousemove", onMousemove);
    }

    drag(ev) {
        this.state.drag = true;
        const insetEl = this.root.el;
        const parent = insetEl.parentNode;
        const clientX = ev.clientX ?? ev.touches[0].clientX;
        const clientY = ev.clientY ?? ev.touches[0].clientY;
        if (!this.state.dragPos) {
            this.state.dragPos = { posX: clientX, posY: clientY };
        }
        const dX = this.state.dragPos.posX - clientX;
        const dY = this.state.dragPos.posY - clientY;
        this.state.dragPos.posX = Math.min(
            Math.max(clientX, parent.offsetLeft),
            parent.offsetLeft + parent.offsetWidth - insetEl.clientWidth
        );
        this.state.dragPos.posY = Math.min(
            Math.max(clientY, parent.offsetTop),
            parent.offsetTop + parent.offsetHeight - insetEl.clientHeight
        );
        insetEl.style.left =
            Math.min(
                Math.max(insetEl.offsetLeft - dX, 0),
                parent.offsetWidth - insetEl.clientWidth
            ) + "px";
        insetEl.style.top =
            Math.min(
                Math.max(insetEl.offsetTop - dY, 0),
                parent.offsetHeight - insetEl.clientHeight
            ) + "px";
    }

    onFullScreenChange() {
        this.root.el.style = "left:''; top:''";
    }
}
