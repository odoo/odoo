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
import { Store } from "@mail/../tests/mock_server/store";

import { SPEAKER_WINDOW } from "@mail/discuss/call/common/discuss_channel_model_patch";

import { advanceTime, beforeEach, describe, disableAnimations, expect, test } from "@odoo/hoot";
import {
    advanceFrame,
    animationFrame,
    drag,
    hover,
    queryAll,
    queryFirst,
    resize,
    tick,
} from "@odoo/hoot-dom";
import { getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { Call } from "@mail/discuss/call/common/call";
import { INSET_MARGIN } from "@mail/discuss/call/common/meeting_layout_engine";

/**
 * Phase 1 acceptance: the same participant must keep the exact same video element across every
 * layout change (pin/unpin, layout switch, sidebar focus swap, participant reorder, resize). A
 * layout change must never destroy and re-create a video surface that stays visible.
 */

describe.current.tags("desktop");
defineMailModels();
beforeEach(() => {
    // Self's own camera/screen come from the browser: without the mock, sharing them silently
    // produces no stream at all and no card ever gets a video element.
    mockGetMedia();
    // The stage animates its geometry through the Web Animations API, which runs on its own
    // timeline: mocked frames do not drive it, so measuring a card would catch it mid-flight.
    // Disabled, `animate` applies the final keyframe at once, which is the geometry asserted here.
    disableAnimations();
});

/**
 * @param {string} name participant name (card aria-label)
 * @returns {HTMLVideoElement|undefined} the video element of that participant's camera card.
 */
function cameraVideo(name) {
    return queryFirst(`.o-discuss-CallParticipantCard[aria-label='${name}'] video[type='camera']`);
}

/**
 * @param {string} name participant name (card aria-label)
 * @returns {HTMLVideoElement|undefined} the video element of that participant's screen card.
 */
function screenVideo(name) {
    return queryFirst(`.o-discuss-CallParticipantCard[aria-label='${name}'] video[type='screen']`);
}

function hoverCard(name) {
    return hover(`.o-discuss-CallParticipantCard[aria-label='${name}']`);
}

async function goFullscreen() {
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await contains(".o-mail-Meeting");
}

async function changeLayout(label) {
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(`.o-discuss-ChangeLayoutDialog-option:contains('${label}')`);
}

/**
 * Open the context menu of a participant card and wait for it. The options button is queried
 * inside that card (the card the pointer left may still render its own for a frame, and an
 * unscoped selector would open that one instead), and the menu is awaited before any caller
 * clicks inside it: the dropdown mounts a frame after the click that opens it.
 *
 * @param {string} name participant name (card aria-label)
 */
async function openCardMenu(name) {
    await hoverCard(name);
    await click(
        `.o-discuss-CallParticipantCard[aria-label='${name}'] [title='Participant options']`
    );
    await contains(".o-discuss-CallContextMenu");
}

async function pinCard(name) {
    await openCardMenu(name);
    await click(".o-discuss-CallContextMenu button:text('Pin')");
}

async function unpinCard(name) {
    await openCardMenu(name);
    await click(".o-discuss-CallContextMenu button:text('Unpin')");
}

/**
 * Setup a channel with `names` remote participants (no media yet) and join it in the wide meeting
 * view.
 *
 * @param {Object} param0
 * @param {string[]} param0.names
 * @param {"tiled"|"spotlight"|"sidebar"|"auto"} [param0.layout="auto"]
 * @returns {Promise<{pyEnv, channelId, network, remotes}>}
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

/**
 * Give a camera to each named remote and wait for their cards to show it.
 */
async function startCameras(remotes, names) {
    for (const name of names) {
        await remotes[name].updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    }
    await contains(".o-discuss-CallParticipantCard video[type='camera']", { count: names.length });
}

/**
 * @param {string} name participant name
 * @returns {import("models").RtcSession} that participant's session in the current call.
 */
function sessionOf(name) {
    return getService("mail.store").rtc.channel.rtc_session_ids.find(
        (session) => session.channel_member_id?.name === name
    );
}

/**
 * Make the named participants start (or stop) talking, as the network would.
 *
 * @param {string[]} names
 * @param {boolean} [isTalking=true]
 */
async function setTalking(names, isTalking = true) {
    getService("discuss.rtc").updateSessionInfo(
        Object.fromEntries(names.map((name) => [sessionOf(name).id, { isTalking }]))
    );
    await animationFrame();
}

/** @returns {string[]} the participants currently on the stage, in render order. */
function stagedNames() {
    return queryAll(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard").map((el) =>
        el.getAttribute("aria-label")
    );
}

test("pin/unpin (tiled → sidebar → tiled) keeps every video element", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"]);
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob"]);
    const aliceVideo = cameraVideo("Alice");
    const bobVideo = cameraVideo("Bob");
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);
    expect(bobVideo).toBeInstanceOf(HTMLVideoElement);

    // Pinning Alice switches to the sidebar layout: Alice fills the main window, Bob moves to the
    // sidebar. Both surfaces must survive the layout switch.
    await pinCard("Alice");
    await contains(".o-discuss-Call-sidebar");
    await contains(".o-discuss-Call-sidebarCard", { count: 2 }); // self avatar + Bob
    expect(cameraVideo("Alice")).toBe(aliceVideo);
    expect(cameraVideo("Bob")).toBe(bobVideo);

    // Unpinning does not switch the layout back by itself: the sidebar stays, elements stay.
    await unpinCard("Alice");
    await contains(".o-discuss-Call-sidebarCard", { count: 2 });
    expect(cameraVideo("Alice")).toBe(aliceVideo);
    expect(cameraVideo("Bob")).toBe(bobVideo);

    // Going back to tiled is a plain layout change: still the same elements.
    await changeLayout("Tiled");
    await contains(".o-discuss-Call-sidebar", { count: 0 });
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard", { count: 3 });
    expect(cameraVideo("Alice")).toBe(aliceVideo);
    expect(cameraVideo("Bob")).toBe(bobVideo);
});

