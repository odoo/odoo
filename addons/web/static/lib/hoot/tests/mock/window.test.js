/** @odoo-module */

import { after, describe, expect, microTick, test, watchListeners } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { EventBus } from "@odoo/owl";
import { mountForTest, parseUrl } from "../local_helpers";

/**
 * @param {string} name
 * @returns {Promise<IDBDatabase>}
 */
function openDatabase(name) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(name);
        request.onupgradeneeded = () => expect.step(`upgrade:${name}`);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

describe(parseUrl(import.meta.url), () => {
    class TestBus extends EventBus {
        addEventListener(type) {
            expect.step(`addEventListener:${type}`);
            return super.addEventListener(...arguments);
        }

        removeEventListener() {
            throw new Error("Cannot remove event listeners");
        }
    }

    /** @type {HTMLAudioElement} */
    let audioElement;
    let observedNode;
    /** @type {RTCPeerConnection} */
    let peerConnection;
    let testBus;

    test("elementFromPoint and elementsFromPoint should be mocked", async () => {
        await mountForTest(/* xml */ `
            <div class="oui" style="position: absolute; left: 10px; top: 10px; width: 250px; height: 250px;">
                Oui
            </div>
        `);

        expect(".oui").toHaveRect({
            x: 10,
            y: 10,
            width: 250,
            height: 250,
        });

        const div = queryOne(".oui");
        expect(document.elementFromPoint(11, 11)).toBe(div);
        expect(document.elementsFromPoint(11, 11)).toEqual([
            div,
            document.body,
            document.documentElement,
        ]);

        expect(document.elementFromPoint(9, 9)).toBe(document.body);
        expect(document.elementsFromPoint(9, 9)).toEqual([document.body, document.documentElement]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests event listeners cleanup.
    test("event listeners are properly removed: setup", async () => {
        const callback = () => expect.step("callback");

        testBus = new TestBus();

        expect.verifySteps([]);

        after(watchListeners());

        testBus.addEventListener("some-event", callback);
        testBus.trigger("some-event");

        expect.verifySteps(["addEventListener:some-event", "callback"]);
    });
    test("event listeners are properly removed: check", async () => {
        testBus.trigger("some-event");

        expect.verifySteps([]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests event listeners cleanup.
    test("event listeners with options are properly removed: setup", async () => {
        after(watchListeners());

        const controller = new AbortController();
        window.addEventListener("hoot-event", () => expect.step("capture"), true);
        window.addEventListener("hoot-event", () => expect.step("signal"), {
            signal: controller.signal,
        });
        window.dispatchEvent(new Event("hoot-event"));

        expect.verifySteps(["capture", "signal"]);

        controller.abort();
        window.dispatchEvent(new Event("hoot-event"));

        expect.verifySteps(["capture"]);
    });
    test("event listeners with options are properly removed: check", async () => {
        window.dispatchEvent(new Event("hoot-event"));

        expect.verifySteps([]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests observers cleanup.
    test("observers are disconnected between tests: setup", async () => {
        expect(MutationObserver.name).toBe("MutationObserver");

        observedNode = document.createElement("div");
        const observer = new MutationObserver(() => expect.step("mutation"));
        observer.observe(observedNode, { attributes: true });
        observedNode.setAttribute("data-value", "1");
        await microTick();

        expect.verifySteps(["mutation"]);
    });
    test("observers are disconnected between tests: check", async () => {
        observedNode.setAttribute("data-value", "2");
        await microTick();

        expect.verifySteps([]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests IndexedDB cleanup.
    test("IndexedDB databases are deleted between tests: setup", async () => {
        await openDatabase("hoot_test_db");
        await openDatabase("hoot_test_db");

        expect.verifySteps(["upgrade:hoot_test_db"]);

        // Left opening at the end of the test
        indexedDB.open("hoot_test_pending_db");
    });
    test("IndexedDB databases are deleted between tests: check", async () => {
        await openDatabase("hoot_test_db");
        await openDatabase("hoot_test_pending_db");

        expect.verifySteps(["upgrade:hoot_test_db", "upgrade:hoot_test_pending_db"]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests media elements cleanup.
    test("media elements are paused between tests: setup", async () => {
        audioElement = new Audio();
        audioElement.loop = true;
        audioElement.play().catch(() => {});

        expect(audioElement.paused).toBe(false);
    });
    test("media elements are paused between tests: check", async () => {
        expect(audioElement.paused).toBe(true);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests peer connections cleanup.
    test("peer connections are closed between tests: setup", async () => {
        peerConnection = new RTCPeerConnection();

        expect(peerConnection.signalingState).toBe("stable");
    });
    test("peer connections are closed between tests: check", async () => {
        expect(peerConnection.signalingState).toBe("closed");
    });

    describe("Web Audio", () => {
        test("AudioContext lifecycle", async () => {
            const audioContext = new AudioContext();
            audioContext.onstatechange = () => expect.step(audioContext.state);

            expect(audioContext.state).toBe("suspended");

            await audioContext.resume();
            await audioContext.close();

            expect.verifySteps(["running", "closed"]);

            await expect(audioContext.close()).rejects.toThrow(/closed/);
        });

        test("audio nodes are inert", async () => {
            const audioContext = new AudioContext();
            const analyser = audioContext.createAnalyser();
            const gain = audioContext.createGain();
            const frequencies = new Uint8Array(analyser.frequencyBinCount).fill(255);

            expect(analyser.connect(gain)).toBe(gain);
            expect(gain.connect(audioContext.destination)).toBe(audioContext.destination);

            analyser.getByteFrequencyData(frequencies);

            expect(frequencies.every((value) => value === 0)).toBe(true);

            await audioContext.audioWorklet.addModule("/processor.js");
            const processor = new AudioWorkletNode(audioContext, "processor");

            expect(processor.port).toBeInstanceOf(MessagePort);
        });

        test("audio nodes constructor options", () => {
            const audioContext = new AudioContext({ sampleRate: 8000 });
            const analyser = new AnalyserNode(audioContext, { fftSize: 64 });
            const gain = new GainNode(audioContext, { gain: 0.5 });
            const destination = new MediaStreamAudioDestinationNode(audioContext, {
                channelCount: 1,
            });

            expect(audioContext.sampleRate).toBe(8000);
            expect(analyser.frequencyBinCount).toBe(32);
            expect(gain.gain.value).toBe(0.5);
            expect(gain.gain.defaultValue).toBe(1);
            expect(destination.channelCount).toBe(1);
            expect(destination.stream.getAudioTracks()).toHaveLength(1);
        });

        test("createMediaStreamDestination provides a real audio track", () => {
            const { stream } = new AudioContext().createMediaStreamDestination();
            const tracks = stream.getAudioTracks();

            expect(tracks).toHaveLength(1);
            expect(tracks[0]).toBeInstanceOf(MediaStreamTrack);
            expect(tracks[0].readyState).toBe("live");
        });

        test("createMediaStreamSource requires an audio track", () => {
            const audioContext = new AudioContext();

            expect(() => audioContext.createMediaStreamSource(new MediaStream())).toThrow(
                /audio track/
            );
        });

        test("decodeAudioData decodes actual audio data", async () => {
            // 16-bit mono PCM WAV file holding 100 samples of silence
            const sampleCount = 100;
            const view = new DataView(new ArrayBuffer(44 + sampleCount * 2));
            const writeString = (offset, string) => {
                for (let i = 0; i < string.length; i++) {
                    view.setUint8(offset + i, string.charCodeAt(i));
                }
            };
            writeString(0, "RIFF");
            view.setUint32(4, 36 + sampleCount * 2, true);
            writeString(8, "WAVEfmt ");
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true); // PCM
            view.setUint16(22, 1, true); // mono
            view.setUint32(24, 8000, true); // sample rate
            view.setUint32(28, 16000, true); // byte rate
            view.setUint16(32, 2, true); // block align
            view.setUint16(34, 16, true); // bits per sample
            writeString(36, "data");
            view.setUint32(40, sampleCount * 2, true);

            const buffer = await new AudioContext().decodeAudioData(view.buffer);

            expect(buffer).toBeInstanceOf(AudioBuffer);
            expect(buffer.duration).toBeCloseTo(sampleCount / 8000);
        });
    });
});
