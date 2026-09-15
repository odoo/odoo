import {
    click,
    contains,
    createVideoStream,
    defineMailModels,
    makeMockRtcNetwork,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";

import { SPEAKER_WINDOW } from "@mail/discuss/call/common/discuss_channel_model_patch";

import { advanceTime, beforeEach, describe, disableAnimations, expect, test } from "@odoo/hoot";
import {
    advanceFrame,
    animationFrame,
    drag,
    freezeTime,
    hover,
    queryAll,
    queryFirst,
    resize,
} from "@odoo/hoot-dom";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Call } from "@mail/discuss/call/common/call";
import { INSET_MARGIN } from "@mail/discuss/call/common/stage/layout_engine";

/**
 * A visible participant must keep the exact same video element across every layout change
 * (pin/unpin, layout switch, sidebar focus swap, reorder, resize).
 */

/**
 * The stage every test below measures against. Cards are laid out from the measured box, so the
 * assertions on their geometry only mean something at a known size: left to the runner's window,
 * a short viewport makes the 16:9 main card fill the width and the stage-versus-card assertions
 * flip. Landscape and roomy, like the desktop this view is for.
 */
const STAGE_SIZE = { width: 1280, height: 720 };

describe.current.tags("desktop");
defineMailModels();
beforeEach(async () => {
    mockGetMedia();
    // Mocked frames do not drive the Web Animations API: a measured card would be mid-flight.
    disableAnimations();
    await resize(STAGE_SIZE);
});

/**
 * Setup a channel with `names` remote participants (no media yet) and join its call.
 *
 * @param {string[]} names
 * @param {"tiled"|"spotlight"|"sidebar"|"auto"} [layout="auto"]
 */
async function openMeetingWithParticipants(names, layout = "auto") {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const memberIds = {};
    for (const name of names) {
        memberIds[name] = pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name }),
        });
    }
    const env = await start();
    const store = getService("mail.store");
    store.settings.callLayout = layout;
    const network = await makeMockRtcNetwork({ env, channelId });
    const remotes = {};
    for (const name of names) {
        remotes[name] = network.makeMockRemote(memberIds[name]);
    }
    await openDiscuss(channelId);
    await click("[title='Join Call']");
    await contains(".o-discuss-Call");
    for (const name of names) {
        await remotes[name].updateConnectionState("connected");
    }
    return { pyEnv, channelId, network, remotes };
}

test("pinning then unpinning a participant keeps every video element", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"]);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    const aliceVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']"
    );
    const bobVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']"
    );
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);
    expect(bobVideo).toBeInstanceOf(HTMLVideoElement);

    // Pinning Alice switches to the sidebar layout. The options button is scoped to the card, as
    // the one the pointer just left still renders its own for a frame.
    await hover(".o-discuss-CallParticipantCard[aria-label='Alice']");
    await click(".o-discuss-CallParticipantCard[aria-label='Alice'] [title='Participant options']");
    await contains(".o-discuss-CallContextMenu");
    await click(".o-discuss-CallContextMenu button:text('Pin')");
    await contains(".o-discuss-Call-sidebar");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Bob']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Mitchell Admin']");
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']")
    ).toBe(bobVideo);

    // Unpinning does not switch the layout back by itself: the sidebar stays, elements stay.
    await hover(".o-discuss-CallParticipantCard[aria-label='Alice']");
    await click(".o-discuss-CallParticipantCard[aria-label='Alice'] [title='Participant options']");
    await contains(".o-discuss-CallContextMenu");
    await click(".o-discuss-CallContextMenu button:text('Unpin')");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Bob']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Mitchell Admin']");
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']")
    ).toBe(bobVideo);

    // Going back to tiled is a plain layout change: still the same elements.
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Tiled')");
    await contains(".o-discuss-Call-sidebar", { count: 0 });
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Alice']");
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Bob']");
    await contains(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Mitchell Admin']"
    );
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']")
    ).toBe(bobVideo);
});

