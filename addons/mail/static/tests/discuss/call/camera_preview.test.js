import { createVideoStream, defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { CameraPreview } from "@mail/discuss/call/common/camera_preview";
import { Rtc } from "@mail/discuss/call/common/rtc_service";

import { describe, expect, getFixture, test, waitFor } from "@odoo/hoot";

import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

test("Camera preview shares a single stream across multiple instances", async () => {
    const cameraRequests = [];
    patch(navigator.mediaDevices, {
        getUserMedia(constraints) {
            const stream = createVideoStream();
            expect.step(`camera request ${cameraRequests.length}`);
            return new Promise((resolve) => {
                resolve(stream);
                cameraRequests.push({ constraints, stream });
            });
        },
    });
    await start();
    const rtc = getService("discuss.rtc");
    rtc.cameraPermission = "granted";
    await mountWithCleanup(CameraPreview);
    await mountWithCleanup(CameraPreview);
    await expect.waitForSteps(["camera request 0"]);
    const videos = getFixture().querySelectorAll("video");
    expect(videos[0].srcObject).toBe(videos[1].srcObject);
});

test("Camera preview restarts on device change and ignores stale blur results", async () => {
    const cameraRequests = [];
    patch(navigator.mediaDevices, {
        getUserMedia(constraints) {
            const deferred = Promise.withResolvers();
            const stream = createVideoStream();
            cameraRequests.push({ constraints, deferred, stream });
            expect.step(`camera request ${cameraRequests.length}`);
            return deferred.promise;
        },
    });
    const blurRequest = Promise.withResolvers();
    const blurredStream = createVideoStream();
    patch(Rtc.prototype, {
        applyBlurEffect() {
            expect.step("blur requested");
            return { stream: blurRequest.promise, close: () => expect.step("blur closed") };
        },
    });
    await start();
    const rtc = getService("discuss.rtc");
    const store = getService("mail.store");
    rtc.cameraPermission = "granted";
    store.settings.useBlur = false;
    const cameraPreview = await mountWithCleanup(CameraPreview);
    await expect.waitForSteps(["camera request 1"]);
    store.settings.useBlur = true;
    cameraRequests[0].deferred.resolve(cameraRequests[0].stream);
    await expect.waitForSteps(["blur requested"]);
    store.settings.cameraInputDeviceId = "selectedCamera";
    store.settings.useBlur = false;
    await expect.waitForSteps(["blur closed"]);
    blurRequest.resolve(blurredStream);
    await blurRequest.promise;
    expect(cameraPreview.state.blurStream).toBe(null);
    await expect.waitForSteps(["camera request 2"]);
    cameraRequests[1].deferred.resolve(cameraRequests[1].stream);
    const video = await waitFor("video:count(1)");
    expect(cameraRequests.map(({ constraints }) => constraints.video.deviceId)).toEqual([
        undefined,
        "selectedCamera",
    ]);
    const liveCameraStreams = cameraRequests.filter(({ stream }) =>
        stream.getTracks().some((track) => track.readyState === "live")
    );
    expect(liveCameraStreams).toHaveLength(1);
    expect(liveCameraStreams[0].constraints.video.deviceId).toBe("selectedCamera");
    expect(video.srcObject).toBe(liveCameraStreams[0].stream);
});
