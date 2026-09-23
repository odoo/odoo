// @ts-check
import { mockBlurManager } from "@mail/../tests/discuss/call/mock_blur_manager";
import {
    contains,
    defineMailModels,
    mockGetMedia,
    start,
} from "@mail/../tests/mail_test_helpers";
import { CallPreview } from "@mail/discuss/call/common/call_preview";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("enabling the camera preview reports the camera state even before the video element mounts", async () => {
    mockGetMedia();
    await start();
    const settings = [];
    await mountWithCleanup(CallPreview, {
        props: {
            activateCamera: 1,
            onSettingsChanged: (s) => settings.push(s),
        },
    });
    await contains("video");
    expect(settings).toEqual([{ camera: true }]);
});

test("closing the preview tears down the blur manager and its stream", async () => {
    mockGetMedia();
    const managers = mockBlurManager();
    await start();
    class Parent extends Component {
        static components = { CallPreview };
        static props = [];
        static template = xml`
            <CallPreview t-if="this.state.show" activateCamera="1" onSettingsChanged="() => {}"/>
        `;
        setup() {
            this.state = useState({ show: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await contains("video");

    getService("mail.store").settings.setUseBlur(true);
    await animationFrame();
    expect(managers).toHaveLength(1);
    const manager = managers[0];
    expect(manager.closed).toBe(false);
    expect(manager.blurStream.getVideoTracks()[0].readyState).toBe("live");

    parent.state.show = false;
    await animationFrame();

    expect(manager.closed).toBe(true);
    expect(manager.blurStream.getVideoTracks()[0].readyState).toBe("ended");
});

test("a destroyed preview stops reacting to call settings", async () => {
    mockGetMedia();
    const managers = mockBlurManager();
    await start();
    class Parent extends Component {
        static components = { CallPreview };
        static props = [];
        static template = xml`
            <CallPreview t-if="this.state.show" activateCamera="1" onSettingsChanged="() => {}"/>
        `;
        setup() {
            this.state = useState({ show: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await contains("video");
    parent.state.show = false;
    await animationFrame();

    getService("mail.store").settings.setUseBlur(true);
    await animationFrame();
    expect(managers).toHaveLength(0);
});
