/** @odoo-module */

import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockPermission } from "@odoo/hoot-mock";
import { contains, makeMockServer, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";

defineMailModels();

test.skip("should have messaging menu button in systray", async () => {
    await mountWithCleanup(WebClient);
    await contains(".o_menu_systray i[aria-label='Messages']").click();

    expect(".o-mail-MessagingMenu").toBeVisible();

    await contains(".o_menu_systray i[aria-label='Messages'].fa-comments").click();
});

test.skip("messaging menu should have topbar buttons", async () => {
    await mountWithCleanup(WebClient);
    await contains(".o_menu_systray i[aria-label='Messages']").click();

    expect(".o-mail-MessagingMenu").toBeVisible();
    expect(".o-mail-MessagingMenu-header button").toHaveCount(4);
    expect("button.fw-bold:contains(All)").toHaveCount(1);
    expect("button:not(.fw-bold):contains(Chats)").toHaveCount(1);
    expect("button:not(.fw-bold):contains(Channels)").toHaveCount(1);
    expect("button:contains(New Message)").toHaveCount(1);
});

test.skip("counter is taking into account failure notification", async () => {
    const { env } = await makeMockServer();

    const channelId = env["discuss.channel"].create({ name: "general" });
    const messageId = env["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        record_name: "general",
        res_model_name: "Channel",
    });
    const memberIds = env["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", env.partner_id],
    ]);
    env["discuss.channel.member"].write(memberIds, {
        seen_message_id: messageId,
    });
    env["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });

    await mountWithCleanup(WebClient);
    await expect(waitFor(".o-mail-MessagingMenu-counter")).resolves.toHaveText("1");
});

test.skip("rendering with OdooBot has a request (default)", async () => {
    mockPermission("notifications", "default");

    await mountWithCleanup(WebClient);

    await expect(waitFor(".o-mail-MessagingMenu-counter")).resolves.toHaveText("1");
    await contains(".o_menu_systray i[aria-label='Messages']").click();

    await waitFor(".o-mail-NotificationItem");

    expect(".o-mail-NotificationItem").toContain("OdooBot has a request");
    expect(".o-mail-NotificationItem img").toHaveAttribute(
        "src",
        `/web/image?field=avatar_128&id=${session.odoobot_id}&model=res.partner`
    );
});
