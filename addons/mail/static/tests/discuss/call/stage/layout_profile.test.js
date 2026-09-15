import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { resolveStageProfile, STAGE } from "@mail/discuss/call/common/stage/layout_profile";

import { describe, expect, test } from "@odoo/hoot";

/** What each stage does differently, asserted on the facts rather than on a rendered stage. */

describe.current.tags("desktop");

describe("which of the five stages a call lands on", () => {
    test("where the call renders and whether it is yours decide the stage", () => {
        expect(resolveStageProfile({ isFullscreen: true, isActiveCall: true }).stage).toBe(
            STAGE.MEETING
        );
        expect(resolveStageProfile({ inChatWindow: true }).stage).toBe(STAGE.CHAT_WINDOW);
        expect(resolveStageProfile({ isPip: true }).stage).toBe(STAGE.PIP);
        expect(resolveStageProfile({}).stage).toBe(STAGE.DISCUSS);
        // A picture-in-picture window is `compact` too; it is the window it lives in.
        expect(resolveStageProfile({ isPip: true, inChatWindow: true }).stage).toBe(STAGE.PIP);
        // Fullscreen outranks the container it started from: a chat window you went fullscreen in
        // is a meeting, not a chat window.
        expect(
            resolveStageProfile({ inChatWindow: true, isFullscreen: true, isActiveCall: true })
                .stage
        ).toBe(STAGE.MEETING);
    });

    test("being fullscreen on one call does not make another call's view a meeting", () => {
        // `isFullscreen` is global while `isActiveCall` is per channel, so a second channel's view
        // sees both. It gets none of the meeting's layout policy.
        const other = resolveStageProfile({ isFullscreen: true, isActiveCall: false });
        expect(other.stage).toBe(STAGE.DISCUSS);
        expect(other.hasSidebar).toBe(false);
        expect(other.allowsSelfInset).toBe(false);
        expect(other.maxMainSpeakers).toBe(1);
        expect(
            resolveStageProfile({
                isFullscreen: true,
                isActiveCall: false,
                participantCount: 4,
                userLayout: CALL_GRID_LAYOUT.AUTO,
            }).capColumnsAtThree
        ).toBe(false);
        expect(
            resolveStageProfile({
                isFullscreen: true,
                isActiveCall: false,
                userLayout: CALL_GRID_LAYOUT.TILED,
                prefersVideoTiles: true,
            }).dropsVideolessTiles
        ).toBe(false);
    });
});