test("switching focus in the sidebar keeps every video element", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob", "Charlie"], "sidebar");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Charlie.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']");
    // Alice is the auto-focus target, so she takes the main window.
    await contains(".o-discuss-Call-sidebarCard[aria-label='Mitchell Admin']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Bob']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Charlie']");
    const aliceVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']"
    );
    const bobVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']"
    );
    const charlieVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']"
    );
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);
    expect(bobVideo).toBeInstanceOf(HTMLVideoElement);
    expect(charlieVideo).toBeInstanceOf(HTMLVideoElement);

    // Pinning Bob swaps him with Alice between the main window and the sidebar.
    await hover(".o-discuss-CallParticipantCard[aria-label='Bob']");
    await click(".o-discuss-CallParticipantCard[aria-label='Bob'] [title='Participant options']");
    await contains(".o-discuss-CallContextMenu");
    await click(".o-discuss-CallContextMenu button:text('Pin')");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] [title='Pinned']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Mitchell Admin']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Alice']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Charlie']");
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']")
    ).toBe(bobVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']")
    ).toBe(charlieVideo);

    // Unpinning keeps Bob focused. The badge going away is the only visible change, so it is what
    // tells the unpin has rendered.
    await hover(".o-discuss-CallParticipantCard[aria-label='Bob']");
    await click(".o-discuss-CallParticipantCard[aria-label='Bob'] [title='Participant options']");
    await contains(".o-discuss-CallContextMenu");
    await click(".o-discuss-CallContextMenu button:text('Unpin')");
    await contains(".o-discuss-CallParticipantCard [title='Pinned']", { count: 0 });
    await contains(".o-discuss-Call-sidebarCard[aria-label='Mitchell Admin']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Alice']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Charlie']");
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']")
    ).toBe(bobVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']")
    ).toBe(charlieVideo);
});

test("switching between spotlight and tiled keeps the focused video element", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice"]);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    // With 2 participants "auto" resolves to spotlight: Alice is the focus target and self is
    // shown as the bottom-right inset.
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Alice']");
    await contains(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Mitchell Admin']"
    );
    const aliceVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']"
    );
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);

    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Tiled')");
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Alice']");
    await contains(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Mitchell Admin']"
    );
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);

    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Spotlight')");
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Alice']");
    await contains(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Mitchell Admin']"
    );
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
});

test("swapping the main and the inset stream keeps both video elements", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='Share Screen']");
    await contains("video[type='screen']:not(.o-inset)");
    // Focusing the shared screen makes the controller float, i.e. hide until the pointer moves.
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click("[title='Turn camera on']");
    await contains("video[type='screen']:not(.o-inset)");
    await contains("video[type='camera'].o-inset");
    const screenEl = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] video[type='screen']"
    );
    const cameraEl = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] video[type='camera']"
    );
    expect(screenEl).toBeInstanceOf(HTMLVideoElement);
    expect(cameraEl).toBeInstanceOf(HTMLVideoElement);

    // Clicking the inset swaps which stream is main: the screen card goes to the inset and the
    // camera card takes the main window.
    await click("video[type='camera'].o-inset");
    await contains("video[type='screen'].o-inset");
    await contains("video[type='camera']:not(.o-inset)");
    expect(
        queryFirst(
            ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] video[type='screen']"
        )
    ).toBe(screenEl);
    expect(
        queryFirst(
            ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] video[type='camera']"
        )
    ).toBe(cameraEl);
});

test("dragging the inset moves it to the corner it is dropped in", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='Share Screen']");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click("[title='Turn camera on']");
    await contains("video[type='camera'].o-inset");
    const insetEl = queryFirst(".o-discuss-CallParticipantCard.o-inset");
    const mainEl = queryFirst(".o-discuss-CallParticipantCard:has(video[type='screen'])");
    const insetVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] video[type='camera']"
    );

    // The inset rests in a corner of the main card, not of the stage: the stage is wider than the
    // 16:9 card, so the two only agree on this if the layout anchored the inset to the card.
    const mainRect = mainEl.getBoundingClientRect();
    expect(mainRect.width).toBeLessThan(
        queryFirst(".o-discuss-Call-mainCards").getBoundingClientRect().width
    );
    let insetRect = insetEl.getBoundingClientRect();
    expect(mainRect.right - insetRect.right).toBeCloseTo(INSET_MARGIN);
    expect(mainRect.bottom - insetRect.bottom).toBeCloseTo(INSET_MARGIN);

    // Dropped in the top-left half of the stage, it snaps to the top-left corner and stays there.
    const dragged = await drag(insetEl);
    await dragged.moveTo(mainEl, { position: { x: 5, y: 5 }, relative: true });
    await dragged.drop();
    await animationFrame();
    insetRect = insetEl.getBoundingClientRect();
    expect(insetRect.left - mainRect.left).toBeCloseTo(INSET_MARGIN);
    expect(insetRect.top - mainRect.top).toBeCloseTo(INSET_MARGIN);
    // Moving a surface is geometry only: it never goes through a re-render of the card.
    expect(
        queryFirst(
            ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] video[type='camera']"
        )
    ).toBe(insetVideo);
});

