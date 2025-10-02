import { beforeEach, expect, test, describe, getFixture } from "@odoo/hoot";
import { setSelection } from "./_helpers/selection";
import { click, hover, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { unformat } from "./_helpers/format";
import { Plugin } from "@html_editor/plugin";
import { Component, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { setupEditor } from "./_helpers/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { parseHTML } from "@html_editor/utils/html";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { insertText } from "./_helpers/user_actions";
import { getScrollContainer } from "@html_editor/core/overlay";

class Test extends models.Model {
    name = fields.Char();
    txt = fields.Html();
    _records = [
        { id: 1, name: "Test", txt: "<p>text</p>".repeat(50) },
        {
            id: 2,
            name: "Test",
            txt: unformat(`
                <table><tbody>
                    <tr>
                        <td><p>cell 0</p></td>
                        <td><p>cell 1</p></td>
                    </tr>
                </tbody></table>
                ${"<p>text</p>".repeat(50)}`),
        },
        { id: 3, name: "Test", txt: "<p>text</p>" },
    ];
}

defineModels([Test]);

test.tags("desktop");
test("Toolbar should not overflow scroll container", async () => {
    const top = (elementOrRange) => elementOrRange.getBoundingClientRect().top;
    const bottom = (elementOrRange) => elementOrRange.getBoundingClientRect().bottom;

    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const scrollableElement = queryOne(".o_content");
    const editable = queryOne(".odoo-editor-editable");

    // Select a paragraph in the middle of the text
    const fifthParagraph = editable.children[5];
    setSelection({
        anchorNode: fifthParagraph,
        anchorOffset: 0,
        focusNode: fifthParagraph,
        focusOffset: 1,
    });
    const range = document.getSelection().getRangeAt(0);

    const toolbar = await waitFor(".o-we-toolbar");

    // Toolbar should be above the selection
    expect(bottom(toolbar)).toBeLessThan(top(range));

    // Scroll down to bring the toolbar close to the top
    let scrollStep = top(toolbar) - top(scrollableElement);
    scrollableElement.scrollTop += scrollStep;
    await animationFrame();

    // Toolbar should be below the selection
    expect(top(toolbar)).toBeGreaterThan(bottom(range));

    // Toolbar should not overflow the scroll container
    expect(top(toolbar)).toBeGreaterThan(top(scrollableElement));

    // Scroll down to make the toolbar overflow the scroll container
    scrollStep = top(toolbar) - top(scrollableElement);
    scrollableElement.scrollTop += scrollStep;
    await animationFrame();

    // Toolbar should be invisible
    expect(toolbar).not.toBeVisible();

    // Scroll up to make the toolbar visible again
    scrollableElement.scrollTop -= scrollStep;
    await animationFrame();

    expect(toolbar).toBeVisible();
});

test.tags("desktop");
test("Toolbar should be visible after scroll bar is added", async () => {
    await mountView({
        type: "form",
        resId: 3,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" options="{'height': 300}"/>
            </form>`,
    });

    // At this point there's no scroll bar around the editable
    const p = queryOne(".odoo-editor-editable p");

    // Add text: this creates a vertical scroll bar in the editable
    const morePs = parseHTML(document, "<p>more text</p>".repeat(20));
    p.after(...morePs.childNodes);

    // Select first paragraph
    setSelection({ anchorNode: p, anchorOffset: 0, focusNode: p, focusOffset: 1 });

    // Toolbar should be visible
    const toolbar = await waitFor(".o-we-toolbar");
    expect(toolbar).toBeVisible();
});

test.tags("desktop");
test("Toolbar should not overflow scroll container at the bottom", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" options="{'height': 300}"/>
            </form>`,
    });
    const lastP = queryOne(".odoo-editor-editable p:last-child");
    // Scroll down to bottom
    lastP.scrollIntoView();

    // Select last paragraph
    setSelection({ anchorNode: lastP, anchorOffset: 0, focusNode: lastP, focusOffset: 1 });

    // Toolbar should be visible
    const toolbar = await waitFor(".o-we-toolbar");
    expect(toolbar).toBeVisible();

    // Scroll up so that toolbar overflows the bottom of the editable
    const scrollableElement = closestScrollableY(lastP);
    scrollableElement.scrollTop -= 100;

    // Toolbar should be hidden
    await waitFor(".o-we-toolbar:not(:visible)");
    expect(toolbar).not.toBeVisible();
});

test.tags("desktop");
test("Toolbar visibility should be updated when editable is resized", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" options="{'height': 300}"/>
            </form>`,
    });

    const lastP = queryOne(".odoo-editor-editable p:last-child");
    // Scroll down to bottom
    lastP.scrollIntoView();

    // Select last paragraph
    setSelection({ anchorNode: lastP, anchorOffset: 0, focusNode: lastP, focusOffset: 1 });

    // Toolbar should be visible
    const toolbar = await waitFor(".o-we-toolbar");
    expect(toolbar).toBeVisible();

    // Resize editable (which is the scroll container)
    const editable = queryOne(".odoo-editor-editable");
    editable.style.height = "150px";

    // Toolbar now overflows the bottom of the container and should be hidden
    await waitFor(".o-we-toolbar:not(:visible)");
    expect(toolbar).not.toBeVisible();
});

describe("powerbox", () => {
    let editor;
    beforeEach(() =>
        patchWithCleanup(Wysiwyg.prototype, {
            setup() {
                super.setup();
                editor = this.editor;
            },
        })
    );

    test.tags("desktop");
    test("Powerbox should be visible in a editable with small height", async () => {
        await mountView({
            type: "form",
            resId: 3,
            resModel: "test",
            arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" options="{'height': 100}"/>
            </form>`,
        });

        // Put cursor at end of first paragraph an insert "/"
        setSelection({ anchorNode: queryOne(".odoo-editor-editable p"), anchorOffset: 1 });
        insertText(editor, "/");

        // Powerbox should be visible
        const powerbox = await waitFor(".o-we-powerbox");
        expect(powerbox).toBeVisible();
    });

    test.tags("desktop");
    test("Powerbox should be visible in a editable with small height (2)", async () => {
        await mountView({
            type: "form",
            resId: 1,
            resModel: "test",
            arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html" options="{'height': 100}"/>
            </form>`,
        });

        // Put cursor at end of third paragraph an insert "/"
        const thirdP = queryOne(".odoo-editor-editable p:nth-child(3)");
        setSelection({ anchorNode: thirdP, anchorOffset: 1 });
        insertText(editor, "/");

        // Powerbox should be visible
        const powerbox = await waitFor(".o-we-powerbox");
        expect(powerbox).toBeVisible();
    });
});

test.tags("desktop");
test("Table column control should always be displayed on top of the table", async () => {
    const top = (el) => el.getBoundingClientRect().top;
    const bottom = (el) => el.getBoundingClientRect().bottom;

    await mountView({
        type: "form",
        resId: 2,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const scrollableElement = queryOne(".o_content");
    const table = queryOne(".odoo-editor-editable table");
    await hover(".odoo-editor-editable td");
    let columnControl = await waitFor(".o-we-table-menu[data-type='column']");

    // Table column control displayed on hover should be above the table
    expect(bottom(columnControl)).toBeLessThan(top(table));

    // Scroll down so that the table is close to the top
    const distanceToTop = top(table) - top(scrollableElement);
    scrollableElement.scrollTop += distanceToTop;
    await animationFrame();

    await hover(".odoo-editor-editable td");
    columnControl = await waitFor(".o-we-table-menu[data-type='column']");

    // Table column control still above the table,
    // even though the table is close to the top
    // of its container, but it should be hidden
    expect(bottom(columnControl)).toBeLessThan(top(table));
    expect(columnControl).not.toBeVisible();
});

test.tags("desktop");
test("Table menu should close on scroll", async () => {
    await mountView({
        type: "form",
        resId: 2,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const scrollableElement = queryOne(".o_content");

    await hover(".odoo-editor-editable td");
    const columnControl = await waitFor(".o-we-table-menu[data-type='column']");
    await click(columnControl);
    await animationFrame();

    // Column menu should be displayed.
    expect(".o-dropdown--menu").toBeVisible();

    // Scroll down
    scrollableElement.scrollTop += 10;
    await waitForNone(".o-dropdown--menu");

    // Column menu should not be visible.
    expect(".o-dropdown--menu").not.toHaveCount();
});

test.tags("desktop");
test("Table menu should only show on contenteditable true tables", async () => {
    await mountView({
        type: "form",
        resId: 2,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    // check that table menu is visible
    await hover(".odoo-editor-editable td");
    await waitFor(".o-we-table-menu[data-type='column']");
    expect(".o-we-table-menu[data-type='column']").toBeVisible();

    // hover away set the table as not editable
    await hover(".o_control_panel");
    queryOne("table").setAttribute("contenteditable", "false");

    // chack that table menu is now not visible
    await hover(".odoo-editor-editable td");
    await waitForNone(".o-we-table-menu[data-type='column']");
    expect(".o-we-table-menu[data-type='column']").not.toHaveCount();
});

test("Toolbar should keep stable while extending down the selection", async () => {
    const top = (el) => el.getBoundingClientRect().top;
    const left = (el) => el.getBoundingClientRect().left;

    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const editable = queryOne(".odoo-editor-editable");

    // Select inner content of a paragraph in the middle of the text
    const fifthParagraph = editable.children[5];
    const textNode = fifthParagraph.firstChild;
    setSelection({
        anchorNode: textNode,
        anchorOffset: 0,
        focusNode: textNode,
        focusOffset: textNode.length,
    });
    const toolbar = await waitFor(".o-we-toolbar");
    const referenceTop = top(toolbar);
    const referenceLeft = left(toolbar);

    const extendSelection = (focusNode, focusOffset) => {
        setSelection({ anchorNode: textNode, anchorOffset: 0, focusNode, focusOffset });
    };

    // Extend the selection to the beginning of the following paragraph. This
    // simulates the selection obtained by moving the mouse while mousedown.
    const sixthParagraph = fifthParagraph.nextElementSibling;
    extendSelection(sixthParagraph, 0);
    await animationFrame();

    // Toolbar should not move
    expect(top(toolbar)).toBe(referenceTop);
    expect(left(toolbar)).toBe(referenceLeft);

    // Extend selection to end of paragraph
    const textNodeSixthParagraph = sixthParagraph.firstChild;
    extendSelection(textNodeSixthParagraph, textNodeSixthParagraph.length);
    await animationFrame();

    // Toolbar should not move
    expect(top(toolbar)).toBe(referenceTop);
    expect(left(toolbar)).toBe(referenceLeft);
});

test("overlay don't close when click on child overlay", async () => {
    class MySubOverlay extends Component {
        static template = xml`<button class="my-suboverlay">Overlay</button>`;
        static props = {};
    }
    class MyOverlay extends Component {
        static template = xml`<div class="my-overlay">Overlay</div>`;
        static props = {};

        setup() {
            const overlayService = useService("overlay");
            let remove;
            onMounted(() => {
                remove = overlayService.add(MySubOverlay, {});
            });
            onWillUnmount(() => remove?.());
        }
    }

    class MyPlugin extends Plugin {
        static id = "my.plugin";
        static dependencies = ["overlay"];
        setup() {
            this.overlay = this.dependencies.overlay.createOverlay(MyOverlay, {});
            this.overlay.open({ target: this.editable });
        }
        destroy() {
            this.overlay.close();
        }
    }

    const { editor } = await setupEditor("<div>edit</div>", {
        config: { Plugins: [...MAIN_PLUGINS, MyPlugin] },
    });
    await waitFor(".my-overlay");
    await contains(".my-suboverlay").click();
    await animationFrame();
    expect(document.activeElement).toBe(queryOne(".my-suboverlay"));
    expect(".my-overlay").toHaveCount(1);
    editor.destroy();
    await animationFrame();

    await setupEditor("<div>edit</div>", {
        config: { Plugins: [...MAIN_PLUGINS, MyPlugin] },
        props: {
            iframe: true,
        },
    });
    await waitFor(".my-overlay");
    await contains(".my-suboverlay").click();
    await animationFrame();
    expect(document.activeElement).toBe(queryOne(".my-suboverlay"));
    expect(".my-overlay").toHaveCount(1);
});

describe("getScrollContainer", () => {
    // Visual hints for easier debugging
    const addVisualHints = (root) => {
        const style = document.createElement("style");
        style.textContent = `
            .fixed {
                border: 3px solid blue;
            }
            .target {
                border: 3px solid orange;
            }
            .expected {
                border: 3px solid green;
            }
            div, iframe {
                margin: 10px;
            }
        `;
        root.prepend(style);
    };
    const setContent = (html, root = getFixture()) => {
        root.innerHTML = html;
        addVisualHints(root);
        return {
            target: root.querySelector(".target"),
            expected: root.querySelector(".expected"),
            iframe: root.querySelector(".iframe"),
        };
    };

    describe("single document", () => {
        test("should return null", () => {
            const { target } = setContent(`<div class="target">Target</div>`);
            expect(getScrollContainer(target)).toBe(null);
        });
        test("should return null (2)", () => {
            const { target } = setContent(`
                <div style="height: 100px">
                    <div class="target" style="height: 200px;">Target</div>
                </div>`);
            expect(getScrollContainer(target)).toBe(null);
        });
        test("should return the target itself", () => {
            const { target } = setContent(`
                <div class="target" style="height: 100px; overflow-y: auto;">
                    <div style="height: 200px;">Content</div>
                </div>`);
            expect(getScrollContainer(target)).toBe(target);
        });
        test("should return target's parent", () => {
            const { target, expected } = setContent(`
                <div class="expected" style="height: 100px; overflow-y: auto;">
                    <div class="target" style="height: 200px;">Target</div>
                </div>`);
            expect(getScrollContainer(target)).toBe(expected);
        });
        test("should return closest scrollable ancestor", () => {
            const { target, expected } = setContent(`
                <div style="height: 200px; overflow-y: auto;">
                    <div class="expected" style="height: 300px; overflow-y: auto;">
                        <div class="target" style="height: 400px;">Target</div>
                    </div>
                </div>`);
            expect(getScrollContainer(target)).toBe(expected);
        });
        test("should return closest scrollable ancestor (2)", () => {
            const { target, expected } = setContent(`
                <div class="expected" style="height: 300px; overflow-y: auto;">
                    <div style="height: 500px; overflow-y: auto;">
                        <div class="target" style="height: 400px;">Target</div>
                    </div>
                </div>`);
            expect(getScrollContainer(target)).toBe(expected);
        });
    });

    describe("with iframe", () => {
        test("should return closest scrollable ancestor inside the iframe", () => {
            // Fixture's content
            const { iframe } = setContent(`<iframe class="iframe" style="height: 500px"></iframe>`);
            // Iframe's content
            const { target, expected } = setContent(
                `<div class="expected" style="height: 300px; overflow-y: auto;">
                    <div class="target" style="height: 400px;">Target</div>
                </div>`,
                iframe.contentDocument.body
            );
            expect(getScrollContainer(target)).toBe(expected);
        });
        test("should return the iframe's document element", () => {
            // Fixture's content
            const { iframe } = setContent(`
                <iframe class="iframe" style="height: 500px"></iframe>`);
            // Iframe's content
            const { target } = setContent(
                `<div class="target" style="height: 600px;">Target</div>`,
                iframe.contentDocument.body
            );
            const documentElement = iframe.contentDocument.documentElement;
            documentElement.classList.add("expected"); // for visual hint
            expect(getScrollContainer(target)).toBe(documentElement);
        });
        test("should return scrollable element in the enclosing document", () => {
            // Fixture's content
            const { iframe, expected } = setContent(`
                <div class="expected" style="height: 300px; overflow-y: auto;">
                    <iframe class="iframe" style="height: 500px"></iframe>
                </div>`);
            // Iframe's content
            const { target } = setContent(
                `<div class="target" style="height: 400px;">Target</div>`,
                iframe.contentDocument.body
            );
            expect(getScrollContainer(target)).toBe(expected);
        });
    });

    describe("with fixed elements", () => {
        test("should return scrollable element inside fixed container", () => {
            const { target, expected } = setContent(`
                <div class="fixed" style="position: fixed, height: 600px">
                    <div class="expected" style="height: 300px; overflow-y: auto;">
                        <div class="target" style="height: 400px;">Target</div>
                    </div>
                </div>`);
            expect(getScrollContainer(target)).toBe(expected);
        });
        test("should not consider scrollable ancestor of a fixed element as the scroll container", () => {
            // The outer div is scrollable, but since the target is inside a
            // fixed container, it is not affected by the scrolling.
            const { target } = setContent(`
                <div style="height: 500px; overflow-y: auto">
                    <div style="height: 700px">
                        <div class="fixed" style="position: fixed">
                            <div class="target" style="height: 400px;">Target</div>
                        </div>
                    </div>
                </div>`);
            expect(getScrollContainer(target)).toBe(null);
        });
        test("should return scrollable element in enclosing document of a fixed element", () => {
            // Fixture's content
            const { iframe, expected } = setContent(`
                <div class="expected" style="height: 300px; overflow-y: auto;">
                    <iframe class="iframe" style="height: 600px"></iframe>
                </div>`);
            // Iframe's content
            // The outer div inside the iframe is scrollable, but since the target is inside a
            // fixed container, it is not affected by the scrolling.
            const { target } = setContent(
                `<div style="height: 500px; overflow-y: auto">
                    <div style="height: 700px">
                        <div class="fixed" style="position: fixed">
                            <div class="target" style="height: 300px;">Target</div>
                        </div>
                    </div>
                </div>`,
                iframe.contentDocument.body
            );
            expect(getScrollContainer(target)).toBe(expected);
        });
        test("should return scrollable element in enclosing document of a fixed element (2)", () => {
            // Fixture's content
            const { iframe, expected } = setContent(`
                <div class="expected" style="height: 300px; overflow-y: auto;">
                    <iframe class="iframe" style="height: 600px"></iframe>
                </div>`);
            // Iframe's content
            // The iframe's document element is scrollable, but since the target
            // is inside a fixed container, it is not affected by the scrolling.
            const { target } = setContent(
                `<div style="height: 700px">
                        <div class="fixed" style="position: fixed">
                            <div class="target" style="height: 300px;">Target</div>
                        </div>
                </div>`,
                iframe.contentDocument.body
            );
            expect(getScrollContainer(target)).toBe(expected);
        });
        test("should return the fixed container if it is scrollable", () => {
            const { target, expected } = setContent(`
                <div class="expected fixed" style="position: fixed; height: 300px; overflow-y: auto;">
                    <div class="target" style="height: 400px;">Target</div>
                </div>`);
            expect(getScrollContainer(target)).toBe(expected);
        });
    });
});

// This test simulates a case in website builder. The values of y and bottom
// returned by getBoundingClientRect are negative for the scroll container (the
// iframe's html element).
test("Overlay should be visible when scroll container has negative value for bottom", async () => {
    const bigContent = "<p>line</p>".repeat(100);
    const { el } = await setupEditor(bigContent, { props: { iframe: true } });
    const iframe = el.ownerDocument.defaultView.frameElement;
    iframe.classList.remove("h-100");
    iframe.style.height = "500px";
    el.style.height = "1000px";

    const lastP = el.querySelector("p:last-child");
    lastP.scrollIntoView();

    const scrollContainer = getScrollContainer(el);
    const { bottom } = scrollContainer.getBoundingClientRect();
    expect(bottom).toBeLessThan(0);
    // Even though bottom is negative, its contents are still visible. An
    // overlay at this point should also be visible.
    setSelection({ anchorNode: lastP, anchorOffset: 0, focusNode: lastP, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toBeVisible();
});
