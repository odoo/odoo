import { rgbToHex, rgbaToHex, blendColors } from "@html_editor/utils/color";
import { expect, getFixture, test } from "@odoo/hoot";

test("should convert an rgb and rgba color to hexadecimal", async () => {
    expect(rgbToHex("rgb(0, 0, 255)")).toBe("#0000ff");
    expect(rgbToHex("rgb(0,0,255)")).toBe("#0000ff");
    expect(rgbaToHex("rgba(0, 0, 255, 0.5)")).toBe("#0000ff80");
});

test("should convert an rgba color to hexadecimal (background is hexadecimal)", async () => {
    const parent = getFixture();
    const node = document.createElement("div");
    parent.style.backgroundColor = "#ff0000"; // red, should be irrelevant
    node.style.backgroundColor = "#0000ff"; // blue
    parent.append(node);
    // white with 50% opacity over blue = light blue
    expect(rgbToHex("rgba(255, 255, 255, 0.5)", node)).toBe("#7f7fff");
    expect(blendColors("rgba(255, 255, 255, 0.5)", node)).toBe("#8080ff");
});

test("should convert an rgba color to hexadecimal (background is color name)", async () => {
    const parent = getFixture();
    const node = document.createElement("div");
    parent.style.backgroundColor = "#ff0000"; // red, should be irrelevant
    node.style.backgroundColor = "blue"; // blue
    parent.append(node);
    // white with 50% opacity over blue = light blue
    expect(rgbToHex("rgba(255, 255, 255, 0.5)", node)).toBe("#7f7fff");
    expect(blendColors("rgba(255, 255, 255, 0.5)", node)).toBe("#8080ff");
});

test("should convert an rgba color to hexadecimal (background is rgb)", async () => {
    const parent = getFixture();
    const node = document.createElement("div");
    parent.style.backgroundColor = "#ff0000"; // red, should be irrelevant
    node.style.backgroundColor = "rgb(0, 0, 255)"; // blue
    parent.append(node);
    // white with 50% opacity over blue = light blue
    expect(rgbToHex("rgba(255, 255, 255, 0.5)", node)).toBe("#7f7fff");
    expect(blendColors("rgba(255, 255, 255, 0.5)", node)).toBe("#8080ff");
    parent.remove();
});

test("should convert an rgba color to hexadecimal (background is rgba)", async () => {
    const parent = getFixture();
    const node = document.createElement("div");
    parent.style.backgroundColor = "rgb(255, 0, 0)"; // red
    node.style.backgroundColor = "rgba(0, 0, 255, 0.5)"; // blue
    parent.append(node);
    // white with 50% opacity over blue with 50% opacity over red = light purple
    expect(rgbToHex("rgba(255, 255, 255, 0.5)", node)).toBe("#bf7fbf");
    expect(blendColors("rgba(255, 255, 255, 0.5)", node)).toBe("#c080c0");
});
