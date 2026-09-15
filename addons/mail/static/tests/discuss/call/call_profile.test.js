import {
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Call } from "@mail/discuss/call/common/call";
import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import { CALL_PROFILE_TYPE } from "@mail/discuss/call/common/call_profile";
import { INSET_MARGIN } from "@mail/discuss/call/common/stage/layout_engine";

import { beforeEach, describe, expect, mockUserAgent, test } from "@odoo/hoot";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";

/**
 * What each profile type answers, read off real `Call` components: a profile is an extension of
 * `call.js`, so the facts it runs on come from a mounted call, a joined RTC session and the store,
 * never from a hand-made object standing in for one.
 */

describe.current.tags("desktop");
defineMailModels();
beforeEach(() => mockGetMedia());

/**
 * A channel with `remotes` remote participants, opened in Discuss with its call joined — so the
 * call view Discuss renders is a real one, and `self` is in it.
 *
 * `video` and `presenting` are how many of those participants have their camera, respectively
 * their screen, on. `otherChannel` adds a second channel with a call of its own that self never
 * joins: what a call view of someone else's call reads.
 *
 * @param {Object} [options]
 * @param {number} [options.remotes=1]
 * @param {number} [options.video=0]
 * @param {number} [options.presenting=0]
 * @param {string} [options.layout] the {@link CALL_GRID_LAYOUT} the user picked
 * @param {boolean} [options.showOnlyVideo] the "Prioritize tiles with video" setting
 * @param {boolean} [options.smallScreen] render on a phone-sized screen
 * @param {boolean} [options.touch] render on a touch device
 * @param {number} [options.otherChannel] participants of a second, unjoined call
 */
async function joinCall({
    remotes = 1,
    video = 0,
    presenting = 0,
    layout = CALL_GRID_LAYOUT.AUTO,
    showOnlyVideo = false,
    smallScreen = false,
    touch = false,
    otherChannel = 0,
} = {}) {
    const pyEnv = await startServer();
    // `create` makes self a member of the channel, hence its presence in the sidebar.
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const addSessions = (id, count, { withVideo = 0, withScreen = 0 } = {}) => {
        for (let i = 0; i < count; i++) {
            pyEnv["discuss.channel.rtc.session"].create({
                channel_id: id,
                channel_member_id: pyEnv["discuss.channel.member"].create({
                    channel_id: id,
                    partner_id: pyEnv["res.partner"].create({ name: `Remote ${id}-${i + 1}` }),
                }),
                is_camera_on: i < withVideo,
                is_screen_sharing_on: i < withScreen,
            });
        }
    };
    addSessions(channelId, remotes, { withVideo: video, withScreen: presenting });
    let otherChannelId;
    if (otherChannel) {
        // Self is a member of it too, but never joins its call.
        otherChannelId = pyEnv["discuss.channel"].create({ name: "Elsewhere" });
        addSessions(otherChannelId, otherChannel);
    }
    if (smallScreen) {
        patchUiSize({ size: SIZES.SM });
    }
    if (touch) {
        mockUserAgent("android");
    }
    const env = await start();
    const store = getService("mail.store");
    store.settings.callLayout = layout;
    store.settings.showOnlyVideo = showOnlyVideo;
    await openDiscuss(channelId);
    const channel = await store["discuss.channel"].getOrFetch(channelId);
    // What the "Join Call" button of the channel does. Joining gives self a session too, so
    // `participantCount` is remotes + 1.
    await store.rtc.toggleCall(channel);
    await contains(".o-discuss-Call");
    let other;
    if (otherChannelId) {
        other = await store["discuss.channel"].getOrFetch(otherChannelId);
    }
    return { channel, env, other, pyEnv, rtc: store.rtc, store };
}

/**
 * A real `Call` for `channel`, mounted with the props of the container under test: none for the
 * Discuss app, `compact` for a chat window, `isPip` for a picture-in-picture window (see the
 * `<Call/>` of each container's template).
 *
 * @param {Object} env
 * @param {Object} props
 */
function mountCall(env, props) {
    return mountWithCleanup(Call, { env, props });
}

/** Fullscreen is global to the client: the flag the fullscreen transition sets. */
function enterFullscreen(rtc) {
    rtc.isFullscreen = true;
}

