import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("basic rendering of markdown message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<odoo-markdown>**body**</odoo-markdown>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message .o-mail-Message-content p strong", { text: "body" });
});

test("basic rendering of markdown message with code snippet", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<odoo-markdown>```javascript \n const highlight = 'code'; \n ```</odoo-markdown>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-content pre code");
});

test(`Markdown links should have target="_blank" attribute`, async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<odoo-markdown>[Odoo](https://odoo.com)</odoo-markdown>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(`.o-mail-Message-content a[target="_blank"]`);
});

test("Link should not be processed inside a markdown code fence", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const codeSnippet = "https://odoo.com \n" +
          "```html \n" +
          "https://odoo.com \n" +
          "``` \n" +
          "test \n" +
          "```html \n" +
          "https://borderdens.com \n" +
          "```";
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", codeSnippet);
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-content a");
    await contains(".o-mail-Message-content pre code", { count: 2 });
});

test("Mentions should not be processed inside a markdown code fence", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    const codeSnippetOpen = "```html\n";
    const codeSnippetClose = "\n```";
    await insertText(".o-mail-Composer-input", codeSnippetOpen);
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-input", { value: "```html\n@TestPartner "});
    await insertText(".o-mail-Composer-input", codeSnippetClose);
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-content pre code");
    await contains(`.o-mail-Message-content a`, { count: 0 }); // code block should no contains html tags
});

test("Link inside inline code should not be processed", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "https://odoo.com \n `https://odoo.com`");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-content a");
    await contains(".o-mail-Message-content code a", { count: 0 });
});