test("switching focus in the sidebar keeps every video element", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob", "Charlie"], "sidebar");
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob", "Charlie"]);
    // Alice is the auto-focus target: main window + self/Bob/Charlie in the sidebar.
    await contains(".o-discuss-Call-sidebarCard", { count: 3 });
    const aliceVideo = cameraVideo("Alice");
    const bobVideo = cameraVideo("Bob");
    const charlieVideo = cameraVideo("Charlie");
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);
    expect(bobVideo).toBeInstanceOf(HTMLVideoElement);
    expect(charlieVideo).toBeInstanceOf(HTMLVideoElement);

    // Pinning Bob makes him the focused main card: Alice moves from the main window to the
    // sidebar, Bob from the sidebar to the main window. No video element is recreated.
    await pinCard("Bob");
    // Wait on the badge, not on the sidebar count: the count is 3 before and after the pin, so it
    // holds on the pre-pin render and lets everything below run against a stage that has not been
    // re-rendered yet.
    await contains(".o-discuss-CallParticipantCard[aria-label='Bob'] [title='Pinned']");
    await contains(".o-discuss-Call-sidebarCard", { count: 3 });
    expect(cameraVideo("Bob")).toBe(bobVideo);
    expect(cameraVideo("Alice")).toBe(aliceVideo);
    expect(cameraVideo("Charlie")).toBe(charlieVideo);

    // Unpinning keeps Bob focused (the layout persists): same elements again. The badge going
    // away is the only visible change, so it is what tells the unpin has been rendered.
    await unpinCard("Bob");
    await contains(".o-discuss-CallParticipantCard [title='Pinned']", { count: 0 });
    await contains(".o-discuss-Call-sidebarCard", { count: 3 });
    expect(cameraVideo("Bob")).toBe(bobVideo);
    expect(cameraVideo("Alice")).toBe(aliceVideo);
    expect(cameraVideo("Charlie")).toBe(charlieVideo);
});

test("spotlight ⇄ tiled keeps the focused video element", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice"]);
    await goFullscreen();
    // With 2 participants (self + Alice) "auto" resolves to spotlight: Alice is the focus target
    // and self is shown as the bottom-right inset (2 cards in the single stage).
    await startCameras(remotes, ["Alice"]);
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard", { count: 2 });
    const aliceVideo = cameraVideo("Alice");
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);

    await changeLayout("Tiled");
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard", { count: 2 });
    expect(cameraVideo("Alice")).toBe(aliceVideo);

    await changeLayout("Spotlight");
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard", { count: 2 });
    expect(cameraVideo("Alice")).toBe(aliceVideo);
});

