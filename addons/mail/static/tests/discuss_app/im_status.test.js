import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";
import { Store } from "@mail/core/common/store_service";

describe.current.tags("desktop");
defineMailModels();

test("initially online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");
});

test("initially offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "offline" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Offline']");
});

test("initially away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "away" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Idle']");
});

test("change icon on change partner im_status", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Online']");
    pyEnv["res.partner"].write([partnerId], { im_status: "offline" });
    // advanceTime() internally mocks date, but time continues to flow.
    // There's no reliable way to exactly wait UPDATE_BUS_PRESENCE_DELAY,
    // And we cannot reliably predict how long it takes to reach internal timeouts
    // Hence we have to overestimate the awaits
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY * 2);
    await contains(".o-mail-ImStatus i[title='Offline']");
    pyEnv["res.partner"].write([partnerId], { im_status: "away" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY * 2);
    await contains(".o-mail-ImStatus i[title='Idle']");
    pyEnv["res.partner"].write([partnerId], { im_status: "online" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY * 2);
    await contains(".o-mail-ImStatus i[title='Online']");
});

test("show im status in messaging menu preview of chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", {
        text: "Demo",
        contains: ["i[aria-label='User is online']"],
    });
});
