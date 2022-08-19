/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_sidebar_category_item_tests.js');

QUnit.test('livechat - avatar: should have a smiley face avatar for an anonymous livechat item', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    const livechatItem = document.querySelector(`
        .o_DiscussSidebarCategoryItem[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
    `);
    assert.containsOnce(
        livechatItem,
        `.o_DiscussSidebarCategoryItem_image`,
        "should have an avatar"
    );
    assert.strictEqual(
        livechatItem.querySelector(`:scope .o_DiscussSidebarCategoryItem_image`).dataset.src,
        '/mail/static/src/img/smiley/avatar.jpg',
        'should have the smiley face as the avatar for anonymous users'
    );
});

QUnit.test('livechat - avatar: should have a partner profile picture for a livechat item linked with a partner', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Jean",
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    const livechatItem = document.querySelector(`
        .o_DiscussSidebarCategoryItem[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
    `);
    assert.containsOnce(
        livechatItem,
        `.o_DiscussSidebarCategoryItem_image`,
        "should have an avatar"
    );
    assert.strictEqual(
        livechatItem.querySelector(`:scope .o_DiscussSidebarCategoryItem_image`).dataset.src,
        `/web/image/res.partner/${resPartnerId1}/avatar_128`,
        'should have the partner profile picture as the avatar for partners'
    );
});

});
});
