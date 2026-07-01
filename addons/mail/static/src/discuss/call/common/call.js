import { useLayoutEffect, useRef, useSubEnv } from "@web/owl2/utils";
import { ActionList } from "@mail/core/common/action_list";
import { BlurPerformanceWarning } from "@mail/discuss/call/common/blur_performance_warning";
import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { CallPresentationBar } from "@mail/discuss/call/common/call_presentation_bar";
import { CallParticipantCard } from "@mail/discuss/call/common/call_participant_card";
import { CallRecordingIndicator } from "@mail/discuss/call/common/call_recording_indicator";
import { PttAdBanner } from "@mail/discuss/call/common/ptt_ad_banner";

import { Component, onMounted, onPatched, onWillUnmount, props, proxy, t } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { ACTION_TAGS } from "@mail/core/common/action";

/** @typedef {import("@mail/discuss/call/common/call_layout").CallLayout} CallLayout */

/**
 * Smallest width (px) a tile keeps in the tiled grid before "Prioritize tiles with video" starts
 * dropping camera-off participants. Together with the meeting view size it defines the column/row
 * cap (how many tiles fit without shrinking) past which video-less tiles are hidden.
 */
const MIN_TILED_TILE_WIDTH = 320;

/**
 * @typedef CardData
 * @property {string} key
 * @property {import("models").RtcSession} session
 * @property {MediaStream} videoStream
 * @property {import("models").ChannelMember} [member]
 */

export class Call extends Component {
    static components = {
        ActionList,
        BlurPerformanceWarning,
        CallActionList,
        CallPresentationBar,
        CallParticipantCard,
        CallRecordingIndicator,
        PttAdBanner,
    };
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
        this.state = proxy({
            sidebar: false,
            tileWidth: 0,
            tileHeight: 0,
            columnCount: 0,
            maxTileCount: Infinity,
            overlay: false,
            /** @type {CardData|undefined} */
            insetCard: undefined,
        });
        this.store = useService("mail.store");
        this.props = props({
            channel: t.instanceOf(this.store["discuss.channel"].Class).optional(),
            compact: t.boolean().optional(),
            hasOverlay: t.boolean().optional(true),
            isPip: t.boolean().optional(),
        });
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
        useLayoutEffect(
            () => this.applyCallLayout(),
            () => [
                this.resolvedCallLayout,
                this.rtc.isFullscreen,
                this.channel?.eq(this.rtc.channel),
                this.channel?.rtc_session_ids.length,
                this.channel?.rtc_session_ids.some((s) => s.is_screen_sharing_on),
            ]
        );
        useHotkey("shift+d", () => this.rtc.toggleDeafen());
        useHotkey("shift+m", ({ target }) => this.rtc.toggleMicrophone({ rootRef: () => target }));
        useHotkey("shift+h", () => this.rtc.raiseHand(!this.rtc.selfSession.raisingHand));
        useSubEnv({ inDiscussCallView: true });
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

    /**
     * @returns {CallLayout} the concrete grid layout to render (never {@link CALL_GRID_LAYOUT.AUTO} nor
     *  {@link CALL_GRID_LAYOUT.DISCUSS}), resolving the "auto" setting from the screenshare state and
     *  participant count.
     */
    get resolvedCallLayout() {
        const layout = this.store.settings.callLayout;
        if (!this.channel || layout !== CALL_GRID_LAYOUT.AUTO) {
            return layout;
        }
        if (this.isAnyonePresenting) {
            // While someone shares their screen, everyone on the auto layout switches to the sidebar
            // so the shared screen takes the main window and participants line up beside it.
            return CALL_GRID_LAYOUT.SIDEBAR;
        }
        return this.channel.rtc_session_ids.length >= 3
            ? CALL_GRID_LAYOUT.TILED
            : CALL_GRID_LAYOUT.SPOTLIGHT;
    }

    /**
     * @returns {import("models").RtcSession|undefined} session to focus in spotlight/sidebar layouts:
     *  the presenter, else the last speaker, else the first remote video, else any remote session.
     */
    get spotlightTarget() {
        const sessions = this.channel.rtc_session_ids;
        return (
            this.channel.pinnedRtcSession ||
            sessions.find((s) => s.is_screen_sharing_on) ||
            this.channel.focusStack.at(-1) ||
            sessions.find((s) => s.notEq(this.rtc.selfSession) && s.hasVideo) ||
            sessions.find((s) => s.notEq(this.rtc.selfSession)) ||
            sessions[0]
        );
    }

