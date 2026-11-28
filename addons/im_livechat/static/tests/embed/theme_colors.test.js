import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { makeRoot } from "@im_livechat/embed/common/boot_helpers";
import {
    capBrightness,
    getBubbleColors,
    getContrastColor,
    MAX_BRIGHTNESS_FOR_WHITE_CONTRAST,
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

test("brightness cap keeps the hue", () => {
    // A light yellow stays a yellow, only darker.
    const capped = capBrightness("#ffff00", MAX_BRIGHTNESS_FOR_WHITE_CONTRAST);
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(capped.substring(i, i + 2), 16));
    expect(r > b && g > b).toBe(true, { message: capped });
});

test("bubble lightness does not depend on how light the color is", () => {
    // Black and white end up on the same gray.
    expect(getBubbleColors("#000000", 0.87, 0.06).background).toBe("#d4d4d4");
    expect(getBubbleColors("#ffffff", 0.87, 0.06).background).toBe("#d4d4d4");
});

test("bubbles of the same color stay apart for each role", () => {
    const visitor = getBubbleColors("#848585", 0.87, 0.06);
    const operator = getBubbleColors("#848585", 0.95, 0.04);
    expect(visitor.background).not.toBe(operator.background);
    expect(getContrastColor(visitor.background)).toBe("#212529");
    expect(getContrastColor(operator.background)).toBe("#212529");
});

test("livechat root exposes the configured colors as CSS variables", async () => {
    await loadDefaultEmbedConfig();
    const root = makeRoot(document.createElement("div"));
    expect(root.style.getPropertyValue("--o-mail-livechat-primary")).toBe("#875A7B");
    expect(root.style.getPropertyValue("--o-mail-livechat-primary-text")).toBe("#FFFFFF");
    expect(root.style.getPropertyValue("--o-mail-livechat-secondary")).toBe("#4EA7F2");
    expect(root.style.getPropertyValue("--o-mail-livechat-secondary-text")).toBe("#212529");
    expect(root.style.getPropertyValue("--o-mail-livechat-primary-bubble-bg")).toMatch(/^#[0-9a-f]{6}$/);
});
