// @ts-check

import { describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame, click, hover, pointerDown, pointerUp } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { FileModel } from "@web/components/file_viewer/file_model";
import { FileViewer } from "@web/components/file_viewer/file_viewer";
import { createFileViewer } from "@web/components/file_viewer/file_viewer_hook";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

describe.current.tags("desktop");

const IMAGE_SOURCE =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

const IMAGE_FILE = {
    name: "test.png",
    defaultSource: IMAGE_SOURCE,
    downloadUrl: "/web/content/1?download=true",
    isImage: true,
    isViewable: true,
};

const TEXT_FILE = {
    name: "test.txt",
    defaultSource: "about:blank",
    downloadUrl: "/web/content/2?download=true",
    isText: true,
    isViewable: true,
};

test("releasing an image pan outside the image does not close the viewer", async () => {
    const viewer = await mountWithCleanup(FileViewer, {
        props: {
            files: [IMAGE_FILE],
            startIndex: 0,
            close: () => expect.step("close"),
        },
    });

    await pointerDown(".o-FileViewer-viewImage");
    expect(viewer.isDragging).toBe(true);

    await hover(".o-FileViewer-main", { position: { x: 5, y: 5 } });
    expect(viewer.didDrag).toBe(true);

    await pointerUp(".o-FileViewer-main");
    expect(viewer.isDragging).toBe(false);
    expect.verifySteps([]);

    await hover(".o-FileViewer-main", { position: { x: 60, y: 60 } });
    expect(viewer.translate.dx).toBe(0);
    expect(viewer.translate.dy).toBe(0);

    await click(".o-FileViewer-main");
    expect.verifySteps(["close"]);
});

test("switching file resets the iframe loaded state", async () => {
    const viewer = await mountWithCleanup(FileViewer, {
        props: {
            files: [TEXT_FILE, IMAGE_FILE],
            startIndex: 0,
            close: () => {},
        },
    });

    viewer.state.isIframeLoaded = true;
    await click(".o-FileViewer-navigation[aria-label='Next']");
    expect(viewer.state.isIframeLoaded).toBe(false);
    expect(viewer.state.index).toBe(1);
});

test("re-anchors on a new files list", async () => {
    const other = { ...IMAGE_FILE, name: "other.png" };
    /** @type {(files: any[]) => void} */
    let update;
    class Parent extends Component {
        static components = { FileViewer };
        static props = {};
        static template = xml`<FileViewer files="this.state.files" startIndex="0" modal="false"/>`;

        /** @type {{ files: any[] }} */
        state;

        setup() {
            this.state = useState({ files: [IMAGE_FILE, other] });
            update = (files) => (this.state.files = files);
        }
    }
    await mountWithCleanup(Parent);
    expect(".o-FileViewer-header .text-truncate").toHaveText("test.png");

    update([other, IMAGE_FILE]);
    await animationFrame();
    expect(".o-FileViewer-header .text-truncate").toHaveText("test.png");

    update([other]);
    await animationFrame();
    expect(".o-FileViewer-header .text-truncate").toHaveText("other.png");

    update([]);
    await animationFrame();
    expect(".o-FileViewer").toHaveCount(0);
});

test("re-anchors on a plain (non-reactive) files list", async () => {
    const other = { ...IMAGE_FILE, name: "other.png" };
    /** @type {() => void} */
    let reorder;
    class Parent extends Component {
        static components = { FileViewer };
        static props = {};
        static template = xml`<FileViewer files="this.files" startIndex="0" modal="false"/>`;
        setup() {
            this.state = useState({ flipped: false });
            this.rawFiles = [IMAGE_FILE, other];
            reorder = () => {
                this.rawFiles = [other, IMAGE_FILE];
                this.state.flipped = true;
            };
        }
        get files() {
            return this.rawFiles;
        }
    }
    await mountWithCleanup(Parent);
    expect(".o-FileViewer-header .text-truncate").toHaveText("test.png");

    reorder();
    await animationFrame();
    expect(".o-FileViewer-header .text-truncate").toHaveText("test.png");
});

