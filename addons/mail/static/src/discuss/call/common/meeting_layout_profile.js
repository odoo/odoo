import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { INSET_MARGIN } from "@mail/discuss/call/common/meeting_layout_engine";

/**
 * Layout policy of the meeting stage: turns the facts of a call — where it is rendered, how many
 * participants, what the user picked — into the parameters the surface selection and the geometry
 * engine then run on. Answering "what does a phone do differently from a fullscreen meeting" means
 * reading {@link mobileStage}, which is the whole of the difference.
 *
 * It is pure: no DOM, no service, no OWL. In particular it never sees the *measured* stage box,
 * and that is a hard rule rather than an accident. Everything decided here has to be known before
 * the stage is measured, because it decides which surfaces exist at all — and therefore which
 * videos get downloaded. Anything a measured box is enough to decide (the tile grid, the sidebar
 * column width, the inset size) belongs to the engine, not here.
 *
 * A new scenario is a new {@link STAGE} plus its function below; nothing outside this file should
 * need a branch for it.
 */

/**
 * The scenario the layout resolves to, and the only thing the policy below branches on. The caller
 * reports plain facts — where it renders, how much room it has, whose call it is — and
 * {@link stageOf} works out which of these they add up to. Neither fullscreen nor a phone is a
 * container, but both are scenarios, which is why this is not just a list of containers.
 */
export const STAGE = Object.freeze({
    MOBILE: "mobile",
    MEETING: "meeting",
    CHAT_WINDOW: "chat_window",
    DISCUSS: "discuss",
    PIP: "pip",
});

/** Cards a chat window renders before collapsing the rest into the "more" indicator. */
const CHAT_WINDOW_MAX_CARDS = 6;
/**
 * Height (px) the floating call controls cover at the bottom of the stage. The inset has to sit
 * above them.
 */
const CONTROLS_HEIGHT = 40;
/** Speakers the spotlight splits its stage between before the rest have to wait for a place. */
const MAX_MAIN_SPEAKERS = 4;
/** Participant count from which the "auto" layout tiles instead of spotlighting. */
const AUTO_TILING_THRESHOLD = 3;

/**
 * Cards a phone renders before collapsing the rest into the "more" indicator. A cap and not a
 * comfort: every card beyond it is a video stream downloaded and decoded to fill a hundred pixels
 * nobody can read, which on a phone is paid in battery and in bandwidth.
 */
const MOBILE_MAX_CARDS = 6;
/** Speakers a phone splits its spotlight between: there is no room to split it four ways. */
const MOBILE_MAX_MAIN_SPEAKERS = 2;
/**
 * Participant count from which a phone tiles. Higher than the roomy one: tiles become unreadable
 * there several participants sooner, so the spotlight keeps the stage for longer.
 */
const MOBILE_AUTO_TILING_THRESHOLD = 5;

/**
 * @typedef StageFacts
 * @property {boolean} [inChatWindow] rendered beside a conversation rather than in Discuss
 * @property {boolean} [isPip] rendered in a picture-in-picture window
 * @property {boolean} [isActiveCall] the rendered channel is the call the user is in
 * @property {boolean} [isFullscreen] the call view has taken over the screen
 * @property {boolean} [isTouch] touch device (no hover, no resizable window)
 * @property {boolean} [isSmallScreen] the whole screen is phone-sized, which selects
 *  {@link STAGE.MOBILE} outright. A different axis from `isTouch`, which is about the pointer: a
 *  tablet is touch and roomy, a narrow desktop window is neither.
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
 * @property {number} maxMainSpeakers how many recent speakers share the main window; 1 keeps the
 *  single big tile every stage but the meeting has always had
 * @property {number} insetBottomMargin bottom gap (px) of an inset in a bottom corner
 */

/**
 * @param {StageFacts} facts
 * @returns {StageProfile}
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
        // A picture-in-picture window differs from Discuss in nothing but taking a whole window,
        // which `isFullSize` already reads off the stage.
        default:
            return base;
    }
}

/**
 * @param {StageFacts} facts
 * @returns {string} a {@link STAGE}
 */
