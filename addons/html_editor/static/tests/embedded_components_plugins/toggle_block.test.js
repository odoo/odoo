import { test, describe, beforeEach, expect } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent, setContent } from "../_helpers/selection";
import {
    addStep,
    deleteBackward,
    deleteForward,
    keydownShiftTab,
    keydownTab,
    splitBlock,
} from "../_helpers/user_actions";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    EmbeddedToggleBlockComponent,
    toggleBlockEmbedding,
} from "@html_editor/others/embedded_components/core/toggle_block/toggle_block";
import { onMounted } from "@odoo/owl";
import { animationFrame, queryOne, tick } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import { ToggleBlockPlugin } from "@html_editor/others/embedded_components/plugins/toggle_block_plugin/toggle_block_plugin";
import { parseHTML } from "@html_editor/utils/html";

let embeddedToggleMountedPromise;

function getConfig(components) {
    return {
        Plugins: [...MAIN_PLUGINS, EmbeddedComponentPlugin, ToggleBlockPlugin],
        resources: {
            embedded_components: components,
        },
    };
}

beforeEach(() => {
    embeddedToggleMountedPromise = new Deferred();
    patchWithCleanup(EmbeddedToggleBlockComponent.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                embeddedToggleMountedPromise.resolve();
            });
        },
    });
});

