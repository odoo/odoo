import {
    createVideoStream,
    defineMailModels,
    makeMockRtcNetwork,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import {
    ANNOTATION_MESSAGE_TYPE,
    ANNOTATION_PROTOCOL_VERSION,
    INK_LIFETIME_MS,
    MAX_POINTS_PER_MESSAGE,
    SEND_INTERVAL_MS,
    isValidAnnotationMessage,
} from "@mail/discuss/call/common/screen_annotation_plugin";

import { advanceTime, beforeEach, describe, expect, queryFirst, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, getService, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    mockGetMedia();
});

function makeMessage(screenSessionId, values = {}) {
    return {
        type: ANNOTATION_MESSAGE_TYPE,
        version: ANNOTATION_PROTOCOL_VERSION,
        screenSessionId,
        strokeId: 1,
        seq: 1,
        points: [0.1, 0.2, 0.3, 0.4],
        isEnded: false,
        ...values,
    };
}

async function startCallWithSharedScreen() {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const streamerMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Streamer" }),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const streamer = network.makeMockRemote(streamerMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await streamer.updateConnectionState("connected");
    await streamer.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Streamer'] video");
    const rtc = getService("discuss.rtc");
    const receive = (senderId, message) =>
        rtc._handleNetworkUpdates({
            detail: { name: "broadcast", payload: { senderId, message } },
        });
    return { annotation: rtc.screenAnnotation, receive, rtc, streamer };
}

test("drawing on a shared screen is toggled from the call actions", async () => {
    const { annotation } = await startCallWithSharedScreen();
    await waitFor(".o-discuss-ScreenAnnotationOverlay:not(.o-isDrawing)");
    expect(annotation.hasSharedScreen).toBe(true);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show the call actions
    if (!queryFirst("[name='screen-annotation']")) {
        await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    }
    await contains("[name='screen-annotation']:count(1)").click();
    await waitFor(".o-discuss-ScreenAnnotationOverlay.o-isDrawing");
    expect(annotation.isDrawing).toBe(true);
    annotation.toggle();
    await waitFor(".o-discuss-ScreenAnnotationOverlay:not(.o-isDrawing)");
});

test("ink of another participant is shown on the shared screen then fades out", async () => {
    const { annotation, receive, streamer } = await startCallWithSharedScreen();
    const screenId = streamer.sessionId;
    await receive(streamer.sessionId, makeMessage(screenId));
    let [stroke] = annotation.getStrokes(screenId);
    expect(stroke.name).toBe("Streamer");
    expect(stroke.points.map(({ x, y }) => [x, y])).toEqual([
        [0.1, 0.2],
        [0.3, 0.4],
    ]);
    // received twice when both the SFU and peer-to-peer deliver it
    await receive(streamer.sessionId, makeMessage(screenId));
    [stroke] = annotation.getStrokes(screenId);
    expect(stroke.points).toHaveLength(2);
    await receive(streamer.sessionId, makeMessage(screenId, { seq: 2, points: [], isEnded: true }));
    annotation.prune(performance.now() + INK_LIFETIME_MS + 1);
    expect([...annotation.getStrokes(screenId)]).toHaveLength(0);
});

test("annotation messages that are invalid or not about a shared screen are ignored", async () => {
    const { annotation, receive, rtc, streamer } = await startCallWithSharedScreen();
    const screenId = streamer.sessionId;
    expect(isValidAnnotationMessage(makeMessage(screenId))).toBe(true);
    expect(isValidAnnotationMessage(makeMessage(screenId, { version: 2 }))).toBe(false);
    expect(isValidAnnotationMessage(makeMessage(screenId, { points: [0.1] }))).toBe(false);
    expect(isValidAnnotationMessage(makeMessage(screenId, { points: [0.1, NaN] }))).toBe(false);
    expect(isValidAnnotationMessage(makeMessage(screenId, { points: "0.1,0.2" }))).toBe(false);
    expect(
        isValidAnnotationMessage(
            makeMessage(screenId, {
                points: Array.from({ length: MAX_POINTS_PER_MESSAGE * 2 + 2 }, () => 0.5),
            })
        )
    ).toBe(false);
    // the own session of the user does not share its screen
    await receive(streamer.sessionId, makeMessage(rtc.selfSession.id));
    expect([...annotation.getStrokes(rtc.selfSession.id)]).toHaveLength(0);
    // coordinates out of the frame are kept on its edge
    await receive(streamer.sessionId, makeMessage(screenId, { points: [-3, 7] }));
    const [stroke] = annotation.getStrokes(screenId);
    expect(stroke.points.map(({ x, y }) => [x, y])).toEqual([[0, 1]]);
});

test("local ink is batched and sent to the call", async () => {
    const { annotation, streamer } = await startCallWithSharedScreen();
    const sent = [];
    patchWithCleanup(annotation, {
        send(message) {
            sent.push(message);
        },
    });
    const screenId = streamer.sessionId;
    annotation.startLocalStroke(screenId, 0.5, 0.5);
    annotation.addLocalPoint(0.6, 0.7);
    expect(sent).toHaveLength(0);
    await advanceTime(SEND_INTERVAL_MS);
    expect(sent).toHaveLength(1);
    expect(sent[0]).toEqual(
        makeMessage(screenId, { strokeId: sent[0].strokeId, points: [0.5, 0.5, 0.6, 0.7] })
    );
    annotation.endLocalStroke();
    expect(sent).toHaveLength(2);
    expect(sent[1].seq).toBe(2);
    expect(sent[1].isEnded).toBe(true);
    expect(sent.every(isValidAnnotationMessage)).toBe(true);
    // the local ink is shown too
    const [stroke] = annotation.getStrokes(screenId);
    expect(stroke.points).toHaveLength(2);
});
