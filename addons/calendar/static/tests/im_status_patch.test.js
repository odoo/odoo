import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineCalendarModels } from "./calendar_test_helpers";

describe.current.tags("desktop");
defineCalendarModels();

test("in a meeting", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    pyEnv["calendar.attendee"].create({ partner_id: partnerId, state: "accepted" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='calendar_today'][title='User is in a meeting']"
    );
});

test("not in a meeting", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    pyEnv["calendar.attendee"].create({ partner_id: partnerId, state: "declined" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='circle'][title='User is online']"
    );
});
