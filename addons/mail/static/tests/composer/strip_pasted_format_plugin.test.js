import { pasteHtml, pasteOdooEditorHtml } from "@html_editor/../tests/_helpers/user_actions";

import {
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { getEditorFromComposerEl } from "@mail/../tests/mail_test_helpers_composer";
import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

async function openComposer() {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-html");
}

test("pasted HTML loses its inline formatting", async () => {
    await openComposer();
    pasteHtml(
        getEditorFromComposerEl(".o-mail-Composer"),
        "<b>Hello</b> <i><u>dear</u></i> <s>old</s> <strong><em>World</em></strong>"
    );
    await contains(".o-mail-Composer-html .o-paragraph:contains('World')");
    expect(".o-mail-Composer-html .o-paragraph").toHaveInnerHTML("Hello dear old World");
});

test("pasted HTML lists become lines", async () => {
    await openComposer();
    pasteHtml(
        getEditorFromComposerEl(".o-mail-Composer"),
        `Fruits:
        <ul>
            <li>Apples</li>
            <li>
                <p>Pears</p>
                <ol><li>Green</li></ol>
            </li>
        </ul>
        Done`
    );
    await contains(".o-mail-Composer-html .o-paragraph:contains('Done')");
    expect(".o-mail-Composer-html :is(ul, ol, li)").toHaveCount(0);
    expect(".o-mail-Composer-html .o-paragraph").toHaveText("Fruits:\nApples\nPears\nGreen\nDone");
});

test("pasted editor HTML loses its inline formatting and its links, but keeps its mentions", async () => {
    await openComposer();
    pasteOdooEditorHtml(
        getEditorFromComposerEl(".o-mail-Composer"),
        `<b>Hello</b> <a href="https://www.odoo.com">Odoo</a> <a class="o_mail_redirect" href="#" data-oe-id="3" data-oe-model="res.partner">@Mitchell Admin</a>`
    );
    await contains(
        ".o-mail-Composer-html .o-paragraph a.o_mail_redirect:contains('@Mitchell Admin')"
    );
    // the mention is the only element left
    expect(".o-mail-Composer-html .o-paragraph :is(a, b)").toHaveCount(1);
    expect(".o-mail-Composer-html .o-paragraph").toHaveText("Hello Odoo @Mitchell Admin");
});

test("dropped HTML loses its inline formatting and its links", async () => {
    await openComposer();
    const paragraph = queryOne(".o-mail-Composer-html .o-paragraph");
    patch(document, {
        caretPositionFromPoint: () => ({ offsetNode: paragraph, offset: 0 }),
    });
    const dataTransfer = new DataTransfer();
    dataTransfer.setData("text/html", `<b>Hello</b><a href="https://www.odoo.com">Odoo</a>`);
    await manuallyDispatchProgrammaticEvent(paragraph, "drop", { dataTransfer });
    await contains(".o-mail-Composer-html .o-paragraph:contains('Odoo')");
    expect(".o-mail-Composer-html .o-paragraph").toHaveInnerHTML("HelloOdoo");
});
