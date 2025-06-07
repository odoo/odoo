import { expect, test } from "@odoo/hoot";
import { press, queryAll, tick, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { loadLanguages } from "@web/core/l10n/translation";
import { ChatGPTPlugin } from "../src/main/chatgpt/chatgpt_plugin";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";

import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { DEFAULT_ALTERNATIVES_MODES } from "../src/main/chatgpt/chatgpt_alternatives_dialog";
import { execCommand } from "./_helpers/userCommands";

const PROMPT_DIALOG_TITLE = "Generate Text with AI";
const ALTERNATIVES_DIALOG_TITLE = "AI Copywriter";
const TRANSLATE_DIALOG_TITLE = "Translate with AI";

const openFromPowerbox = async (editor) => {
    await insertText(editor, "/ChatGPT");
    await animationFrame();
    await press("Enter");
};
const openFromToolbar = async () => {
    await contains(".o-we-toolbar .btn[name='chatgpt']").click();
};
const translateButtonFromToolbar = async () => {
    await contains(".o-we-toolbar .btn[name='translate']").click();
};
const translateDropdownFromToolbar = async () => {
    await contains(".lang:contains('French (BE) / Français (BE)')").click();
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

test("ChatGPT dialog opens in translate mode when clicked on translate button in toolbar", async () => {
    await setupEditor("<p>te[s]t</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });

    // Expect the toolbar to not have translate dropdown.
    expect(".o-we-toolbar [name='translate'].o-dropdown").toHaveCount(0);

    // Expect the toolbar to have translate button.
    expect(".o-we-toolbar .btn[name='translate']").toHaveCount(1);

    // Select Translate button in the toolbar.
    await translateButtonFromToolbar();

    // Expect the ChatGPT Translate Dialog to be open.
    const translateDialogHeaderSelector = `.o_dialog .modal-header:contains("${TRANSLATE_DIALOG_TITLE}")`;
    await waitFor(translateDialogHeaderSelector);

    // Expect the ChatGPT Alternatives Dialog not to be open.
    const alternativesDialogHeaderSelector = `.o_dialog .modal-header:contains("${ALTERNATIVES_DIALOG_TITLE}")`;
    expect(alternativesDialogHeaderSelector).toHaveCount(0);
});

test("ChatGPT dialog opens in translate mode when clicked on translate dropdown in toolbar", async () => {
    loadLanguages.installedLanguages = false;
    onRpc("/web/dataset/call_kw/res.lang/get_installed", () => {
        return [
            ["en_US", "English (US)"],
            ["fr_BE", "French (BE) / Français (BE)"],
        ];
    });
    await setupEditor("<p>te[s]t</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });

    // Expect the toolbar to have translate dropdown.
    expect(".o-we-toolbar [name='translate'].o-dropdown").toHaveCount(1);

    // Select Translate button in the toolbar.
    await translateButtonFromToolbar();
    await waitFor(".dropdown-menu");
    await translateDropdownFromToolbar();

    // Expect the ChatGPT Translate Dialog to be open.
    const translateDialogHeaderSelector = `.o_dialog .modal-header:contains("${TRANSLATE_DIALOG_TITLE}")`;
    await waitFor(translateDialogHeaderSelector);

    // Expect the ChatGPT Alternatives Dialog not to be open.
    const alternativesDialogHeaderSelector = `.o_dialog .modal-header:contains("${ALTERNATIVES_DIALOG_TITLE}")`;
    expect(alternativesDialogHeaderSelector).toHaveCount(0);
    loadLanguages.installedLanguages = false;
});

test("Translate/ChatGPT should be disabled if selection spans across non editable content or unsplittable (1)", async () => {
    await setupEditor("<div>[ab]</div>");
    await animationFrame();
    await tick();
    expect(".o-we-toolbar [name='translate']").not.toHaveAttribute("disabled");
});

test("Translate/ChatGPT should be disabled if selection spans across non editable content or unsplittable (2)", async () => {
    await setupEditor("<div>a[b</div><div>c]d</div>");
    await animationFrame();
    await tick();
    expect(".o-we-toolbar [name='translate']").not.toHaveAttribute("disabled");
});

test("Translate/ChatGPT should be disabled if selection spans across non editable content or unsplittable (3)", async () => {
    await setupEditor('<div contenteditable="false">a[b</div><div>c]d</div>');
    await animationFrame();
    await tick();
    expect(".o-we-toolbar [name='translate']").toHaveAttribute("disabled");
});

test("Translate/ChatGPT should be disabled if selection spans across non editable content or unsplittable (4)", async () => {
    await setupEditor('<div class="oe_unbreakable">a[b</div><div>c]d</div>');
    await animationFrame();
    await tick();
    expect(".o-we-toolbar [name='translate']").toHaveAttribute("disabled");
});

test("Translate/ChatGPT should be disabled if selection spans across non editable content or unsplittable (5)", async () => {
    await setupEditor('<div>a[b</div><div>c]d</div><div class="oe_unbreakable">e</div>');
    await animationFrame();
    await tick();
    expect(".o-we-toolbar [name='translate']").not.toHaveAttribute("disabled");
});

test("Translate/ChatGPT should be disabled if selection spans across non editable content or unsplittable (6)", async () => {
    await setupEditor('<div>a[b</div><div>cd</div><div class="oe_unbreakable">e]</div>');
    await animationFrame();
    await tick();
    expect(".o-we-toolbar [name='translate']").toHaveAttribute("disabled");
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

test("insert the response from ChatGPT translate dialog", async () => {
    loadLanguages.installedLanguages = false;
    onRpc("/web/dataset/call_kw/res.lang/get_installed", () => {
        return [
            ["en_US", "English (US)"],
            ["fr_BE", "French (BE) / Français (BE)"],
        ];
    });
    const { editor, el } = await setupEditor("<p>[Hello]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });
    onRpc("/html_editor/generate_text", () => `Bonjour`);

    // Select Translate button in the toolbar.
    await translateButtonFromToolbar();
    await waitFor(".dropdown-menu");
    await translateDropdownFromToolbar();

    // Insert the response.
    await waitFor(".o-chatgpt-translated");
    expect("footer button.btn[disabled]").toHaveCount(0);
    await contains("footer button.btn").click();

    // Expect the response to have been inserted in the middle of the text.
    expect(getContent(el)).toBe(`<p>Bonjour[]</p>`);
    loadLanguages.installedLanguages = false;

    // Expect to undo and redo the inserted text.
    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe(`<p>[Hello]</p>`);
    execCommand(editor, "historyRedo");
    expect(getContent(el)).toBe(`<p>Bonjour[]</p>`);
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

test("ChatGPT toolbar button should have icon and 'AI' text", async () => {
    await setupEditor("<p>[abc]</p>");
    await waitFor(".o-we-toolbar");

    // Icon should be present.
    expect(".o-we-toolbar .btn[name='chatgpt'] span.fa-magic").toHaveCount(1);

    // Text should be present.
    expect(".o-we-toolbar .btn[name='chatgpt']").toHaveText("AI");
});

test("Translate button should be positioned before ChatGPT button in toolbar", async () => {
    await setupEditor("<p>[abc]</p>");
    await waitFor(".o-we-toolbar");

    const buttons = queryAll(".o-we-toolbar .btn-group[name='ai'] .btn");
    expect(buttons).toHaveCount(2);
    expect(buttons[0]).toHaveAttribute("name", "translate");
    expect(buttons[1]).toHaveAttribute("name", "chatgpt");
});

test("press escape to close ChatGPT dialog", async () => {
    const { editor, el } = await setupEditor("<p>te[]st</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });

    // Select ChatGPT in the Powerbox.
    await openFromPowerbox(editor);

    // Expect the ChatGPT Prompt Dialog to be open.
    const promptDialogHeaderSelector = `.o_dialog .modal-header:contains("${PROMPT_DIALOG_TITLE}")`;
    await waitFor(promptDialogHeaderSelector);
    expect('.modal [name="promptInput"]').toBeFocused();

    await press("escape");
    await animationFrame();
    expect(promptDialogHeaderSelector).toHaveCount(0);
    expect(getContent(el)).toBe("<p>te[]st</p>");
});

test("AI is an alias to ChatGPT command in the Powerbox", async () => {
    const { editor } = await setupEditor("<p>[]<br></p>");
    insertText(editor, "/AI");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("ChatGPT");

    // Search is case-insensitive: "/ai" should also match.
    press("backspace");
    press("backspace");
    insertText(editor, "ai");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("ChatGPT");
});

test("pressing control + enter should send the prompt only once", async () => {
    const { editor } = await setupEditor("<p>[]<br></p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTPlugin] },
    });

    onRpc("/html_editor/generate_text", () => `Hey there!`);

    // Select ChatGPT in the Powerbox.
    await openFromPowerbox(editor);
    contains(".o_dialog textarea").edit("Write something");
    await animationFrame();

    // Pressing control + enter.
    contains(".o_dialog textarea").press(["control", "Enter"]);
    await waitFor(".o-chatgpt-message");
    expect(".o-chatgpt-message").toHaveCount(2); // user message + response.
});
