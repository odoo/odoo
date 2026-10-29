/** @odoo-module */

import {
    describe,
    expect,
    microTick,
    mockPermission,
    mockSendBeacon,
    mockTouch,
    mockVibrate,
    test,
} from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

/**
 * @param {Promise<any>} promise
 */
const ensureResolvesImmediatly = (promise) =>
    Promise.race([
        promise,
        new Promise((resolve, reject) => reject("failed to resolve in a single micro tick")),
    ]);

describe(parseUrl(import.meta.url), () => {
    describe("clipboard", () => {
        test.tags("secure");
        test("read/write calls are resolved immediatly", async () => {
            navigator.clipboard.write([
                new ClipboardItem({
                    "text/plain": new Blob(["some text"], { type: "text/plain" }),
                }),
            ]);

            const items = await ensureResolvesImmediatly(navigator.clipboard.read());

            expect(items).toHaveLength(1);
            expect(items[0]).toBeInstanceOf(ClipboardItem);

            const blob = await ensureResolvesImmediatly(items[0].getType("text/plain"));

            expect(blob).toBeInstanceOf(Blob);

            const value = await ensureResolvesImmediatly(blob.text());

            expect(value).toBe("some text");
        });
    });

    describe("permission-gated APIs", () => {
        test("geolocation positions are never available", async () => {
            const onSuccess = () => expect.step("success");
            const onError = (error) => expect.step(`error:${error.code}`);

            navigator.geolocation.getCurrentPosition(onSuccess, onError);

            expect.verifySteps([]);

            await microTick();

            expect.verifySteps(["error:1"]); // PERMISSION_DENIED

            mockPermission("geolocation", "granted");
            navigator.geolocation.watchPosition(onSuccess, onError);
            await microTick();

            expect.verifySteps(["error:2"]); // POSITION_UNAVAILABLE
        });

        test.tags("secure");
        test("permission-gated requests are rejected", async () => {
            await expect(navigator.credentials.get()).rejects.toThrow(/not allowed/);
            await expect(navigator.storage.getDirectory()).rejects.toThrow(/not allowed/);
            await expect(navigator.storage.persist()).resolves.toBe(false);
            await expect(navigator.wakeLock.request("screen")).rejects.toThrow(/not allowed/);
        });
    });

    test("unmocked native methods can be called", () => {
        expect(navigator.javaEnabled()).toBe(false);
        expect(navigator.javaEnabled).toBe(navigator.javaEnabled);
    });

    test("permission statuses are notified of their changes", async () => {
        const camera = await navigator.permissions.query({ name: "camera" });
        camera.onchange = () => expect.step(camera.state);

        mockPermission("camera", "granted");

        expect.verifySteps(["granted"]);
    });

    test("maxTouchPoints", () => {
        mockTouch(false);

        expect(navigator.maxTouchPoints).toBe(0);

        mockTouch(true);

        expect(navigator.maxTouchPoints).toBe(1);
    });

    describe.tags("secure");
    describe("mediaDevices", () => {
        /** @type {MediaDevices} */
        let mediaDevices;
        /** @type {MediaStreamTrack[]} */
        let tracks = [];

        test("getUserMedia: audio and video", async () => {
            mockPermission("camera", "granted");
            mockPermission("microphone", "granted");

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true,
                video: true,
            });

            expect(stream).toBeInstanceOf(MediaStream);
            expect(stream.getAudioTracks().map((track) => track.kind)).toEqual(["audio"]);
            expect(stream.getVideoTracks().map((track) => track.kind)).toEqual(["video"]);
            expect(stream.getTracks()).toHaveLength(2);

            const [audioTrack] = stream.getAudioTracks();

            expect(stream.getTrackById(audioTrack.id)).toBe(audioTrack);
            expect(audioTrack.readyState).toBe("live");

            audioTrack.stop();

            expect(audioTrack.readyState).toBe("ended");
        });

        test("getUserMedia: permissions", async () => {
            const { mediaDevices } = navigator;
            const microphone = await navigator.permissions.query({ name: "microphone" });
            microphone.onchange = () => expect.step(microphone.state);

            // Denied by default
            await expect(mediaDevices.getUserMedia({ audio: true })).rejects.toThrow(/not allowed/);

            expect.verifySteps([]);

            // "prompt": accepted by the user
            mockPermission("microphone", "prompt");

            await expect(mediaDevices.getUserMedia({ audio: true })).resolves.toBeInstanceOf(
                MediaStream
            );

            expect.verifySteps(["prompt", "granted"]);

            // Any denied device makes the whole request fail
            await expect(mediaDevices.getUserMedia({ audio: true, video: true })).rejects.toThrow(
                /not allowed/
            );
        });

        test("getUserMedia: tracks can be used by native APIs", async () => {
            mockPermission("camera", "granted");
            mockPermission("microphone", "granted");

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true,
                video: true,
            });

            expect(stream.getTracks().every((track) => track instanceof MediaStreamTrack)).toBe(
                true
            );
            expect(new MediaStream(stream.getAudioTracks()).getTracks()).toHaveLength(1);
        });

        test("getUserMedia: no constraints", async () => {
            await expect(navigator.mediaDevices.getUserMedia({})).rejects.toThrow(TypeError);
        });

        test("getDisplayMedia", async () => {
            const stream = await navigator.mediaDevices.getDisplayMedia();

            expect(stream.getAudioTracks()).toHaveLength(0);
            expect(stream.getVideoTracks()).toHaveLength(1);
        });

        // ! WARNING: the following 2 tests need to be run sequentially to work, as they
        // ! attempt to test the in-between-tests media devices cleanup.
        test("tracks are stopped and instance is reset between tests: setup", async () => {
            mockPermission("camera", "granted");
            mockPermission("microphone", "granted");
            mediaDevices = navigator.mediaDevices;
            const stream = await mediaDevices.getUserMedia({ audio: true, video: true });
            tracks = [...stream.getTracks(), ...stream.clone().getTracks()];

            expect(navigator.mediaDevices).toBe(mediaDevices);
            expect(tracks.map((track) => track.readyState)).toEqual([
                "live",
                "live",
                "live",
                "live",
            ]);
        });

        test("tracks are stopped and instance is reset between tests: check", () => {
            expect(navigator.mediaDevices).not.toBe(mediaDevices);
            expect(tracks.map((track) => track.readyState)).toEqual([
                "ended",
                "ended",
                "ended",
                "ended",
            ]);
        });
    });

    test("sendBeacon", () => {
        expect(() => navigator.sendBeacon("/route", new Blob([]))).toThrow(/sendBeacon/);

        mockSendBeacon(expect.step);

        expect.verifySteps([]);

        navigator.sendBeacon("/route", new Blob([]));

        expect.verifySteps(["/route"]);
    });

    test("vibrate", () => {
        expect(() => navigator.vibrate(100)).toThrow(/vibrate/);

        mockVibrate(expect.step);

        expect.verifySteps([]);

        navigator.vibrate(100);

        expect.verifySteps([100]);
    });
});
