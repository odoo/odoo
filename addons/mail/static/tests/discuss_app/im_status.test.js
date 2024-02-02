/** @odoo-module */

import { test } from "@odoo/hoot";
import { click, contains, openDiscuss, start, startServer } from "../mail_test_helpers";

import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";

import { Store } from "@mail/core/common/store_service";
import { Command, constants } from "@web/../tests/web_test_helpers";

test.skip("initially online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");
});

test.skip("initially offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "offline" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Offline']");
});

test.skip("initially away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "away" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Idle']");
});

test.skip("change icon on change partner im_status", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { advanceTime } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Online']");
    pyEnv["res.partner"].write([partnerId], { im_status: "offline" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Offline']");
    pyEnv["res.partner"].write([partnerId], { im_status: "away" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Idle']");
    pyEnv["res.partner"].write([partnerId], { im_status: "online" });
    await advanceTime(UPDATE_BUS_PRESENCE_DELAY);
    await contains(".o-mail-ImStatus i[title='Online']");
});

test.skip("show im status in messaging menu preview of chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: constants.PARTNER_ID }),
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
