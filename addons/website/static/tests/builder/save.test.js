import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame, click, queryOne } from "@odoo/hoot-dom";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";
import {
    defineWebsiteModels,
    exampleWebsiteContent,
    modifyText,
    setupWebsiteBuilder,
    wrapExample,
} from "./website_helpers";

defineWebsiteModels();

test("basic save", async () => {
    const resultSave = setupSaveAndReloadIframe();
    const { getEditor, getEditableContent } = await setupWebsiteBuilder(exampleWebsiteContent);
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    await modifyText(getEditor(), getEditableContent());

    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave.length).toBe(1);
    expect(resultSave[0]).toBe(
        '<div id="wrap" class="oe_structure oe_empty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"><h1 class="title">H1ello</h1></div>'
    );
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    expect(":iframe #wrap").not.toHaveClass("o_editable");
    expect(":iframe #wrap .title:contains('H1ello')").toHaveCount(1);
});

test("nothing to save", async () => {
    const resultSave = setupSaveAndReloadIframe();
    const { getEditor, getEditableContent } = await setupWebsiteBuilder(exampleWebsiteContent);
    await modifyText(getEditor(), getEditableContent());
    await animationFrame();
    await contains(".o-snippets-menu button.fa-undo").click();
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave.length).toBe(0);
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    expect(":iframe #wrap").not.toHaveClass("o_editable");
    expect(":iframe #wrap .title:contains('Hello')").toHaveCount(1);
});

test("discard modified elements", async () => {
    setupSaveAndReloadIframe();
    const { getEditor, getEditableContent } = await setupWebsiteBuilder(exampleWebsiteContent);
    await modifyText(getEditor(), getEditableContent());
    await contains(".o-snippets-top-actions button[data-action='cancel']").click();
    await contains(".modal-content button.btn-primary").click();
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    expect(":iframe #wrap").not.toHaveClass("o_editable");
    expect(":iframe #wrap .title:contains('Hello')").toHaveCount(1);
});

test("discard without any modifications", async () => {
    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        async reloadIframeAndCloseEditor() {
            this.websiteContent.el.contentDocument.body.innerHTML = wrapExample;
        },
    });
    await setupWebsiteBuilder(exampleWebsiteContent);
    await contains(".o-snippets-top-actions button[data-action='cancel']").click();
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    expect(":iframe #wrap").not.toHaveClass("o_editable");
    expect(":iframe #wrap .title:contains('Hello')").toHaveCount(1);
});

test("disable discard button when clicking on save", async () => {
    await setupWebsiteBuilder();
    await click(".o-snippets-top-actions button[data-action='save']");
    expect(".o-snippets-top-actions button[data-action='cancel']").toHaveAttribute("disabled", "");
});

test("content is escaped twice", async () => {
    const { getEditor } = await setupWebsiteBuilder(`<div class="my_content">hey</div>`);
    const editor = getEditor();
    const div = queryOne(":iframe .my_content");
    setSelection({ anchorNode: div.firstChild, anchorOffset: 0 });
    await insertText(editor, "<div>html</div>");

    onRpc("ir.ui.view", "save", ({ args }) => {
        const savedView = args[1];
        // we expect the html sent to have doubly escaped text content
        expect(savedView).toInclude(
            `<div class="my_content">&amp;lt;div&amp;gt;html&amp;lt;/div&amp;gt;hey</div>`
        );
        return true;
    });
    await contains(".o-snippets-top-actions button:contains(Save)").click();
});

test("content is not escaped twice inside data-oe-model nodes which are not ir.ui.view", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<div class="my_content" data-oe-model="other">hey</div>`
    );
    const editor = getEditor();
    const div = queryOne(":iframe .my_content");
    setSelection({ anchorNode: div.firstChild, anchorOffset: 0 });
    await insertText(editor, "<div>html</div>");

    onRpc("ir.ui.view", "save", ({ args }) => {
        const savedView = args[1];
        // we expect the html sent to have simply escaped text content
        expect(savedView).toInclude(
            `<div class="my_content" data-oe-model="other">&lt;div&gt;html&lt;/div&gt;hey</div>`
        );
        return true;
    });
    await contains(".o-snippets-top-actions button:contains(Save)").click();
});

test("content is not escaped twice inside root data-oe-model node which is not ir.ui.view", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<div class="my_content" data-oe-model="other" data-oe-id="42" data-oe-field="thing">hey</div>`
    );
    const editor = getEditor();
    const div = queryOne(":iframe .my_content");
    setSelection({ anchorNode: div.firstChild, anchorOffset: 0 });
    await insertText(editor, "<div>html</div>");

    onRpc("ir.ui.view", "save", ({ args }) => {
        const savedView = args[1];
        // we expect the html sent to have simply escaped text content
        expect(savedView).toInclude(
            `<div class="my_content" data-oe-model="other" data-oe-id="42" data-oe-field="thing">&lt;div&gt;html&lt;/div&gt;hey</div>`
        );
        return true;
    });
    await contains(".o-snippets-top-actions button:contains(Save)").click();
});

function setupSaveAndReloadIframe() {
    const resultSave = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        resultSave.push(args[1]);
        return true;
    });
    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        async reloadIframeAndCloseEditor() {
            this.websiteContent.el.contentDocument.body.innerHTML =
                resultSave.at(-1) || wrapExample;
        },
    });
    return resultSave;
}
