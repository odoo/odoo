// @ts-check
/** @odoo-module native */
import { ACTION_TAGS } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import { BlurPerformanceWarning } from "@mail/discuss/call/common/blur_performance_warning";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { CallParticipantCard } from "@mail/discuss/call/common/call_participant_card";
import { PttAdBanner } from "@mail/discuss/call/common/ptt_ad_banner";
import { inDiscussCallViewProps, useInDiscussCallView } from "@mail/utils/common/hooks";
import {
    Component,
    onMounted,
    onPatched,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { isEventHandled, markEventHandled } from "@web/core/utils/dom/events";
import { useService } from "@web/core/utils/hooks";

const log = makeLogger("mail.rtc.ui");
/**
 * @typedef CardData
 * @property {string} key
 * @property {import("models").RtcSession} session
 * @property {MediaStream | false | undefined} videoStream
 * @property {"camera" | "screen"} [type]
 * @property {import("models").ChannelMember} [member]
 */

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @property {boolean} [compact]
 * @property {boolean} [isPip]
 * @extends {Component<Props, import("@web/env").OdooEnv>}
 */
export class Call extends Component {
    static components = {
        ActionList,
        BlurPerformanceWarning,
        CallActionList,
        CallParticipantCard,
        PttAdBanner,
    };
    static props = ["thread?", "compact?", "hasOverlay?", ...inDiscussCallViewProps];
    static defaultProps = { hasOverlay: true };
    static template = "discuss.Call";

    /** @type {number|undefined} */
    overlayTimeout;

    setup() {
        useLifecycleLog(log);
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
        });
        this.store = useService("mail.store");
        this.callActions = useCallActions({ thread: () => this.channel });
        onMounted(() => {
            this.resizeObserver = new ResizeObserver(() =>
                this.arrangeTiles({ remeasure: true }),
            );
            this.resizeObserver.observe(this.grid.el);
            this.arrangeTiles({ remeasure: true });
        });
        onPatched(() => this.arrangeTiles());
        onWillUnmount(() => {
            this.resizeObserver.disconnect();
            browser.clearTimeout(this.overlayTimeout);
        });
        useHotkey("shift+d", () => this.rtc.toggleDeafen());
        useHotkey("shift+m", () => this.rtc.toggleMicrophone());
        useInDiscussCallView();
    }

    get layoutActions() {
        if (!this.isActiveCall) {
            return [];
        }
        return this.callActions.actions.filter((action) =>
            action.tags.includes(ACTION_TAGS.CALL_LAYOUT),
        );
    }

    get isFullSize() {
        return this.props.isPip || this.rtc.state.isFullscreen;
    }

    get isActiveCall() {
        return Boolean(this.channel.eq(this.rtc.channel));
    }

    get minimized() {
        if (
            this.rtc.state.isFullscreen ||
            !this.channel ||
            this.channel.activeRtcSession
        ) {
            return false;
        }
        if (!this.isActiveCall || this.channel.videoCount === 0 || this.props.compact) {
            return true;
        }
        return false;
    }

    get channel() {
        return this.props.thread || this.rtc.channel;
    }

    /** @returns {{ inset: CardData | undefined, main: CardData[] }} */
    get cards() {
        const activeSession = this.channel.activeRtcSession;
        if (!activeSession) {
            return { inset: undefined, main: this.channel.visibleCards };
        }
        const type = activeSession.mainVideoStreamType;
        const inset =
            type === "screen" || activeSession.is_screen_sharing_on
                ? this.makeCard(activeSession, type === "camera" ? "screen" : "camera")
                : undefined;
        return { inset, main: [this.makeCard(activeSession, type)] };
    }

    get insetCard() {
        return this.cards.inset;
    }

    get visibleMainCards() {
        return this.cards.main;
    }

    /**
     * @param {import("models").RtcSession} session
     * @param {"camera" | "screen"} [videoType]
     * @returns {CardData}
     */
    makeCard(session, videoType) {
        return {
            key: "session_" + session.id,
            session,
            type: videoType,
            videoStream: session.getStream(videoType),
        };
    }

    get hasCallNotifications() {
        return Boolean(
            (!this.props.compact || this.rtc.state.isFullscreen) &&
            this.isActiveCall &&
            this.rtc.notifications.size,
        );
    }

    get hasSidebarButton() {
        return Boolean(
            this.channel.activeRtcSession &&
            this.state.overlay &&
            (!this.props.compact || this.rtc.state.isFullscreen),
        );
    }

    get isControllerFloating() {
        return (
            this.rtc.state.isFullscreen ||
            (this.channel.activeRtcSession && !this.ui.isSmall)
        );
    }

    /** @param {MouseEvent} ev */
    onMouseleaveMain(ev) {
        if (
            ev.relatedTarget &&
            /** @type {Element} */ (ev.relatedTarget).closest(".o-dropdown--menu")
        ) {
            return;
        }
        this.state.overlay = false;
    }

    /** @param {MouseEvent} ev */
    onMousemoveMain(ev) {
        if (isEventHandled(ev, "CallMain.MousemoveOverlay")) {
            return;
        }
        this.showOverlay();
    }

    /** @param {MouseEvent} ev */
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

    /**
     * @param {Object} [options]
     * @param {boolean} [options.remeasure=false]
     */
    arrangeTiles({ remeasure = false } = {}) {
        if (!this.grid.el) {
            return;
        }
        const aspectRatio = this.minimized ? 1 : 16 / 9;
        const tileCount = this.grid.el.children.length;
        const cheapKey = `${aspectRatio},${tileCount}`;
        if (!remeasure && cheapKey === this._lastCheapKey) {
            return;
        }
        this._lastCheapKey = cheapKey;
        const { width, height } = this.grid.el.getBoundingClientRect();
        const inputsKey = `${width},${height},${aspectRatio},${tileCount}`;
        if (inputsKey === this._lastTileInputsKey) {
            return;
        }
        this._lastTileInputsKey = inputsKey;
        const endArrange = log.perf("arrangeTiles");
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
        endArrange({ tileCount, columnCount: optimal.columnCount, remeasure });
    }
}
