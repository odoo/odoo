/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_seen_indicator_tests.js');

QUnit.test('rendering when just one has received the message', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv['res.partner'].create({ name: "Other User" });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: 'chat', // only chat channel have seen notification
    });
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const [mailChannelMemberId1] = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId], ['partner_id', '=', resPartnerId1]]);
    pyEnv['mail.channel.member'].write([mailChannelMemberId1], {
        fetched_message_id: mailMessageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "should display only one seen indicator icon"
    );
});

QUnit.test('rendering when everyone have received the message', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv['res.partner'].create({ name: "Other User" });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: 'chat',
    });
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const mailChannelMemberIds = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId]]);
    pyEnv['mail.channel.member'].write(mailChannelMemberIds, {
        fetched_message_id: mailMessageId,
        seen_message_id: false,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "should display only one seen indicator icon"
    );
});

QUnit.test('rendering when just one has seen the message', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv['res.partner'].create({ name: "Other User" });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: 'chat',
    });
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const mailChannelMemberIds = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId]]);
    pyEnv['mail.channel.member'].write(mailChannelMemberIds, {
        fetched_message_id: mailMessageId,
        seen_message_id: false,
    });
    const [mailChannelMemberId1] = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId], ['partner_id', '=', resPartnerId1]]);
    pyEnv['mail.channel.member'].write([mailChannelMemberId1], {
        seen_message_id: mailMessageId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "should display two seen indicator icon"
    );
});

QUnit.test('rendering when just one has seen & received the message', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv['res.partner'].create({ name: "Other User" });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: 'chat',
    });
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const [mailChannelMemberId1] = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId], ['partner_id', '=', resPartnerId1]]);
    pyEnv['mail.channel.member'].write([mailChannelMemberId1], {
        seen_message_id: mailMessageId,
        fetched_message_id: mailMessageId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "should display two seen indicator icon"
    );
});

QUnit.test('rendering when just everyone has seen the message', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo User" });
    const resPartnerId2 = pyEnv['res.partner'].create({ name: "Other User" });
    const mailChannelId = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
        ],
        channel_type: 'chat',
    });
    const mailMessageId = pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const mailChannelMemberIds = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId]]);
    pyEnv['mail.channel.member'].write(mailChannelMemberIds, {
        fetched_message_id: mailMessageId,
        seen_message_id: mailMessageId,
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.hasClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not considered as all seen"
    );
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "should display two seen indicator icon"
    );
});

});
});