test("inset stream swap keeps both video elements (main ⇄ inset)", async () => {
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
    const screenEl = screenVideo("Mitchell Admin");
    const cameraEl = cameraVideo("Mitchell Admin");
    expect(screenEl).toBeInstanceOf(HTMLVideoElement);
    expect(cameraEl).toBeInstanceOf(HTMLVideoElement);

    // Clicking the inset swaps which stream is main: the screen card goes to the inset and the
    // camera card takes the main window. Both are the exact same elements as before.
    await click("video[type='camera'].o-inset");
    await contains("video[type='screen'].o-inset");
    await contains("video[type='camera']:not(.o-inset)");
    expect(screenVideo("Mitchell Admin")).toBe(screenEl);
    expect(cameraVideo("Mitchell Admin")).toBe(cameraEl);
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
    const mainEl = queryFirst(".o-discuss-Call-mainCardStyle:not(.o-inset)");
    const insetVideo = cameraVideo("Mitchell Admin");

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
    expect(cameraVideo("Mitchell Admin")).toBe(insetVideo);
});

test("a new participant reorders the grid without recreating existing videos", async () => {
    const { pyEnv, channelId, network, remotes } = await openMeetingWithParticipants([
        "Alice",
        "Bob",
        "Charlie",
    ]);
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob", "Charlie"]);
    const videos = {
        Alice: cameraVideo("Alice"),
        Bob: cameraVideo("Bob"),
        Charlie: cameraVideo("Charlie"),
    };
    expect(cameraVideo("Alice")).toBeInstanceOf(HTMLVideoElement);

    // "Aaron" sorts first: joining him mid-call shifts everyone in the grid.
    const aaronMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Aaron" }),
    });
    const aaronRemote = network.makeMockRemote(aaronMemberId);
    // The store only learns about the new session through the bus; without this insert the
    // connection change would be dropped as an unknown session.
    pyEnv["bus.bus"]._sendone(
        pyEnv["res.partner"].browse(serverState.partnerId),
        "mail.record/insert",
        new Store()
            .add(pyEnv["discuss.channel.rtc.session"].browse(aaronRemote.sessionId), {
                channel_member_id: { id: aaronMemberId },
            })
            .add(pyEnv["discuss.channel.member"].browse(aaronMemberId), {
                partner_id: { id: pyEnv["res.partner"].search([["name", "=", "Aaron"]])[0] },
                channel_id: { id: channelId, model: "discuss.channel" },
            })
            .as_dict()
    );
    await aaronRemote.updateConnectionState("connected");
    await aaronRemote.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard video[type='camera']", { count: 4 });
    expect(cameraVideo("Alice")).toBe(videos.Alice);
    expect(cameraVideo("Bob")).toBe(videos.Bob);
    expect(cameraVideo("Charlie")).toBe(videos.Charlie);
    expect(cameraVideo("Aaron")).toBeInstanceOf(HTMLVideoElement);
});

test("resize keeps every video element and only changes geometry", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob", "Charlie"]);
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob", "Charlie"]);
    const aliceVideo = cameraVideo("Alice");
    const aliceCard = queryFirst(".o-discuss-CallParticipantCard[aria-label='Alice']");
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);

    await resize({ width: 1280, height: 720 });
    await animationFrame();
    await tick();
    await contains(".o-discuss-CallParticipantCard video[type='camera']", { count: 3 });
    expect(cameraVideo("Alice")).toBe(aliceVideo);
    // The geometry is re-applied through the transform (compositor) without recreating anything.
    expect(aliceCard.style.transform).toInclude("translate3d");
    expect(aliceCard.style.width).not.toBe("");
    expect(aliceCard.style.height).not.toBe("");
});

