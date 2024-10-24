import { test, describe, beforeEach, expect } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { deleteBackward, keydownShiftTab, keydownTab, splitBlock } from "../_helpers/user_actions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    EmbeddedToggleComponent,
    toggleEmbedding,
} from "@html_editor/others/embedded_components/core/toggle/toggle";
import { onMounted } from "@odoo/owl";
import { Deferred } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import { TogglePlugin } from "@html_editor/others/embedded_components/plugins/toggle_plugin/toggle_plugin";
import { getContent } from "../_helpers/selection";
import { animationFrame } from "@odoo/hoot-dom";

let embeddedToggleMountedPromise;

function getConfig(components) {
    return {
        Plugins: [...MAIN_PLUGINS, EmbeddedComponentPlugin, TogglePlugin],
        resources: {
            embedded_components: components,
        },
    };
}

beforeEach(() => {
    embeddedToggleMountedPromise = new Deferred();
    patchWithCleanup(EmbeddedToggleComponent.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                embeddedToggleMountedPromise.resolve();
            });
        },
    });
});

describe("deleteBackward applied to toggle", () => {
    test("toggle open: should be inside the content", async () => {
        browser.localStorage.setItem(`Toggle1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<p><br></p>
                <div data-embedded="toggle" data-oe-protected="true" data-embedded-props='{ "toggleId": "1" }' contenteditable="false" class="mb-2">
                    <div data-embedded-editable="title">
                        <p>Hello World<br></p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf<br></p>
                    </div>
                </div>
                <p>[]<br></p>
            `
            ),
            {
                config: getConfig([toggleEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            unformat(`
            <p><br></p>
                <div data-embedded="toggle" data-oe-protected="true" data-embedded-props='{ "toggleId": "1" }' contenteditable="false" class="mb-2">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf[]<br></p>
                        </div>
                    </div>
                </div>`)
        );
    });
    test("toggle closed: should be inside the title", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<p><br></p>
                <div data-embedded="toggle" data-oe-protected="true" data-embedded-props='{ "toggleId": "1" }' contenteditable="false" class="mb-2">
                    <div data-embedded-editable="title">
                        <p>Hello World<br></p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf<br></p>
                    </div>
                </div>
                <p>[]<br></p>
            `
            ),
            {
                config: getConfig([toggleEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            unformat(`
            <p><br></p>
                <div data-embedded="toggle" data-oe-protected="true" data-embedded-props='{ "toggleId": "1" }' contenteditable="false" class="mb-2">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello World[]<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf<br></p>
                        </div>
                    </div>
                </div>`)
        );
    });
    test("delete title: content to restore", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<p><br></p>
                <div data-embedded="toggle" data-oe-protected="true" data-embedded-props='{ "toggleId": "1" }' contenteditable="false" class="mb-2">
                    <div data-embedded-editable="title">
                        <p>[]Hello World<br></p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>Good<br></p>
                        <p>Riddance<br></p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            unformat(`
            <p><br></p>
            <p>[]Hello World</p>
            <p>Good<br></p>
            <p>Riddance<br></p>
            `)
        );
    });
});
describe("Enter applied to toggle title", () => {
    describe("Enter on closed toggle: creates new toggle", () => {
        test("Split title + content follows new toggle", async () => {
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" data-embedded-props='{ "toggleId": "1" }' contenteditable="false" class="mb-2">
                        <div data-embedded-editable="title">
                            <p>Hello []World<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <p>asdf<br></p>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            patchWithCleanup(TogglePlugin.prototype, {
                getUniqueIdentifier() {
                    return "2";
                },
            });
            embeddedToggleMountedPromise = new Deferred();
            splitBlock(editor);
            await embeddedToggleMountedPromise;
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{"toggleId":"2"}'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p><br></p>
                        </div>
                    </div>
                </div>
                <div data-embedded="toggle" data-oe-protected="true" data-embedded-props='{ "toggleId": "1" }' contenteditable="false" class="mb-2">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>[]World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf<br></p>
                        </div>
                    </div>
                </div>
            `)
            );
        });
        test("Don't split title", async () => {
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                        <div data-embedded-editable="title">
                            <p>Hello World[]<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <p>asdf<br></p>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            patchWithCleanup(TogglePlugin.prototype, {
                getUniqueIdentifier() {
                    return "2";
                },
            });
            embeddedToggleMountedPromise = new Deferred();
            splitBlock(editor);
            await embeddedToggleMountedPromise;
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf<br></p>
                        </div>
                    </div>
                </div>
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{"toggleId":"2"}'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p placeholder="Toggle Title" class="o-we-hint">[]<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p><br></p>
                        </div>
                    </div>
                </div>
            `)
            );
        });
    });
    describe("Enter on open toggle: setSelection in content", () => {
        test("Split title", async () => {
            browser.localStorage.setItem(`Toggle1.showContent`, "true");
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                        <div data-embedded-editable="title">
                            <p>Hello World[]<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <p>asdf<br></p>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            splitBlock(editor);
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf[]<br></p>
                        </div>
                    </div>
                </div>`)
            );
        });
        test("Don't split title", async () => {
            browser.localStorage.setItem(`Toggle1.showContent`, "true");
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                        <div data-embedded-editable="title">
                            <p>Hello []World<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <p>asdf<br></p>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            splitBlock(editor);
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello <br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>[]World<br></p>
                            <p>asdf<br></p>
                        </div>
                    </div>
                </div>`)
            );
        });
    });
});
describe("tab and shift+tab applied to toggle title", () => {
    describe("Use tab in different situations", () => {
        test("Tab moves down a level: normal toggle", async () => {
            browser.localStorage.setItem(`Toggle1.showContent`, "true");
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                        <div data-embedded-editable="title">
                            <p>Goodbye World<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <p><br></p>
                        </div>
                    </div>
                    <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                        <div data-embedded-editable="title">
                            <p>Hello []World<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <p>asdf<br></p>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            await keydownTab(editor);
            await animationFrame();
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Goodbye World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                                <div class="d-flex flex-row align-items-center">
                                    <button class="btn d-flex align-items-center o_embedded_toggle_button">
                                        <i class="fa fa-fw align-self-center fa-caret-right"></i>
                                    </button>
                                    <div class="flex-fill">
                                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                            <p>Hello []World<br></p>
                                        </div>
                                    </div>
                                </div>
                                <div class="ps-4 d-none">
                                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                                        <p>asdf<br></p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`)
            );
        });
        test("Tab moves down a level: in encapsulated toggle", async () => {
            browser.localStorage.setItem(`Toggle1.showContent`, "true");
            browser.localStorage.setItem(`Toggle2.showContent`, "true");
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                        <div data-embedded-editable="title">
                            <p>Goodbye World<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                                <div data-embedded-editable="title">
                                    <p>Old News<br></p>
                                </div>
                                <div data-embedded-editable="content">
                                    <p>Hello World: before<br></p>
                                </div>
                            </div>
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "3" }'>
                                <div data-embedded-editable="title">
                                    <p>Hello []World<br></p>
                                </div>
                                <div data-embedded-editable="content">
                                    <p>asdf<br></p>
                                </div>
                            </div>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            await keydownTab(editor);
            await animationFrame();
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Goodbye World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                                <div class="d-flex flex-row align-items-center">
                                    <button class="btn d-flex align-items-center o_embedded_toggle_button">
                                        <i class="fa fa-fw align-self-center fa-caret-down"></i>
                                    </button>
                                    <div class="flex-fill">
                                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                            <p>Old News<br></p>
                                        </div>
                                    </div>
                                </div>
                                <div class="ps-4">
                                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                                        <p>Hello World: before<br></p>
                                        <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "3" }'>
                                            <div class="d-flex flex-row align-items-center">
                                                <button class="btn d-flex align-items-center o_embedded_toggle_button">
                                                    <i class="fa fa-fw align-self-center fa-caret-right"></i>
                                                </button>
                                                <div class="flex-fill">
                                                    <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                                        <p>Hello []World<br></p>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="ps-4 d-none">
                                                <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                                                    <p>asdf<br></p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`)
            );
        });
    });
    describe("Use shift+tab in different situation", () => {
        test("Shift+tab moves up a level: back to editable level", async () => {
            browser.localStorage.setItem(`Toggle1.showContent`, "true");
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                        <div data-embedded-editable="title">
                            <p>Goodbye World<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                                <div data-embedded-editable="title">
                                    <p>Old []News<br></p>
                                </div>
                                <div data-embedded-editable="content">
                                    <p><br></p>
                                </div>
                            </div>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            await keydownShiftTab(editor);
            await animationFrame();
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Goodbye World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p><br></p>
                        </div>
                    </div>
                </div>
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Old []News<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p><br></p>
                        </div>
                    </div>
                </div>
            `)
            );
        });
        test("Shift+tab moves up a level: move to parent content", async () => {
            browser.localStorage.setItem(`Toggle1.showContent`, "true");
            browser.localStorage.setItem(`Toggle2.showContent`, "true");
            const { editor, el } = await setupEditor(
                unformat(
                    `<div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                        <div data-embedded-editable="title">
                            <p>Goodbye World<br></p>
                        </div>
                        <div data-embedded-editable="content">
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                                <div data-embedded-editable="title">
                                    <p>Old News<br></p>
                                </div>
                                <div data-embedded-editable="content">
                                    <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "3" }'>
                                        <div data-embedded-editable="title">
                                            <p>Deep []News<br></p>
                                        </div>
                                        <div data-embedded-editable="content">
                                            <p><br></p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `
                ),
                {
                    config: getConfig([toggleEmbedding]),
                }
            );
            await embeddedToggleMountedPromise;
            await keydownShiftTab(editor);
            await animationFrame();
            expect(getContent(el)).toBe(
                unformat(`
                <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn d-flex align-items-center o_embedded_toggle_button">
                            <i class="fa fa-fw align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Goodbye World<br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "2" }'>
                                <div class="d-flex flex-row align-items-center">
                                    <button class="btn d-flex align-items-center o_embedded_toggle_button">
                                        <i class="fa fa-fw align-self-center fa-caret-down"></i>
                                    </button>
                                    <div class="flex-fill">
                                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                            <p>Old News<br></p>
                                        </div>
                                    </div>
                                </div>
                                <div class="ps-4">
                                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                                        <p><br></p>
                                    </div>
                                </div>
                            </div>
                            <div data-embedded="toggle" data-oe-protected="true" contenteditable="false" class="mb-2" data-embedded-props='{ "toggleId": "3" }'>
                                <div class="d-flex flex-row align-items-center">
                                    <button class="btn d-flex align-items-center o_embedded_toggle_button">
                                        <i class="fa fa-fw align-self-center fa-caret-right"></i>
                                    </button>
                                    <div class="flex-fill">
                                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                            <p>Deep []News<br></p>
                                        </div>
                                    </div>
                                </div>
                                <div class="ps-4 d-none">
                                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                                        <p><br></p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`)
            );
        });
    });
});