describe("which of the five types a call lands on", () => {
    test("where the call renders and whether it is yours decide the type", async () => {
        const { channel, env, rtc } = await joinCall();
        const inDiscuss = await mountCall(env, { channel });
        const inChatWindow = await mountCall(env, { channel, compact: true });
        const inPip = await mountCall(env, { isPip: true });
        // A picture-in-picture window is `compact` too; it is the window it lives in.
        const inCompactPip = await mountCall(env, { channel, compact: true, isPip: true });
        expect(inDiscuss.profile.type).toBe(CALL_PROFILE_TYPE.DISCUSS);
        expect(inChatWindow.profile.type).toBe(CALL_PROFILE_TYPE.CHAT_WINDOW);
        expect(inPip.profile.type).toBe(CALL_PROFILE_TYPE.PIP);
        expect(inCompactPip.profile.type).toBe(CALL_PROFILE_TYPE.PIP);
        // Fullscreen outranks the container it started from: a chat window you went fullscreen in
        // is a meeting, not a chat window.
        enterFullscreen(rtc);
        expect(inDiscuss.profile.type).toBe(CALL_PROFILE_TYPE.MEETING);
        expect(inChatWindow.profile.type).toBe(CALL_PROFILE_TYPE.MEETING);
    });

    test("being fullscreen on one call does not make another call's view a meeting", async () => {
        // Fullscreen is global while the joined call is not, so a second channel's view sees both.
        // It gets none of the meeting's layout policy.
        const { env, other, rtc, store } = await joinCall({ otherChannel: 3 });
        enterFullscreen(rtc);
        const elsewhere = await mountCall(env, { channel: other });
        expect(elsewhere.profile.type).toBe(CALL_PROFILE_TYPE.DISCUSS);
        expect(elsewhere.profile.hasSidebar).toBe(false);
        expect(elsewhere.profile.allowsSelfInset).toBe(false);
        expect(elsewhere.profile.maxMainSpeakers).toBe(1);
        expect(elsewhere.profile.capColumnsAtThree).toBe(false);
        store.settings.callLayout = CALL_GRID_LAYOUT.TILED;
        store.settings.showOnlyVideo = true;
        expect(elsewhere.profile.dropsVideolessTiles).toBe(false);
    });
});

