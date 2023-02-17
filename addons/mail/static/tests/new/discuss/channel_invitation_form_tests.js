/** @odoo-module **/

import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("channel invitation form", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test(
    "should display the channel invitation form after clicking on the invite button of a chat",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(channelId);
        await click(".o-mail-discuss-header button[title='Add Users']");
        assert.containsOnce(target, ".o-mail-channel-invitation-form");
    }
);

QUnit.test(
    "should be able to search for a new user to invite from an existing chat",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId_1 = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        const partnerId_2 = pyEnv["res.partner"].create({
            email: "testpartner2@odoo.com",
            name: "TestPartner2",
        });
        pyEnv["res.users"].create({ partner_id: partnerId_1 });
        pyEnv["res.users"].create({ partner_id: partnerId_2 });
        const channelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId_1 }],
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-mail-discuss-header button[title='Add Users']");
        await insertText(".o-mail-channel-invitation-form-search-input", "TestPartner2");
        assert.strictEqual(
            target.querySelector(".o-mail-channel-invitation-form-selectable-partner").textContent,
            "TestPartner2"
        );
    }
);

QUnit.test("Invitation form should display channel group restriction", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const groupId = pyEnv["res.groups"].create({
        name: "testGroup",
    });
    const channelId = pyEnv["mail.channel"].create({
        name: "TestChanel",
        channel_member_ids: [[0, 0, { partner_id: pyEnv.currentPartnerId }]],
        channel_type: "channel",
        group_public_id: groupId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-header button[title='Add Users']");
    assert.containsOnce(
        target,
        '.o-mail-channel-invitation-form:contains(Access restricted to group "testGroup")'
    );
});

QUnit.test(
    "should be able to create a new group chat from an existing chat",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId_1 = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        const partnerId_2 = pyEnv["res.partner"].create({
            email: "testpartner2@odoo.com",
            name: "TestPartner2",
        });
        pyEnv["res.users"].create({ partner_id: partnerId_1 });
        pyEnv["res.users"].create({ partner_id: partnerId_2 });
        const channelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId_1 }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-mail-discuss-header button[title='Add Users']");
        await insertText(".o-mail-channel-invitation-form-search-input", "TestPartner2");
        await click(".form-check-input");
        await click("button[title='Create Group Chat']");
        assert.strictEqual(
            target.querySelector(".o-mail-discuss-thread-name").value,
            "Mitchell Admin, TestPartner, TestPartner2"
        );
    }
);
