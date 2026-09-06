import { useLayoutEffect, useSubEnv } from "@web/owl2/utils";
import { BlurPerformanceWarning } from "@mail/discuss/call/common/blur_performance_warning";
import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { CallPresentationBar } from "@mail/discuss/call/common/call_presentation_bar";
import { CallParticipantCard } from "@mail/discuss/call/common/call_participant_card";
import {
    computeLayout,
    SURFACE_CORNER,
    SURFACE_PLACEMENT,
} from "@mail/discuss/call/common/meeting_layout_engine";
import { resolveStageProfile } from "@mail/discuss/call/common/meeting_layout_profile";
import { GeometryRenderer } from "@mail/discuss/call/common/meeting_geometry_renderer";
import { MeetingSurfaceManager } from "@mail/discuss/call/common/meeting_surface_manager";
import { PttAdBanner } from "@mail/discuss/call/common/ptt_ad_banner";

import {
    Component,
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
import { useCallActions } from "@mail/discuss/call/common/call_actions";

/** @typedef {import("@mail/discuss/call/common/call_layout").CallLayout} CallLayout */

/** Key of the "more participants" indicator rect, when rendered. */
const MORE_CARDS_KEY = "__more__";

/**
 * The layout request the stage would make right now, as an order-sensitive string. Two renders
 * sharing a signature ask the layout engine for the exact same thing, so the second one needs no
 * computation.
 *
 * It covers the profile and not only the surfaces, because the surface list is not enough to tell
 * two requests apart: switching the layout menu from "auto" to "tiled" while the grid is already
 * tiled changes nothing but `capColumnsAtThree`, and a signature blind to it would leave the grid
 * capped at three columns for as long as nothing else moved. The measured stage box is deliberately
 * left out — the ResizeObserver, not this, is what notices a resize.
 *
 * @param {import("@mail/discuss/call/common/meeting_surface_manager").MeetingSurface[]} surfaces
 * @param {boolean} hasMoreCards
 * @param {import("@mail/discuss/call/common/meeting_layout_profile").StageProfile} profile
 * @param {string} [insetCorner]
 * @returns {string}
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
        profile.insetBottomMargin,
        insetCorner,
    ].join("/");
}

/**
 * @typedef CardData
 * @property {string} key
 * @property {import("models").RtcSession} session
 * @property {MediaStream} videoStream
 * @property {import("models").ChannelMember} [member]
 */

export class Call extends Component {
    static components = {
        BlurPerformanceWarning,
        CallActionList,
        CallPresentationBar,
        CallParticipantCard,
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
        this.callActions = useCallActions({ channel: () => this.channel });
        this.surfaceManager = new MeetingSurfaceManager();
        this.geometryRenderer = new GeometryRenderer();
        this._layoutScheduled = false;
        /** {@link renderedSignature} of the last layout that was actually applied. */
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

    /**
     * Every layout decision this context makes, in one place. Reading the services is the only
     * thing this component is uniquely able to do; the decisions themselves are a pure function of
     * what it reads, so they live in {@link resolveStageProfile} where they can be tested and
     * extended without a DOM.
     *
     * @returns {import("@mail/discuss/call/common/meeting_layout_profile").StageProfile}
     */
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

    get hasSidebar() {
        return this.profile.hasSidebar;
    }

    /**
     * The sessions sharing the main window, in render order, or an empty list in a grid of equal
     * tiles. Several of them only in the spotlight, where the recent speakers
     * ({@link DiscussChannel.activeSpeakers}) split the stage rather than fight over it; every
     * other layout keeps the single focused session it always had.
     *
     * @returns {import("models").RtcSession[]}
     */
    get focusedSessions() {
        const { runsMeetingLayouts, layout, maxMainSpeakers } = this.profile;
        if (!runsMeetingLayouts) {
            return this.channel?.activeRtcSession ? [this.channel.activeRtcSession] : [];
        }
        if (layout === CALL_GRID_LAYOUT.TILED) {
            return [];
        }
        const speakers = this.channel.activeSpeakers.slice(0, maxMainSpeakers);
        if (speakers.length > 1) {
            return speakers;
        }
        // Nobody (or a single person) has spoken recently: fall back to the plain focus heuristic,
        // so a silent call still shows the presenter or the last speaker rather than nothing.
        const focused = this.channel.activeRtcSession || this.spotlightTarget;
        return focused ? [focused] : [];
    }

    syncFocusedSession() {
        if (!this.profile.runsMeetingLayouts) {
            return;
        }
        // The rest of the call UI (card highlight, controller placement, video quality) reads a
        // single session, so the first one on stage stands for the whole set.
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
     * Cards rendered in the tiled grid. With "Prioritize tiles with video" on, video-less tiles are
     * dropped once showing every tile would overflow the column/row cap ({@link state.maxTileCount}),
     * so participants sharing video keep a comfortable size. Only applies to the fullscreen tiled
     * layout; every other layout/context shows all cards.
     *
     * Where {@link StageProfile.maxCards} does cut the grid short, the speakers are moved to the
     * front so the cap never hides the person talking.
     *
     * @returns {CardData[]}
     */
    get tiledCards() {
        let cards = this.channel?.visibleCards ?? [];
        if (this.profile.dropsVideolessTiles && cards.length > this.state.maxTileCount) {
            const videoCards = cards.filter((card) => card.session?.hasVideo);
            cards = videoCards.length ? videoCards : cards;
        }
        // Only once the cap actually bites: reordering a grid that shows everyone anyway would
        // shuffle every tile each time someone speaks, for no gain.
        return cards.length > this.profile.maxCards ? this.speakersFirst(cards) : cards;
    }

    /**
     * The surfaces to render, in render order, reconciled through {@link MeetingSurfaceManager} so
     * a participant media keeps the same DOM (and video element) as long as it stays desired.
     * `reconcile` is idempotent for equal descriptors, so the template and {@link arrangeTiles} may
     * both read this in the same frame.
     *
     * @returns {{surfaces: MeetingSurface[], hasMoreCards: boolean}} `hasMoreCards` tells whether
     *  the chat window collapsed the remaining cards into the "more participants" indicator; those
     *  get no surface at all, so their videos are not downloaded.
     */
    get renderedSurfaces() {
        const { maxCards } = this.profile;
        const desired = this.desiredCardData;
        const hasMoreCards = desired.length > maxCards;
        const surfaces = this.surfaceManager.reconcile(
            hasMoreCards ? desired.slice(0, maxCards) : desired
        );
        return { surfaces, hasMoreCards };
    }

    /** @returns {string} the {@link signatureOf} what the stage currently renders. */
    get renderedSignature() {
        const { surfaces, hasMoreCards } = this.renderedSurfaces;
        return signatureOf(surfaces, hasMoreCards, this.profile, this.state.insetCorner);
    }

    /**
     * @returns {Array<CardData & { placement: string }>} the desired surfaces for the current
     *  layout, before the chat-window cap, each carrying the {@link SURFACE_PLACEMENT} the layout
     *  wants for it. Whatever is left out is dropped by the manager, releasing its video element.
     */
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
            // A split stage has no room for a picture-in-picture over it, and no single session it
            // would belong to.
            return result;
        }
        const insetCard = this.insetCard(focused[0]);
        // A session presenting before its main video type is known resolves both cards to the same
        // media; rendering it twice would give two surfaces the same key.
        if (insetCard && !mainKeys.has(insetCard.key)) {
            result.push({ ...insetCard, placement: SURFACE_PLACEMENT.INSET });
        }
        return result;
    }

    /**
     * The card shown in the main area when a session is focused: its "main" stream (screen if
     * {@link RtcSession.mainVideoStreamType} is `"screen"` and the session is presenting, camera
     * otherwise). Falls back to the camera card (avatar) when the main type has no stream.
     *
     * @param {import("models").RtcSession} session
     * @returns {CardData}
     */
    mainCard(session) {
        if (session.mainVideoStreamType === "screen" && session.is_screen_sharing_on) {
            return this.cardOf(session, "screen");
        }
        return this.cardOf(session, "camera");
    }

    /**
     * The card of a session in the `visibleCards` order, or a synthesized card when the media is
     * not currently in the list (e.g. a stale "screen" main type).
     *
     * @param {import("models").RtcSession} session
     * @param {"camera"|"screen"} type
     * @returns {CardData}
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
     * The sidebar column: every visible card except the ones already filling the main window.
     * Recent speakers come first — the sidebar layout keeps its single main window (usually a
     * shared screen), so the top of the column is where you look to see who is talking — then
     * self, then everyone else.
     *
     * @param {Set<string>} mainKeys keys of the cards on the main window
     * @returns {CardData[]}
     */
    sidebarCards(mainKeys) {
        return this.speakersFirst(
            this.channel.visibleCards.filter((card) => !mainKeys.has(card.key))
        );
    }

    /**
     * Reorder cards so the recent speakers ({@link DiscussChannel.activeSpeakers}) come first, in
     * the order they started speaking, then self, then everyone else. Whoever is talking ends up
     * where the layout is most likely to keep them: the top of the sidebar column, or inside the
     * card cap of a small screen.
     *
     * @param {CardData[]} cards
     * @returns {CardData[]}
     */
    speakersFirst(cards) {
        const speakerCards = [];
        const selfCards = [];
        const otherCards = [];
        for (const card of cards) {
            if (card.session?.in(this.channel.activeSpeakers)) {
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
        return [...speakerCards, ...selfCards, ...otherCards];
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
     * @param {import("models").RtcSession} session the spotlighted session.
     * @returns {boolean} whether self should be shown as an inset over that session.
     */
    hasSelfInset(session) {
        return Boolean(
            this.profile.allowsSelfInset &&
                this.rtc.selfSession &&
                session.notEq(this.rtc.selfSession)
        );
    }

    /**
     * Move the inset by a pointer delta, clamped to the stage. The only geometry the engine does
     * not decide: it goes straight to the renderer as a non-animated move, because it has to be
     * under the pointer on this very frame.
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
     * Snap the inset to the stage corner it was let go closest to. A corner, never the dragged
     * pixels: it stays meaningful across a resize or a layout change, where absolute coordinates
     * would put the inset off-screen.
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
     * @param {MeetingSurface} surface
     * @returns {string} the CSS class set of the card rendering this surface.
     */
    surfaceClassName(surface) {
        switch (surface.data.placement) {
            case SURFACE_PLACEMENT.SIDEBAR:
                return "o-discuss-Call-sidebarCard p-1";
            case SURFACE_PLACEMENT.INSET:
                return "o-discuss-Call-mainCardStyle o-bg-black";
            default:
                return "o-discuss-Call-mainCardStyle";
        }
    }

    /**
     * The single layout trigger: every event that can move a tile (resize, participant lifecycle,
     * layout/pin/screen-share change) funnels through here and is coalesced into one
     * {@link arrangeTiles}.
     *
     * The merge window is the current task, not the next animation frame: OWL patches the DOM
     * inside an animation frame, so a frame-deferred layout would let the browser paint the cards
     * that patch just created before they have any geometry.
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
     * Apply the geometry {@link computeLayout} returns to the rendered cards. Runs outside the OWL
     * render loop, so a resize only moves surfaces and never re-renders the component tree.
     */
    arrangeTiles() {
        const gridEl = this.gridRef();
        if (!gridEl) {
            return;
        }
        const { surfaces, hasMoreCards } = this.renderedSurfaces;
        const signature = signatureOf(surfaces, hasMoreCards, this.profile, this.state.insetCorner);
        // Drop the height a previous auto-height pass wrote before measuring, otherwise the stage
        // only ever grows.
        gridEl.style.height = "";
        const { width, height } = gridEl.getBoundingClientRect();
        if (!this.profile.autoHeight && height <= 0) {
            return;
        }
        const layout = this.computeStageLayout({ width, height, surfaces, hasMoreCards });
        // Read back into the render: the surfaces are unchanged, so this re-render does not make
        // `onPatched` ask for another layout.
        this.state.maxTileCount = layout.maxTileCount;
        this.state.cropsTiles = layout.cropsTiles;
        // Only a pass that reached every surface counts as applied. A layout computed for surfaces
        // OWL has not rendered yet places the ones that do have an element and skips the rest; were
        // that recorded, the patch bringing the missing elements in would find the signature it
        // already knows and never lay them out, leaving them at whatever size the CSS gave them
        // next to correctly sized neighbours.
        if (this.applyGeometry(gridEl, layout, surfaces, hasMoreCards)) {
            this._appliedSignature = signature;
        }
    }

    /**
     * Turn the measured stage and the rendered surfaces into the geometry request the engine
     * answers. The engine sees nothing but sizes and placements: every scenario-dependent knob
     * comes from the profile, which was resolved before the stage was measured.
     *
     * @param {{ width: number, height: number, surfaces: MeetingSurface[], hasMoreCards: boolean }} stage
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
                    ? [{ key: MORE_CARDS_KEY, placement: SURFACE_PLACEMENT.MAIN }]
                    : []),
            ],
            capColumnsAtThree,
            fillMainWidth,
            insetCorner: this.state.insetCorner,
            insetBottomMargin,
        });
    }

    /**
     * Hand each card the rect the engine computed for it. A surface with no rect is released, so a
     * card that leaves the layout does not keep the transform it had.
     *
     * @param {HTMLElement} gridEl
     * @param {Object} layout as returned by {@link computeLayout}
     * @param {MeetingSurface[]} surfaces
     * @param {boolean} hasMoreCards
     * @returns {boolean} whether every surface had an element to place, i.e. whether this layout
     *  covers the whole stage as rendered.
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
