import { expect, test } from "@odoo/hoot";
import { press, tick, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { loadLanguages } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";

import { ChatGPTTranslatePlugin } from "@html_editor/main/chatgpt/chatgpt_translate_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { expandToolbar } from "./_helpers/toolbar";
import { execCommand } from "./_helpers/userCommands";

const TRANSLATE_DIALOG_TITLE = "Translate with AI";

const translateButtonFromToolbar = async () => {
    await contains(".o-we-toolbar .btn[name='translate']").click();
};
const translateDropdownFromToolbar = async () => {
    await contains(".lang:contains('French (BE) / Français (BE)')").click();
};

test("ChatGPT dialog opens in translate mode when clicked on translate button in toolbar", async () => {
    await setupEditor("<p>te[s]t</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTTranslatePlugin] },
    });

    await expandToolbar();
    // Expect the toolbar to not have translate dropdown.
    expect(".o-we-toolbar [name='translate'].o-dropdown").toHaveCount(0);

    // Expect the toolbar to have translate button.
    expect(".o-we-toolbar .btn[name='translate']").toHaveCount(1);

    // Select Translate button in the toolbar.
    await translateButtonFromToolbar();

    // Expect the ChatGPT Translate Dialog to be open.
    const translateDialogHeaderSelector = `.o_dialog .modal-header:contains("${TRANSLATE_DIALOG_TITLE}")`;
    await waitFor(translateDialogHeaderSelector);
});

test("ChatGPT dialog opens in translate mode when clicked on translate dropdown in toolbar", async () => {
    loadLanguages.installedLanguages = false;
    onRpc("res.lang", "get_installed", () => [
        ["en_US", "English (US)"],
        ["fr_BE", "French (BE) / Français (BE)"],
    ]);
    await setupEditor("<p>te[s]t</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTTranslatePlugin] },
    });

    // Expect the toolbar to have translate dropdown.
    await expandToolbar();
    expect(".o-we-toolbar [name='translate'].o-dropdown").toHaveCount(1);

    // Select Translate button in the toolbar.
    await translateButtonFromToolbar();
    await waitFor(".dropdown-menu");
    await translateDropdownFromToolbar();

    // Expect the ChatGPT Translate Dialog to be open.
    const translateDialogHeaderSelector = `.o_dialog .modal-header:contains("${TRANSLATE_DIALOG_TITLE}")`;
    await waitFor(translateDialogHeaderSelector);
});

test("Translate should be disabled if selection spans across non editable content or unsplittable (1)", async () => {
    await setupEditor("<div>[ab]</div>");
    await animationFrame();
    await tick();
    await expandToolbar();
    expect(".o-we-toolbar [name='translate']").not.toHaveAttribute("disabled");
});

test("Translate should be disabled if selection spans across non editable content or unsplittable (2)", async () => {
    await setupEditor("<div>a[b</div><div>c]d</div>");
    await animationFrame();
    await tick();
    await expandToolbar();
    expect(".o-we-toolbar [name='translate']").not.toHaveAttribute("disabled");
});

test.todo("should not open toolbar when selection contains contenteditable false", async () => {
    await setupEditor('<div contenteditable="false">a[b</div><div>c]d</div>');
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(0);
});

test("Translate should be disabled if selection spans across non editable content or unsplittable (4)", async () => {
    await setupEditor('<div class="oe_unbreakable">a[b</div><div>c]d</div>');
    await animationFrame();
    await tick();
    await expandToolbar();
    expect(".o-we-toolbar [name='translate']").toHaveAttribute("disabled");
});

test("Translate should be disabled if selection spans across non editable content or unsplittable (5)", async () => {
    await setupEditor('<div>a[b</div><div>c]d</div><div class="oe_unbreakable">e</div>');
    await animationFrame();
    await tick();
    await expandToolbar();
    expect(".o-we-toolbar [name='translate']").not.toHaveAttribute("disabled");
});

test("Translate should be disabled if selection spans across non editable content or unsplittable (6)", async () => {
    await setupEditor('<div>a[b</div><div>cd</div><div class="oe_unbreakable">e]</div>');
    await animationFrame();
    await tick();
    await expandToolbar();
    expect(".o-we-toolbar [name='translate']").toHaveAttribute("disabled");
});

test("insert the response from ChatGPT translate dialog", async () => {
    loadLanguages.installedLanguages = false;
    onRpc("res.lang", "get_installed", () => [
        ["en_US", "English (US)"],
        ["fr_BE", "French (BE) / Français (BE)"],
    ]);
    const { editor, el } = await setupEditor("<p>[Hello]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTTranslatePlugin] },
    });
    onRpc("/html_editor/generate_text", () => `Bonjour`);

    // Select Translate button in the toolbar.
    await expandToolbar();
    await translateButtonFromToolbar();
    await waitFor(".dropdown-menu");
    await translateDropdownFromToolbar();

    // Insert the response.
    await waitFor(".o-chatgpt-translated");
    expect("footer button.btn[disabled]").toHaveCount(0);
    await contains("footer button.btn").click();

    await animationFrame();

    // Expect the response to have been inserted in the middle of the text.
    expect(getContent(el)).toBe(`<p>Bonjour[]</p>`);
    loadLanguages.installedLanguages = false;

    // Expect to undo and redo the inserted text.
    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe(`<p>[Hello]</p>`);
    execCommand(editor, "historyRedo");
    expect(getContent(el)).toBe(`<p>Bonjour[]</p>`);
});

test("Translate dropdown should have the default language at top", async () => {
    loadLanguages.installedLanguages = false;
    const languages = [
        ["zh_HK", "Chinese (HK)"],
        ["nl_NL", "Dutch / Nederlands"],
        ["en", "English"],
        ["fr_BE", "French (BE) / Français (BE)"],
    ];

    onRpc("res.lang", "get_installed", () => languages);
    await setupEditor("<p>[test]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTTranslatePlugin] },
    });
    await expandToolbar();

    // Select Translate button in the toolbar.
    await translateButtonFromToolbar();
    await waitFor(".dropdown-menu");

    const expectedLanguage = languages.find(([code]) => code === user.lang);

    // Expect the default language to be at the top.
    expect(".dropdown-menu .dropdown-item:first-child").toHaveText(expectedLanguage[1]);
    loadLanguages.installedLanguages = false;
});

test("press escape to close translate dialog", async () => {
    await setupEditor("<p>[test]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChatGPTTranslatePlugin] },
    });

    await expandToolbar();
    // Select Translate button in the toolbar.
    await translateButtonFromToolbar();

    // Expect the ChatGPT Translate Dialog to be open.
    const translateDialogHeaderSelector = `.o_dialog .modal-header:contains("${TRANSLATE_DIALOG_TITLE}")`;
    await waitFor(translateDialogHeaderSelector);

    await press("escape");
    await animationFrame();
    expect(translateDialogHeaderSelector).toHaveCount(0);
});