describe("meeting profile", () => {
    test("a shared screen gives the meeting its sidebar, nowhere else", async () => {
        const { channel, env, rtc } = await joinCall({ remotes: 1, presenting: 1 });
        const inDiscuss = await mountCall(env, { channel });
        const inChatWindow = await mountCall(env, { channel, compact: true });
        // No other type gets a sidebar, an inset or a shared spotlight.
        expect(inDiscuss.profile.hasSidebar).toBe(false);
        expect(inDiscuss.profile.allowsSelfInset).toBe(false);
        expect(inDiscuss.profile.maxMainSpeakers).toBe(1);
        expect(inChatWindow.profile.hasSidebar).toBe(false);
        expect(inChatWindow.profile.allowsSelfInset).toBe(false);
        expect(inChatWindow.profile.maxMainSpeakers).toBe(1);
        enterFullscreen(rtc);
        expect(inDiscuss.profile.hasSidebar).toBe(true);
    });

    test("self is an inset only in a two-person spotlight", async () => {
        const { channel, env, rtc } = await joinCall({ remotes: 1 });
        enterFullscreen(rtc);
        const meeting = await mountCall(env, { channel });
        expect(meeting.profile.layout).toBe(CALL_GRID_LAYOUT.SPOTLIGHT);
        expect(meeting.profile.allowsSelfInset).toBe(true);
    });

    test("a third participant takes self out of the inset", async () => {
        const { channel, env, rtc } = await joinCall({ remotes: 2 });
        enterFullscreen(rtc);
        const meeting = await mountCall(env, { channel });
        expect(meeting.profile.allowsSelfInset).toBe(false);
    });

    test("auto spotlights a call of two", async () => {
        const { channel, env, rtc } = await joinCall({ remotes: 1 });
        enterFullscreen(rtc);
        expect((await mountCall(env, { channel })).profile.layout).toBe(CALL_GRID_LAYOUT.SPOTLIGHT);
    });

    test("auto tiles from the third participant on", async () => {
        const { channel, env, rtc } = await joinCall({ remotes: 2 });
        enterFullscreen(rtc);
        expect((await mountCall(env, { channel })).profile.layout).toBe(CALL_GRID_LAYOUT.TILED);
    });

    test("a shared screen wins over the participant count, and an explicit choice over both", async () => {
        const { channel, env, rtc, store } = await joinCall({ remotes: 8, presenting: 1 });
        enterFullscreen(rtc);
        const meeting = await mountCall(env, { channel });
        expect(meeting.profile.layout).toBe(CALL_GRID_LAYOUT.SIDEBAR);
        store.settings.callLayout = CALL_GRID_LAYOUT.SPOTLIGHT;
        expect(meeting.profile.layout).toBe(CALL_GRID_LAYOUT.SPOTLIGHT);
    });

    test("the 3-column cap is an auto comfort, not something an explicit grid wants", async () => {
        const { channel, env, rtc, store } = await joinCall({ remotes: 3 });
        enterFullscreen(rtc);
        const meeting = await mountCall(env, { channel });
        expect(meeting.profile.layout).toBe(CALL_GRID_LAYOUT.TILED);
        expect(meeting.profile.capColumnsAtThree).toBe(true);
        store.settings.callLayout = CALL_GRID_LAYOUT.TILED;
        expect(meeting.profile.layout).toBe(CALL_GRID_LAYOUT.TILED);
        expect(meeting.profile.capColumnsAtThree).toBe(false);
    });

    test("only an explicit tiled grid drops the tiles without video", async () => {
        const { channel, env, rtc, store } = await joinCall({
            remotes: 3,
            layout: CALL_GRID_LAYOUT.TILED,
            showOnlyVideo: true,
        });
        enterFullscreen(rtc);
        const meeting = await mountCall(env, { channel });
        expect(meeting.profile.dropsVideolessTiles).toBe(true);
        store.settings.showOnlyVideo = false;
        expect(meeting.profile.dropsVideolessTiles).toBe(false);
        // "Auto" that happens to tile never hides anyone.
        store.settings.showOnlyVideo = true;
        store.settings.callLayout = CALL_GRID_LAYOUT.AUTO;
        expect(meeting.profile.layout).toBe(CALL_GRID_LAYOUT.TILED);
        expect(meeting.profile.dropsVideolessTiles).toBe(false);
    });

    test("only an unclaimed spotlight splits its stage between recent speakers", async () => {
        const { channel, env, rtc, store } = await joinCall({
            remotes: 3,
            layout: CALL_GRID_LAYOUT.SPOTLIGHT,
        });
        enterFullscreen(rtc);
        const meeting = await mountCall(env, { channel });
        expect(meeting.profile.maxMainSpeakers).toBe(4);
        // The sidebar keeps one main window and sorts the speakers to the top of its column.
        store.settings.callLayout = CALL_GRID_LAYOUT.SIDEBAR;
        expect(meeting.profile.maxMainSpeakers).toBe(1);
        // A manual pin and a shared screen both mean "this session, whole".
        store.settings.callLayout = CALL_GRID_LAYOUT.SPOTLIGHT;
        const [session] = channel.rtc_session_ids;
        channel.pinnedRtcSession = session;
        expect(meeting.profile.maxMainSpeakers).toBe(1);
        channel.pinnedRtcSession = undefined;
        session.is_screen_sharing_on = true;
        expect(meeting.profile.maxMainSpeakers).toBe(1);
    });
});