describe("meeting stage", () => {
    test("it is the only stage running the sidebar, the self inset and a shared spotlight", () => {
        expect(
            resolveStageProfile({ isFullscreen: true, isActiveCall: true, isPresenting: true })
                .hasSidebar
        ).toBe(true);
        // Self is an inset only in a two-person spotlight.
        const meeting = {
            isFullscreen: true,
            isActiveCall: true,
            userLayout: CALL_GRID_LAYOUT.AUTO,
        };
        expect(resolveStageProfile({ ...meeting, participantCount: 2 }).allowsSelfInset).toBe(true);
        expect(resolveStageProfile({ ...meeting, participantCount: 3 }).allowsSelfInset).toBe(
            false
        );
        // No other stage gets a sidebar, an inset or a shared spotlight.
        for (const elsewhere of [{}, { inChatWindow: true }]) {
            const profile = resolveStageProfile({ ...elsewhere, isPresenting: true });
            expect(profile.hasSidebar).toBe(false);
            expect(profile.allowsSelfInset).toBe(false);
            expect(profile.maxMainSpeakers).toBe(1);
        }
    });

    test("auto resolves to spotlight, tiled or sidebar from the call itself", () => {
        const auto = {
            isFullscreen: true,
            isActiveCall: true,
            userLayout: CALL_GRID_LAYOUT.AUTO,
        };
        expect(resolveStageProfile({ ...auto, participantCount: 2 }).layout).toBe(
            CALL_GRID_LAYOUT.SPOTLIGHT
        );
        expect(resolveStageProfile({ ...auto, participantCount: 3 }).layout).toBe(
            CALL_GRID_LAYOUT.TILED
        );
        // A shared screen wins over the participant count, whatever it is.
        expect(
            resolveStageProfile({ ...auto, participantCount: 9, isPresenting: true }).layout
        ).toBe(CALL_GRID_LAYOUT.SIDEBAR);
    });

    test("an explicit layout choice outranks the auto heuristic", () => {
        expect(
            resolveStageProfile({
                isFullscreen: true,
                isActiveCall: true,
                userLayout: CALL_GRID_LAYOUT.SPOTLIGHT,
                participantCount: 9,
                isPresenting: true,
            }).layout
        ).toBe(CALL_GRID_LAYOUT.SPOTLIGHT);
        // The 3-column cap is an "auto" comfort, not something an explicit grid wants.
        const tiled = {
            isFullscreen: true,
            isActiveCall: true,
            participantCount: 4,
            userLayout: CALL_GRID_LAYOUT.TILED,
        };
        expect(resolveStageProfile(tiled).layout).toBe(CALL_GRID_LAYOUT.TILED);
        expect(resolveStageProfile(tiled).capColumnsAtThree).toBe(false);
    });

    test("only an explicit tiled grid drops the tiles without video", () => {
        const tiled = {
            isFullscreen: true,
            isActiveCall: true,
            userLayout: CALL_GRID_LAYOUT.TILED,
        };
        expect(resolveStageProfile({ ...tiled, prefersVideoTiles: true }).dropsVideolessTiles).toBe(
            true
        );
        expect(
            resolveStageProfile({ ...tiled, prefersVideoTiles: false }).dropsVideolessTiles
        ).toBe(false);
        // "Auto" that happens to tile never hides anyone.
        expect(
            resolveStageProfile({
                isFullscreen: true,
                isActiveCall: true,
                participantCount: 4,
                userLayout: CALL_GRID_LAYOUT.AUTO,
                prefersVideoTiles: true,
            }).dropsVideolessTiles
        ).toBe(false);
    });

    test("only an unclaimed spotlight splits its stage between recent speakers", () => {
        const spotlight = {
            isFullscreen: true,
            isActiveCall: true,
            userLayout: CALL_GRID_LAYOUT.SPOTLIGHT,
        };
        expect(resolveStageProfile(spotlight).maxMainSpeakers).toBe(4);
        // The sidebar keeps one main window and sorts the speakers to the top of its column.
        expect(
            resolveStageProfile({
                isFullscreen: true,
                isActiveCall: true,
                userLayout: CALL_GRID_LAYOUT.SIDEBAR,
            }).maxMainSpeakers
        ).toBe(1);
        // A shared screen and a manual pin both mean "this session, whole".
        expect(resolveStageProfile({ ...spotlight, isPresenting: true }).maxMainSpeakers).toBe(1);
        expect(resolveStageProfile({ ...spotlight, isPinned: true }).maxMainSpeakers).toBe(1);
    });
});