test("layout triggers are coalesced into a single computation", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob", "Charlie"]);
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob", "Charlie"]);
    let computationCount = 0;
    patchWithCleanup(Call.prototype, {
        arrangeTiles() {
            computationCount += 1;
            return super.arrangeTiles();
        },
    });
    // Drain any layout still pending from the setup, then count from zero.
    await animationFrame();
    await tick();
    computationCount = 0;
    const store = getService("mail.store");
    const channel = store.rtc.channel;
    const [alice] = channel.rtc_session_ids;
    // Three real triggers (focus/speaker, pin, layout mode) in the same task: OWL renders once
    // and requestLayout coalesces everything into a single computation.
    channel.focusStack.push(alice);
    channel.pinnedRtcSession = alice;
    store.settings.callLayout = "spotlight";
    await animationFrame();
    await tick();
    expect(computationCount).toBe(1);
    // Nothing left pending: no extra computation on the following frames.
    await animationFrame();
    await tick();
    expect(computationCount).toBe(1);
});

test("a card mounted by a render is positioned before the browser can paint it", async () => {
    const { pyEnv, channelId, network, remotes } = await openMeetingWithParticipants([
        "Alice",
        "Bob",
    ]);
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob"]);
    // A card that OWL just mounted is absolutely positioned but has no geometry of its own: the
    // layout must be applied on the render's own task, not on the next animation frame, or the
    // browser paints every new card stacked in the corner of the stage first.
    const positioned = [];
    patchWithCleanup(Call.prototype, {
        arrangeTiles() {
            const result = super.arrangeTiles();
            positioned.push(
                queryAll(".o-discuss-CallParticipantCard").every((el) => el.style.transform)
            );
            return result;
        },
    });
    const charlieMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Charlie" }),
    });
    const charlieRemote = network.makeMockRemote(charlieMemberId);
    pyEnv["bus.bus"]._sendone(
        pyEnv["res.partner"].browse(serverState.partnerId),
        "mail.record/insert",
        new Store()
            .add(pyEnv["discuss.channel.rtc.session"].browse(charlieRemote.sessionId), {
                channel_member_id: { id: charlieMemberId },
            })
            .add(pyEnv["discuss.channel.member"].browse(charlieMemberId), {
                partner_id: { id: pyEnv["res.partner"].search([["name", "=", "Charlie"]])[0] },
                channel_id: { id: channelId, model: "discuss.channel" },
            })
            .as_dict()
    );
    await charlieRemote.updateConnectionState("connected");
    await contains(".o-discuss-CallParticipantCard[aria-label='Charlie']");
    await tick();
    // Every layout pass since Charlie joined left all three cards with a geometry.
    expect(positioned.length).toBeGreaterThan(0);
    expect(positioned.every(Boolean)).toBe(true);
});

/**
 * Every surface is positioned by arrangeTiles, so it must be out of the flow: a card left in it
 * is offset by the height of the ones before it *and* by its own transform, which pushes the
 * grid diagonally out of the stage.
 *
 * @param {string} label layout under test, for the assertion messages
 */
async function expectCardsInsideStage(label) {
    // Let every pending layout pass run (animations are disabled, so the geometry is final).
    await advanceFrame(20);
    const stage = queryFirst(".o-discuss-Call-mainCards").getBoundingClientRect();
    const cards = queryAll(".o-discuss-CallParticipantCard");
    expect(cards.length).toBeGreaterThan(1);
    for (const card of cards) {
        const rect = card.getBoundingClientRect();
        expect(getComputedStyle(card).position).toBe("absolute", {
            message: `${label}: ${card.getAttribute("aria-label")} is positioned by the stage`,
        });
        expect(rect.x).toBeWithin(stage.x, stage.x + stage.width);
        expect(rect.y).toBeWithin(stage.y, stage.y + stage.height);
        expect(rect.x + rect.width).toBeWithin(stage.x, stage.x + stage.width + 1);
        expect(rect.y + rect.height).toBeWithin(stage.y, stage.y + stage.height + 1);
    }
}

test("tiled cards land on the computed grid instead of stacking in the flow", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"]);
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob"]);
    await changeLayout("Tiled");
    await animationFrame();
    await tick();
    await expectCardsInsideStage("tiled");
});

