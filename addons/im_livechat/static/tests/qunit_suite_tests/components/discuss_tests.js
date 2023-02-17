/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { datetime_to_str } from 'web.time';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_tests.js');

QUnit.skipRefactoring('livechats are sorted by last activity time in the sidebar: most recent at the top', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [0, 0, {
                    last_interest_dt: datetime_to_str(new Date(2021, 0, 1)),
                    partner_id: pyEnv.currentPartnerId,
                }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                [0, 0, {
                    last_interest_dt: datetime_to_str(new Date(2021, 0, 2)),
                    partner_id: pyEnv.currentPartnerId,
                }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    const initialLivechats = document.querySelectorAll('.o_DiscussSidebarView_categoryLivechat .o_DiscussSidebarCategory_item');
    assert.strictEqual(
        initialLivechats.length,
        2,
        "should have 2 livechat items"
    );
    assert.strictEqual(
        Number(initialLivechats[0].dataset.channelId),
        mailChannelId2,
        "first livechat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        Number(initialLivechats[1].dataset.channelId),
        mailChannelId1,
        "second livechat should be the one with the less recent last activity time"
    );

    // post a new message on the last channel
    await afterNextRender(() => initialLivechats[1].click());
    await afterNextRender(() => document.execCommand('insertText', false, "Blabla"));
    await afterNextRender(() => document.querySelector('.o-mail-composer-send-button').click());

    const newLivechats = document.querySelectorAll('.o_DiscussSidebarView_categoryLivechat .o_DiscussSidebarCategory_item');
    assert.strictEqual(
        newLivechats.length,
        2,
        "should have 2 livechat items"
    );
    assert.strictEqual(
        Number(newLivechats[0].dataset.channelId),
        mailChannelId1,
        "first livechat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        Number(newLivechats[1].dataset.channelId),
        mailChannelId2,
        "second livechat should be the one with the less recent last activity time"
    );
});

QUnit.skipRefactoring('invite button should be present on livechat', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create(
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
    );
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o-mail-discuss-actions button[data-action="add-users"]',
        "Invite button should be visible in top bar when livechat is active thread"
    );
});

QUnit.skipRefactoring('call buttons should not be present on livechat', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create(
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
    );
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_ThreadViewTopbar_callButton',
        "Call buttons should not be visible in top bar when livechat is active thread"
    );
});

QUnit.skipRefactoring('reaction button should not be present on livechat', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
        channel_partner_ids: [pyEnv.currentPartnerId, pyEnv.publicPartnerId],
    });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    await insertText('.o-mail-composer-textarea', "Test");
    await click('.o-mail-composer-send-button');
    await click('.o-mail-message');
    assert.containsNone(
        document.body,
        '.o_MessageActionView_actionReaction',
        "should not have action to add a reaction"
    );
});

});
});