describe("deleteBackward applied to toggle", () => {
    test("toggle open, after toggle: should append to content", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<p><br></p>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>Hello World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
                <p>[]stuff</p>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <p><br></p>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello World</p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf[]stuff</p>
                        </div>
                    </div>
                </div>`)
        );
    });
    test("toggle closed, after toggle: should append to title", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<p><br></p>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>Hello World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
                <p>[]stuff</p>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            unformat(`
            <p><br></p>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>Hello World[]stuff</p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf</p>
                        </div>
                    </div>
                </div>`)
        );
    });
    test("start of title: should explode toggle", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<p><br></p>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>[]Hello World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>Good</p>
                        <p>Riddance</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            unformat(`
            <p><br></p>
            <p>[]Hello World</p>
            <p>Good</p>
            <p>Riddance</p>
            `)
        );
    });
    test("start of content: should append to title", async () => {
        const { editor } = await setupEditor(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>HelloWorld</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>[]Good</p>
                        <p>Riddance</p>
                    </div>
                </div>
            `),
            { config: getConfig([toggleBlockEmbedding]) }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect("[data-embedded-editable='title']").toHaveInnerHTML(`
            <p>HelloWorldGood</p>
        `);
    });
    test("end of content: should unwrap from content", async () => {
        const { editor } = await setupEditor(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>HelloWorld</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>Good</p>
                        <p>[]Riddance</p>
                    </div>
                </div>
            `),
            { config: getConfig([toggleBlockEmbedding]) }
        );
        await embeddedToggleMountedPromise;
        deleteBackward(editor);
        expect("[data-embedded-editable='content'").toHaveInnerHTML(`
            <p>Good</p>
        `);
        expect(queryOne("[data-embedded='toggleBlock']").nextElementSibling).toHaveOuterHTML(`
            <p>Riddance</p>
        `);
    });
});
describe("deleteForward applied to toggle", () => {
    test("empty paragraph, before toggle: should remove empty paragraph", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<p>[]<br></p>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>HelloWorld</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteForward(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>[]HelloWorld</p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf</p>
                        </div>
                    </div>
                </div>`)
        );
    });
    test("end of paragraph, before toggle: should explode sibling toggle", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<p>before[]</p>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>HelloWorld</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteForward(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <p>before[]HelloWorld</p>
                <p>asdf</p>
            `)
        );
    });
    test("toggle open, end of title: should explode first toggle and append to title", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>HelloWorld[]</p>
                    </div>
                    <div data-embedded-editable="content">
                        <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "2" }' contenteditable="false">
                            <div data-embedded-editable="title">
                                <p>second</p>
                            </div>
                            <div data-embedded-editable="content">
                                <p>third</p>
                            </div>
                        </div>
                    </div>
                </div>
            `),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteForward(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>HelloWorld[]second</p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>third</p>
                        </div>
                    </div>
                </div>`)
        );
    });
    test("toggle closed, end of title: should explode sibling toggle and append to title", async () => {
        const { editor, el } = await setupEditor(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>HelloWorld[]</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>invisible</p>
                    </div>
                </div>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "2" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>second</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>third</p>
                    </div>
                </div>
            `),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteForward(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>HelloWorld[]second</p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>invisible</p>
                        </div>
                    </div>
                </div>
                <p>third</p>
            `)
        );
    });
    test("end of content: should explode sibling toggle and append to content", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>HelloWorld</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>invisible[]</p>
                    </div>
                </div>
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "2" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>second</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>third</p>
                    </div>
                </div>
            `),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        deleteForward(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>HelloWorld</p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>invisible[]second</p>
                        </div>
                    </div>
                </div>
                <p>third</p>
            `)
        );
    });
});
describe("Enter applied to toggle title", () => {
    test("start of title: should create new toggle before", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <p>[]HelloWorld</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        patchWithCleanup(ToggleBlockPlugin.prototype, {
            getUniqueIdentifier() {
                return "2";
            },
        });
        embeddedToggleMountedPromise = new Deferred();
        splitBlock(editor);
        await embeddedToggleMountedPromise;
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{"toggleBlockId":"2"}'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-right"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p><br></p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p o-we-hint-text="Add something inside this toggle" class="o-we-hint"><br></p>
                        </div>
                    </div>
                </div>
                <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                            <i class="fa align-self-center fa-caret-down"></i>
                        </button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <p>[]HelloWorld</p>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf</p>
                        </div>
                    </div>
                </div>
            `)
        );
    });
    test("toggle closed, non-empty title: should create new sibling toggle with split title", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>Hello []World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        patchWithCleanup(ToggleBlockPlugin.prototype, {
            getUniqueIdentifier() {
                return "2";
            },
        });
        embeddedToggleMountedPromise = new Deferred();
        splitBlock(editor);
        await embeddedToggleMountedPromise;
        expect(getContent(el)).toBe(
            unformat(`
            <div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                <div class="d-flex flex-row align-items-center">
                    <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                        <i class="fa align-self-center fa-caret-right"></i>
                    </button>
                    <div class="flex-fill ms-1">
                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                            <p>Hello&nbsp;</p>
                        </div>
                    </div>
                </div>
                <div class="ps-4 ms-1 d-none">
                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                        <p>asdf</p>
                    </div>
                </div>
            </div>
            <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{"toggleBlockId":"2"}'>
                <div class="d-flex flex-row align-items-center">
                    <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                        <i class="fa align-self-center fa-caret-right"></i>
                    </button>
                    <div class="flex-fill ms-1">
                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                            <p>[]World</p>
                        </div>
                    </div>
                </div>
                <div class="ps-4 ms-1 d-none">
                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                        <p o-we-hint-text="Add something inside this toggle" class="o-we-hint"><br></p>
                    </div>
                </div>
            </div>
        `)
        );
    });
    test("toggle open, non-empty title: should prepend content with split title", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <p>Hello []World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        splitBlock(editor);
        expect(getContent(el)).toBe(
            unformat(`
            <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                <div class="d-flex flex-row align-items-center">
                    <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                        <i class="fa align-self-center fa-caret-down"></i>
                    </button>
                    <div class="flex-fill ms-1">
                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                            <p>Hello&nbsp;</p>
                        </div>
                    </div>
                </div>
                <div class="ps-4 ms-1">
                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                        <p>[]World</p>
                        <p>asdf</p>
                    </div>
                </div>
            </div>`)
        );
    });
    test("empty title: should explode toggle", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <p>[]<br></p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        splitBlock(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                <p>asdf</p>
            `)
        );
    });
});
describe("Tab applied to toggle title", () => {
    test("toggle closed, should move inside previous toggle", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <p>Goodbye World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p><br></p>
                    </div>
                </div>
                <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "2" }'>
                    <div data-embedded-editable="title">
                        <p>Hello []World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        await keydownTab(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
            <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                <div class="d-flex flex-row align-items-center">
                    <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                        <i class="fa align-self-center fa-caret-down"></i>
                    </button>
                    <div class="flex-fill ms-1">
                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                            <p>Goodbye World</p>
                        </div>
                    </div>
                </div>
                <div class="ps-4 ms-1">
                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                        <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "2" }'>
                            <div class="d-flex flex-row align-items-center">
                                <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                                    <i class="fa align-self-center fa-caret-right"></i>
                                </button>
                                <div class="flex-fill ms-1">
                                    <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                        <p>Hello []World</p>
                                    </div>
                                </div>
                            </div>
                            <div class="ps-4 ms-1 d-none">
                                <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                                    <p>asdf</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`)
        );
    });
    test("toggle open, should move inside previous toggle and unwrap content", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        browser.sessionStorage.setItem(`html_editor.ToggleBlock2.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <p>Goodbye World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p><br></p>
                    </div>
                </div>
                <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "2" }'>
                    <div data-embedded-editable="title">
                        <p>Hello[]World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        await keydownTab(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
            <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                <div class="d-flex flex-row align-items-center">
                    <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                        <i class="fa align-self-center fa-caret-down"></i>
                    </button>
                    <div class="flex-fill ms-1">
                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                            <p>Goodbye World</p>
                        </div>
                    </div>
                </div>
                <div class="ps-4 ms-1">
                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                        <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "2" }'>
                            <div class="d-flex flex-row align-items-center">
                                <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                                    <i class="fa align-self-center fa-caret-down"></i>
                                </button>
                                <div class="flex-fill ms-1">
                                    <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                        <p>Hello[]World</p>
                                    </div>
                                </div>
                            </div>
                            <div class="ps-4 ms-1">
                                <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                                    <p o-we-hint-text="Add something inside this toggle" class="o-we-hint"><br></p>
                                </div>
                            </div>
                        </div>
                        <p>asdf</p>
                    </div>
                </div>
            </div>`)
        );
    });
});
describe("Shift+Tab applied to toggle title", () => {
    test("should become a sibling of parent toggle and append next siblings into own content", async () => {
        browser.sessionStorage.setItem(`html_editor.ToggleBlock1.showContent`, "true");
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <p>Goodbye World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "2" }'>
                            <div data-embedded-editable="title">
                                <p>Old []News</p>
                            </div>
                            <div data-embedded-editable="content">
                                <p><br></p>
                            </div>
                        </div>
                        <p>absorb</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        await keydownShiftTab(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
            <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                <div class="d-flex flex-row align-items-center">
                    <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                        <i class="fa align-self-center fa-caret-down"></i>
                    </button>
                    <div class="flex-fill ms-1">
                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                            <p>Goodbye World</p>
                        </div>
                    </div>
                </div>
                <div class="ps-4 ms-1">
                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                        <p o-we-hint-text="Add something inside this toggle" class="o-we-hint"><br></p>
                    </div>
                </div>
            </div>
            <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "2" }'>
                <div class="d-flex flex-row align-items-center">
                    <button class="btn p-0 border-0 align-items-center justify-content-center btn-light">
                        <i class="fa align-self-center fa-caret-down"></i>
                    </button>
                    <div class="flex-fill ms-1">
                        <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                            <p>Old []News</p>
                        </div>
                    </div>
                </div>
                <div class="ps-4 ms-1">
                    <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                        <p>absorb</p>
                    </div>
                </div>
            </div>
        `)
        );
    });
});
describe("Hide and show toggle content", () => {
    test("Change toggle state", async () => {
        await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <p>Hello []World</p>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        expect(
            queryOne("[data-embedded-editable='content']").parentElement.matches(".d-none")
        ).toBe(true);
        await contains("[data-embedded='toggleBlock'] button").click();
        await animationFrame();
        expect(
            queryOne("[data-embedded-editable='content']").parentElement.matches(".d-none")
        ).toBe(false);
    });
});
describe("Insert (paste, drop) inside toggle title", () => {
    test("Only allow one paragraph related element inside title", async () => {
        const { editor, el } = await setupEditor(
            unformat(
                `<div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div data-embedded-editable="title">
                        <div class="o-paragraph">Hello[]World</div>
                    </div>
                    <div data-embedded-editable="content">
                        <p>asdf</p>
                    </div>
                </div>
            `
            ),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        expect("[data-embedded-editable='title']").toHaveInnerHTML(`
            <div class="o-paragraph">HelloWorld</div>
        `);
        editor.shared.dom.insert(parseHTML(editor.document, `<p>New</p>`));
        addStep(editor);
        expect("[data-embedded-editable='title']").toHaveInnerHTML(`
            <div class="o-paragraph">HelloNewWorld</div>
        `);
        editor.shared.dom.insert(
            parseHTML(editor.document, `<div class="oe_unbreakable">brol</div>`)
        );
        addStep(editor);
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="toggleBlock" data-oe-protected="true" contenteditable="false" data-embedded-props='{ "toggleBlockId": "1" }'>
                    <div class="d-flex flex-row align-items-center">
                        <button class="btn p-0 border-0 align-items-center justify-content-center btn-light"><i class="fa align-self-center fa-caret-right"></i></button>
                        <div class="flex-fill ms-1">
                            <div data-embedded-editable="title" data-oe-protected="false" contenteditable="true">
                                <div class="o-paragraph">HelloNew</div>
                            </div>
                        </div>
                    </div>
                    <div class="ps-4 ms-1 d-none">
                        <div data-embedded-editable="content" data-oe-protected="false" contenteditable="true">
                            <p>asdf</p>
                        </div>
                    </div>
                </div>
                <div class="oe_unbreakable">brol</div>
                <div class="o-paragraph">[]World</div>
            `)
        );
    });
});