test("a participant joining mid-call keeps the video element of everyone else", async () => {
    const { pyEnv, channelId, network, remotes } = await openMeetingWithParticipants([
        "Alice",
        "Bob",
        "Charlie",
    ]);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Charlie.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']");
    const aliceVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']"
    );
    const bobVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']"
    );
    const charlieVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']"
    );
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);

    // "Aaron" sorts first: joining him mid-call shifts everyone in the grid.
    const aaronMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Aaron" }),
    });
    // Creating the session is what tells the client someone joined: the mock server broadcasts
    // the same `rtc_session_ids` insert the real one does.
    const aaronRemote = network.makeMockRemote(aaronMemberId);
    await aaronRemote.updateConnectionState("connected");
    await aaronRemote.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Aaron'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']");
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']")
    ).toBe(bobVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']")
    ).toBe(charlieVideo);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Aaron'] video[type='camera']")
    ).toBeInstanceOf(HTMLVideoElement);
});

test("resize keeps every video element and only changes geometry", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob", "Charlie"]);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Charlie.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']");
    const aliceVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']"
    );
    const aliceCard = queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice']");
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);

    // Narrower than the baseline stage, so the layout really has to move the cards.
    await resize({ width: STAGE_SIZE.width - 280, height: STAGE_SIZE.height });
    await animationFrame();
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']");
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    // The geometry is re-applied through the transform (compositor) without recreating anything.
    expect(aliceCard.style.transform).toInclude("translate3d");
    expect(aliceCard.style.width).not.toBe("");
    expect(aliceCard.style.height).not.toBe("");
});

test("several changes in the same task lay the stage out once", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob", "Charlie"]);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Charlie.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie'] video[type='camera']");
    let computationCount = 0;
    patchWithCleanup(Call.prototype, {
        arrangeTiles() {
            computationCount += 1;
            return super.arrangeTiles();
        },
    });
    // Drain what the setup left pending, then count from zero. One `animationFrame` covers both
    // schedulers: it resolves on a `setTimeout`, so after OWL's render and after the microtask
    // `requestLayout` queued from it.
    await animationFrame();
    computationCount = 0;
    const store = getService("mail.store");
    const channel = store.rtc.channel;
    const aliceSession = channel.rtc_session_ids.find(
        (session) => session.id === remotes.Alice.sessionId
    );
    // Three real triggers (focus/speaker, pin, layout mode) in the same task: OWL renders once
    // and requestLayout coalesces everything into a single computation.
    channel.focusStack.push(aliceSession);
    channel.pinnedRtcSession = aliceSession;
    store.settings.callLayout = "spotlight";
    await animationFrame();
    expect(computationCount).toBe(1);
    // Nothing left pending: no extra computation on the following frames.
    await animationFrame();
    expect(computationCount).toBe(1);
});

test("a card has its place on the very frame it appears", async () => {
    const { pyEnv, channelId, network, remotes } = await openMeetingWithParticipants([
        "Alice",
        "Bob",
    ]);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    const charlieMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Charlie" }),
    });
    const charlieRemote = network.makeMockRemote(charlieMemberId);
    await charlieRemote.updateConnectionState("connected");
    // One frame is all Charlie's card gets: OWL mounts it, and the layout runs on the microtask
    // that mount queues. Deferred to the next frame instead, every card would still be at the
    // origin here — which is what the browser would have painted.
    await animationFrame();
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie']");
    for (const card of queryAll(".o-discuss-CallParticipantCard")) {
        expect(card.style.transform).toInclude("translate3d");
    }
});

