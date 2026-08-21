import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { resolveStageProfile, STAGE } from "@mail/discuss/call/common/meeting_layout_profile";

import { describe, expect, test } from "@odoo/hoot";

/**
 * The layout policy is a pure function of the facts of a call, so every scenario — a chat window,
 * a fullscreen meeting, a picture-in-picture — is one call away, with no DOM and no component.
 * That is the point of the module: what a stage does differently is asserted here, not inferred
 * from a rendered stage. The blocks below mirror the stages the module itself branches on.
 */

describe.current.tags("desktop");

/** An ongoing 4-person call, on whichever stage the test needs. */
function ongoingCall(facts) {
    return resolveStageProfile({
        isActiveCall: true,
        participantCount: 4,
        hasVideo: true,
        ...facts,
    });
}

describe("stage resolution", () => {
    test("where the call renders and whether it is yours decide the stage", () => {
        expect(ongoingCall({ isFullscreen: true }).stage).toBe(STAGE.MEETING);
        expect(ongoingCall({ inChatWindow: true }).stage).toBe(STAGE.CHAT_WINDOW);
        expect(ongoingCall({ isPip: true }).stage).toBe(STAGE.PIP);
        expect(ongoingCall({}).stage).toBe(STAGE.DISCUSS);
        // A picture-in-picture window is `compact` too; it is the window it lives in.
        expect(ongoingCall({ isPip: true, inChatWindow: true }).stage).toBe(STAGE.PIP);
        // Fullscreen outranks the container it started from: a chat window you went fullscreen in
        // is a meeting, not a chat window.
        expect(ongoingCall({ inChatWindow: true, isFullscreen: true }).stage).toBe(STAGE.MEETING);
    });

    test("being fullscreen on one call does not make another call's view a meeting", () => {
        // `isFullscreen` is global while `isActiveCall` is per channel, so a second channel's view
        // sees both. It gets none of the meeting's layout policy.
        const other = ongoingCall({ isFullscreen: true, isActiveCall: false });
        expect(other.stage).toBe(STAGE.DISCUSS);
        expect(other.hasSidebar).toBe(false);
        expect(other.allowsSelfInset).toBe(false);
        expect(other.maxMainSpeakers).toBe(1);
        // These two used to key off `isFullscreen` alone and leaked onto this view.
        expect(
            ongoingCall({
                isFullscreen: true,
                isActiveCall: false,
                userLayout: CALL_GRID_LAYOUT.AUTO,
            }).capColumnsAtThree
        ).toBe(false);
        expect(
            ongoingCall({
                isFullscreen: true,
                isActiveCall: false,
                userLayout: CALL_GRID_LAYOUT.TILED,
                prefersVideoTiles: true,
            }).dropsVideolessTiles
        ).toBe(false);
    });

    test("every stage answers the same set of questions", () => {
        // The stages are spread over a shared base, so a key only one of them sets would read as
        // `undefined` at the call site rather than fail here.
        const keysOf = (facts) => Object.keys(ongoingCall(facts)).sort();
        const meeting = keysOf({ isFullscreen: true });
        expect(keysOf({ inChatWindow: true })).toEqual(meeting);
        expect(keysOf({ isPip: true })).toEqual(meeting);
        expect(keysOf({})).toEqual(meeting);
        expect(keysOf({ isSmallScreen: true })).toEqual(meeting);
    });
});

