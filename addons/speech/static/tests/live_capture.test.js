import { Deferred, describe, expect, test } from "@odoo/hoot";
import {
    ChunkRecorder,
    MAX_CHUNK_S,
    downsample,
    encodeWav,
} from "@speech/live_capture/chunk_recorder";
import { Dictation } from "@speech/live_capture/dictation";

const RATE = 1000;

function tone(seconds, amplitude = 0.5) {
    return Float32Array.from({ length: seconds * RATE }, (_, index) =>
        index % 2 ? amplitude : -amplitude,
    );
}

function recorder() {
    const chunks = [];
    const instance = new ChunkRecorder((chunk) => chunks.push(chunk));
    instance.sampleRate = RATE;
    return { instance, chunks };
}

describe("ChunkRecorder", () => {
    test("a phrase is cut at the first pause after the minimum", () => {
        const { instance, chunks } = recorder();
        instance.feed(tone(3));
        instance.feed(tone(0.5, 0));
        expect(chunks).toHaveLength(0);
        instance.feed(tone(3));
        instance.feed(tone(0.5, 0));
        expect(chunks).toHaveLength(1);
        expect(chunks[0].startS).toBe(0);
        expect(chunks[0].durationS).toBe(7);
        expect(chunks[0].mimetype).toBe("audio/wav");
    });

    test("speech without a pause is cut at the maximum", () => {
        const { instance, chunks } = recorder();
        for (let second = 0; second < MAX_CHUNK_S + 2; second++) {
            instance.feed(tone(1));
        }
        expect(chunks).toHaveLength(1);
        expect(chunks[0].durationS).toBe(MAX_CHUNK_S);
        instance.cut();
        expect(chunks[1].startS).toBe(MAX_CHUNK_S);
    });

    test("silence throughout is never sent, but still moves the clock", () => {
        const { instance, chunks } = recorder();
        instance.feed(tone(6, 0));
        instance.cut();
        expect(chunks).toHaveLength(0);
        instance.feed(tone(2));
        instance.cut();
        expect(chunks[0].startS).toBe(6);
    });

    test("the wav is 16-bit mono at the rate it says", () => {
        const bytes = encodeWav(Float32Array.from([0, 1, -1]), 16000);
        const view = new DataView(bytes.buffer);
        expect(new TextDecoder().decode(bytes.slice(0, 4))).toBe("RIFF");
        expect(view.getUint16(22, true)).toBe(1);
        expect(view.getUint32(24, true)).toBe(16000);
        expect(view.getInt16(46, true)).toBe(0x7fff);
        expect(view.getInt16(48, true)).toBe(-0x8000);
    });

    test("downsampling averages and keeps the duration", () => {
        const result = downsample(Float32Array.from([1, 3, 5, 7]), 4, 2);
        expect([...result]).toEqual([2, 6]);
    });
});

describe("Dictation", () => {
    function session(pushes) {
        const texts = [];
        const sent = [];
        const bus = {
            addChannel() {},
            deleteChannel() {},
            subscribe() {},
            unsubscribe() {},
        };
        const orm = {
            call(model, method) {
                return method === "push_chunk" ? pushes.shift() : Promise.resolve();
            },
        };
        const dictation = new Dictation({
            orm,
            bus,
            onChunkSent: (index) => sent.push(index),
            onChunkText: (index, text) => texts.push([index, text]),
        });
        dictation.id = 5;
        dictation.channel = "speech.live/speech.dictation/5";
        return { dictation, texts, sent };
    }

    const chunk = { audio: "", startS: 0, durationS: 6, mimetype: "audio/wav" };

    test("each chunk's words go to the chunk that asked for them", async () => {
        const first = new Deferred();
        const second = new Deferred();
        const { dictation, texts, sent } = session([first, second]);
        dictation.send(chunk);
        dictation.send(chunk);
        expect(sent).toEqual([0, 1]);
        first.resolve(11);
        second.resolve(12);
        await Promise.all([...dictation.sending]);
        dictation.onNotification({
            model: "speech.dictation",
            id: 5,
            event: "chunk",
            segment_id: 12,
            text: "second",
        });
        dictation.onNotification({
            model: "speech.dictation",
            id: 5,
            event: "chunk",
            segment_id: 11,
            text: "first",
        });
        expect(texts).toEqual([
            [1, "second"],
            [0, "first"],
        ]);
    });

    test("words that arrive before their chunk was acknowledged wait for it", async () => {
        const push = new Deferred();
        const { dictation, texts } = session([push]);
        dictation.send(chunk);
        dictation.onNotification({
            model: "speech.dictation",
            id: 5,
            event: "chunk",
            segment_id: 21,
            text: "early",
        });
        expect(texts).toEqual([]);
        push.resolve(21);
        await Promise.all([...dictation.sending]);
        expect(texts).toEqual([[0, "early"]]);
    });

    test("another record's words are ignored", async () => {
        const { dictation, texts } = session([Promise.resolve(31)]);
        dictation.send(chunk);
        await Promise.all([...dictation.sending]);
        dictation.onNotification({
            model: "conversation.conversation",
            id: 5,
            event: "chunk",
            segment_id: 31,
            text: "not mine",
        });
        expect(texts).toEqual([]);
    });

    test("a chunk the server refused is answered with nothing", async () => {
        const { dictation, texts } = session([Promise.reject(new Error("refused"))]);
        dictation.onError = () => {};
        dictation.send(chunk);
        await Promise.all([...dictation.sending]).catch(() => {});
        await Promise.resolve();
        expect(texts).toEqual([[0, ""]]);
    });
});
