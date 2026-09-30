import { click, start } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineHrGamificationModels } from "@hr_gamification/../tests/hr_gamification_test_helpers";
import { asyncStep, makeMockServer, mockService, serverState, waitForSteps } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

defineHrGamificationModels();

test("badge notification opens employee form", async () => {
    const { env } = await makeMockServer();

    const badgeUserId = env["gamification.badge.user"].create({
        badge_name: "Best Employee",
        user_id: serverState.userId,
        user_partner_id: serverState.partnerId,
    });

    const employeeId = env["hr.employee.public"].create(
        {
            name: "Demo",
            user_id: serverState.userId,
            company_id: user.activeCompany.id,
        })

    const messageId = env["mail.message"].create(
        {
            message_type: 'user_notification',
            model: "gamification.badge.user",
            res_id: badgeUserId,
            body: "You've received a badge!",
            needaction: true,
        });

    env["mail.notification"].create(
        {
            mail_message_id: messageId,
            res_partner_id: serverState.partnerId,
            notification_status: "sent",
            notification_type: "inbox",
        },
    );

    mockService("action", {
        doAction(action) {
            asyncStep("do_action");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.res_model).toBe("hr.employee.public");
            expect(action.views).toEqual([[false, "form"]]);
            expect(action.res_id).toBe(employeeId);
        },})

    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", {
        text: "You've received a badge!",
    });
    await waitForSteps(["do_action"]);
});
