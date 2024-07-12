import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { press, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { insertText } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { ChatGPTPlugin } from "../src/main/chatgpt/chatgpt_plugin";

import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { DEFAULT_ALTERNATIVES_MODES } from "../src/main/chatgpt/chatgpt_alternatives_dialog";

const PROMPT_DIALOG_TITLE = "Generate Text with AI";
const ALTERNATIVES_DIALOG_TITLE = "AI Copywriter";

const openFromPowerbox = async (editor) => {
    insertText(editor, "/ChatGPT");
    await animationFrame();
    press("Enter");
};
const openFromToolbar = async () => {
    await contains(".o-we-toolbar [name='ai'] .btn").click();
};

test("ChatGPT dialog opens in prompt mode when selection is collapsed (with Powerbox)", async () => {
    const { editor } = await setupEditor("<p>te[]st</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });

    // Select ChatGPT in the Powerbox.
    await openFromPowerbox(editor);

    // Expect the ChatGPT Prompt Dialog to be open.
    const promptDialogHeaderSelector = `.o_dialog .modal-header:contains("${PROMPT_DIALOG_TITLE}")`;
    await waitFor(promptDialogHeaderSelector);

    // Expect the ChatGPT Alternatives Dialog not to be open.
    const alternativesDialogHeaderSelector = `.o_dialog .modal-header:contains("${ALTERNATIVES_DIALOG_TITLE}")`;
    expect(alternativesDialogHeaderSelector).toHaveCount(0);
});

test("ChatGPT dialog opens in alternatives mode when selection is not collapsed (with toolbar)", async () => {
    await setupEditor("<p>te[s]t</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });

    // Select ChatGPT in the toolbar.
    await openFromToolbar();

    // Expect the ChatGPT Alternatives Dialog to be open.
    const alternativesDialogHeaderSelector = `.o_dialog .modal-header:contains("${ALTERNATIVES_DIALOG_TITLE}")`;
    await waitFor(alternativesDialogHeaderSelector);

    // Expect the ChatGPT Prompt Dialog not to be open.
    const promptDialogHeaderSelector = `.o_dialog .modal-header:contains("${PROMPT_DIALOG_TITLE}")`;
    expect(promptDialogHeaderSelector).toHaveCount(0);
});

test("ChatGPT alternatives dialog generates alternatives for each button", async () => {
    const { editor } = await setupEditor("<p>[test]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });
    let rpcIndex = 1;
    onRpc("/html_editor/generate_text", () => `Alternative #${rpcIndex++}`);

    // Select ChatGPT in the toolbar.
    await openFromToolbar();

    // Expect 3 alternatives to have been generated and to be displayed in
    // reverse order.
    await waitFor(".o-chatgpt-alternative");
    let alternativesCount = 3;
    expect(".o-chatgpt-alternative").toHaveCount(alternativesCount);
    const alternatives = editor.document.querySelectorAll(".o-chatgpt-alternative");
    expect(getContent(alternatives[0])).toBe("<p>Alternative #3</p>");
    expect(getContent(alternatives[1])).toBe("<p>Alternative #2</p>");
    expect(getContent(alternatives[2])).toBe("<p>Alternative #1</p>");

    // Click on each button and expect a new alternative to be generated each
    // time.
    const buttons = editor.document.querySelectorAll("main.modal-body button[data-mode]");
    for (const button of buttons) {
        const dataMode = button.getAttribute("data-mode");
        await contains(`main.modal-body button[data-mode=${dataMode}]`).click();
        alternativesCount += 1;
        expect(".o-chatgpt-alternative").toHaveCount(alternativesCount);
        const newAlternative = editor.document.querySelector(".o-chatgpt-alternative");
        expect(getContent(newAlternative)).toBe(
            `<span class="badge bg-secondary float-end">${DEFAULT_ALTERNATIVES_MODES[dataMode]}</span>` +
                `<p>Alternative #${alternativesCount}</p>`
        );
    }
});

test("insert the response from ChatGPT prompt dialog", async () => {
    const { editor, el } = await setupEditor("<p>te[]st</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });
    onRpc(
        "/html_editor/generate_text",
        () => `
Here you go!
Enjoy :-)
    `
    );

    // Select ChatGPT in the Powerbox.
    await openFromPowerbox(editor);

    // Ask it to generate a list.
    await contains(".o_dialog textarea").edit("Write something.");
    await contains("footer button.btn").click();

    // Insert the response.
    await waitFor(".o-message-insert");
    expect(".o-message-insert").toHaveCount(1); // There shouldn't be more that one.
    await contains(".o-message-insert").click();

    // Expect the response to have been inserted in the middle of the text.
    expect(getContent(el)).toBe(`<p>teHere you go!</p><p>Enjoy :-)[]st</p>`);
});

test("insert the response from ChatGPT alternatives dialog", async () => {
    const { el } = await setupEditor("<p>t[es]t</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });
    let rpcIndex = 1;
    onRpc("/html_editor/generate_text", () => `Alternative #${rpcIndex++}`);

    // Select ChatGPT in the Powerbox.
    await openFromToolbar();

    // Insert the top response.
    await waitFor(".o-chatgpt-alternative");
    expect(".o-chatgpt-alternative").toHaveCount(3);
    expect("footer button.btn[disabled]").toHaveCount(1);
    await contains(".o-chatgpt-alternative").click();
    expect("footer button.btn[disabled]").toHaveCount(0);
    await contains("footer button.btn").click();

    // Expect the response to have replaced the selected text.
    expect(getContent(el)).toBe(`<p>tAlternative #3[]t</p>`);
});

test("ChatGPT prompt dialog properly formats an unordered list", async () => {
    const { editor } = await setupEditor("<p>te[]st</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });
    onRpc(
        "/html_editor/generate_text",
        () => `
        - First item
        - Second item
        - Third item
    `
    );

    // Select ChatGPT in the Powerbox.
    await openFromPowerbox(editor);

    // Ask it to generate a list.
    await contains(".o_dialog textarea").edit("Generate a list.");
    await contains("footer button.btn").click();

    // Expect it to recognize the response is a list and format it.
    await waitFor(".o-chatgpt-message");
    expect(".o-chatgpt-message").toHaveCount(2); // user message + response
    expect(getContent(editor.document.querySelectorAll(".o-chatgpt-message div")[1])).toBe(
        `<ul><li>First item</li><li>Second item</li><li>Third item</li></ul>`
    );
});
