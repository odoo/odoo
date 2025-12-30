import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { simulateArrowKeyPress } from "../_helpers/user_actions";

describe("simulateArrowKeyPress method", () => {
    describe("move", () => {
        describe("inside text", () => {
            test("should move up within text", async () => {
                const { el, editor } = await setupEditor(`<p>01</p><p>ab<br>c[]d</p>`);
                await simulateArrowKeyPress(editor, "ArrowUp");
                expect(getContent(el)).toBe(`<p>01</p><p>a[]b<br>cd</p>`);
            });
            test("should move down within text", async () => {
                const { el, editor } = await setupEditor(`<p>a[]b<br>cd</p><p>01</p>`);
                await simulateArrowKeyPress(editor, "ArrowDown");
                expect(getContent(el)).toBe(`<p>ab<br>c[]d</p><p>01</p>`);
            });
            test("should move left within text", async () => {
                const { el, editor } = await setupEditor(`<p>01</p><p>a[]b<br>cd</p>`);
                await simulateArrowKeyPress(editor, "ArrowLeft");
                expect(getContent(el)).toBe(`<p>01</p><p>[]ab<br>cd</p>`);
            });
            test("should move right within text", async () => {
                const { el, editor } = await setupEditor(`<p>ab<br>c[]d</p><p>01</p>`);
                await simulateArrowKeyPress(editor, "ArrowRight");
                expect(getContent(el)).toBe(`<p>ab<br>cd[]</p><p>01</p>`);
            });
        });
        describe("leaving text", () => {
            test("should move up outside text", async () => {
                const { el, editor } = await setupEditor(`<p>xy</p><p>01</p><p>a[]b<br>cd</p>`);
                await simulateArrowKeyPress(editor, "ArrowUp");
                expect(getContent(el)).toBe(`<p>xy</p><p>0[]1</p><p>ab<br>cd</p>`);
            });
            test("should move down outside text", async () => {
                const { el, editor } = await setupEditor(`<p>ab<br>c[]d</p><p>01</p><p>xy</p>`);
                await simulateArrowKeyPress(editor, "ArrowDown");
                expect(getContent(el)).toBe(`<p>ab<br>cd</p><p>0[]1</p><p>xy</p>`);
            });
            test("should move left outside text", async () => {
                const { el, editor } = await setupEditor(`<p>xy</p><p>01</p><p>[]ab<br>cd</p>`);
                await simulateArrowKeyPress(editor, "ArrowLeft");
                expect(getContent(el)).toBe(`<p>xy</p><p>01[]</p><p>ab<br>cd</p>`);
            });
            test("should move right outside text", async () => {
                const { el, editor } = await setupEditor(`<p>ab<br>cd[]</p><p>01</p><p>xy</p>`);
                await simulateArrowKeyPress(editor, "ArrowRight");
                expect(getContent(el)).toBe(`<p>ab<br>cd</p><p>[]01</p><p>xy</p>`);
            });
        });
    });
    describe("select", () => {
        describe("inside text", () => {
            test("should move up within text", async () => {
                const { el, editor } = await setupEditor(`<p>01</p><p>ab<br>c[]d</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowUp"]);
                expect(getContent(el)).toBe(`<p>01</p><p>a]b<br>c[d</p>`);
            });
            test("should move down within text", async () => {
                const { el, editor } = await setupEditor(`<p>a[]b<br>cd</p><p>01</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowDown"]);
                expect(getContent(el)).toBe(`<p>a[b<br>c]d</p><p>01</p>`);
            });
            test("should move left within text", async () => {
                const { el, editor } = await setupEditor(`<p>01</p><p>a[]b<br>cd</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowLeft"]);
                expect(getContent(el)).toBe(`<p>01</p><p>]a[b<br>cd</p>`);
            });
            test("should move right within text", async () => {
                const { el, editor } = await setupEditor(`<p>ab<br>c[]d</p><p>01</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowRight"]);
                expect(getContent(el)).toBe(`<p>ab<br>c[d]</p><p>01</p>`);
            });
        });
        describe("leaving text", () => {
            test("should move up outside text", async () => {
                const { el, editor } = await setupEditor(`<p>xy</p><p>01</p><p>a[]b<br>cd</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowUp"]);
                expect(getContent(el)).toBe(`<p>xy</p><p>0]1</p><p>a[b<br>cd</p>`);
            });
            test("should move down outside text", async () => {
                const { el, editor } = await setupEditor(`<p>ab<br>c[]d</p><p>01</p><p>xy</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowDown"]);
                expect(getContent(el)).toBe(`<p>ab<br>c[d</p><p>0]1</p><p>xy</p>`);
            });
            test("should move left outside text", async () => {
                const { el, editor } = await setupEditor(`<p>xy</p><p>01</p><p>[]ab<br>cd</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowLeft"]);
                expect(getContent(el)).toBe(`<p>xy</p><p>01]</p><p>[ab<br>cd</p>`);
            });
            test("should move right outside text", async () => {
                const { el, editor } = await setupEditor(`<p>ab<br>cd[]</p><p>01</p><p>xy</p>`);
                await simulateArrowKeyPress(editor, ["Shift", "ArrowRight"]);
                expect(getContent(el)).toBe(`<p>ab<br>cd[</p><p>]01</p><p>xy</p>`);
            });
        });
        describe("through separator", () => {
            test("should move up a single time", async () => {
                const { el, editor } = await setupEditor(`<p>abc</p><p>x</p><hr><p>[]yz</p>`);
                expect(getContent(el)).toBe(
                    `<p>abc</p><p>x</p><hr contenteditable="false"><p>[]yz</p>`
                );
                await simulateArrowKeyPress(editor, ["Shift", "ArrowUp"]);
                expect(getContent(el)).toBe(
                    `<p>abc</p><p>x]</p><hr contenteditable="false"><p>[yz</p>`
                );
            });
        });
    });
});