    /**
     * Drive {@link DiscussChannel.activeRtcSession} and the sidebar from the resolved layout. Only
     * runs in the fullscreen meeting view, where the auto-focus heuristics are disabled.
     *
     * @returns {void}
     */
    applyCallLayout() {
        if (!this.rtc.isFullscreen || !this.isActiveCall) {
            return;
        }
        if (this.resolvedCallLayout === CALL_GRID_LAYOUT.TILED) {
            this.channel.activeRtcSession = undefined;
            this.state.sidebar = false;
            return;
        }
        if (!this.channel.activeRtcSession) {
            const target = this.spotlightTarget;
            if (target) {
                this.channel.activeRtcSession = target;
                target.mainVideoStreamType = target.is_screen_sharing_on ? "screen" : "camera";
            }
        }
        this.state.sidebar = this.resolvedCallLayout === CALL_GRID_LAYOUT.SIDEBAR;
    }

    get isFullSize() {
        return this.props.isPip || this.rtc.isFullscreen;
    }

    get isActiveCall() {
        return Boolean(this.channel.eq(this.rtc.channel));
    }

    get minimized() {
        if (this.rtc.isFullscreen || !this.channel || this.channel.activeRtcSession) {
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
     * Cards rendered in the tiled grid. With "Prioritize tiles with video" on, video-less tiles are
     * dropped once showing every tile would overflow the column/row cap ({@link state.maxTileCount}),
     * so participants sharing video keep a comfortable size. Only applies to the fullscreen tiled
     * layout; every other layout/context shows all cards.
     *
     * @returns {CardData[]}
     */
    get tiledCards() {
        const cards = this.channel.visibleCards;
        if (
            !this.rtc.isFullscreen ||
            this.store.settings.callLayout !== CALL_GRID_LAYOUT.TILED ||
            !this.store.settings.showOnlyVideo ||
            cards.length <= this.state.maxTileCount
        ) {
            return cards;
        }
        const videoCards = cards.filter((card) => card.session?.hasVideo);
        return videoCards.length ? videoCards : cards;
    }

    /** @returns {CardData[]} */
    get visibleMainCards() {
        const activeSession = this.channel.activeRtcSession;
        if (!activeSession) {
            this.state.insetCard = undefined;
            return this.tiledCards;
        }
        const type = activeSession.mainVideoStreamType;
        if (type === "screen" || activeSession.is_screen_sharing_on) {
            this.setInset(activeSession, type === "camera" ? "screen" : "camera");
        } else if (this.hasSelfInset(activeSession)) {
            this.setInset(this.rtc.selfSession, "camera");
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
        if (this.state.insetCard?.key === key) {
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

    /**
     * @param {import("models").RtcSession} activeSession the spotlighted session.
     * @returns {boolean} whether self should be shown as a bottom-right inset (two-person spotlight).
     */
    hasSelfInset(activeSession) {
        return Boolean(
            this.rtc.isFullscreen &&
                this.resolvedCallLayout === CALL_GRID_LAYOUT.SPOTLIGHT &&
                this.channel.rtc_session_ids.length === 2 &&
                this.rtc.selfSession &&
                activeSession.notEq(this.rtc.selfSession)
        );
    }

    get hasCallNotifications() {
        return Boolean(
            (!this.props.compact || this.rtc.isFullscreen) &&
                this.isActiveCall &&
                this.rtc.notifications.size
        );
    }

    get isControllerFloating() {
        return this.rtc.isFullscreen || (this.channel.activeRtcSession && !this.ui.isSmall);
    }

    onMouseleaveMain(ev) {
        if (
            ev.relatedTarget &&
            (ev.relatedTarget.closest(".o-dropdown--menu") ||
                ev.relatedTarget.closest(".o_popover"))
        ) {
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
        // Column/row cap: how many tiles fit at MIN_TILED_TILE_WIDTH without shrinking further. Used
        // by "Prioritize tiles with video" to decide when video-less tiles must be dropped.
        const capColumns = Math.max(1, Math.floor(width / MIN_TILED_TILE_WIDTH));
        const capRows = Math.max(1, Math.floor(height / (MIN_TILED_TILE_WIDTH / aspectRatio)));
        this.state.maxTileCount = capColumns * capRows;
        // "Auto" resolved to tiled caps the grid at 3 columns (full height); an explicit "Tiled"
        // choice keeps maximizing the tile area across as many columns as fit.
        const autoTiled =
            this.rtc.isFullscreen &&
            this.store.settings.callLayout === CALL_GRID_LAYOUT.AUTO &&
            this.resolvedCallLayout === CALL_GRID_LAYOUT.TILED;
        const maxColumnCount = autoTiled ? Math.min(tileCount, 3) : tileCount;
        let optimal = {
            area: 0,
            columnCount: 0,
            tileHeight: 0,
            tileWidth: 0,
        };
        for (let columnCount = 1; columnCount <= maxColumnCount; columnCount++) {
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
