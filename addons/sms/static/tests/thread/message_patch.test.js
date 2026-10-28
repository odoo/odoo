import {
    click,
    contains,
    openFormView,
    start,
    startServer
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { defineSMSModels } from "@sms/../tests/sms_test_helpers";

describe.current.tags("desktop");
defineSMSModels();

test("Notification Processing", async () => {
    const { partnerId } = await _prepareSmsNotification("process");
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification();
    await _assertContainsPopoverWithIcon("hourglass_bottom");
});

test("Notification Pending", async () => {
    const { partnerId } = await _prepareSmsNotification("pending");
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification();
    await _assertContainsPopoverWithIcon("send");
});

test("Notification Sent", async () => {
    const { partnerId } = await _prepareSmsNotification("sent");
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsPopoverWithIcon("check");
});

test("Notification Error", async () => {
    const { partnerId } = await _prepareSmsNotification("exception");
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification();
    await click(".o-mail-Message-notification");
    await waitFor(".o-mail-MessageNotificationPopover:count(1)");
    await waitFor(".o-mail-MessageNotificationPopover [title='Error']:count(1)");
});

const _prepareSmsNotification = async (notification_status) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Someone", partner_share: true });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "sms",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: notification_status,
        notification_type: "sms",
        res_partner_id: partnerId,
    });
    return { partnerId, messageId };
};

const _assertContainsSmsNotification = async () => {
    await waitFor(".o-mail-Message:count(1)");
    await waitFor(".o-mail-Message-notification:count(1)");
    await waitFor(".o-mail-Message-notification i:count(1)");
    await waitFor(".o-mail-Message-notification i[data-icon='smartphone']:count(1)");
};

const _assertContainsPopoverWithIcon = async (iconName) => {
    await click(".o-mail-Message-notification");
    await waitFor(".o-mail-MessageNotificationPopover:count(1)");
    await waitFor(".o-mail-MessageNotificationPopover i:count(1)");
    await waitFor(`.o-mail-MessageNotificationPopover i[data-icon='${iconName}']:count(1)`);
    await contains(".o-mail-MessageNotificationPopover", { text: "ToSomeone" });
};
