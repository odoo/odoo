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
        const resPartnerId1 = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        pyEnv["res.users"].create({ partner_id: resPartnerId1 });
        const mailChannelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(mailChannelId);
        await click(".o-mail-discuss-actions button[title='Add Users']");
        assert.containsOnce(target, ".o-mail-channel-invitation-form");
    }
);

QUnit.test(
    "should be able to search for a new user to invite from an existing chat",
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        const resPartnerId2 = pyEnv["res.partner"].create({
            email: "testpartner2@odoo.com",
            name: "TestPartner2",
        });
        pyEnv["res.users"].create({ partner_id: resPartnerId1 });
        pyEnv["res.users"].create({ partner_id: resPartnerId2 });
        const mailChannelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId);
        await click(".o-mail-discuss-actions button[title='Add Users']");
        await insertText(".o-mail-channel-invitation-form-search-input", "TestPartner2");
        assert.strictEqual(
            target.querySelector(".o-mail-channel-invitation-form-selectable-partner").textContent,
            "TestPartner2"
        );
    }
);

QUnit.test("Invitation form should display channel group restriction", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: resPartnerId1 });
    const resGroupId1 = pyEnv["res.groups"].create({
        name: "testGroup",
    });
    const mailChannelId1 = pyEnv["mail.channel"].create({
        name: "TestChanel",
        channel_member_ids: [[0, 0, { partner_id: pyEnv.currentPartnerId }]],
        channel_type: "channel",
        group_public_id: resGroupId1,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    await click(".o-mail-discuss-actions button[title='Add Users']");
    assert.containsOnce(target, ".o-mail-channel-invitation-form-access-restricted");
});

QUnit.test(
    "should be able to create a new group chat from an existing chat",
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        const resPartnerId2 = pyEnv["res.partner"].create({
            email: "testpartner2@odoo.com",
            name: "TestPartner2",
        });
        pyEnv["res.users"].create({ partner_id: resPartnerId1 });
        pyEnv["res.users"].create({ partner_id: resPartnerId2 });
        const mailChannelId = pyEnv["mail.channel"].create({
            name: "TestChanel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId);
        await click(".o-mail-discuss-actions button[data-action='add-users']");
        await insertText(".o-mail-channel-invitation-form-search-input", "TestPartner2");
        await click(".form-check-input");
        await click("button[title='Create Group Chat']");
        assert.strictEqual(
            target.querySelector(".o-mail-discuss-thread-name").value,
            "Mitchell Admin, TestPartner, TestPartner2"
        );
    }
);