describe("chat window stage", () => {
    test("it grows with its cards and stops after a handful of them", () => {
        const chatWindow = resolveStageProfile({ inChatWindow: true, hasFocus: true });
        expect(chatWindow.maxCards).toBe(6);
        expect(chatWindow.autoHeight).toBe(true);
        expect(chatWindow.fillMainWidth).toBe(true);
        // Discuss is a plain grid filling the space its container gives it.
        const inDiscuss = resolveStageProfile({ hasFocus: true });
        expect(inDiscuss.maxCards).toBe(Infinity);
        expect(inDiscuss.autoHeight).toBe(false);
        expect(inDiscuss.fillMainWidth).toBe(false);
    });

    test("it keeps its inset clear of the floating call controls", () => {
        expect(resolveStageProfile({ inChatWindow: true }).insetBottomMargin).toBe(40);
        // Everywhere else the inset sits at the regular margin from the tile edge.
        expect(
            resolveStageProfile({ isFullscreen: true, isActiveCall: true }).insetBottomMargin
        ).toBe(8);
    });

    test("a touch chat window has a height of its own", () => {
        // It is full-screen there, so it must fill its container instead of growing with its cards.
        const chatWindow = { inChatWindow: true, hasFocus: true };
        expect(resolveStageProfile({ ...chatWindow, isTouch: false }).autoHeight).toBe(true);
        expect(resolveStageProfile({ ...chatWindow, isTouch: true }).autoHeight).toBe(false);
    });

    test("a call with nothing to show big collapses to a strip", () => {
        // In your own call, with nobody's video and nobody spotlighted, there is nothing to show
        // big. `isActiveCall` matters here: a call you are not in is a strip whatever it shows.
        const idle = { isActiveCall: true, hasVideo: false };
        expect(resolveStageProfile(idle).minimized).toBe(true);
        // Anything worth a big tile expands it again.
        expect(resolveStageProfile({ ...idle, hasVideo: true }).minimized).toBe(false);
        expect(resolveStageProfile({ ...idle, hasFocus: true }).minimized).toBe(false);
        expect(resolveStageProfile({ ...idle, isFullscreen: true }).minimized).toBe(false);
        // A chat window stays a strip even with video: only a spotlight earns a real stage there.
        const chatWindow = { isActiveCall: true, inChatWindow: true, hasVideo: true };
        expect(resolveStageProfile(chatWindow).minimized).toBe(true);
        expect(resolveStageProfile(chatWindow).autoHeight).toBe(false);
        expect(resolveStageProfile({ ...chatWindow, hasFocus: true }).minimized).toBe(false);
        expect(resolveStageProfile({ ...chatWindow, hasFocus: true }).autoHeight).toBe(true);
    });
});

describe("mobile stage", () => {
    test("a phone is its own stage, whatever it renders inside", () => {
        for (const inside of [{}, { inChatWindow: true }]) {
            expect(resolveStageProfile({ isSmallScreen: true, ...inside }).stage).toBe(
                STAGE.MOBILE
            );
        }
        expect(
            resolveStageProfile({ isSmallScreen: true, isFullscreen: true, isActiveCall: true })
                .stage
        ).toBe(STAGE.MOBILE);
    });

    test("it only ever renders a handful of cards", () => {
        // Every card past the cap is a video stream downloaded to fill a hundred pixels.
        expect(resolveStageProfile({ participantCount: 9 }).maxCards).toBe(Infinity);
        expect(resolveStageProfile({ isSmallScreen: true, participantCount: 9 }).maxCards).toBe(6);
    });

    test("it spotlights where a roomy screen would already tile", () => {
        const onPhone = {
            isSmallScreen: true,
            isFullscreen: true,
            isActiveCall: true,
            userLayout: CALL_GRID_LAYOUT.AUTO,
        };
        expect(resolveStageProfile({ ...onPhone, participantCount: 4 }).layout).toBe(
            CALL_GRID_LAYOUT.SPOTLIGHT
        );
        expect(resolveStageProfile({ ...onPhone, participantCount: 5 }).layout).toBe(
            CALL_GRID_LAYOUT.TILED
        );
        // An explicit choice still outranks the heuristic, phone or not.
        expect(
            resolveStageProfile({
                ...onPhone,
                participantCount: 4,
                userLayout: CALL_GRID_LAYOUT.TILED,
            }).layout
        ).toBe(CALL_GRID_LAYOUT.TILED);
    });

    test("it splits its spotlight between two speakers, not four", () => {
        // Otherwise the wider tiling threshold above would just move the same tiny tiles into the
        // spotlight: four ways across a phone is the thing worth avoiding, not the layout name.
        const spotlight = {
            isFullscreen: true,
            isActiveCall: true,
            userLayout: CALL_GRID_LAYOUT.SPOTLIGHT,
        };
        expect(resolveStageProfile({ ...spotlight, isSmallScreen: true }).maxMainSpeakers).toBe(2);
        expect(resolveStageProfile(spotlight).maxMainSpeakers).toBe(4);
    });

    test("it never caps its grid at three columns", () => {
        // Three columns across a phone is three columns of nothing, whatever the participant count.
        const onPhone = {
            isSmallScreen: true,
            isFullscreen: true,
            isActiveCall: true,
            participantCount: 9,
            userLayout: CALL_GRID_LAYOUT.AUTO,
        };
        expect(resolveStageProfile(onPhone).layout).toBe(CALL_GRID_LAYOUT.TILED);
        expect(resolveStageProfile(onPhone).capColumnsAtThree).toBe(false);
    });

    test("the focused card fills the phone rather than the width alone", () => {
        // `fillMainWidth` switches the engine's portrait branch off, which a phone needs: sized
        // from the width, its card would cover a quarter of the screen and the rest stay black.
        const onPhone = resolveStageProfile({ isSmallScreen: true, hasFocus: true });
        expect(onPhone.fillMainWidth).toBe(false);
        expect(resolveStageProfile({ inChatWindow: true, hasFocus: true }).fillMainWidth).toBe(
            true
        );
        // The call controls span the bottom of every phone call view, focus or not.
        expect(onPhone.insetBottomMargin).toBe(40);
    });

    test("a phone in the call it is fullscreen on still runs the meeting layouts", () => {
        // The rows mobileStage repeats from meetingStage are the ones pinned here: drift between
        // the two shows up as this test going red.
        const inCall = resolveStageProfile({
            isSmallScreen: true,
            isFullscreen: true,
            isActiveCall: true,
            isPresenting: true,
        });
        expect(inCall.runsMeetingLayouts).toBe(true);
        expect(inCall.hasSidebar).toBe(true);
        expect(
            resolveStageProfile({
                isSmallScreen: true,
                isFullscreen: true,
                isActiveCall: true,
                participantCount: 2,
                userLayout: CALL_GRID_LAYOUT.AUTO,
            }).allowsSelfInset
        ).toBe(true);
    });

    test("a phone that is not in the call gets none of the meeting layouts", () => {
        const beside = resolveStageProfile({ isSmallScreen: true, inChatWindow: true });
        expect(beside.runsMeetingLayouts).toBe(false);
        expect(beside.hasSidebar).toBe(false);
        expect(beside.allowsSelfInset).toBe(false);
        expect(beside.maxMainSpeakers).toBe(1);
    });
});