describe("hint", () => {
    test("should show normal hint when focusing embedded content element", async () => {
        const { el } = await setupEditor(
            unformat(`<div data-embedded="toggleBlock" data-oe-protected="true" data-embedded-props='{ "toggleBlockId": "1" }' contenteditable="false">
                    <div data-embedded-editable="title">
                        <p>[]<br></p>
                    </div>
                    <div data-embedded-editable="content">
                        <p><br></p>
                    </div>
                </div>`),
            {
                config: getConfig([toggleBlockEmbedding]),
            }
        );
        await embeddedToggleMountedPromise;
        expect("[data-embedded-editable='title']").toHaveInnerHTML(
            '<p o-we-hint-text="Toggle title" class="o-we-hint"><br></p>'
        );
        await contains("[data-embedded='toggleBlock'] button").click();
        await animationFrame();
        const content = el.querySelector("[data-embedded-editable='content'");
        expect(content).toHaveInnerHTML(
            '<p o-we-hint-text="Add something inside this toggle" class="o-we-hint"><br></p>'
        );
        setContent(content, "<p>[]<br></p>");
        await tick(); // selectionChange
        expect(content).toHaveInnerHTML(
            `<p o-we-hint-text='Type "/" for commands' class="o-we-hint"><br></p>`
        );
    });
});
