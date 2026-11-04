import {
    assertSteps,
    click,
    contains,
    openFormView,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { defineSMSModels } from "@sms/../tests/sms_test_helpers";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSMSModels();

test("Notification Processing", async () => {
    const { partnerId } = await _prepareSmsNotification("process");
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification();
    await _assertContainsPopoverWithIcon("fa-hourglass-half");
});

test("Notification Pending", async () => {
    const { partnerId } = await _prepareSmsNotification("pending");
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification();
    await _assertContainsPopoverWithIcon("fa-paper-plane-o");
});

test("Notification Sent", async () => {
    const { partnerId } = await _prepareSmsNotification("sent");
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsPopoverWithIcon("fa-check");
});

test("Notification Error", async () => {
    const { partnerId, messageId } = await _prepareSmsNotification("exception");
    mockService("action", {
        doAction(action, options) {
            if (action?.res_model === "res.partner") {
                return super.doAction(...arguments);
            }
            expect(action).toBe("sms.sms_resend_action");
            expect(options.additionalContext.default_mail_message_id).toBe(messageId);
            step("do_action");
        },
    });
    await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification();
    await click(".o-mail-Message-notification");
    await assertSteps(["do_action"]);
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
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    await contains(".o-mail-Message-notification i.fa-mobile");
};

const _assertContainsPopoverWithIcon = async (iconClassName) => {
    await click(".o-mail-Message-notification");
    await contains(".o-mail-MessageNotificationPopover");
    await contains(".o-mail-MessageNotificationPopover i");
    await contains(`.o-mail-MessageNotificationPopover i.${iconClassName}`);
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone" });
};