test("every card of a tiled grid stays inside the stage", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"]);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    // The layout change renders on this frame and lays out on the microtask that render queues.
    await animationFrame();

    // Every surface must be out of the flow: one left in it takes both the height of its
    // predecessors and its own transform, which pushes the grid diagonally out of the stage.
    const stage = queryFirst(".o-discuss-Call-mainCards").getBoundingClientRect();
    const cards = queryAll(".o-discuss-CallParticipantCard");
    expect(cards.length).toBeGreaterThan(1);
    for (const card of cards) {
        const rect = card.getBoundingClientRect();
        expect(getComputedStyle(card).position).toBe("absolute", {
            message: `tiled: ${card.getAttribute("aria-label")} is positioned by the stage`,
        });
        expect(rect.x).toBeWithin(stage.x, stage.x + stage.width);
        expect(rect.y).toBeWithin(stage.y, stage.y + stage.height);
        expect(rect.x + rect.width).toBeWithin(stage.x, stage.x + stage.width + 1);
        expect(rect.y + rect.height).toBeWithin(stage.y, stage.y + stage.height + 1);
    }
});

test("every card of a sidebar column stays inside the stage", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"], "sidebar");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await remotes.Bob.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']");
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']");
    // Alice is the auto-focus target, so self and Bob line up in the sidebar column.
    await contains(".o-discuss-Call-sidebarCard[aria-label='Mitchell Admin']");
    await contains(".o-discuss-Call-sidebarCard[aria-label='Bob']");
    await animationFrame();

    // A card left in the flow stacks under its predecessors and then applies its transform on top,
    // which walks the column out of the stage.
    const stage = queryFirst(".o-discuss-Call-mainCards").getBoundingClientRect();
    const cards = queryAll(".o-discuss-CallParticipantCard");
    expect(cards.length).toBeGreaterThan(1);
    for (const card of cards) {
        const rect = card.getBoundingClientRect();
        expect(getComputedStyle(card).position).toBe("absolute", {
            message: `sidebar: ${card.getAttribute("aria-label")} is positioned by the stage`,
        });
        expect(rect.x).toBeWithin(stage.x, stage.x + stage.width);
        expect(rect.y).toBeWithin(stage.y, stage.y + stage.height);
        expect(rect.x + rect.width).toBeWithin(stage.x, stage.x + stage.width + 1);
        expect(rect.y + rect.height).toBeWithin(stage.y, stage.y + stage.height + 1);
    }
});

test("recent speakers share the spotlight", async () => {
    // The spotlight holds up to 4 speakers at once, in the order they took the floor, and each of
    // them keeps their place until they have been quiet for SPEAKER_WINDOW.
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve"];
    const { remotes } = await openMeetingWithParticipants(names, "tiled");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    // Start the cameras while the grid still shows everyone: the spotlight renders only whoever
    // holds the stage, so the others would have no card to give a stream to.
    for (const name of names) {
        await remotes[name].updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    }
    for (const name of names) {
        await contains(`.o-discuss-CallParticipantCard[aria-label='${name}'] video[type='camera']`);
    }
    getService("mail.store").settings.callLayout = "spotlight";
    await animationFrame();

    getService("discuss.rtc").updateSessionInfo({
        [remotes.Alice.sessionId]: { isTalking: true },
    });
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice"]);
    const aliceVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']"
    );
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);

    // Bob answering joins Alice on the stage rather than taking it from her: a conversation
    // between the two would otherwise trade the main window on every sentence.
    getService("discuss.rtc").updateSessionInfo({ [remotes.Bob.sessionId]: { isTalking: true } });
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Bob"]);
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='camera']")
    ).toBe(aliceVideo);
    const bobVideo = queryFirst(
        ".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']"
    );

    getService("discuss.rtc").updateSessionInfo({
        [remotes.Charlie.sessionId]: { isTalking: true },
        [remotes.Dave.sessionId]: { isTalking: true },
    });
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Bob", "Charlie", "Dave"]);

    // The stage is full: Eve waits for a place rather than pushing anyone out.
    getService("discuss.rtc").updateSessionInfo({ [remotes.Eve.sessionId]: { isTalking: true } });
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Bob", "Charlie", "Dave"]);

    // The assertions below sit a millisecond either side of SPEAKER_WINDOW, and an unfrozen hoot
    // clock carries the real time the test took, which a loaded machine lapses the window with.
    // Frozen, `requestAnimationFrame` stops firing too, hence the `advanceFrame` calls.
    freezeTime();

    // Alice going quiet does not free her place until her SPEAKER_WINDOW has lapsed.
    getService("discuss.rtc").updateSessionInfo({
        [remotes.Alice.sessionId]: { isTalking: false },
    });
    await advanceFrame(1);
    await advanceTime(SPEAKER_WINDOW - 1);
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Bob", "Charlie", "Dave"]);

    // One millisecond later it has lapsed: she leaves, everyone shifts up and Eve takes her place.
    await advanceTime(1);
    await advanceFrame(1);
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Bob", "Charlie", "Dave", "Eve"]);
    // Bob held the stage from his first word onwards, so all this shifting never rebuilt his card.
    expect(
        queryFirst(".o-discuss-CallParticipantCard[aria-label='Bob'] video[type='camera']")
    ).toBe(bobVideo);
});