function stageOf({
    inChatWindow = false,
    isPip = false,
    isFullscreen = false,
    isActiveCall = false,
    isSmallScreen = false,
}) {
    // A phone is its own scenario before it is anything else: a chat window there is not the little
    // strip beside a conversation it is on a desktop, and a meeting there has a third of the width.
    if (isSmallScreen) {
        return STAGE.MOBILE;
    }
    // Only the fullscreen stage of the call you are actually in is a meeting. Being fullscreen on
    // one channel does not turn another channel's call view into one, wherever it is rendered.
    if (isFullscreen && isActiveCall) {
        return STAGE.MEETING;
    }
    // Order is the priority: a picture-in-picture window is `compact` too, and is the stage it
    // is rendered in rather than the one it is styled like.
    if (isPip) {
        return STAGE.PIP;
    }
    if (inChatWindow) {
        return STAGE.CHAT_WINDOW;
    }
    return STAGE.DISCUSS;
}

/**
 * What every stage answers before it gets a say: a plain grid of equal tiles, no sidebar, no inset,
 * one participant on the main window at a time.
 *
 * @param {StageFacts} facts
 * @param {string} stage
 * @returns {StageProfile}
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
 * The fullscreen stage of your own call: the only one that runs the meeting layouts — a sidebar
 * column, self as an inset, a stage several speakers can share.
 *
 * @param {StageFacts} facts
 * @param {StageProfile} base
 * @returns {Partial<StageProfile>}
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
        // Only the spotlight has a stage to split, and only when nothing else has claimed the main
        // window: a shared screen and a manual pin both mean "this, whole". The sidebar layout
        // sorts the speakers to the top of its column instead of splitting.
        maxMainSpeakers: splitsBetween(facts, layout) ? MAX_MAIN_SPEAKERS : 1,
    };
}

/**
 * Everything a call does differently on a phone, in one place. It is a stage of its own rather than
 * a modifier on the others because a phone is not a smaller desktop: a chat window there is not the
 * strip beside a conversation, and the layouts it can afford are a different set.
 *
 * It repeats a few of {@link meetingStage}'s rows on purpose. They are the price of being able to
 * read the whole phone story top to bottom, and of letting it diverge without touching the desktop.
 *
 * @param {StageFacts} facts
 * @returns {Partial<StageProfile>}
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
    // A phone in the call it is fullscreen on is still a meeting, with a third of the width.
    const inMeeting = isFullscreen && isActiveCall;
    return {
        layout,
        runsMeetingLayouts: inMeeting,
        // Past this, cards are video streams decoded to fill a hundred pixels of a phone.
        maxCards: MOBILE_MAX_CARDS,
        hasSidebar: inMeeting && layout === CALL_GRID_LAYOUT.SIDEBAR,
        allowsSelfInset:
            inMeeting && layout === CALL_GRID_LAYOUT.SPOTLIGHT && participantCount === 2,
        // Never: three columns across a phone is three columns of nothing.
        capColumnsAtThree: false,
        dropsVideolessTiles:
            inMeeting && userLayout === CALL_GRID_LAYOUT.TILED && prefersVideoTiles,
        maxMainSpeakers: inMeeting && splitsBetween(facts, layout) ? MOBILE_MAX_MAIN_SPEAKERS : 1,
        // Never, unlike a chat window: `fillMainWidth` sizes the focused card from the width at the
        // source ratio, which is how an auto-height stage learns the height it has to take. A phone
        // already has one, and it is a shape no video is: a 16:9 card sized from the width covers a
        // quarter of it. The engine's portrait branch is what fills a phone, and `fillMainWidth`
        // switches it off.
        fillMainWidth: false,
        // The call controls sit along the bottom of every phone call view.
        insetBottomMargin: CONTROLS_HEIGHT,
    };
}

/**
 * @param {StageFacts} facts
 * @param {string} layout the resolved {@link CALL_GRID_LAYOUT}
 * @returns {boolean} whether the main window is up for grabs between the recent speakers, rather
 *  than claimed by a shared screen or a manual pin.
 */
function splitsBetween({ isPresenting = false, isPinned = false }, layout) {
    return layout === CALL_GRID_LAYOUT.SPOTLIGHT && !isPresenting && !isPinned;
}

/**
 * A call rendered beside a conversation: the room belongs to the conversation, so the stage grows
 * with its content instead of claiming a height, and stops after a handful of cards.
 *
 * @param {StageFacts} facts
 * @param {StageProfile} base
 * @returns {Partial<StageProfile>}
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
 * @param {number} [tilingThreshold] participants from which "auto" tiles, for the stages with less
 *  room to tile in.
 * @returns {string} a {@link CALL_GRID_LAYOUT}
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
 * @param {StageFacts} facts
 * @param {string} stage
 * @returns {boolean} whether the stage collapses to a strip of avatars: there is nothing to show
 *  big, and the container would rather give the room to the conversation.
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