describe("meeting stage", () => {
    test("it is the only stage running the sidebar, the self inset and a shared spotlight", () => {
        const meeting = ongoingCall({ isFullscreen: true, isPresenting: true });
        expect(meeting.hasSidebar).toBe(true);
        // Self is an inset only in a two-person spotlight.
        const oneToOne = { isFullscreen: true, userLayout: CALL_GRID_LAYOUT.AUTO };
        expect(ongoingCall({ ...oneToOne, participantCount: 2 }).allowsSelfInset).toBe(true);
        expect(ongoingCall({ ...oneToOne, participantCount: 3 }).allowsSelfInset).toBe(false);
        // Nowhere else gets any of it.
        for (const elsewhere of [{}, { inChatWindow: true }]) {
            const profile = ongoingCall({ ...elsewhere, isPresenting: true });
            expect(profile.hasSidebar).toBe(false);
            expect(profile.allowsSelfInset).toBe(false);
            expect(profile.maxMainSpeakers).toBe(1);
        }
    });

    test("auto resolves to spotlight, tiled or sidebar from the call itself", () => {
        const auto = { isFullscreen: true, userLayout: CALL_GRID_LAYOUT.AUTO };
        expect(ongoingCall({ ...auto, participantCount: 2 }).layout).toBe(
            CALL_GRID_LAYOUT.SPOTLIGHT
        );
        expect(ongoingCall({ ...auto, participantCount: 3 }).layout).toBe(CALL_GRID_LAYOUT.TILED);
        // A shared screen wins over the participant count, whatever it is.
        expect(ongoingCall({ ...auto, participantCount: 9, isPresenting: true }).layout).toBe(
            CALL_GRID_LAYOUT.SIDEBAR
        );
    });

    test("an explicit layout choice outranks the auto heuristic", () => {
        const profile = ongoingCall({
            isFullscreen: true,
            userLayout: CALL_GRID_LAYOUT.SPOTLIGHT,
            participantCount: 9,
            isPresenting: true,
        });
        expect(profile.layout).toBe(CALL_GRID_LAYOUT.SPOTLIGHT);
        // ... and the 3-column cap is an "auto" comfort, not something an explicit grid wants.
        expect(ongoingCall({ isFullscreen: true, userLayout: CALL_GRID_LAYOUT.TILED }).layout).toBe(
            CALL_GRID_LAYOUT.TILED
        );
        expect(
            ongoingCall({ isFullscreen: true, userLayout: CALL_GRID_LAYOUT.TILED })
                .capColumnsAtThree
        ).toBe(false);
    });

    test("only an explicit tiled grid drops the tiles without video", () => {
        const tiled = { isFullscreen: true, userLayout: CALL_GRID_LAYOUT.TILED };
        expect(ongoingCall({ ...tiled, prefersVideoTiles: true }).dropsVideolessTiles).toBe(true);
        expect(ongoingCall({ ...tiled, prefersVideoTiles: false }).dropsVideolessTiles).toBe(false);
        // "Auto" that happens to tile never hides anyone.
        expect(
            ongoingCall({
                isFullscreen: true,
                userLayout: CALL_GRID_LAYOUT.AUTO,
                prefersVideoTiles: true,
            }).dropsVideolessTiles
        ).toBe(false);
    });

    test("only an unclaimed spotlight splits its stage between recent speakers", () => {
        const spotlight = { isFullscreen: true, userLayout: CALL_GRID_LAYOUT.SPOTLIGHT };
        expect(ongoingCall(spotlight).maxMainSpeakers).toBe(4);
        // The sidebar keeps one main window and sorts the speakers to the top of its column.
        expect(
            ongoingCall({ isFullscreen: true, userLayout: CALL_GRID_LAYOUT.SIDEBAR })
                .maxMainSpeakers
        ).toBe(1);
        // A shared screen and a manual pin both mean "this session, whole".
        expect(ongoingCall({ ...spotlight, isPresenting: true }).maxMainSpeakers).toBe(1);
        expect(ongoingCall({ ...spotlight, isPinned: true }).maxMainSpeakers).toBe(1);
    });
});

describe("chat window stage", () => {
    test("it grows with its cards and stops after a handful of them", () => {
        const chatWindow = ongoingCall({ inChatWindow: true, hasFocus: true });
        expect(chatWindow.maxCards).toBe(6);
        expect(chatWindow.autoHeight).toBe(true);
        expect(chatWindow.fillMainWidth).toBe(true);
        // Discuss is a plain grid filling the space its container gives it.
        const inDiscuss = ongoingCall({ hasFocus: true });
        expect(inDiscuss.maxCards).toBe(Infinity);
        expect(inDiscuss.autoHeight).toBe(false);
        expect(inDiscuss.fillMainWidth).toBe(false);
    });

    test("it keeps its inset clear of the floating call controls", () => {
        expect(ongoingCall({ inChatWindow: true }).insetBottomMargin).toBe(40);
        // Everywhere else the inset sits at the regular margin from the tile edge.
        expect(ongoingCall({ isFullscreen: true }).insetBottomMargin).toBe(8);
    });

    test("a touch chat window has a height of its own", () => {
        // It is full-screen there, so it must fill its container instead of growing with its cards.
        const chatWindow = { inChatWindow: true, hasFocus: true };
        expect(ongoingCall({ ...chatWindow, isTouch: false }).autoHeight).toBe(true);
        expect(ongoingCall({ ...chatWindow, isTouch: true }).autoHeight).toBe(false);
    });

    test("a call with nothing to show big collapses to a strip", () => {
        const idle = { hasVideo: false };
        expect(ongoingCall(idle).minimized).toBe(true);
        // Anything worth a big tile expands it again.
        expect(ongoingCall({ ...idle, hasVideo: true }).minimized).toBe(false);
        expect(ongoingCall({ ...idle, hasFocus: true }).minimized).toBe(false);
        expect(ongoingCall({ ...idle, isFullscreen: true }).minimized).toBe(false);
        // A chat window stays a strip even with video: the conversation gets the room, and only a
        // spotlighted session earns the space of a real stage. That is also what makes it the one
        // stage whose height grows with its content.
        const chatWindow = { inChatWindow: true, hasVideo: true };
        expect(ongoingCall(chatWindow).minimized).toBe(true);
        expect(ongoingCall(chatWindow).autoHeight).toBe(false);
        expect(ongoingCall({ ...chatWindow, hasFocus: true }).minimized).toBe(false);
        expect(ongoingCall({ ...chatWindow, hasFocus: true }).autoHeight).toBe(true);
    });
});

