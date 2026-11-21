import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { makeRoot } from "@im_livechat/embed/common/boot_helpers";
import {
    capBrightness,
    getContrastColor,
    MAX_BRIGHTNESS_FOR_WHITE_CONTRAST,
    normalizeBrightness,
} from "@im_livechat/embed/common/color_utils";
import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineLivechatModels();

test("contrast color is white on dark colors, dark on light ones", () => {
    expect(getContrastColor("#000000")).toBe("#FFFFFF");
    expect(getContrastColor("#71639e")).toBe("#FFFFFF");
    expect(getContrastColor("#ffffff")).toBe("#212529");
    expect(getContrastColor("#f0cda8")).toBe("#212529");
});

test("brightness cap keeps enough contrast against white", () => {
    expect(capBrightness("#71639e", MAX_BRIGHTNESS_FOR_WHITE_CONTRAST)).toBe("#71639e");
    for (const color of ["#ffffff", "#ffff00", "#f0cda8", "#4ea7f2"]) {
        const capped = capBrightness(color, MAX_BRIGHTNESS_FOR_WHITE_CONTRAST);
        expect(getContrastColor(capped)).toBe("#FFFFFF", { message: `${color} -> ${capped}` });
    }
});

test("normalized brightness does not depend on how light the color is", () => {
    // Black and white end up on the same gray.
    expect(normalizeBrightness("#000000", 0.55)).toBe("#8c8c8c");
    expect(normalizeBrightness("#ffffff", 0.55)).toBe("#8c8c8c");
});

test("livechat root exposes the configured colors as CSS variables", async () => {
    await loadDefaultEmbedConfig();
    const root = makeRoot(document.createElement("div"));
    expect(root.style.getPropertyValue("--o-mail-livechat-primary")).toBe("#875A7B");
    expect(root.style.getPropertyValue("--o-mail-livechat-primary-text")).toBe("#FFFFFF");
    expect(root.style.getPropertyValue("--o-mail-livechat-secondary")).toBe("#4EA7F2");
    expect(root.style.getPropertyValue("--o-mail-livechat-secondary-text")).toBe("#212529");
    expect(root.style.getPropertyValue("--o-mail-livechat-bubble-bg-ratio")).toBe("45%");
});
