import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { deleteBackward, pasteText, redo, undo } from "@html_editor/../tests/_helpers/user_actions";

import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import {
    getEditorFromComposerEl,
    insertTextInComposer,
} from "@mail/../tests/mail_test_helpers_composer";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryFirst, waitUntil } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();

/** @returns {string[]} texts of the ranges visually styled as links in the composer */
function getVisualLinks() {
    const composerEl = queryFirst(".o-mail-Composer-html");
    return [...(CSS.highlights.get("o-mail-VisualLink") ?? [])]
        .filter((range) => composerEl?.contains(range.commonAncestorContainer))
        .map((range) => range.toString());
}

async function expectVisualLinks(expected) {
    await waitUntil(() => JSON.stringify(getVisualLinks()) === JSON.stringify(expected), {
        timeout: 1000,
    }).catch(() => {});
    expect(getVisualLinks()).toEqual(expected);
}

async function openComposer() {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-html");
}

test("typed URL is visually linkified without altering the content", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "see https://www.odoo.com please");
    await expectVisualLinks(["https://www.odoo.com"]);
    // Purely visual: no link element is created in the composer.
    expect(".o-mail-Composer-html a").toHaveCount(0);
});

test("text without URL is not visually linkified", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "hello world, see you at odoo");
    await expectVisualLinks([]);
});

test("typing inside or after a URL keeps it linkified while it still matches", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "www.odoo.com");
    await expectVisualLinks(["www.odoo.com"]);
    await insertTextInComposer(".o-mail-Composer", "/discuss");
    await expectVisualLinks(["www.odoo.com/discuss"]);
    // A space ends the URL: what follows is not part of the link.
    await insertTextInComposer(".o-mail-Composer", " now");
    await expectVisualLinks(["www.odoo.com/discuss"]);
    // Typing in the middle of the URL extends it.
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    const textNode = editor.editable.querySelector(".o-paragraph").firstChild;
    setSelection({ anchorNode: textNode, anchorOffset: 8 });
    await insertTextInComposer(".o-mail-Composer", "-erp");
    await expectVisualLinks(["www.odoo-erp.com/discuss"]);
});

test("URL is no longer linkified once it stops matching", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "http://x.io");
    await expectVisualLinks(["http://x.io"]);
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    for (let i = 0; i < 4; i++) {
        deleteBackward(editor);
    }
    await animationFrame();
    await expectVisualLinks([]);
    await insertTextInComposer(".o-mail-Composer", "y.io");
    await expectVisualLinks(["http://y.io"]);
});

test("pasted URLs are visually linkified", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "links: ");
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    pasteText(editor, "https://odoo.com/a and www.odoo.com/b");
    await expectVisualLinks(["https://odoo.com/a", "www.odoo.com/b"]);
});

test("undo and redo keep visual links in sync", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "go to ");
    await insertTextInComposer(".o-mail-Composer", "odoo.com");
    await expectVisualLinks([]);
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    setSelection({
        anchorNode: editor.editable.querySelector(".o-paragraph").firstChild,
        anchorOffset: 6,
    });
    await insertTextInComposer(".o-mail-Composer", "www.");
    await expectVisualLinks(["www.odoo.com"]);
    undo(editor);
    await expectVisualLinks([]);
    redo(editor);
    await expectVisualLinks(["www.odoo.com"]);
});

test("mentions are not visually linkified, URL next to them is", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "@");
    await click(".o-mail-Composer-suggestion strong:text('Mitchell Admin')");
    await insertTextInComposer(".o-mail-Composer", "www.odoo.com");
    await expectVisualLinks(["www.odoo.com"]);
});

test("visually linkified URL is an actual link once the message is posted", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "see https://www.odoo.com please");
    await expectVisualLinks(["https://www.odoo.com"]);
    await click(".o-mail-Composer button[title='Send']:enabled");
    await contains(".o-mail-Message-body a[href='https://www.odoo.com/']", {
        text: "https://www.odoo.com",
    });
    await contains(".o-mail-Message-body", { text: "see https://www.odoo.com please" });
});
