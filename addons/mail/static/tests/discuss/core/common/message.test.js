import {
    click,
    contains,
    defineMailModels,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineMailModels();

test("clicking message link does not swap open chat window", async () => {
    const pyEnv = await startServer();
    const [rdId, supportId] = pyEnv["discuss.channel"].create([
        { name: "R&D" },
        { name: "Support" },
    ]);
    const messageRdId = pyEnv["mail.message"].create({
        body: "Hello R&D",
        model: "discuss.channel",
        res_id: rdId,
    });
    const urlRd = `${getOrigin()}/mail/message/${messageRdId}`;
    const messageSupportId = pyEnv["mail.message"].create({
        body: `Hello from there <a class="o_message_redirect" href="${urlRd}" data-oe-model="mail.message" data-oe-id="${messageRdId}">${urlRd}</a>`,
        model: "discuss.channel",
        res_id: supportId,
    });
    const urlSupport = `${getOrigin()}/mail/message/${messageSupportId}`;
    pyEnv["mail.message"].create({
        body: `Hello back <a class="o_message_redirect" href="${urlSupport}" data-oe-model="mail.message" data-oe-id="${messageSupportId}">${urlSupport}</a>`,
        model: "discuss.channel",
        res_id: rdId,
    });
    setupChatHub({ opened: [rdId, supportId] });
    await start();
    await contains(".o-mail-ChatWindow:eq(0) .o-mail-ChatWindow-header:contains(R&D)");
    await contains(".o-mail-ChatWindow:eq(1) .o-mail-ChatWindow-header:contains(Support)");
    await click("a.o_message_redirect:contains(R&D)");
    await contains(".o-mail-Message.o-highlighted:contains(Hello R&D)");
    await contains(".o-mail-ChatWindow:eq(0) .o-mail-ChatWindow-header:contains(R&D)");
    await contains(".o-mail-ChatWindow:eq(1) .o-mail-ChatWindow-header:contains(Support)");
    await click("a.o_message_redirect:contains(Support)");
    await contains(".o-mail-Message.o-highlighted:contains(Hello from there)");
    await contains(".o-mail-ChatWindow:eq(0) .o-mail-ChatWindow-header:contains(R&D)");
    await contains(".o-mail-ChatWindow:eq(1) .o-mail-ChatWindow-header:contains(Support)");
});
