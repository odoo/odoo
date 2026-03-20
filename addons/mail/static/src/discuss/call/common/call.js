import { useRef, useState } from "@web/owl2/utils";
import { BlurPerformanceWarning } from "@mail/discuss/call/common/blur_performance_warning";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { CallPresentationBar } from "@mail/discuss/call/common/call_presentation_bar";
import { CallParticipantCard } from "@mail/discuss/call/common/call_participant_card";
import { PttAdBanner } from "@mail/discuss/call/common/ptt_ad_banner";

import { Component, onMounted, onPatched, onWillUnmount, toRaw } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { ActionList } from "@mail/core/common/action_list";
import { ACTION_TAGS } from "@mail/core/common/action";
import { inDiscussCallViewProps, useInDiscussCallView } from "@mail/utils/common/hooks";

/**
 * @typedef CardData
 * @property {string} key
 * @property {import("models").RtcSession} session
 * @property {MediaStream} videoStream
 * @property {import("models").ChannelMember} [member]
 */

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @property {boolean} [compact]
 * @extends {Component<Props, Env>}
 */
export class Call extends Component {
    static components = {
        ActionList,
        BlurPerformanceWarning,
        CallActionList,
        CallPresentationBar,
        CallParticipantCard,
        PttAdBanner,
    };
    static props = ["channel?", "compact?", "hasOverlay?", ...inDiscussCallViewProps];
    static defaultProps = { hasOverlay: true };
    static template = "discuss.Call";

    overlayTimeout;

    setup() {
        super.setup();
        this.grid = useRef("grid");
        this.root = useRef("root");
        this.notification = useService("notification");
        this.rtc = useService("discuss.rtc");
        this.isMobileOs = isMobileOS();
        this.ui = useService("ui");
        this.state = useState({
            sidebar: false,
            tileWidth: 0,
            tileHeight: 0,
            columnCount: 0,
            overlay: false,
            /** @type {CardData|undefined} */
            insetCard: undefined,
        });
        this.store = useService("mail.store");
        this.callActions = useCallActions({ channel: () => this.channel });
        onMounted(() => {
            this.resizeObserver = new ResizeObserver(() => this.arrangeTiles());
            this.resizeObserver.observe(this.grid.el);
            this.arrangeTiles();
        });
        onPatched(() => this.arrangeTiles());
        onWillUnmount(() => {
            this.resizeObserver.disconnect();
            browser.clearTimeout(this.overlayTimeout);
        });
        useHotkey("shift+d", () => this.rtc.toggleDeafen());
        useHotkey("shift+m", () => this.rtc.toggleMicrophone());
        useHotkey("shift+h", () => this.rtc.raiseHand(!this.rtc.selfSession.raisingHand));
        useInDiscussCallView();
    }

    get layoutActions() {
        if (!this.isActiveCall) {
            return [];
        }
        return this.callActions.actions.filter((action) =>
            action.tags.includes(ACTION_TAGS.CALL_LAYOUT)
        );
    }

    get isAnyonePresenting() {
        return this.channel.rtc_session_ids.some((s) => s.is_screen_sharing_on);
    }

    get isFullSize() {
        return this.props.isPip || this.rtc.isFullscreen;
    }

    get isActiveCall() {
        return Boolean(this.channel.eq(this.rtc.channel));
    }

    get minimized() {
        if (this.rtc.isFullscreen || !this.channel || this.mainRtcSessions.length) {
            return false;
        }
        if (!this.isActiveCall || this.channel.videoCount === 0 || this.props.compact) {
            return true;
        }
        return false;
    }

    get channel() {
        return this.props.channel || this.rtc.channel;
    }

    /**
     * @param {import("models").RtcSession} session
     * @returns {import("@mail/discuss/call/common/rtc_service").VideoType}
     */
    getSessionMainType(session) {
        let type = session.mainVideoStreamType;
        if (type === "screen" && !session.is_screen_sharing_on) {
            type = "camera";
        }
        if (type === "camera" && !session.is_camera_on) {
            type = "screen";
        }
        if (type !== "camera" && type !== "screen") {
            type = session.is_screen_sharing_on ? "screen" : "camera";
        }
        return type;
    }

    /**
     * @param {import("models").RtcSession} session
     * @returns {CardData}
     */
    makeSessionCard(session) {
        const type = this.getSessionMainType(session);
        return {
            key: "session_" + session.id,
            session,
            type,
            videoStream: session.getStream(type),
        };
    }

    get mainRtcSessions() {
        const mainSessions = [];
        const activeSession = this.channel.activeRtcSession;
        if (activeSession?.in(this.channel.rtc_session_ids)) {
            mainSessions.push(activeSession);
        }
        for (const session of this.channel.pinnedRtcSessions) {
            if (!mainSessions.some((currentSession) => currentSession.eq(session))) {
                mainSessions.push(session);
            }
        }
        return mainSessions;
    }

