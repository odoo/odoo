import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { CallParticipantCard } from "@mail/discuss/call/common/call_participant_card";
import { PttAdBanner } from "@mail/discuss/call/common/ptt_ad_banner";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";

import {
    Component,
    onMounted,
    onWillUnmount,
    toRaw,
    useComponent,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useService } from "@web/core/utils/hooks";
import { throttleForAnimation } from "@web/core/utils/timing";
import { BlurPerformanceWarning } from "./blur_performance_warning";

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
        BlurPerformanceWarning,
        CallActionList,
        CallParticipantCard,
        PttAdBanner,
    };
    static props = ["thread?", "compact?", "isPip?", "hasOverlay?", "class?"];
    static defaultProps = { hasOverlay: true };
    static template = "discuss.Call";

    overlayTimeout;

    setup() {
        super.setup();
        this.grid = useRef("grid");
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
        this.tiles = useArrangeTiles({ refName: "grid", minimized: this.minimized });
        this.store = useService("mail.store");
        onWillUnmount(() => {
            browser.clearTimeout(this.overlayTimeout);
        });
        useHotkey("shift+d", () => this.rtc.toggleDeafen());
        useHotkey("shift+m", () => this.rtc.toggleMicrophone());
    }

    get isFullSize() {
        return this.props.isPip || this.rtc.state.isFullscreen;
    }

    get isActiveCall() {
        return Boolean(this.channel.eq(this.rtc.channel));
    }

    get minimized() {
        if (this.rtc.state.isFullscreen || this.channel.activeRtcSession) {
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

    /** @returns {CardData[]} */
    get visibleMainCards() {
        const activeSession = this.channel.activeRtcSession;
        if (!activeSession) {
            this.state.insetCard = undefined;
            return this.channel.visibleCards;
        }
        const type = activeSession.mainVideoStreamType;
        if (type === "screen" || activeSession.is_screen_sharing_on) {
            this.setInset(activeSession, type === "camera" ? "screen" : "camera");
        } else {
            this.state.insetCard = undefined;
        }
        return [
            {
                key: "session_" + activeSession.id,
                session: activeSession,
                type,
                videoStream: activeSession.getStream(type),
            },
        ];
    }

    /**
     * @param {import("models").RtcSession} session
     * @param {String} [videoType]
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
            (!this.props.compact || this.rtc.state.isFullscreen) &&
                this.isActiveCall &&
                this.rtc.notifications.size
        );
    }

    get hasSidebarButton() {
        return Boolean(
            this.channel.activeRtcSession &&
                this.state.overlay &&
                (!this.props.compact || this.rtc.state.isFullscreen)
        );
    }

    get isControllerFloating() {
        return this.rtc.state.isFullscreen || (this.channel.activeRtcSession && !this.ui.isSmall);
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
}

export function useArrangeTiles({ refName }) {
    const component = useComponent();
    const ref = useRef(refName);
    const TILE_GAP = 4;
    const state = useState({ styles: [] });

    const arrangeTiles = throttleForAnimation(() => {
        if (!ref.el) {
            return;
        }
        const { width, height } = ref.el.getBoundingClientRect();
        const aspectRatio = component.minimized ? 1 : 16 / 9;
        const tileCount = component.channel.visibleCards.length;
        const paddedWidth = width - 2 * TILE_GAP;
        const paddedHeight = height - 2 * TILE_GAP;
        let best = { area: 0, columnCount: 0, tileHeight: 0, tileWidth: 0 };
        for (let columnCount = 1; columnCount <= tileCount; columnCount++) {
            const rowCount = Math.ceil(tileCount / columnCount);
            const potentialTileWidthByHeight =
                ((paddedHeight - (rowCount - 1) * TILE_GAP) / rowCount) * aspectRatio;
            let tileHeight;
            let tileWidth;
            if (
                potentialTileWidthByHeight >
                (paddedWidth - (columnCount - 1) * TILE_GAP) / columnCount
            ) {
                tileWidth = Math.floor((paddedWidth - (columnCount - 1) * TILE_GAP) / columnCount);
                tileHeight = Math.floor(tileWidth / aspectRatio);
            } else {
                tileHeight = Math.floor((paddedHeight - (rowCount - 1) * TILE_GAP) / rowCount);
                tileWidth = Math.floor(tileHeight * aspectRatio);
            }
            const area = tileHeight * tileWidth;
            if (area > best.area) {
                best = { area, columnCount, tileHeight, tileWidth };
            }
        }
        const { columnCount, tileWidth, tileHeight } = best;
        const rowCount = Math.ceil(tileCount / columnCount);
        const layoutWidth = columnCount * tileWidth + (columnCount - 1) * TILE_GAP;
        const layoutHeight = rowCount * tileHeight + (rowCount - 1) * TILE_GAP;
        const offsetX = TILE_GAP + (paddedWidth - layoutWidth) / 2;
        const offsetY = TILE_GAP + (paddedHeight - layoutHeight) / 2;
        const numberOfTilesInLastRow = tileCount % columnCount;
        const lastRowOffset = numberOfTilesInLastRow
            ? ((columnCount - numberOfTilesInLastRow) * (tileWidth + TILE_GAP)) / 2
            : 0;
        state.styles = Array.from({ length: tileCount }, (_, i) => {
            const col = i % columnCount;
            const row = Math.floor(i / columnCount);
            const isLastRow = rowCount - 1 === row;
            const centerOffset = isLastRow ? lastRowOffset : 0;
            const left = offsetX + col * (tileWidth + TILE_GAP) + centerOffset;
            const top = offsetY + row * (tileHeight + TILE_GAP);
            return `position: absolute; left: ${left}px; top: ${top}px; width: ${tileWidth}px; height: ${tileHeight}px; box-sizing: border-box;`;
        });
    });
    let resizeObserver;
    onMounted(() => {
        resizeObserver = new ResizeObserver(() => arrangeTiles());
        resizeObserver.observe(ref.el);
        arrangeTiles();
    });
    onWillUnmount(() => resizeObserver.disconnect());
    useEffect(
        () => {
            arrangeTiles();
        },
        () => [ref.el, component.channel.visibleCards.length, component.minimized]
    );

    return state;
}
