import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import {
    click,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineHrModels();

let channelId;
beforeEach(async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    const employeeId = pyEnv["hr.employee"].create({ name: "Mario" });
    channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    onRpc("hr.employee", "search_read", () => {
        expect.step("employee lookup");
        return [{ id: employeeId }];
    });
});

test("employee profile lookup is skipped in Discuss and sidebar items", async () => {
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-DiscussContent-threadName[title='Mario']:count(1)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Mario')):count(1)");
    expect.verifySteps([]);
});

test("employee profile is available in chat windows", async () => {
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatWindow:has(:text('Mario')):count(1)");
    await click(".o-mail-ChatWindow [title='Open Actions Menu']");
    await waitFor(".o-dropdown-item:text('View Profile'):count(1)");
    expect.verifySteps(["employee lookup"]);
});