    get hasMainRtcSessions() {
        return Boolean(this.mainRtcSessions.length);
    }

    /** @returns {CardData[]} */
    get visibleMainCards() {
        const [activeSession] = this.mainRtcSessions;
        if (!activeSession) {
            this.state.insetCard = undefined;
            return this.channel.visibleCards;
        }
        if (this.mainRtcSessions.length > 1) {
            this.state.insetCard = undefined;
            return this.mainRtcSessions.map((session) => this.makeSessionCard(session));
        }
        const type = this.getSessionMainType(activeSession);
        if (type === "screen" || activeSession.is_screen_sharing_on) {
            this.setInset(activeSession, type === "camera" ? "screen" : "camera");
        } else {
            this.state.insetCard = undefined;
        }
        return [this.makeSessionCard(activeSession)];
    }

    get sidebarCards() {
        const selfCards = [];
        const otherVisibleCards = [];
        const cards = this.channel.visibleCards;
        for (let i = 0; i < cards.length; i++) {
            if (cards[i].session?.eq(this.rtc.selfSession)) {
                selfCards.push(cards[i]);
            } else {
                otherVisibleCards.push(cards[i]);
            }
        }
        return selfCards.concat(otherVisibleCards);
    }

    /**
     * @param {import("models").RtcSession} session
     * @param {import("@mail/discuss/call/common/rtc_service").VideoType} [videoType]
     */
    setInset(session, videoType) {
        const key = "session_" + session.id;
        if (toRaw(this.state).insetCard?.key === key) {
            this.state.insetCard.type = videoType;
            this.state.insetCard.videoStream = session.getStream(videoType);
        } else {
            this.state.insetCard = {
                key,
                session,
                type: videoType,
                videoStream: session.getStream(videoType),
            };
        }
    }

    get hasCallNotifications() {
        return Boolean(
            (!this.props.compact || this.rtc.isFullscreen) &&
                this.isActiveCall &&
                this.rtc.notifications.size
        );
    }

    get hasSidebarButton() {
        return Boolean(
            this.hasMainRtcSessions &&
                this.state.overlay &&
                (!this.props.compact || this.rtc.isFullscreen)
        );
    }

    get isControllerFloating() {
        return this.rtc.isFullscreen || (this.hasMainRtcSessions && !this.ui.isSmall);
    }

    onMouseleaveMain(ev) {
        if (ev.relatedTarget && ev.relatedTarget.closest(".o-dropdown--menu")) {
            // the overlay should not be hidden when the cursor leaves to enter the controller dropdown
            return;
        }
        this.state.overlay = false;
    }

    onMousemoveMain(ev) {
        if (isEventHandled(ev, "CallMain.MousemoveOverlay")) {
            return;
        }
        this.showOverlay();
    }

    onMousemoveOverlay(ev) {
        markEventHandled(ev, "CallMain.MousemoveOverlay");
        this.state.overlay = true;
        browser.clearTimeout(this.overlayTimeout);
    }

    showOverlay() {
        this.state.overlay = true;
        browser.clearTimeout(this.overlayTimeout);
        this.overlayTimeout = browser.setTimeout(() => {
            this.state.overlay = false;
        }, 3000);
    }

    arrangeTiles() {
        if (!this.grid.el) {
            return;
        }
        this.grid.el.style.setProperty("--width", "0");
        this.grid.el.style.setProperty("--height", "0");
        const { width, height } = this.grid.el.getBoundingClientRect();
        const aspectRatio = this.minimized && this.channel.videoCount === 0 ? 1 : 16 / 9;
        const tileCount = this.grid.el.children.length;
        let optimal = {
            area: 0,
            columnCount: 0,
            tileHeight: 0,
            tileWidth: 0,
        };
        for (let columnCount = 1; columnCount <= tileCount; columnCount++) {
            const rowCount = Math.ceil(tileCount / columnCount);
            const potentialHeight = width / (columnCount * aspectRatio);
            const potentialWidth = height / rowCount;
            let tileHeight;
            let tileWidth;
            if (potentialHeight > potentialWidth) {
                tileHeight = Math.floor(potentialWidth);
                tileWidth = Math.floor(tileHeight * aspectRatio);
            } else {
                tileWidth = Math.floor(width / columnCount);
                tileHeight = Math.floor(tileWidth / aspectRatio);
            }
            const area = tileHeight * tileWidth;
            if (area <= optimal.area) {
                continue;
            }
            optimal = {
                area,
                columnCount,
                tileHeight,
                tileWidth,
            };
        }
        Object.assign(this.state, {
            tileWidth: optimal.tileWidth,
            tileHeight: optimal.tileHeight,
            columnCount: optimal.columnCount,
        });
        this.grid.el.style.setProperty("--width", `${this.state.tileWidth}px`);
        this.grid.el.style.setProperty("--height", `${this.state.tileHeight}px`);
    }
}
