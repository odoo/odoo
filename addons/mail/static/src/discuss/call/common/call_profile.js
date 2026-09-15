import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { INSET_MARGIN } from "@mail/discuss/call/common/stage/layout_engine";

/** @typedef {import("@mail/discuss/call/common/call").CallStagePipeline} CallStagePipeline */

/**
 * The pre-step of the {@link CallStagePipeline}.
 *
 * Turns a rendered call into the parameters its stage runs on: which surfaces exist at all, and
 * the geometry they are laid out with. Blind to the measured stage box on purpose: that choice of
 * surfaces settles which videos get downloaded, before anything is measured.
 */

/**
 * The scenario the layout resolves to, and the only thing the policy below branches on.
 *
 * @typedef {typeof CALL_PROFILE_TYPE[keyof typeof CALL_PROFILE_TYPE]} CallProfileType
 */
export const CALL_PROFILE_TYPE = Object.freeze({
    MOBILE: "mobile",
    MEETING: "meeting",
    CHAT_WINDOW: "chat_window",
    DISCUSS: "discuss",
    PIP: "pip",
});

/** Cards a chat window renders before collapsing the rest into the "more" indicator. */
const CHAT_WINDOW_MAX_CARDS = 6;
/** Height (px) the floating call controls cover: the inset has to sit above them. */
const CONTROLS_HEIGHT = 40;
/** Speakers the spotlight splits its stage between before the rest have to wait for a place. */
const MAX_MAIN_SPEAKERS = 4;
/** Participant count from which the "auto" layout tiles instead of spotlighting. */
const AUTO_TILING_THRESHOLD = 3;

/** Cards a phone renders: every one beyond is a stream decoded to fill a hundred pixels. */
const MOBILE_MAX_CARDS = 6;
/** Speakers a phone splits its spotlight between: there is no room to split it four ways. */
const MOBILE_MAX_MAIN_SPEAKERS = 2;
/** Participant count from which a phone tiles: tiles become unreadable there much sooner. */
const MOBILE_AUTO_TILING_THRESHOLD = 5;

/** @typedef {import("@mail/discuss/call/common/call").Call} Call */
/** @typedef {import("@mail/discuss/call/common/call_layout").CallLayout} CallLayout */

/**
 * Every layout decision of a call, resolved once from the call itself. The fields below are the
 * answers of the default type, Discuss, and the constructor's switch is the one place a scenario
 * departs from them. A new scenario is a new {@link CALL_PROFILE_TYPE} and a new case, never a
 * branch spread through the rows.
 */
export class CallProfile {
    /** Which of the five scenarios these values were resolved for. @type {CallProfileType} */
    type = CALL_PROFILE_TYPE.DISCUSS;
    /** The concrete layout to render, never AUTO. @type {CallLayout} */
    layout = CALL_GRID_LAYOUT.SPOTLIGHT;
    /**
     * The stage picks what fills the main window from the recent speakers, instead of leaving it
     * to the auto-focus heuristics.
     */
    runsMeetingLayouts = false;
    /** The stage is a slim strip of avatars: there is nothing to show big. */
    minimized = false;
    /** A sidebar column is rendered next to the main window. */
    hasSidebar = false;
    /** Self is shown as an inset over the spotlighted participant. */
    allowsSelfInset = false;
    /** Surfaces to render at most; the rest collapse into an indicator. */
    maxCards = Infinity;
    /** The stage has no height of its own and takes its content's. */
    autoHeight = false;
    /** Tile aspect ratio. */
    aspectRatio = 1;
    /** The focused card spans the whole main area. */
    fillMainWidth = false;
    /** Cap the tiled grid at 3 columns. */
    capColumnsAtThree = false;
    /** Hide the tiles with no video rather than shrink the whole grid past what the stage holds. */
    dropsVideolessTiles = false;
    /** How many recent speakers share the main window; 1 is the single big tile. */
    maxMainSpeakers = 1;
    /** Bottom gap (px) of an inset in a bottom corner. */
    insetBottomMargin = INSET_MARGIN;