test("sidebar cards land on the computed column instead of stacking in the flow", async () => {
    const { remotes } = await openMeetingWithParticipants(["Alice", "Bob"], "sidebar");
    await goFullscreen();
    await startCameras(remotes, ["Alice", "Bob"]);
    // Alice is the auto-focus target: self and Bob line up in the sidebar column.
    await contains(".o-discuss-Call-sidebarCard", { count: 2 });
    await animationFrame();
    await tick();
    await expectCardsInsideStage("sidebar");
});

test("recent speakers share the spotlight instead of fighting over it", async () => {
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve"];
    const { remotes } = await openMeetingWithParticipants(names, "tiled");
    await goFullscreen();
    // Cameras first: the spotlight only renders whoever holds the stage, so nobody else would have
    // a card to give a stream to.
    await startCameras(remotes, names);
    getService("mail.store").settings.callLayout = "spotlight";
    await animationFrame();

    await setTalking(["Alice"]);
    expect(stagedNames()).toEqual(["Alice"]);
    const aliceVideo = cameraVideo("Alice");
    expect(aliceVideo).toBeInstanceOf(HTMLVideoElement);

    // Bob answering used to replace Alice outright, which is the thrash: two people going back and
    // forth traded the main window on every sentence. They now share it.
    await setTalking(["Bob"]);
    expect(stagedNames()).toEqual(["Alice", "Bob"]);
    expect(cameraVideo("Alice")).toBe(aliceVideo);

    await setTalking(["Charlie", "Dave"]);
    expect(stagedNames()).toEqual(["Alice", "Bob", "Charlie", "Dave"]);

    // The stage is full: a fifth speaker waits for a place rather than pushing anyone out.
    await setTalking(["Eve"]);
    expect(stagedNames()).toEqual(["Alice", "Bob", "Charlie", "Dave"]);

    // Alice going quiet does not free her place right away — that is what the window is for.
    await setTalking(["Alice"], false);
    await advanceTime(SPEAKER_WINDOW - 500);
    expect(stagedNames()).toEqual(["Alice", "Bob", "Charlie", "Dave"]);

    // Once it lapses she leaves, everyone shifts up and Eve takes the free place.
    await advanceTime(1000);
    await animationFrame();
    expect(stagedNames()).toEqual(["Bob", "Charlie", "Dave", "Eve"]);
    // The three who never stopped talking kept the exact same video element throughout.
    expect(cameraVideo("Bob")).toBeInstanceOf(HTMLVideoElement);
});

test("a pinned participant keeps the whole stage while others talk", async () => {
    await openMeetingWithParticipants(["Alice", "Bob", "Charlie"], "spotlight");
    await goFullscreen();
    // `pin` keeps an explicit spotlight, so this isolates the pin from the sidebar layout.
    await pinCard("Alice");
    await contains(".o-discuss-CallParticipantCard[aria-label='Alice'] [title='Pinned']");

    await setTalking(["Bob", "Charlie"]);
    // A pin means "this participant, whole": speakers go nowhere near the main window.
    expect(stagedNames()).toEqual(["Alice"]);
});

test("a small screen renders only the cards it has room for", async () => {
    // The cap is about what gets *downloaded*, not about what fits: every card past it is a video
    // stream fetched and decoded to fill a hundred pixels of a phone.
    patchUiSize({ size: SIZES.SM });
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Fay", "Gus", "Hal", "Ivy"];
    await openMeetingWithParticipants(names, "tiled");
    await goFullscreen();
    // 9 remotes plus self, capped at SMALL_SCREEN_MAX_CARDS.
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard", { count: 6 });
    // The rest collapse into the indicator the chat window already used, and get no surface at all.
    await contains(".o-discuss-Call-moreIndicator");
});

test("the card cap never hides whoever is talking", async () => {
    patchUiSize({ size: SIZES.SM });
    const names = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Fay", "Gus", "Hal", "Ivy"];
    await openMeetingWithParticipants(names, "tiled");
    await goFullscreen();
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard", { count: 6 });
    expect(stagedNames()).not.toInclude("Ivy");

    // Ivy is last in the participant order, so the cap cut her: speaking has to bring her back.
    await setTalking(["Ivy"]);
    expect(stagedNames()).toInclude("Ivy");
    expect(stagedNames()).toHaveLength(6);
});