describe("what the stages answer alike", () => {
    test("every stage fills in the whole profile", () => {
        // The stages are spread over a shared base, so a key only one of them sets would read as
        // `undefined` at the call site rather than fail here. Adding a row to StageProfile is
        // meant to fail this until every stage has an answer for it.
        for (const facts of [
            { isFullscreen: true, isActiveCall: true },
            { inChatWindow: true },
            { isPip: true },
            {},
            { isSmallScreen: true },
        ]) {
            expect(Object.keys(resolveStageProfile(facts)).sort()).toEqual([
                "allowsSelfInset",
                "aspectRatio",
                "autoHeight",
                "capColumnsAtThree",
                "dropsVideolessTiles",
                "fillMainWidth",
                "hasSidebar",
                "insetBottomMargin",
                "isFullSize",
                "layout",
                "maxCards",
                "maxMainSpeakers",
                "minimized",
                "runsMeetingLayouts",
                "stage",
            ]);
        }
    });

    test("an invitation grid uses square avatar tiles", () => {
        expect(resolveStageProfile({ isActiveCall: false }).aspectRatio).toBe(1);
        expect(resolveStageProfile({ isActiveCall: true }).aspectRatio).toBe(16 / 9);
    });

    test("a meeting and a picture-in-picture take a whole window, the others do not", () => {
        expect(resolveStageProfile({ isFullscreen: true, isActiveCall: true }).isFullSize).toBe(
            true
        );
        expect(resolveStageProfile({ isPip: true }).isFullSize).toBe(true);
        expect(resolveStageProfile({}).isFullSize).toBe(false);
        expect(resolveStageProfile({ inChatWindow: true }).isFullSize).toBe(false);
    });
});