for (const layout of ["spotlight", "sidebar"]) {
    test(`a sole recent speaker takes focus in ${layout}`, async () => {
        const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"], layout);
        await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
        await click(".o-discuss-CallActionList button[title='More']");
        await click("[name='fullscreen']");
        await contains(".o-mail-Meeting");
        const channel = getService("discuss.rtc").channel;
        expect(channel.activeRtcSession).toBe(
            channel.rtc_session_ids.find((session) => session.id === remotes.Alice.sessionId)
        );

        getService("discuss.rtc").updateSessionInfo({
            [remotes.Bob.sessionId]: { isTalking: true },
        });
        await animationFrame();
        expect(channel.activeRtcSession).toBe(
            channel.rtc_session_ids.find((session) => session.id === remotes.Bob.sessionId)
        );
        expect(
            queryAll(".o-discuss-CallParticipantCard").sort(
                (a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight
            )[0]
        ).toHaveAttribute("aria-label", "Bob");
    });

    test(`a presenter keeps focus while another participant talks in ${layout}`, async () => {
        const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"], layout);
        await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
        await click(".o-discuss-CallActionList button[title='More']");
        await click("[name='fullscreen']");
        await contains(".o-mail-Meeting");
        await remotes.Alice.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
        await contains("video[type='screen']:not(.o-inset)");
        const video = queryFirst(
            ".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='screen']"
        );

        getService("discuss.rtc").updateSessionInfo({
            [remotes.Bob.sessionId]: { isTalking: true },
        });
        await animationFrame();
        const channel = getService("discuss.rtc").channel;
        expect(channel.activeRtcSession).toBe(
            channel.rtc_session_ids.find((session) => session.id === remotes.Alice.sessionId)
        );
        expect(
            queryAll(".o-discuss-CallParticipantCard").sort(
                (a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight
            )[0]
        ).toHaveAttribute("aria-label", "Alice");
        expect(
            queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice'] video[type='screen']")
        ).toBe(video);
    });
}

test("a split spotlight follows its last remaining speaker", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"], "spotlight");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    getService("discuss.rtc").updateSessionInfo({
        [remotes.Alice.sessionId]: { isTalking: true },
        [remotes.Bob.sessionId]: { isTalking: true },
    });
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Bob"]);

    // Frozen so the SPEAKER_WINDOW boundary below does not depend on how long the test took; a
    // frozen `requestAnimationFrame` then needs the `advanceFrame` calls to fire.
    freezeTime();
    getService("discuss.rtc").updateSessionInfo({
        [remotes.Alice.sessionId]: { isTalking: false },
    });
    await advanceFrame(1);
    await advanceTime(SPEAKER_WINDOW - 1);
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Bob"]);
    await advanceTime(1);
    await advanceFrame(1);
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Bob"]);
    const channel = getService("discuss.rtc").channel;
    expect(channel.activeRtcSession).toBe(
        channel.rtc_session_ids.find((session) => session.id === remotes.Bob.sessionId)
    );

    // Once everyone is quiet, keep the last speaker on stage.
    getService("discuss.rtc").updateSessionInfo({ [remotes.Bob.sessionId]: { isTalking: false } });
    await advanceFrame(1);
    await advanceTime(SPEAKER_WINDOW);
    await advanceFrame(1);
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Bob"]);
});

test("a pinned participant keeps the whole stage until unpinned", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob", "Charlie"], "spotlight");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    // `pin` keeps an explicit spotlight, so this isolates the pin from the sidebar layout.
    await hover(".o-discuss-CallParticipantCard[aria-label='Alice']");
    await click(".o-discuss-CallParticipantCard[aria-label='Alice'] [title='Participant options']");
    await contains(".o-discuss-CallContextMenu");
    await click(".o-discuss-CallContextMenu button:text('Pin')");
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] [title='Pinned']");

    getService("discuss.rtc").updateSessionInfo({
        [remotes.Bob.sessionId]: { isTalking: true },
        [remotes.Charlie.sessionId]: { isTalking: true },
    });
    await animationFrame();
    // A pin means "this participant, whole": speakers go nowhere near the main window.
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice"]);

    await hover(".o-discuss-CallParticipantCard[aria-label='Alice']");
    await click(".o-discuss-CallParticipantCard[aria-label='Alice'] [title='Participant options']");
    await contains(".o-discuss-CallContextMenu");
    await click(".o-discuss-CallContextMenu button:text('Unpin')");
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Bob", "Charlie"]);
    const channel = getService("discuss.rtc").channel;
    expect(channel.activeRtcSession).toBe(
        channel.rtc_session_ids.find((session) => session.id === remotes.Bob.sessionId)
    );
});

