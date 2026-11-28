import { defineCrmLivechatModels } from "@crm_livechat/../tests/crm_livechat_test_helpers";

import {
    actionPanel,
    click,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";

import { describe, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";

import { Command, serverState } from "@web/../tests/web_test_helpers";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

describe.current.tags("desktop");
defineCrmLivechatModels();

test("can create a lead from the thread action after the conversation ends", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    const pyEnv = await startServer();
    serverState.groupSalesTeamId = pyEnv["res.groups"].create({ name: "Sale Salesman" });
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: [
            Command.link(serverState.groupLivechatId),
            Command.link(serverState.groupSalesTeamId),
        ],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channel_id = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    await start();
    await openDiscuss(channel_id);
    await waitFor(`${actionPanel("Information")}:count(1)`); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Create Lead']");
    await insertText(".o-mail-ChannelCommandDialog-form input", "testlead");
    await click(".o-mail-ActionPanel button", { text: "Create Lead" });
    const [{ date }] = pyEnv["mail.message"].search_read([["res_id", "=", channel_id]]);
    const time = deserializeDateTime(date).toLocaleString(luxon.DateTime.TIME_SIMPLE, {
        locale: user.lang,
    });
    await waitFor(
        `.o-mail-NotificationMessage:text('${serverState.partnerName} created a new lead: testlead${time}'):count(1)`
    );
});

test("cannot create a lead without sales access", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: [Command.link(serverState.groupLivechatId)],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Batman" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Batcave",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-DiscussContent-header button[title='Members']:count(1)");
    await waitForNone(".o-mail-DiscussContent-header button[title='Create Lead']");
    await insertTextInComposer(".o-mail-Composer", "/");
    await waitFor(".o-mail-Composer-suggestion strong:text('help'):count(1)");
    await waitForNone(".o-mail-Composer-suggestion strong:text('lead')");
});

test("cannot create a lead from unsupported channel types", async () => {
    const pyEnv = await startServer();
    serverState.groupSalesTeamId = pyEnv["res.groups"].create({ name: "Sale Salesman" });
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: [Command.link(serverState.groupSalesTeamId)],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Internal conversation",
        channel_type: "group",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer:count(1)");
    await waitForNone(".o-mail-DiscussContent-header button[title='Create Lead']");
    await insertTextInComposer(".o-mail-Composer", "/");
    await waitFor(".o-mail-Composer-suggestion strong:text('help'):count(1)");
    await waitForNone(".o-mail-Composer-suggestion strong:text('lead')");
});
