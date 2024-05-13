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
import { onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteSlidesModels } from "@website_slides/../tests/website_slides_test_helpers";

describe.current.tags("desktop");
defineWebsiteSlidesModels();

test("grant course access", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["slide.channel"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: channelId,
        request_partner_id: partnerId,
        res_model: "slide.channel",
    });
    onRpc("action_grant_access", (args) => {
        expect(args.args).toHaveLength(1);
        expect(args.args[0]).toHaveLength(1);
        expect(args.args[0][0]).toBe(channelId);
        expect(args.kwargs.partner_id).toBe(partnerId);
        step("access_grant");
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    });
    await start();
    await openFormView("slide.channel", channelId);
    await contains(".o-mail-Activity");
    await click("button", { text: "Grant Access" });
    await assertSteps(["access_grant"]);
});

test("refuse course access", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["slide.channel"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: channelId,
        request_partner_id: partnerId,
        res_model: "slide.channel",
    });
    onRpc("action_refuse_access", (args) => {
        expect(args.args).toHaveLength(1);
        expect(args.args[0]).toHaveLength(1);
        expect(args.args[0][0]).toBe(channelId);
        expect(args.kwargs.partner_id).toBe(partnerId);
        step("access_refuse");
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    });
    await start();
    await openFormView("slide.channel", channelId);
    await contains(".o-mail-Activity");
    await click("button", { text: "Refuse Access" });
    await assertSteps(["access_refuse"]);
});