test("a small screen renders only the cards it has room for", async () => {
    // The cap is about what gets *downloaded*, not about what fits: every card past it is a video
    // stream fetched and decoded to fill a hundred pixels of a phone.
    patchUiSize({ size: SIZES.SM });
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Fay", "Gus", "Hal", "Ivy"];
    await openMeetingWithParticipants(names, "tiled");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    // The rest collapse into the indicator the chat window already used, and get no surface at all.
    await contains(".o-discuss-Call-moreIndicator");
    // Self leads, then the participant order: Fay, Gus, Hal and Ivy are the ones the cap drops.
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Mitchell Admin", "Alice", "Bob", "Charlie", "Dave", "Eve"]);
});

test("the card cap never hides whoever is talking", async () => {
    patchUiSize({ size: SIZES.SM });
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Fay", "Gus", "Hal", "Ivy"];
    const { remotes } = await openMeetingWithParticipants(names, "tiled");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await contains(".o-discuss-Call-moreIndicator");
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Mitchell Admin", "Alice", "Bob", "Charlie", "Dave", "Eve"]);

    // Ivy is last in the participant order, so the cap cut her: speaking has to bring her back,
    // ahead of everyone, and Eve is the one that leaves for her.
    getService("discuss.rtc").updateSessionInfo({ [remotes.Ivy.sessionId]: { isTalking: true } });
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Ivy", "Mitchell Admin", "Alice", "Bob", "Charlie", "Dave"]);
});

test("someone sharing their screen gets a card before their video arrives", async () => {
    patchUiSize({ size: SIZES.SM });
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Fay", "Gus", "Hal", "Ivy"];
    const { remotes } = await openMeetingWithParticipants(names, "sidebar");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await contains(".o-discuss-Call-moreIndicator");
    // Alice is the auto-focus target, so she holds the main window and the sidebar column takes
    // the cap: Fay, Gus, Hal and Ivy are the ones it drops.
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Mitchell Admin", "Bob", "Charlie", "Dave", "Eve"]);

    // Only a mounted card starts the video download, so the metadata alone has to bring a
    // presenter in: one the cap left out would wait for a track that never arrives.
    await remotes.Ivy.updateInfo({ is_screen_sharing_on: true });
    await animationFrame();
    expect(
        queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
            el.getAttribute("aria-label")
        )
    ).toEqual(["Alice", "Ivy", "Mitchell Admin", "Bob", "Charlie", "Dave"]);

    // The track arriving is then just a second card for the same participant.
    await remotes.Ivy.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Ivy'] video[type='screen']");
});

test("the overflow indicator takes a sidebar slot rather than half the main window", async () => {
    patchUiSize({ size: SIZES.SM });
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Fay", "Gus", "Hal", "Ivy"];
    const { remotes } = await openMeetingWithParticipants(names, "sidebar");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
    await remotes.Alice.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-Call-moreIndicator");
    // The indicator's own geometry lands on the layout that the frame after its render triggers.
    await animationFrame();

    // The indicator stands for the cards the cap cut out of the sidebar column, so it is one more
    // slot of that column: a main slot would make it share the presenter's window and halve it.
    const indicatorEl = queryFirst(".o-discuss-Call-moreIndicator");
    const sidebarCardEl = queryFirst(".o-discuss-Call-sidebarCard");
    expect(indicatorEl.style.width).toBe(sidebarCardEl.style.width);
    expect(indicatorEl.style.height).toBe(sidebarCardEl.style.height);

    // The shared screen stays larger than the indicator instead of splitting the stage with it.
    const screenCard = queryFirst(".o-discuss-CallParticipantCard:has(video[type='screen'])");
    expect(screenCard.clientHeight).toBeGreaterThan(indicatorEl.clientHeight);
});
