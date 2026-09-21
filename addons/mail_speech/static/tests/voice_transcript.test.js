import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    Command,
    getService,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

/**
 * @param {Object} pyEnv
 * @returns {{ channelId: number, attachmentId: number }}
 */
function voiceMessageIn(pyEnv) {
    const channelId = pyEnv["discuss.channel"].create({
        name: "Notes",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "Voice.mp3",
        mimetype: "audio/mpeg",
        voice_ids: [Command.create({})],
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    return { channelId, attachmentId };
}

/**
 * @param {number} attachmentId
 * @param {Object} values
 */
function speechArrives(attachmentId, values) {
    getService("mail.store").insert({
        "ir.attachment": [{ id: attachmentId, ...values }],
    });
}

test("a transcribed voice message shows what it says", async () => {
    const pyEnv = await startServer();
    const { channelId, attachmentId } = voiceMessageIn(pyEnv);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-VoicePlayer");
    speechArrives(attachmentId, {
        transcript_state: "done",
        transcript_text: "left you a note about Tuesday",
    });
    await contains(".o-mail-VoiceTranscript-text", {
        text: "left you a note about Tuesday",
    });
});

test("an untranscribed voice message offers to transcribe it", async () => {
    const pyEnv = await startServer();
    const { channelId, attachmentId } = voiceMessageIn(pyEnv);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-VoicePlayer");
    speechArrives(attachmentId, { can_transcribe: true, transcript_state: "none" });
    await contains(".o-mail-VoiceTranscript button", { text: "Transcribe" });
});

test("a voice message being transcribed says so and cannot be asked twice", async () => {
    const pyEnv = await startServer();
    const { channelId, attachmentId } = voiceMessageIn(pyEnv);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-VoicePlayer");
    speechArrives(attachmentId, { can_transcribe: true, transcript_state: "queued" });
    await contains(".o-mail-VoiceTranscript button:disabled", {
        text: "Transcribing…",
    });
});

test("a voice message no engine can read offers nothing", async () => {
    const pyEnv = await startServer();
    const { channelId, attachmentId } = voiceMessageIn(pyEnv);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-VoicePlayer");
    speechArrives(attachmentId, { can_transcribe: false, transcript_state: "none" });
    await contains(".o-mail-VoiceTranscript");
    expect(".o-mail-VoiceTranscript button").toHaveCount(0);
});

test("asking for a transcript calls the model that queues one", async () => {
    const pyEnv = await startServer();
    const { channelId, attachmentId } = voiceMessageIn(pyEnv);
    const asked = [];
    onRpc("ir.attachment", "action_transcribe", ({ args }) => {
        asked.push(args[0]);
        return true;
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-VoicePlayer");
    speechArrives(attachmentId, { can_transcribe: true, transcript_state: "none" });
    await click(".o-mail-VoiceTranscript button");
    expect(asked).toEqual([[attachmentId]]);
    await contains(".o-mail-VoiceTranscript button:disabled");
});

test("a transcript replaces the offer to make one", async () => {
    const pyEnv = await startServer();
    const { channelId, attachmentId } = voiceMessageIn(pyEnv);
    await start();
    await openDiscuss(channelId);
    speechArrives(attachmentId, { can_transcribe: true, transcript_state: "none" });
    await contains(".o-mail-VoiceTranscript button", { text: "Transcribe" });
    speechArrives(attachmentId, {
        transcript_state: "done",
        transcript_text: "the invoice went out",
    });
    await contains(".o-mail-VoiceTranscript-text", { text: "the invoice went out" });
    expect(".o-mail-VoiceTranscript button").toHaveCount(0);
});
