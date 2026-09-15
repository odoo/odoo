import { useLayoutEffect, useSubEnv } from "@web/owl2/utils";
import { BlurPerformanceWarning } from "@mail/discuss/call/common/blur_performance_warning";
import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { CallPresentationBar } from "@mail/discuss/call/common/call_presentation_bar";
import { CallParticipantCard } from "@mail/discuss/call/common/call_participant_card";
import { CallRecordingIndicator } from "@mail/discuss/call/common/call_recording_indicator";
import { PttAdBanner } from "@mail/discuss/call/common/ptt_ad_banner";
import { GeometryRenderer } from "@mail/discuss/call/common/stage/geometry_renderer";
import {
    computeLayout,
    SURFACE_CORNER,
    SURFACE_PLACEMENT,
} from "@mail/discuss/call/common/stage/layout_engine";
import { resolveStageProfile } from "@mail/discuss/call/common/stage/layout_profile";
import { SurfaceManager } from "@mail/discuss/call/common/stage/surface_manager";

import {
    Component,
    computed,
    onMounted,
    onPatched,
    onWillUnmount,
    proxy,
    signal,
    t,
    useProps,
} from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { clamp } from "@web/core/utils/numbers";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";

/** @typedef {import("@mail/discuss/call/common/call_layout").CallLayout} CallLayout */
/** @typedef {import("@mail/discuss/call/common/stage/layout_profile").StageProfile} StageProfile */
/** @typedef {import("@mail/discuss/call/common/stage/surface_manager").Surface} Surface */
/** @typedef {import("@mail/discuss/call/common/stage/surface_manager").SurfaceDescriptor} SurfaceDescriptor */

const MORE_CARDS_KEY = "__more__";

/**
 * The layout request this render would make: two renders sharing a signature need only one layout
 * pass. Excludes the measured box — the ResizeObserver is what notices a resize.
 *
 * @param {Surface[]} surfaces
 * @param {boolean} hasMoreCards
 * @param {StageProfile} profile
 * @param {string} [insetCorner]
 */
function signatureOf(surfaces, hasMoreCards, profile, insetCorner) {
    const keys = surfaces.map((surface) => `${surface.key}:${surface.data.placement}`);
    if (hasMoreCards) {
        keys.push(MORE_CARDS_KEY);
    }
    return [
        keys.join("|"),
        profile.autoHeight,
        profile.aspectRatio,
        profile.capColumnsAtThree,
        profile.fillMainWidth,
        profile.hasSidebar,
        profile.insetBottomMargin,
        insetCorner,
    ].join("/");
}

/**
 * One media of one participant, or one pending invitation: what a surface renders.
 *
 * @typedef CardData
 * @property {string} key
 * @property {import("models").RtcSession} [session] unset on an invitation card
 * @property {"camera"|"screen"} [type] unset on an invitation card
 * @property {MediaStream} [videoStream] unset while the media has no track yet
 * @property {import("models").ChannelMember} [member] set on an invitation card only
 */

export class Call extends Component {
    static components = {
        BlurPerformanceWarning,
        CallActionList,
        CallPresentationBar,
        CallParticipantCard,
        CallRecordingIndicator,
        PttAdBanner,
    };
    static template = "discuss.Call";