test("youtube URLs are matched on the host, not on a substring", async () => {
    const videoId = (url) =>
        Object.assign(new FileModel(), { type: "url", url }).youtubeVideoId;

    expect([
        videoId("https://www.youtube.com/watch?v=abc123"),
        videoId("https://youtube.com/watch?app=desktop&v=abc123&t=30"),
        videoId("https://youtu.be/abc123"),
        videoId("https://youtu.be/abc123?t=30"),
        videoId("https://www.youtube.com/embed/abc123"),
        videoId("https://www.youtube.com/shorts/abc123"),
        videoId("https://www.youtube-nocookie.com/embed/abc123"),
    ]).toEqual(Array(7).fill("abc123"));

    const impostor = Object.assign(new FileModel(), {
        type: "url",
        url: "https://example.com/my-youtube-clone/page",
    });
    expect(impostor.isUrlYoutube).toBe(false);
    expect(impostor.defaultSource).not.toInclude("youtube.com/embed");

    expect(videoId("https://youtube.evil.com/watch?v=abc123")).toBe(null);
});

test("dragging an image measures the layout once per frame, not once per event", async () => {
    let measures = 0;
    class Probe extends FileViewer {
        updateZoomerStyle() {
            measures++;
            return super.updateZoomerStyle();
        }
    }
    const viewer = await mountWithCleanup(Probe, {
        props: { files: [IMAGE_FILE], startIndex: 0, modal: false },
    });
    await animationFrame();
    viewer.zoomIn();
    viewer.zoomIn();
    await animationFrame();

    measures = 0;
    await pointerDown(".o-FileViewer-viewImage", { position: { x: 0, y: 0 } });
    for (let i = 1; i <= 20; i++) {
        await hover(".o-FileViewer-main", { position: { x: i * 3, y: i * 2 } });
    }
    expect(measures).toBeLessThan(20);
    expect(viewer.translate.dx).toBe(60);
    expect(viewer.translate.dy).toBe(40);

    const beforeDrop = measures;
    await pointerUp(".o-FileViewer-main");
    expect(measures).toBeGreaterThan(beforeDrop);
    expect(viewer.translate.dx).toBe(0);
    expect(viewer.translate.dy).toBe(0);
});

test("the viewer recovers when the file list empties and refills", async () => {
    const other = { ...IMAGE_FILE, name: "other.png" };
    class Parent extends Component {
        static props = ["*"];
        static components = { FileViewer };
        static template = xml`<FileViewer files="this.state.files" startIndex="0"/>`;
        setup() {
            this.state = useState({ files: [IMAGE_FILE] });
        }
    }
    const parent = await mountWithCleanup(Parent);
    expect(".o-FileViewer").toHaveCount(1);

    parent.state.files = [];
    await animationFrame();
    expect(".o-FileViewer").toHaveCount(0);

    parent.state.files = [other];
    await animationFrame();
    expect(".o-FileViewer").toHaveCount(1);
});

test("a rotated image is re-sized when the window is", async () => {
    patchWithCleanup(browser, { innerWidth: 1000, innerHeight: 600 });
    const viewer = await mountWithCleanup(FileViewer, {
        props: { files: [IMAGE_FILE], startIndex: 0, close: () => {} },
    });
    viewer.rotate();
    await animationFrame();
    expect(viewer.imageStyle).toInclude("max-height: 1000px");
    expect(viewer.imageStyle).toInclude("max-width: 600px");

    patchWithCleanup(browser, { innerWidth: 500, innerHeight: 900 });
    browser.dispatchEvent(new Event("resize"));
    await animationFrame();
    expect(viewer.imageStyle).toInclude("max-height: 500px");
    expect(viewer.imageStyle).toInclude("max-width: 900px");
});