describe("chat window profile", () => {
    test("it grows with its cards and stops after a handful of them", async () => {
        const { channel, env } = await joinCall({ remotes: 1 });
        channel.activeRtcSession = channel.rtc_session_ids[0];
        const inChatWindow = await mountCall(env, { channel, compact: true });
        expect(inChatWindow.profile.maxCards).toBe(6);
        expect(inChatWindow.profile.autoHeight).toBe(true);
        expect(inChatWindow.profile.fillMainWidth).toBe(true);
        // Discuss is a plain grid filling the space its container gives it.
        const inDiscuss = await mountCall(env, { channel });
        expect(inDiscuss.profile.maxCards).toBe(Infinity);
        expect(inDiscuss.profile.autoHeight).toBe(false);
        expect(inDiscuss.profile.fillMainWidth).toBe(false);
    });

    test("it keeps its inset clear of the floating call controls", async () => {
        const { channel, env, rtc } = await joinCall();
        expect((await mountCall(env, { channel, compact: true })).profile.insetBottomMargin).toBe(
            40
        );
        // Everywhere else the inset sits at the regular margin from the tile edge.
        enterFullscreen(rtc);
        expect((await mountCall(env, { channel })).profile.insetBottomMargin).toBe(INSET_MARGIN);
    });

    test("a chat window with a height of its own fills it instead of growing", async () => {
        // A touch chat window is full-screen there, so it must fill its container.
        const { channel, env } = await joinCall({ touch: true });
        channel.activeRtcSession = channel.rtc_session_ids[0];
        const inChatWindow = await mountCall(env, { channel, compact: true });
        expect(inChatWindow.profile.type).toBe(CALL_PROFILE_TYPE.CHAT_WINDOW);
        expect(inChatWindow.profile.autoHeight).toBe(false);
    });

    test("a call with nothing to show big collapses to a strip", async () => {
        // In your own call, with nobody's video and nobody spotlighted, there is nothing to show
        // big. Being in the call matters here: a call you are not in is a strip whatever it shows.
        const { channel, env, other, rtc } = await joinCall({ otherChannel: 2 });
        const inDiscuss = await mountCall(env, { channel });
        expect(inDiscuss.profile.minimized).toBe(true);
        expect((await mountCall(env, { channel: other })).profile.minimized).toBe(true);
        // Anything worth a big tile expands it again.
        const [session] = channel.rtc_session_ids;
        session.is_camera_on = true;
        expect(inDiscuss.profile.minimized).toBe(false);
        session.is_camera_on = false;
        channel.activeRtcSession = session;
        expect(inDiscuss.profile.minimized).toBe(false);
        channel.activeRtcSession = undefined;
        enterFullscreen(rtc);
        expect(inDiscuss.profile.minimized).toBe(false);
    });

    test("a chat window stays a strip even with video: only a spotlight earns a stage there", async () => {
        const { channel, env } = await joinCall({ remotes: 1, video: 1 });
        const inChatWindow = await mountCall(env, { channel, compact: true });
        expect(inChatWindow.profile.minimized).toBe(true);
        expect(inChatWindow.profile.autoHeight).toBe(false);
        channel.activeRtcSession = channel.rtc_session_ids[0];
        expect(inChatWindow.profile.minimized).toBe(false);
        expect(inChatWindow.profile.autoHeight).toBe(true);
    });
});