    overlayTimeout;
    gridRef = signal.ref();
    rootRef = signal.ref();

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.rtc = useService("discuss.rtc");
        this.isMobileOs = isMobileOS();
        this.ui = useService("ui");
        this.state = proxy({
            cropsTiles: false,
            insetCorner: undefined,
            maxTileCount: Infinity,
            overlay: false,
        });
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]).optional(),
            compact: t.boolean().optional(),
            hasOverlay: t.boolean().optional(true),
            isPip: t.boolean().optional(),
        });
        this.surfaceManager = new SurfaceManager();
        this.geometryRenderer = new GeometryRenderer();
        /** Memoized: three readers per patch, and every read re-sorts and re-reconciles. */
        this._stageContent = computed(() => {
            const { maxCards } = this.profile;
            const desired = this.desiredCardData;
            const hasMoreCards = desired.length > maxCards;
            const surfaces = this.surfaceManager.reconcile(
                hasMoreCards ? desired.slice(0, maxCards) : desired
            );
            return { surfaces, hasMoreCards };
        });
        this._layoutScheduled = false;
        this._appliedSignature = undefined;
        onMounted(() => {
            this.resizeObserver = new ResizeObserver(() => this.requestLayout());
            const gridEl = this.gridRef();
            if (gridEl) {
                this.resizeObserver.observe(gridEl);
            }
            this.arrangeTiles();
        });
        onPatched(() => {
            if (this.channel && this.renderedSignature !== this._appliedSignature) {
                this.requestLayout();
            }
        });
        onWillUnmount(() => {
            this.resizeObserver.disconnect();
            this.geometryRenderer.dispose();
            this._layoutScheduled = false;
            browser.clearTimeout(this.overlayTimeout);
        });
        useLayoutEffect(
            () => {
                this.syncFocusedSession();
                this.requestLayout();
            },
            () => [
                this.profile.layout,
                this.rtc.isFullscreen,
                this.channel?.eq(this.rtc.channel),
                this.channel?.rtc_session_ids.length,
                this.channel?.rtc_session_ids.some((s) => s.is_screen_sharing_on),
                this.focusedSessions.map((session) => session.id).join(),
            ]
        );
        useHotkey("shift+d", () => this.rtc.toggleDeafen());
        useHotkey("shift+m", ({ target }) => this.rtc.toggleMicrophone({ rootRef: () => target }));
        useHotkey("shift+h", () => this.rtc.raiseHand(!this.rtc.selfSession.raisingHand));
        useSubEnv({
            inDiscussCallView: true,
            dragInsetBy: (key, dX, dY) => this.dragInsetBy(key, dX, dY),
            dropInset: (key) => this.dropInset(key),
        });
    }

    get isAnyonePresenting() {
        return Boolean(this.channel?.rtc_session_ids.some((s) => s.is_screen_sharing_on));
    }

    /** Every layout decision of this stage, in one place. */
    get profile() {
        return resolveStageProfile({
            hasFocus: Boolean(this.channel?.activeRtcSession),
            hasVideo: Boolean(this.channel?.videoCount),
            inChatWindow: Boolean(this.props.compact),
            isActiveCall: this.isActiveCall,
            isFullscreen: this.rtc.isFullscreen,
            isPinned: Boolean(this.channel?.pinnedRtcSession),
            isPip: Boolean(this.props.isPip),
            isPresenting: this.isAnyonePresenting,
            isSmallScreen: this.ui.isSmall,
            isTouch: this.isMobileOs,
            participantCount: this.channel?.rtc_session_ids.length ?? 0,
            prefersVideoTiles: this.store.settings.showOnlyVideo,
            userLayout: this.store.settings.callLayout,
        });
    }

    /** The session the spotlight and sidebar layouts fall back on. */
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

    get hasSidebar() {
        return this.profile.hasSidebar;
    }

    /**
     * The sessions sharing the main window, or none in a grid of equal tiles. More than one only
     * in the spotlight, where {@link DiscussChannel.activeSpeakers} split it.
     */
    get focusedSessions() {
        const { runsMeetingLayouts, layout, maxMainSpeakers } = this.profile;
        if (!runsMeetingLayouts) {
            return this.channel?.activeRtcSession ? [this.channel.activeRtcSession] : [];
        }
        if (layout === CALL_GRID_LAYOUT.TILED) {
            return [];
        }
        if (!this.channel.pinnedRtcSession && !this.isAnyonePresenting) {
            const speakers = this.channel.activeSpeakers.slice(0, maxMainSpeakers);
            if (speakers.length) {
                return speakers;
            }
        }
        // Keep a pin or presentation focused, or retain the last speaker when the call is quiet.
        const focused = this.channel.activeRtcSession || this.spotlightTarget;
        return focused ? [focused] : [];
    }

    syncFocusedSession() {
        if (!this.profile.runsMeetingLayouts) {
            return;
        }
        // The rest of the call UI reads one session, so the first on stage stands for the set.
        const focused = this.focusedSessions[0];
        const active = this.channel.activeRtcSession;
        if (active?.eq(focused) || (!active && !focused)) {
            return;
        }
        this.channel.activeRtcSession = focused;
        if (focused) {
            focused.mainVideoStreamType = focused.is_screen_sharing_on ? "screen" : "camera";
        }
    }

    get isFullSize() {
        return this.profile.isFullSize;
    }

    get isActiveCall() {
        return Boolean(this.channel?.eq(this.rtc.channel));
    }

    get minimized() {
        return this.profile.minimized;
    }

    get channel() {
        return this.props.channel || this.rtc.channel;
    }

    /**
     * Cards rendered in the tiled grid. Dropping the video-less ones once the grid overflows keeps
     * the participants sharing video at a comfortable size.
     */
    get tiledCards() {
        let cards = this.channel?.visibleCards ?? [];
        if (this.profile.dropsVideolessTiles && cards.length > this.state.maxTileCount) {
            const videoCards = cards.filter((card) => card.session?.hasVideo);
            cards = videoCards.length ? videoCards : cards;
        }
        // Only once the cap bites: reordering a grid showing everyone just shuffles it on speech.
        return cards.length > this.profile.maxCards ? this.stageOrder(cards) : cards;
    }

    /**
     * What the stage puts on screen, reconciled so a media keeps its DOM while it stays desired.
     * The cards the cap left out get no surface, hence no video download.
     */
    get stageContent() {
        return this._stageContent();
    }

    /** In the sidebar wherever there is one: a main slot would halve the presenter's window. */
    get moreCardsPlacement() {
        return this.hasSidebar ? SURFACE_PLACEMENT.SIDEBAR : SURFACE_PLACEMENT.MAIN;
    }

    get renderedSignature() {
        const { surfaces, hasMoreCards } = this.stageContent;
        return signatureOf(surfaces, hasMoreCards, this.profile, this.state.insetCorner);
    }

    /** The {@link SurfaceDescriptor} the layout wants, before the card cap. */
    get desiredCardData() {
        const focused = this.focusedSessions;
        if (!focused.length) {
            return this.tiledCards.map((card) => ({ ...card, placement: SURFACE_PLACEMENT.MAIN }));
        }
        const mainCards = focused.map((session) => this.mainCard(session));
        const mainKeys = new Set(mainCards.map((card) => card.key));
        const result = mainCards.map((card) => ({ ...card, placement: SURFACE_PLACEMENT.MAIN }));
        if (this.hasSidebar) {
            for (const card of this.sidebarCards(mainKeys)) {
                result.push({ ...card, placement: SURFACE_PLACEMENT.SIDEBAR });
            }
            return result;
        }
        if (focused.length > 1) {
            // A split stage has no room for an inset, and no single session it would belong to.
            return result;
        }
        const insetCard = this.insetCard(focused[0]);
        // Both cards can resolve to the same media, which would give two surfaces the same key.
        if (insetCard && !mainKeys.has(insetCard.key)) {
            result.push({ ...insetCard, placement: SURFACE_PLACEMENT.INSET });
        }
        return result;
    }

    /**
     * @param {import("models").RtcSession} session
     */
    mainCard(session) {
        if (session.mainVideoStreamType === "screen" && session.is_screen_sharing_on) {
            return this.cardOf(session, "screen");
        }
        return this.cardOf(session, "camera");
    }

    /**
     * Synthesizes a card when `visibleCards` has none, e.g. for a stale "screen" main type.
     *
     * @param {import("models").RtcSession} session
     * @param {"camera"|"screen"} type
     */
    cardOf(session, type) {
        const card = this.channel.visibleCards.find(
            (card) => card.session?.eq(session) && card.type === type
        );
        return (
            card || {
                key: `session_${type === "screen" ? "secondary" : "main"}_${session.id}`,
                session,
                type,
                videoStream: session.getStream(type),
            }
        );
    }

    /**
     * The sidebar column, in {@link stageOrder}: its top is who is presenting or talking.
     *
     * @param {Set<string>} mainKeys keys of the cards on the main window
     */
    sidebarCards(mainKeys) {
        return this.stageOrder(this.channel.visibleCards.filter((card) => !mainKeys.has(card.key)));
    }

    /**
     * Reorder cards by what the stage must not hide. Presenters lead because the card cap decides
     * what gets downloaded: one left beyond it never gets the track that would bring it back.
     *
     * @param {CardData[]} cards
     */
    stageOrder(cards) {
        const presenterCards = [];
        const speakerCards = [];
        const selfCards = [];
        const otherCards = [];
        for (const card of cards) {
            if (card.session?.is_screen_sharing_on) {
                presenterCards.push(card);
            } else if (card.session?.in(this.channel.activeSpeakers)) {
                speakerCards.push(card);
            } else if (card.session?.eq(this.rtc.selfSession)) {
                selfCards.push(card);
            } else {
                otherCards.push(card);
            }
        }
        speakerCards.sort(
            (a, b) =>
                this.channel.activeSpeakers.indexOf(a.session) -
                this.channel.activeSpeakers.indexOf(b.session)
        );
        return [...presenterCards, ...speakerCards, ...selfCards, ...otherCards];
    }

    insetCard(session) {
        if (this.channel.videoCount === 0) {
            return undefined;
        }
        const type = session.mainVideoStreamType;
        if (type === "screen" || session.is_screen_sharing_on) {
            return this.cardOf(session, type === "camera" ? "screen" : "camera");
        }
        if (this.hasSelfInset(session)) {
            return this.cardOf(this.rtc.selfSession, "camera");
        }
        return undefined;
    }

    /**
     * @param {import("models").RtcSession} session
     */
    hasSelfInset(session) {
        return Boolean(
            this.profile.allowsSelfInset &&
                this.rtc.selfSession &&
                session.notEq(this.rtc.selfSession)
        );
    }

    /**
     * Move the inset by a pointer delta, clamped to the stage. Unanimated, so it lands under the
     * pointer on this frame.
     *
     * @param {string} key surface key of the inset
     * @param {number} dX horizontal pointer movement (px)
     * @param {number} dY vertical pointer movement (px)
     */
    dragInsetBy(key, dX, dY) {
        const gridEl = this.gridRef();
        const rect = this.geometryRenderer.currentRect(key);
        const el = gridEl?.querySelector(`[data-surface="${CSS.escape(key)}"]`);
        if (!rect || !el) {
            return;
        }
        this.geometryRenderer.setTarget(
            key,
            {
                ...rect,
                x: clamp(rect.x + dX, 0, gridEl.clientWidth - rect.width),
                y: clamp(rect.y + dY, 0, gridEl.clientHeight - rect.height),
            },
            el,
            { animate: false }
        );
    }

    /**
     * Snap the inset to the closest stage corner. A corner and not the dropped pixels, which a
     * resize or a layout change would put off-screen.
     *
     * @param {string} key surface key of the inset
     */
    dropInset(key) {
        const gridEl = this.gridRef();
        const rect = this.geometryRenderer.currentRect(key);
        if (!gridEl || !rect) {
            return;
        }
        const isLeft = rect.x + rect.width / 2 < gridEl.clientWidth / 2;
        if (rect.y + rect.height / 2 < gridEl.clientHeight / 2) {
            this.state.insetCorner = isLeft ? SURFACE_CORNER.TOP_LEFT : SURFACE_CORNER.TOP_RIGHT;
        } else {
            this.state.insetCorner = isLeft
                ? SURFACE_CORNER.BOTTOM_LEFT
                : SURFACE_CORNER.BOTTOM_RIGHT;
        }
        // The corner is not part of the render, so nothing else would pick the change up.
        this.requestLayout();
    }

    get hasCallNotifications() {
        return Boolean(
            (!this.props.compact || this.rtc.isFullscreen) &&
                this.isActiveCall &&
                this.rtc.notifications.size
        );
    }

    get bottomNotifications() {
        return this.hasCallNotifications
            ? [...this.rtc.notifications.values()].filter((notif) => notif.position !== "top")
            : [];
    }

    get topNotifications() {
        return this.hasCallNotifications
            ? [...this.rtc.notifications.values()].filter((notif) => notif.position === "top")
            : [];
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

    /**
     * Every card is out of the flow: the layout engine writes size and translate as inline styles.
     *
     * @param {Surface} surface
     */
    surfaceClassName(surface) {
        switch (surface.data.placement) {
            case SURFACE_PLACEMENT.SIDEBAR:
                return "o-discuss-Call-sidebarCard position-absolute p-1";
            case SURFACE_PLACEMENT.INSET:
                return "o-discuss-Call-mainCardStyle position-absolute o-bg-black";
            default:
                return "o-discuss-Call-mainCardStyle position-absolute";
        }
    }

    /**
     * The single layout trigger, coalescing every event that can move a tile. Merged over the
     * current task and not the next frame: OWL patches inside a frame, and the browser would paint
     * the new cards before they have geometry.
     */
    requestLayout() {
        if (this._layoutScheduled) {
            return;
        }
        this._layoutScheduled = true;
        Promise.resolve().then(() => {
            if (!this._layoutScheduled) {
                return;
            }
            this._layoutScheduled = false;
            this.arrangeTiles();
        });
    }

    /**
     * Place the rendered cards. Runs outside the OWL render loop, so a resize only moves surfaces
     * and never re-renders the component tree.
     */
    arrangeTiles() {
        const gridEl = this.gridRef();
        if (!gridEl) {
            return;
        }
        const { surfaces, hasMoreCards } = this.stageContent;
        const signature = signatureOf(surfaces, hasMoreCards, this.profile, this.state.insetCorner);
        if (this.profile.autoHeight) {
            // Clear it first, or the stage only ever grows. Guarded, as clearing a height that was
            // never set still costs a reflow on the read below, on every ResizeObserver tick.
            gridEl.style.height = "";
        }
        const { width, height } = gridEl.getBoundingClientRect();
        if (!this.profile.autoHeight && height <= 0) {
            return;
        }
        const layout = this.computeStageLayout({ width, height, surfaces, hasMoreCards });
        // Read back into the render; the surfaces are unchanged, so it asks for no further layout.
        this.state.maxTileCount = layout.maxTileCount;
        this.state.cropsTiles = layout.cropsTiles;
        // Recording a partial pass would leave the surfaces OWL had not rendered yet unplaced
        // forever: the patch bringing their elements in would find a signature it already knows.
        if (this.applyGeometry(gridEl, layout, surfaces, hasMoreCards)) {
            this._appliedSignature = signature;
        }
    }

    /**
     * @param {{ width: number, height: number, surfaces: Surface[], hasMoreCards: boolean }} stage
     */
    computeStageLayout({ width, height, surfaces, hasMoreCards }) {
        const { autoHeight, aspectRatio, capColumnsAtThree, fillMainWidth, insetBottomMargin } =
            this.profile;
        return computeLayout({
            width,
            height,
            autoHeight,
            aspectRatio,
            surfaces: [
                ...surfaces.map(({ key, data }) => ({ key, placement: data.placement })),
                ...(hasMoreCards
                    ? [{ key: MORE_CARDS_KEY, placement: this.moreCardsPlacement }]
                    : []),
            ],
            capColumnsAtThree,
            fillMainWidth,
            insetCorner: this.state.insetCorner,
            insetBottomMargin,
        });
    }

    /**
     * Hand each card its rect, releasing the surfaces that got none so they keep no stale
     * transform. False as soon as one surface has no element yet.
     *
     * @param {HTMLElement} gridEl
     * @param {Object} layout as returned by {@link computeLayout}
     * @param {Surface[]} surfaces
     * @param {boolean} hasMoreCards
     */
    applyGeometry(gridEl, layout, surfaces, hasMoreCards) {
        if (layout.stageHeight !== undefined) {
            gridEl.style.height = `${layout.stageHeight}px`;
        }
        const elementsByKey = new Map();
        for (const el of gridEl.querySelectorAll("[data-surface]")) {
            elementsByKey.set(el.dataset.surface, el);
        }
        const entries = surfaces.map(({ key }) => ({ key, el: elementsByKey.get(key) }));
        const activeKeys = new Set(surfaces.map((surface) => surface.key));
        if (hasMoreCards) {
            entries.push({ key: MORE_CARDS_KEY, el: elementsByKey.get(MORE_CARDS_KEY) });
            activeKeys.add(MORE_CARDS_KEY);
        } else {
            this.geometryRenderer.remove(MORE_CARDS_KEY);
        }
        let placedAll = true;
        for (const { key, el } of entries) {
            if (!el) {
                placedAll = false;
                continue;
            }
            const rect = layout.rects[key];
            if (rect) {
                this.geometryRenderer.setTarget(key, rect, el);
            } else {
                this.geometryRenderer.remove(key, el);
            }
        }
        this.geometryRenderer.prune(activeKeys);
        return placedAll;
    }
}