    /** @param {Call} call */
    constructor(call) {
        this.type = resolveType(call);
        this.layout = resolveLayout(call);
        this.minimized = resolveMinimized(call, this.type);
        this.aspectRatio = call.isActiveCall ? 16 / 9 : 1;
        switch (this.type) {
            // A type of its own rather than a modifier on the others, so a phone can diverge
            // without touching the desktop — hence the rows repeated from the meeting, guarded by
            // `inMeeting`: a phone runs the meeting layouts only for the call it is fullscreen on.
            case CALL_PROFILE_TYPE.MOBILE: {
                const inMeeting = Boolean(call.rtc.isFullscreen && call.isActiveCall);
                this.layout = resolveLayout(call, MOBILE_AUTO_TILING_THRESHOLD);
                this.runsMeetingLayouts = inMeeting;
                this.maxCards = MOBILE_MAX_CARDS;
                this.hasSidebar = inMeeting && this.layout === CALL_GRID_LAYOUT.SIDEBAR;
                this.allowsSelfInset =
                    inMeeting &&
                    this.layout === CALL_GRID_LAYOUT.SPOTLIGHT &&
                    participantCount(call) === 2;
                this.dropsVideolessTiles =
                    inMeeting &&
                    userLayout(call) === CALL_GRID_LAYOUT.TILED &&
                    prefersVideoTiles(call);
                this.maxMainSpeakers =
                    inMeeting && splitsBetween(call, this.layout) ? MOBILE_MAX_MAIN_SPEAKERS : 1;
                // The call controls sit along the bottom of every phone call view.
                this.insetBottomMargin = CONTROLS_HEIGHT;
                // `capColumnsAtThree` and `fillMainWidth` stay off: three columns across a phone
                // is three columns of nothing, and a card sized from the width would cover a
                // quarter of the screen instead of running the engine's portrait branch.
                break;
            }
            // The fullscreen stage of your own call: the only one several speakers can share.
            case CALL_PROFILE_TYPE.MEETING: {
                this.runsMeetingLayouts = true;
                this.hasSidebar = this.layout === CALL_GRID_LAYOUT.SIDEBAR;
                this.allowsSelfInset =
                    this.layout === CALL_GRID_LAYOUT.SPOTLIGHT && participantCount(call) === 2;
                // No explicit choice is "auto", which the resolved layout no longer says.
                this.capColumnsAtThree =
                    !hasExplicitLayout(call) && this.layout === CALL_GRID_LAYOUT.TILED;
                this.dropsVideolessTiles =
                    userLayout(call) === CALL_GRID_LAYOUT.TILED && prefersVideoTiles(call);
                this.maxMainSpeakers = splitsBetween(call, this.layout) ? MAX_MAIN_SPEAKERS : 1;
                break;
            }
            // A call rendered beside a conversation: the room belongs to the conversation, so the
            // stage grows with its content instead of claiming a height.
            case CALL_PROFILE_TYPE.CHAT_WINDOW: {
                this.maxCards = CHAT_WINDOW_MAX_CARDS;
                // A touch chat window is full-screen there, so it fills its container instead.
                this.autoHeight = !call.isMobileOs && !this.minimized && !call.isFullSize;
                this.fillMainWidth = Boolean(call.channel?.activeRtcSession);
                this.insetBottomMargin = CONTROLS_HEIGHT;
                break;
            }
            // A picture-in-picture window differs from Discuss only in taking a whole window,
            // which the call itself answers.
        }
    }
}

/**
 * Which of the five scenarios a call renders in. The order is the precedence between them.
 *
 * @param {Call} call
 * @returns {CallProfileType}
 */
function resolveType(call) {
    if (call.ui.isSmall) {
        return CALL_PROFILE_TYPE.MOBILE;
    }
    // Fullscreen on one channel does not turn another channel's call view into a meeting.
    if (call.rtc.isFullscreen && call.isActiveCall) {
        return CALL_PROFILE_TYPE.MEETING;
    }
    // Before the chat window: a picture-in-picture window is `compact` too.
    if (call.props.isPip) {
        return CALL_PROFILE_TYPE.PIP;
    }
    if (call.props.compact) {
        return CALL_PROFILE_TYPE.CHAT_WINDOW;
    }
    return CALL_PROFILE_TYPE.DISCUSS;
}

/** @param {Call} call */
function participantCount(call) {
    return call.channel?.rtc_session_ids.length ?? 0;
}

/**
 * The layout the user picked, {@link CALL_GRID_LAYOUT.AUTO} included.
 *
 * @param {Call} call
 * @returns {CallLayout}
 */
function userLayout(call) {
    return call.store.settings.callLayout;
}

/** The "Prioritize tiles with video" setting. @param {Call} call */
function prefersVideoTiles(call) {
    return Boolean(call.store.settings.showOnlyVideo);
}

/**
 * Whether the user picked a layout themselves, rather than leaving it on
 * {@link CALL_GRID_LAYOUT.AUTO}.
 *
 * @param {Call} call
 */
function hasExplicitLayout(call) {
    return Boolean(userLayout(call)) && userLayout(call) !== CALL_GRID_LAYOUT.AUTO;
}

/**
 * Whether the main window is up for grabs between the recent speakers, rather than claimed by a
 * shared screen or a manual pin. Only the spotlight has a stage to split.
 *
 * @param {Call} call
 * @param {CallLayout} layout the resolved {@link CALL_GRID_LAYOUT}
 */
function splitsBetween(call, layout) {
    return (
        layout === CALL_GRID_LAYOUT.SPOTLIGHT &&
        !call.isAnyonePresenting &&
        !call.channel?.pinnedRtcSession
    );
}

/**
 * Resolve {@link CALL_GRID_LAYOUT.AUTO} into the layout it means right now. An explicit choice is
 * returned untouched: the user outranks the heuristic.
 *
 * @param {Call} call
 * @param {number} [tilingThreshold] participants from which "auto" tiles
 * @returns {CallLayout}
 */
function resolveLayout(call, tilingThreshold = AUTO_TILING_THRESHOLD) {
    if (hasExplicitLayout(call)) {
        return userLayout(call);
    }
    if (call.isAnyonePresenting) {
        return CALL_GRID_LAYOUT.SIDEBAR;
    }
    return participantCount(call) >= tilingThreshold
        ? CALL_GRID_LAYOUT.TILED
        : CALL_GRID_LAYOUT.SPOTLIGHT;
}

/**
 * Whether the stage collapses to a strip of avatars: there is nothing to show big.
 *
 * @param {Call} call
 * @param {CallProfileType} type
 */
function resolveMinimized(call, type) {
    if (call.rtc.isFullscreen || call.channel?.activeRtcSession) {
        return false;
    }
    return (
        type === CALL_PROFILE_TYPE.CHAT_WINDOW || !call.isActiveCall || !call.channel?.videoCount
    );
}
