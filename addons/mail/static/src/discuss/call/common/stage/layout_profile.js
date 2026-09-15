import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { INSET_MARGIN } from "@mail/discuss/call/common/stage/layout_engine";

/**
 * Turns the facts of a call into the parameters the surface selection and the geometry engine run
 * on. Blind to the measured stage box on purpose: it decides which surfaces exist at all, hence
 * which videos get downloaded, before anything is measured.
 */

/** The scenario the layout resolves to, and the only thing the policy below branches on. */
export const STAGE = Object.freeze({
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

/**
 * @typedef StageFacts
 * @property {boolean} [inChatWindow] rendered beside a conversation rather than in Discuss
 * @property {boolean} [isPip] rendered in a picture-in-picture window
 * @property {boolean} [isActiveCall] the rendered channel is the call the user is in
 * @property {boolean} [isFullscreen] the call view has taken over the screen
 * @property {boolean} [isTouch] touch device (no hover, no resizable window)
 * @property {boolean} [isSmallScreen] the whole screen is phone-sized. A different axis from
 *  `isTouch`: a tablet is touch and roomy, a narrow desktop window is neither.
 * @property {number} [participantCount]
 * @property {boolean} [hasVideo] anyone is sharing a camera or a screen
 * @property {boolean} [hasFocus] a session is spotlighted
 * @property {boolean} [isPresenting] someone is sharing their screen
 * @property {boolean} [isPinned] a participant was manually pinned to the main window
 * @property {string} [userLayout] the layout the user picked, {@link CALL_GRID_LAYOUT} included AUTO
 * @property {boolean} [prefersVideoTiles] the "Prioritize tiles with video" setting
 */

/**
 * @typedef StageProfile
 * @property {string} stage the {@link STAGE} these values were resolved for
 * @property {string} layout the concrete layout to render, never AUTO
 * @property {boolean} runsMeetingLayouts the stage picks what fills the main window from the
 *  recent speakers, instead of leaving it to the auto-focus heuristics
 * @property {boolean} isFullSize the stage takes a whole window
 * @property {boolean} minimized the stage is a slim strip of avatars
 * @property {boolean} hasSidebar a sidebar column is rendered next to the main window
 * @property {boolean} allowsSelfInset self is shown as an inset over the spotlighted participant
 * @property {number} maxCards surfaces to render at most; the rest collapse into an indicator
 * @property {boolean} autoHeight the stage has no height of its own and takes its content's
 * @property {number} aspectRatio tile aspect ratio
 * @property {boolean} fillMainWidth the focused card spans the whole main area
 * @property {boolean} capColumnsAtThree cap the tiled grid at 3 columns
 * @property {boolean} dropsVideolessTiles hide the tiles with no video rather than shrink the
 *  whole grid past what the stage can hold
 * @property {number} maxMainSpeakers how many recent speakers share the main window; 1 is the
 *  single big tile
 * @property {number} insetBottomMargin bottom gap (px) of an inset in a bottom corner
 */

/**
 * @param {StageFacts} facts
 */
export function resolveStageProfile(facts = {}) {
    const stage = stageOf(facts);
    const base = baseProfile(facts, stage);
    switch (stage) {
        case STAGE.MOBILE:
            return { ...base, ...mobileStage(facts) };
        case STAGE.MEETING:
            return { ...base, ...meetingStage(facts, base) };
        case STAGE.CHAT_WINDOW:
            return { ...base, ...chatWindowStage(facts, base) };
        // A picture-in-picture window differs from Discuss only in taking a whole window.
        default:
            return base;
    }
}

/**
 * @param {StageFacts} facts
 */
function stageOf({
    inChatWindow = false,
    isPip = false,
    isFullscreen = false,
    isActiveCall = false,
    isSmallScreen = false,
}) {
    if (isSmallScreen) {
        return STAGE.MOBILE;
    }
    // Fullscreen on one channel does not turn another channel's call view into a meeting.
    if (isFullscreen && isActiveCall) {
        return STAGE.MEETING;
    }
    // Before the chat window: a picture-in-picture window is `compact` too.
    if (isPip) {
        return STAGE.PIP;
    }
    if (inChatWindow) {
        return STAGE.CHAT_WINDOW;
    }
    return STAGE.DISCUSS;
}

/**
 * What every stage answers before it gets a say.
 *
 * @param {StageFacts} facts
 * @param {string} stage
 */
function baseProfile(facts, stage) {
    const { isActiveCall = false, isFullscreen = false } = facts;
    return {
        stage,
        layout: resolveLayout(facts),
        runsMeetingLayouts: false,
        isFullSize: isFullscreen || stage === STAGE.PIP,
        minimized: resolveMinimized(facts, stage),
        hasSidebar: false,
        allowsSelfInset: false,
        maxCards: Infinity,
        autoHeight: false,
        aspectRatio: isActiveCall ? 16 / 9 : 1,
        fillMainWidth: false,
        capColumnsAtThree: false,
        dropsVideolessTiles: false,
        maxMainSpeakers: 1,
        insetBottomMargin: INSET_MARGIN,
    };
}

/**
 * The fullscreen stage of your own call: the only one several speakers can share.
 *
 * @param {StageFacts} facts
 * @param {StageProfile} base
 */
function meetingStage(facts, base) {
    const {
        participantCount = 0,
        userLayout = CALL_GRID_LAYOUT.AUTO,
        prefersVideoTiles = false,
    } = facts;
    const { layout } = base;
    return {
        runsMeetingLayouts: true,
        hasSidebar: layout === CALL_GRID_LAYOUT.SIDEBAR,
        allowsSelfInset: layout === CALL_GRID_LAYOUT.SPOTLIGHT && participantCount === 2,
        capColumnsAtThree:
            userLayout === CALL_GRID_LAYOUT.AUTO && layout === CALL_GRID_LAYOUT.TILED,
        dropsVideolessTiles: userLayout === CALL_GRID_LAYOUT.TILED && prefersVideoTiles,
        maxMainSpeakers: splitsBetween(facts, layout) ? MAX_MAIN_SPEAKERS : 1,
    };
}

/**
 * A stage of its own rather than a modifier on the others, so a phone can diverge without touching
 * the desktop — hence the repeated rows.
 *
 * @param {StageFacts} facts
 */
function mobileStage(facts) {
    const {
        isFullscreen = false,
        isActiveCall = false,
        participantCount = 0,
        userLayout = CALL_GRID_LAYOUT.AUTO,
        prefersVideoTiles = false,
    } = facts;
    const layout = resolveLayout(facts, MOBILE_AUTO_TILING_THRESHOLD);
    const inMeeting = isFullscreen && isActiveCall;
    return {
        layout,
        runsMeetingLayouts: inMeeting,
        maxCards: MOBILE_MAX_CARDS,
        hasSidebar: inMeeting && layout === CALL_GRID_LAYOUT.SIDEBAR,
        allowsSelfInset:
            inMeeting && layout === CALL_GRID_LAYOUT.SPOTLIGHT && participantCount === 2,
        // Three columns across a phone is three columns of nothing.
        capColumnsAtThree: false,
        dropsVideolessTiles:
            inMeeting && userLayout === CALL_GRID_LAYOUT.TILED && prefersVideoTiles,
        maxMainSpeakers: inMeeting && splitsBetween(facts, layout) ? MOBILE_MAX_MAIN_SPEAKERS : 1,
        // A phone already has a height, and it is a shape no video is: sizing the focused card
        // from the width would cover a quarter of it. Off, so the engine's portrait branch runs.
        fillMainWidth: false,
        // The call controls sit along the bottom of every phone call view.
        insetBottomMargin: CONTROLS_HEIGHT,
    };
}

/**
 * Whether the main window is up for grabs between the recent speakers, rather than claimed by a
 * shared screen or a manual pin. Only the spotlight has a stage to split.
 *
 * @param {StageFacts} facts
 * @param {string} layout the resolved {@link CALL_GRID_LAYOUT}
 */
function splitsBetween({ isPresenting = false, isPinned = false }, layout) {
    return layout === CALL_GRID_LAYOUT.SPOTLIGHT && !isPresenting && !isPinned;
}

/**
 * A call rendered beside a conversation: the room belongs to the conversation, so the stage grows
 * with its content instead of claiming a height.
 *
 * @param {StageFacts} facts
 * @param {StageProfile} base
 */
function chatWindowStage(facts, base) {
    const { isTouch = false, hasFocus = false } = facts;
    return {
        maxCards: CHAT_WINDOW_MAX_CARDS,
        // A touch chat window is full-screen there, so it fills its container instead.
        autoHeight: !isTouch && !base.minimized && !base.isFullSize,
        fillMainWidth: hasFocus,
        insetBottomMargin: CONTROLS_HEIGHT,
    };
}

/**
 * Resolve {@link CALL_GRID_LAYOUT.AUTO} into the layout it means right now. An explicit choice is
 * returned untouched: the user outranks the heuristic.
 *
 * @param {StageFacts} facts
 * @param {number} [tilingThreshold] participants from which "auto" tiles
 */
function resolveLayout(
    { userLayout = CALL_GRID_LAYOUT.AUTO, isPresenting = false, participantCount = 0 },
    tilingThreshold = AUTO_TILING_THRESHOLD
) {
    if (userLayout !== CALL_GRID_LAYOUT.AUTO) {
        return userLayout;
    }
    if (isPresenting) {
        return CALL_GRID_LAYOUT.SIDEBAR;
    }
    return participantCount >= tilingThreshold
        ? CALL_GRID_LAYOUT.TILED
        : CALL_GRID_LAYOUT.SPOTLIGHT;
}

/**
 * Whether the stage collapses to a strip of avatars: there is nothing to show big.
 *
 * @param {StageFacts} facts
 * @param {string} stage
 */
function resolveMinimized(
    { hasFocus = false, hasVideo = false, isActiveCall = false, isFullscreen = false },
    stage
) {
    if (isFullscreen || hasFocus) {
        return false;
    }
    return stage === STAGE.CHAT_WINDOW || !isActiveCall || !hasVideo;
}
