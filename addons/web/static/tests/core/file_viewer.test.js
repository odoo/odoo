import { expect, test, waitFor } from "@odoo/hoot";
import { click, press } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { FileModel } from "@web/core/file_viewer/file_model";
import { FileViewer } from "@web/core/file_viewer/file_viewer";

test("can delete an attachment from the file viewer", async () => {
    const attachment = Object.assign(new FileModel(), {
        id: 1,
        name: "test_image.png",
        mimetype: "image/png",
    });
    await mountWithCleanup(FileViewer, {
        props: {
            files: [attachment],
            startIndex: 0,
            canUnlink: () => true,
            onUnlink: (file) => {
                expect.step(`delete_file ${file.name}`);
                return true;
            },
        },
    });
    await waitFor(".o-FileViewer");
    await click(".o-FileViewer-headerButton[title='Remove']");
    expect.verifySteps(["delete_file test_image.png"]);
});

/**
 * @returns {FileModel}
 */
function makeImage() {
    return Object.assign(new FileModel(), {
        id: 1,
        name: "test_image.png",
        mimetype: "image/png",
    });
}

const RESET_ZOOM_BUTTON =
    ".o-FileViewer-toolbar .o-FileViewer-toolbarButton[title='Reset Zoom (0)']";
const ZOOM_IN_BUTTON = ".o-FileViewer-toolbar .o-FileViewer-toolbarButton[title='Zoom In (+)']";
const ZOOM_OUT_BUTTON = ".o-FileViewer-toolbar .o-FileViewer-toolbarButton[title='Zoom Out (-)']";

function imageAtScale(scale) {
    return `.o-FileViewer-viewImage[style*='scale3d(${scale}, ${scale}, 1)']`;
}

test("image toolbar exposes its buttons", async () => {
    await mountWithCleanup(FileViewer, {
        props: { files: [makeImage()], startIndex: 0 },
    });
    await waitFor(".o-FileViewer-toolbar");
    expect(".o-FileViewer-toolbar").toHaveAttribute("role", "toolbar");
    expect(ZOOM_IN_BUTTON).toHaveCount(1);
    expect(RESET_ZOOM_BUTTON).toHaveCount(1);
    expect(`${RESET_ZOOM_BUTTON} i`).toHaveAttribute("data-icon", "recenter");
    expect(ZOOM_OUT_BUTTON).toHaveCount(1);
    expect(".o-FileViewer-toolbar [title='Rotate (r)']").toHaveCount(1);
    expect(".o-FileViewer-toolbar [title='Print']").toHaveCount(1);
    expect(".o-FileViewer-toolbar .o-FileViewer-download").toHaveCount(1);
});

test("reset zoom button is inert at default zoom and active once zoomed", async () => {
    await mountWithCleanup(FileViewer, {
        props: { files: [makeImage()], startIndex: 0 },
    });
    await waitFor(".o-FileViewer-toolbar");
    expect(RESET_ZOOM_BUTTON).toHaveClass(["pe-none", "text-muted"]);
    expect(RESET_ZOOM_BUTTON).toHaveAttribute("aria-disabled", "true");

    await click(ZOOM_IN_BUTTON);
    await waitFor(imageAtScale(1.5));
    expect(RESET_ZOOM_BUTTON).not.toHaveClass("pe-none");
    expect(RESET_ZOOM_BUTTON).not.toHaveClass("text-muted");
    expect(RESET_ZOOM_BUTTON).not.toHaveAttribute("aria-disabled");

    await click(RESET_ZOOM_BUTTON);
    await waitFor(imageAtScale(1));
    expect(RESET_ZOOM_BUTTON).toHaveClass(["pe-none", "text-muted"]);
    expect(RESET_ZOOM_BUTTON).toHaveAttribute("aria-disabled", "true");
});

test("zoom out button is inert at minimum zoom", async () => {
    await mountWithCleanup(FileViewer, {
        props: { files: [makeImage()], startIndex: 0 },
    });
    await waitFor(".o-FileViewer-toolbar");
    expect(ZOOM_OUT_BUTTON).not.toHaveClass("pe-none");
    expect(ZOOM_OUT_BUTTON).not.toHaveAttribute("aria-disabled");

    // a single zoom out step (0.5) brings the scale down to the minimum (0.5)
    await click(ZOOM_OUT_BUTTON);
    await waitFor(imageAtScale(0.5));
    expect(ZOOM_OUT_BUTTON).toHaveClass(["pe-none", "text-muted"]);
    expect(ZOOM_OUT_BUTTON).toHaveAttribute("aria-disabled", "true");

    await click(ZOOM_IN_BUTTON);
    await waitFor(imageAtScale(1));
    expect(ZOOM_OUT_BUTTON).not.toHaveClass("pe-none");
    expect(ZOOM_OUT_BUTTON).not.toHaveAttribute("aria-disabled");
});

test("keyboard shortcuts still work after the focused button is removed", async () => {
    const pdf = Object.assign(new FileModel(), {
        id: 2,
        name: "test_pdf.pdf",
        mimetype: "application/pdf",
    });
    await mountWithCleanup(FileViewer, {
        props: {
            files: [makeImage(), pdf],
            startIndex: 0,
            close: () => expect.step("close"),
        },
    });
    await waitFor(".o-FileViewer-toolbar");
    await click(ZOOM_IN_BUTTON);
    await waitFor(imageAtScale(1.5));
    expect(ZOOM_IN_BUTTON).toBeFocused();

    // switching to the PDF removes the image toolbar, and its focused button
    await press("ArrowRight");
    await waitFor(".o-FileViewer-header:contains(test_pdf.pdf)");
    expect(".o-FileViewer-toolbar").toHaveCount(0);
    expect(".o-FileViewer").toBeFocused();

    await press("ArrowLeft");
    await waitFor(".o-FileViewer-header:contains(test_image.png)");
    await press("Escape");
    expect.verifySteps(["close"]);
});
