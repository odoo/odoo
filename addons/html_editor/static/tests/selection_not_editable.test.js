import { animationFrame, expect, queryOne, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { EditorOverlay } from "@html_editor/core/overlay";
import { SelectionPlugin } from "@html_editor/core/selection_plugin";
import { setSelection } from "./_helpers/selection";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

// Rect for a collapsed range can be called an indeterminate amount of times; we only register the first instance when relevant
let gotRectForCollapsedRange = false;

patchWithCleanup(EditorOverlay.prototype, {
    getRectForCollapsedRange() {
        if (!gotRectForCollapsedRange) {
            gotRectForCollapsedRange = true;
            expect.step("getRectForCollapsedRange");
        }
        return super.getRectForCollapsedRange(...arguments);
    },
});

patchWithCleanup(SelectionPlugin.prototype, {
    updateActiveSelection() {
        expect.step("activeSelectionUpdated");
        return super.updateActiveSelection();
    },
    scrollToSelection(selection) {
        expect.step("scrolledToSelection");
        return super.scrollToSelection(selection);
    },
});

const editorContent = `
<div style="background-color: #F7F7F7;">
    <div contenteditable="true" style="padding: 20px;">
        <section style="padding-left: 15px; padding-right: 15px;" contenteditable="false" class="o_not_editable">
            <a class="selecthere" target="_blank" href="http://www.example.com">
                <img class="img img-fluid o_editable_media mx-auto py-4" style="width: 30% !important" src="/web/image/res.company/1/logo" data-original-src="/web/image/res.company/1/logo" data-mimetype="undefined">
            </a>
        </section>
        <section style="padding-left: 15px; padding-right: 15px;">
            <p style="padding-top: 2500px;">
                Great stories are <strong>for everyone</strong> even when only written <strong>for just one person</strong>. If you try to write with a wide, general audience in mind, your story will sound fake and lack emotion. No one will be interested. Write for one person. If it's genuine for the one, it's genuine for the rest.
            </p>
        </section>
    </div>
</div>
`;

test.tags("firefox", "desktop");
test("Don't fire selection events when the first link is selected", async () => {
    const { editor } = await setupEditor(unformat(editorContent), { props: { iframe: true } });
    const targetLink = editor.document.querySelector(".selecthere");
    // select the spot
    setSelection({
        anchorNode: targetLink,
        anchorOffset: 0,
        focusNode: targetLink,
        focusOffset: 0,
    });
    await animationFrame();
    // Assert that the selection has changed and that we are dealing on a collapsed range
    expect.verifySteps(["activeSelectionUpdated", "getRectForCollapsedRange"]);
    // an overlay should be displayed
    const overlayEl = queryOne(".overlay");
    const previousOverlayTop = overlayEl.style.top;

    // Attempt scrolldown; check that the collapsed range is once more called upon, but that no selection change has been registered
    gotRectForCollapsedRange = false;
    const scrollableElement = editor.document.querySelector("body");
    scrollableElement.scrollTop += 500;
    await animationFrame();
    // No selection event must have been fired; the selection must not be scrolling up!
    expect.verifySteps(["getRectForCollapsedRange"]);
    // The overlay should move with scroll normally
    expect(overlayEl.style.top).not.toEqual(previousOverlayTop);
});
