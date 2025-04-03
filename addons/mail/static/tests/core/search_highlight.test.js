import { HIGHLIGHT_CLASS, searchHighlight } from "@mail/core/common/message_search_hook";
import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    openFormView,
    patchUiSize,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";

import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Search highlight", async () => {
    const testCases = [
        {
            input: markup`test odoo`,
            output: `test <span class="${HIGHLIGHT_CLASS}">odoo</span>`,
            searchTerm: "odoo",
        },
        {
            input: markup`<a href="https://www.odoo.com">https://www.odoo.com</a>`,
            output: `<a href="https://www.odoo.com">https://www.<span class="${HIGHLIGHT_CLASS}">odoo</span>.com</a>`,
            searchTerm: "odoo",
        },
        {
            input: '<a href="https://www.odoo.com">https://www.odoo.com</a>',
            output: `&lt;a href="https://www.<span class="${HIGHLIGHT_CLASS}">odoo</span>.com"&gt;https://www.<span class="${HIGHLIGHT_CLASS}">odoo</span>.com&lt;/a&gt;`,
            searchTerm: "odoo",
        },
        {
            input: markup`<a href="https://www.odoo.com">Odoo</a>`,
            output: `<a href="https://www.odoo.com"><span class="${HIGHLIGHT_CLASS}">Odoo</span></a>`,
            searchTerm: "odoo",
        },
        {
            input: markup`<a href="https://www.odoo.com">Odoo</a> Odoo is a free software`,
            output: `<a href="https://www.odoo.com"><span class="${HIGHLIGHT_CLASS}">Odoo</span></a> <span class="${HIGHLIGHT_CLASS}">Odoo</span> is a free software`,
            searchTerm: "odoo",
        },
        {
            input: markup`odoo is a free software`,
            output: `<span class="${HIGHLIGHT_CLASS}">odoo</span> is a free software`,
            searchTerm: "odoo",
        },
        {
            input: markup`software ODOO is a free`,
            output: `software <span class="${HIGHLIGHT_CLASS}">ODOO</span> is a free`,
            searchTerm: "odoo",
        },
        {
            input: markup`<ul>
                <li>Odoo</li>
                <li><a href="https://odoo.com">Odoo ERP</a> Best ERP</li>
            </ul>`,
            output: `<ul>
                <li><span class="${HIGHLIGHT_CLASS}">Odoo</span></li>
                <li><a href="https://odoo.com"><span class="${HIGHLIGHT_CLASS}">Odoo</span> ERP</a> Best ERP</li>
            </ul>`,
            searchTerm: "odoo",
        },
        {
            input: markup`test <strong>Odoo</strong> test`,
            output: `<span class="${HIGHLIGHT_CLASS}">test</span> <strong><span class="${HIGHLIGHT_CLASS}">Odoo</span></strong> <span class="${HIGHLIGHT_CLASS}">test</span>`,
            searchTerm: "odoo test",
        },
        {
            input: markup`test <br> test`,
            output: `<span class="${HIGHLIGHT_CLASS}">test</span> <br> <span class="${HIGHLIGHT_CLASS}">test</span>`,
            searchTerm: "odoo test",
        },
        {
            input: markup`<strong>test</strong> test`,
            output: `<strong><span class="${HIGHLIGHT_CLASS}">test</span></strong> <span class="${HIGHLIGHT_CLASS}">test</span>`,
            searchTerm: "test",
        },
        {
            input: markup`<strong>a</strong> test`,
            output: `<strong><span class="${HIGHLIGHT_CLASS}">a</span></strong> <span class="${HIGHLIGHT_CLASS}">test</span>`,
            searchTerm: "a test",
        },
        {
            input: markup`&amp;amp;`,
            output: `<span class="${HIGHLIGHT_CLASS}">&amp;amp;</span>`,
            searchTerm: "&amp;",
        },
        {
            input: markup`&amp;amp;`,
            output: `<span class="${HIGHLIGHT_CLASS}">&amp;</span>amp;`,
            searchTerm: "&",
        },
        {
            input: markup`<strong>test</strong> hello`,
            output: `<strong><span class="${HIGHLIGHT_CLASS}">test</span></strong> <span class="${HIGHLIGHT_CLASS}">hello</span>`,
            searchTerm: "test hello",
        },
        {
            input: markup`<p>&lt;strong&gt;test&lt;/strong&gt; hello</p>`,
            output: `<p>&lt;strong&gt;<span class="${HIGHLIGHT_CLASS}">test</span>&lt;/strong&gt; <span class="${HIGHLIGHT_CLASS}">hello</span></p>`,
            searchTerm: "test hello",
        },
    ];
    for (const { input, output, searchTerm } of testCases) {
        expect(searchHighlight(searchTerm, input).toString()).toBe(output);
    }
});

test("Display highligthed search in chatter", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(`.o-mail-SearchMessageResult .o-mail-Message span.${HIGHLIGHT_CLASS}`);
});

test("Display multiple highligthed search in chatter", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not test empty",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "not empty");
    triggerHotkey("Enter");
    await contains(`.o-mail-SearchMessageResult .o-mail-Message span.${HIGHLIGHT_CLASS}`, {
        count: 2,
    });
});

test("Display highligthed search in Discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click("button[title='Search Messages']");
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(`.o-mail-SearchMessagesPanel .o-mail-Message span.${HIGHLIGHT_CLASS}`);
});

test("Display multiple highligthed search in Discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not prout empty",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click("button[title='Search Messages']");
    await insertText(".o_searchview_input", "not empty");
    triggerHotkey("Enter");
    await contains(`.o-mail-SearchMessagesPanel .o-mail-Message span.${HIGHLIGHT_CLASS}`, {
        count: 2,
    });
});

test("Display highligthed with escaped character must ignore them", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "<p>&lt;strong&gt;test&lt;/strong&gt; hello</p>",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "test hello");
    triggerHotkey("Enter");
    await contains(`.o-mail-SearchMessageResult .o-mail-Message span.${HIGHLIGHT_CLASS}`, {
        count: 2,
    });
    await contains(`.o-mail-Message-body`, { text: "<strong>test</strong> hello" });
});