test("printing closes the window when the job is handed off, not on a timer", async () => {
    let closed = false;
    let printed = false;
    let fallbackDelay = null;
    const frame = document.createElement("iframe");
    getFixture().append(frame);
    const printWindow = frame.contentWindow;
    patchWithCleanup(printWindow, {
        print: () => {
            printed = true;
        },
        close: () => {
            closed = true;
        },
        setTimeout: (/** @type {Function} */ fn, /** @type {number} */ ms) => {
            fallbackDelay = ms;
            return 1;
        },
    });
    patchWithCleanup(browser, { open: () => printWindow });

    const viewer = await mountWithCleanup(FileViewer, {
        props: { files: [IMAGE_FILE], startIndex: 0, close: () => {} },
    });
    viewer.onClickPrint();
    expect(printed).toBe(false);

    printWindow.document.body.firstChild.dispatchEvent(new Event("load"));
    expect(printed).toBe(true);
    expect(closed).toBe(false, { message: "not closed out from under the dialog" });
    expect(fallbackDelay).toBe(1000, { message: "a fallback, not the mechanism" });

    printWindow.dispatchEvent(new Event("afterprint"));
    expect(closed).toBe(true);
});

test("zoom is bounded at both ends", async () => {
    const viewer = await mountWithCleanup(FileViewer, {
        props: { files: [IMAGE_FILE], startIndex: 0, close: () => {} },
    });

    for (let i = 0; i < 40; i++) {
        viewer.zoomOut({ scroll: true });
    }
    expect(viewer.state.scale).toBe(viewer.minScale);

    for (let i = 0; i < 400; i++) {
        viewer.zoomIn({ scroll: true });
    }
    expect(viewer.state.scale).toBe(viewer.maxScale);

    viewer.resetZoom();
    expect(viewer.state.scale).toBe(1);
});

describe("createFileViewer", () => {
    /** @returns {any} */
    function registeredViewer() {
        return registry
            .category("main_components")
            .getEntries()
            .find(([key]) => key.startsWith("web.file_viewer"))?.[1];
    }

    test("a list with nothing viewable in it opens no viewer", () => {
        const { open, close } = createFileViewer();
        open(IMAGE_FILE, [{ name: "b.bin", isViewable: false }]);
        expect(registeredViewer()).toBe(undefined);
        close();
    });

    test("the viewable members of the list are what the viewer gets", () => {
        const { open, close } = createFileViewer();
        open(IMAGE_FILE, [{ name: "b.bin", isViewable: false }, IMAGE_FILE]);
        expect(registeredViewer().props.files).toEqual([IMAGE_FILE]);
        expect(registeredViewer().props.startIndex).toBe(0);
        close();
        expect(registeredViewer()).toBe(undefined);
    });
});

test("an audio recording is viewable, and is not a video", async () => {
    for (const mimetype of [
        "audio/aac",
        "audio/flac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/opus",
        "audio/wav",
        "audio/webm",
        "audio/x-m4a",
        "audio/x-wav",
    ]) {
        const file = new FileModel();
        file.mimetype = mimetype;
        file.name = `recording.${mimetype}`;
        file.id = 1;
        expect(file.isAudio).toBe(true, { message: `${mimetype} is audio` });
        expect(file.isVideo).toBe(false, { message: `${mimetype} is not video` });
        expect(file.isViewable).toBe(true, { message: `${mimetype} is viewable` });
    }
});

test("a viewable recording renders a player rather than a dead Preview", async () => {
    const AUDIO_FILE = {
        name: "call.webm",
        defaultSource: "about:blank",
        downloadUrl: "/web/content/9?download=true",
        isAudio: true,
        isViewable: true,
    };
    await mountWithCleanup(FileViewer, {
        props: { files: [AUDIO_FILE], startIndex: 0, close: () => {} },
    });
    expect("audio").toHaveCount(1);
    expect("video").toHaveCount(0);
});
