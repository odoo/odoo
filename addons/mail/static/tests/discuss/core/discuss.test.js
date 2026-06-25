import { onWebsocketEvent } from "@bus/../tests/mock_websocket";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";
import { makeMockEnv } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Member list and Pinned Messages Panel menu are exclusive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // member list open by default
    await click("[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel");
    await contains(".o-discuss-ChannelMemberList", { count: 0 });
});

test("subscribe to presence channels according to store data", async () => {
    const env = await makeMockEnv();
    const store = env.services["mail.store"];
    onWebsocketEvent("subscribe", (data) => expect.step(`subscribe - [${data.channels}]`));
    expect(env.services.bus_service.isActive).toBe(false);
    // Should not subscribe to presences as bus service is not started.
    store["res.partner"].insert({ id: 1, name: "Partner 1", user_ids: [1] });
    store["res.partner"].insert({ id: 2, name: "Partner 2", user_ids: [2] });
    store["res.users"].insert({ id: 1, name: "User 1" });
    store["res.users"].insert({ id: 2, name: "User 2" });
    await tick();
    expect.waitForSteps([]);
    // Starting the bus should subscribe to known presence channels.
    env.services.bus_service.start();
    await expect.waitForSteps([
        "subscribe - [odoo-presence-res.users_1,odoo-presence-res.users_2]",
    ]);
    // Discovering new presence channels should refresh the subscription.
    store["mail.guest"].insert({ id: 1 });
    await expect.waitForSteps([
        "subscribe - [odoo-presence-mail.guest_1,odoo-presence-res.users_1,odoo-presence-res.users_2]",
    ]);
    // Updating "im_status_access_token" should refresh the subscription.
    store["mail.guest"].insert({ id: 1, im_status_access_token: "token" });
    await expect.waitForSteps([
        "subscribe - [odoo-presence-mail.guest_1-token,odoo-presence-res.users_1,odoo-presence-res.users_2]",
    ]);
});

test("partner representativeUser selector picks the best user by company and share", async () => {
    const env = await makeMockEnv();
    const store = env.services["mail.store"];
    const companyA = store["res.company"].insert({ id: 1, name: "Company A" });
    const companyB = store["res.company"].insert({ id: 2, name: "Company B" });
    const portalUser = store["res.users"].insert({
        id: 1,
        name: "Portal",
        share: true,
        company_ids: [companyA.id],
    });
    const internalA = store["res.users"].insert({
        id: 2,
        name: "Internal A",
        share: false,
        company_ids: [companyA.id],
    });
    const internalB = store["res.users"].insert({
        id: 3,
        name: "Internal B",
        share: false,
        company_ids: [companyB.id],
    });
    const partner = store["res.partner"].insert({
        id: 1,
        name: "Multi-company Partner",
        user_ids: [portalUser.id, internalA.id, internalB.id],
        company_id: companyA.id,
    });
    // No active company → fallback to first internal user
    expect(partner.representativeUser).toBe(internalA);
    // Active company A → prefers internal user of A
    store.self_user = store["res.users"].insert({
        id: 4,
        name: "Self",
        share: false,
        company_id: companyA.id,
        company_ids: [companyA.id, companyB.id],
    });
    await tick();
    expect(partner.representativeUser).toBe(internalA);
    // Switch active company to B → prefers internal user of B
    store.self_user.company_id = companyB;
    await tick();
    expect(partner.representativeUser).toBe(internalB);
    // Portal-only partner → any user of active company
    const portalPartner = store["res.partner"].insert({
        id: 2,
        name: "Portal-only",
        user_ids: [portalUser.id],
        company_id: companyA.id,
    });
    store.self_user.company_id = companyA;
    await tick();
    expect(portalPartner.representativeUser).toBe(portalUser);
    // No users → undefined
    const empty = store["res.partner"].insert({ id: 3, name: "Empty", user_ids: [] });
    expect(empty.representativeUser).toBe(undefined);
});