describe("mobile stage", () => {
    const onPhone = { isSmallScreen: true };

    test("a phone is its own stage, whatever it renders inside", () => {
        for (const inside of [{}, { inChatWindow: true }]) {
            expect(ongoingCall({ ...onPhone, ...inside }).stage).toBe(STAGE.MOBILE);
        }
        expect(ongoingCall({ ...onPhone, isFullscreen: true }).stage).toBe(STAGE.MOBILE);
    });

    test("it only ever renders a handful of cards", () => {
        // Every card past the cap is a video stream downloaded to fill a hundred pixels.
        expect(ongoingCall({ participantCount: 9 }).maxCards).toBe(Infinity);
        expect(ongoingCall({ ...onPhone, participantCount: 9 }).maxCards).toBe(6);
    });

    test("it spotlights where a roomy screen would already tile", () => {
        const auto = { ...onPhone, isFullscreen: true, userLayout: CALL_GRID_LAYOUT.AUTO };
        expect(ongoingCall({ ...auto, participantCount: 4 }).layout).toBe(
            CALL_GRID_LAYOUT.SPOTLIGHT
        );
        expect(ongoingCall({ ...auto, participantCount: 5 }).layout).toBe(CALL_GRID_LAYOUT.TILED);
        // An explicit choice still outranks the heuristic, phone or not.
        expect(
            ongoingCall({ ...auto, participantCount: 4, userLayout: CALL_GRID_LAYOUT.TILED }).layout
        ).toBe(CALL_GRID_LAYOUT.TILED);
    });

    test("it splits its spotlight between two speakers, not four", () => {
        // Otherwise the wider tiling threshold above would just move the same tiny tiles into the
        // spotlight: four ways across a phone is the thing worth avoiding, not the layout name.
        const spotlight = { isFullscreen: true, userLayout: CALL_GRID_LAYOUT.SPOTLIGHT };
        expect(ongoingCall({ ...spotlight, ...onPhone }).maxMainSpeakers).toBe(2);
        expect(ongoingCall(spotlight).maxMainSpeakers).toBe(4);
    });

    test("it never caps its grid at three columns", () => {
        // Three columns across a phone is three columns of nothing, whatever the participant count.
        const auto = { ...onPhone, isFullscreen: true, userLayout: CALL_GRID_LAYOUT.AUTO };
        expect(ongoingCall({ ...auto, participantCount: 9 }).layout).toBe(CALL_GRID_LAYOUT.TILED);
        expect(ongoingCall({ ...auto, participantCount: 9 }).capColumnsAtThree).toBe(false);
    });

    test("the focused card fills the phone rather than the width alone", () => {
        // `fillMainWidth` sizes the card from the width at the source ratio, which is how an
        // auto-height chat window learns the height to take — and it switches the engine's portrait
        // branch off. A phone has a height of its own, in a shape no video is: taking that path
        // would spend a quarter of the screen on the card and the rest on black.
        const profile = ongoingCall({ ...onPhone, hasFocus: true });
        expect(profile.fillMainWidth).toBe(false);
        expect(ongoingCall({ inChatWindow: true, hasFocus: true }).fillMainWidth).toBe(true);
        // The call controls span the bottom of every phone call view, focus or not.
        expect(profile.insetBottomMargin).toBe(40);
    });

    test("a phone in the call it is fullscreen on still runs the meeting layouts", () => {
        // The rows mobileStage repeats from meetingStage are the ones pinned here: drift between
        // the two shows up as this test going red.
        const inCall = ongoingCall({ ...onPhone, isFullscreen: true, isPresenting: true });
        expect(inCall.runsMeetingLayouts).toBe(true);
        expect(inCall.hasSidebar).toBe(true);
        const oneToOne = {
            ...onPhone,
            isFullscreen: true,
            userLayout: CALL_GRID_LAYOUT.AUTO,
            participantCount: 2,
        };
        expect(ongoingCall(oneToOne).allowsSelfInset).toBe(true);
    });

    test("a phone that is not in the call gets none of the meeting layouts", () => {
        const beside = ongoingCall({ ...onPhone, inChatWindow: true });
        expect(beside.runsMeetingLayouts).toBe(false);
        expect(beside.hasSidebar).toBe(false);
        expect(beside.allowsSelfInset).toBe(false);
        expect(beside.maxMainSpeakers).toBe(1);
    });
});

describe("every stage", () => {
    test("an invitation grid uses square avatar tiles", () => {
        expect(ongoingCall({ isActiveCall: false }).aspectRatio).toBe(1);
        expect(ongoingCall({ isActiveCall: true }).aspectRatio).toBe(16 / 9);
    });

    test("a meeting and a picture-in-picture take a whole window, the others do not", () => {
        expect(ongoingCall({ isFullscreen: true }).isFullSize).toBe(true);
        expect(ongoingCall({ isPip: true }).isFullSize).toBe(true);
        expect(ongoingCall({}).isFullSize).toBe(false);
        expect(ongoingCall({ inChatWindow: true }).isFullSize).toBe(false);
    });
});
