/* @odoo-module */

import { CallContextMenu } from "@mail/discuss/call/common/call_context_menu";
import { CallParticipantVideo } from "@mail/discuss/call/common/call_participant_video";
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

const HIDDEN_CONNECTION_STATES = new Set(["connected", "completed"]);

export class CallParticipantCard extends Component {
    static props = ["className", "cardData", "thread", "minimized?", "inset?"];
    static components = { CallParticipantVideo };
    static template = "discuss.CallParticipantCard";

    setup() {
        this.contextMenuAnchorRef = useRef("contextMenuAnchor");
        this.root = useRef("root");
        this.popover = usePopover(CallContextMenu);
        this.rpc = useService("rpc");
        this.rtc = useState(useService("discuss.rtc"));
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.rootHover = useHover("root");
        this.threadService = useService("mail.thread");
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
        return !this.rtcSession?.eq(this.rtc.state.selfSession);
    }

    get rtcSession() {
        return this.props.cardData.session;
    }

    get channelMember() {
        return this.rtcSession ? this.rtcSession.channelMember : this.props.cardData.member;
    }

    get isOfActiveCall() {
        return Boolean(this.rtcSession && this.rtcSession.channelId === this.rtc.state.channel?.id);
    }

    get showConnectionState() {
        return Boolean(
            this.isOfActiveCall &&
                !this.rtcSession.channelMember?.persona.eq(this.store.self) &&
                !HIDDEN_CONNECTION_STATES.has(this.rtcSession.connectionState)
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
        return Boolean(this.rtcSession && this.rtcSession.isTalking && !this.rtcSession.isMute);
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
            if (this.rtcSession.eq(channel.activeRtcSession) && !this.props.inset) {
                channel.activeRtcSession = undefined;
                this.rtcSession.mainVideoStream = undefined;
            } else {
                const activeRtcSession = channel.activeRtcSession;
                const mainVideoStream = this.rtcSession.mainVideoStream;
                channel.activeRtcSession = this.rtcSession;
                this.rtcSession.mainVideoStream = this.props.cardData.videoStream;
                if (this.props.inset && activeRtcSession) {
                    const videoType =
                        activeRtcSession.videoStreams.get("camera") === mainVideoStream
                            ? "camera"
                            : "screen";
                    this.props.inset(activeRtcSession, videoType);
                }
            }
            return;
        }
        const channelData = await this.rpc("/mail/rtc/channel/cancel_call_invitation", {
            channel_id: this.props.thread.id,
            member_ids: [this.channelMember.id],
        });
        this.props.thread.update({ invitedMembers: channelData.invitedMembers });
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