describe("mobile profile", () => {
    test("a phone is its own type, whatever it renders inside", async () => {
        const { channel, env, rtc } = await joinCall({ smallScreen: true });
        expect((await mountCall(env, { channel })).profile.type).toBe(CALL_PROFILE_TYPE.MOBILE);
        expect((await mountCall(env, { channel, compact: true })).profile.type).toBe(
            CALL_PROFILE_TYPE.MOBILE
        );
        enterFullscreen(rtc);
        expect((await mountCall(env, { channel })).profile.type).toBe(CALL_PROFILE_TYPE.MOBILE);
    });

    test("it only ever renders a handful of cards", async () => {
        // Every card past the cap is a video stream downloaded to fill a hundred pixels.
        const { channel, env } = await joinCall({ remotes: 8, smallScreen: true });
        expect((await mountCall(env, { channel })).profile.maxCards).toBe(6);
    });

    test("a roomy screen renders every card of the same call", async () => {
        const { channel, env } = await joinCall({ remotes: 8 });
        expect((await mountCall(env, { channel })).profile.maxCards).toBe(Infinity);
    });

    test("it spotlights where a roomy screen would already tile", async () => {
        const { channel, env, rtc, store } = await joinCall({ remotes: 3, smallScreen: true });
        enterFullscreen(rtc);
        const onPhone = await mountCall(env, { channel });
        expect(onPhone.profile.layout).toBe(CALL_GRID_LAYOUT.SPOTLIGHT);
        // An explicit choice still outranks the heuristic, phone or not.
        store.settings.callLayout = CALL_GRID_LAYOUT.TILED;
        expect(onPhone.profile.layout).toBe(CALL_GRID_LAYOUT.TILED);
    });

    test("it tiles from the fifth participant on, and never at three columns", async () => {
        // Three columns across a phone is three columns of nothing, whatever the count.
        const { channel, env, rtc } = await joinCall({ remotes: 4, smallScreen: true });
        enterFullscreen(rtc);
        const onPhone = await mountCall(env, { channel });
        expect(onPhone.profile.layout).toBe(CALL_GRID_LAYOUT.TILED);
        expect(onPhone.profile.capColumnsAtThree).toBe(false);
    });

    test("it splits its spotlight between two speakers, not four", async () => {
        // Otherwise the wider tiling threshold above would just move the same tiny tiles into the
        // spotlight: four ways across a phone is the thing worth avoiding, not the layout name.
        const { channel, env, rtc } = await joinCall({
            remotes: 3,
            layout: CALL_GRID_LAYOUT.SPOTLIGHT,
            smallScreen: true,
        });
        enterFullscreen(rtc);
        expect((await mountCall(env, { channel })).profile.maxMainSpeakers).toBe(2);
    });

    test("the focused card fills the phone rather than the width alone", async () => {
        // `fillMainWidth` switches the engine's portrait branch off, which a phone needs: sized
        // from the width, its card would cover a quarter of the screen and the rest stay black.
        const { channel, env } = await joinCall({ smallScreen: true });
        channel.activeRtcSession = channel.rtc_session_ids[0];
        const onPhone = await mountCall(env, { channel });
        expect(onPhone.profile.fillMainWidth).toBe(false);
        // The call controls span the bottom of every phone call view, focus or not.
        expect(onPhone.profile.insetBottomMargin).toBe(40);
    });

    test("a phone in the call it is fullscreen on still runs the meeting layouts", async () => {
        // The rows the mobile case repeats from the meeting one are pinned here: drift between the
        // two shows up as this test going red.
        const { channel, env, rtc } = await joinCall({
            remotes: 1,
            presenting: 1,
            smallScreen: true,
        });
        enterFullscreen(rtc);
        const onPhone = await mountCall(env, { channel });
        expect(onPhone.profile.runsMeetingLayouts).toBe(true);
        expect(onPhone.profile.hasSidebar).toBe(true);
    });

    test("a phone keeps self as an inset in a two-person spotlight", async () => {
        const { channel, env, rtc } = await joinCall({ remotes: 1, smallScreen: true });
        enterFullscreen(rtc);
        expect((await mountCall(env, { channel })).profile.allowsSelfInset).toBe(true);
    });

    test("a phone that is not in the call gets none of the meeting layouts", async () => {
        const { env, other, rtc } = await joinCall({ smallScreen: true, otherChannel: 2 });
        enterFullscreen(rtc);
        const beside = await mountCall(env, { channel: other });
        expect(beside.profile.type).toBe(CALL_PROFILE_TYPE.MOBILE);
        expect(beside.profile.runsMeetingLayouts).toBe(false);
        expect(beside.profile.hasSidebar).toBe(false);
        expect(beside.profile.allowsSelfInset).toBe(false);
        expect(beside.profile.maxMainSpeakers).toBe(1);
    });
});

describe("what the types answer alike", () => {
    test("every type fills in the whole profile", async () => {
        // Every row is a field of CallProfile, so a case that forgets one leaves the default
        // rather than an `undefined` at the call site. Adding a row is meant to fail this until
        // it is listed here.
        const { channel, env, rtc } = await joinCall();
        const profiles = [
            (await mountCall(env, { channel })).profile,
            (await mountCall(env, { channel, compact: true })).profile,
            (await mountCall(env, { isPip: true })).profile,
        ];
        enterFullscreen(rtc);
        profiles.push((await mountCall(env, { channel })).profile);
        for (const profile of profiles) {
            expect(Object.keys(profile).sort()).toEqual([
                "allowsSelfInset",
                "aspectRatio",
                "autoHeight",
                "capColumnsAtThree",
                "dropsVideolessTiles",
                "fillMainWidth",
                "hasSidebar",
                "insetBottomMargin",
                "layout",
                "maxCards",
                "maxMainSpeakers",
                "minimized",
                "runsMeetingLayouts",
                "type",
            ]);
        }
    });

    test("a phone fills in the whole profile too", async () => {
        const { channel, env } = await joinCall({ smallScreen: true });
        expect(Object.keys((await mountCall(env, { channel })).profile).sort()).toHaveLength(14);
    });

    test("the call you are in gets video tiles, the one you are not gets avatars", async () => {
        const { channel, env, other } = await joinCall({ otherChannel: 2 });
        expect((await mountCall(env, { channel })).profile.aspectRatio).toBe(16 / 9);
        expect((await mountCall(env, { channel: other })).profile.aspectRatio).toBe(1);
    });
});
