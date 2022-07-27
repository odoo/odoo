/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js');

QUnit.test('receive visitor typing status "is typing"', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { messaging, openDiscuss } = await start({
        discuss: {
            context: { active_id: mailChannelId1 },
        },
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel.member/typing_status', {
            'channel_id': mailChannelId1,
            'is_typing': true,
            'partner_id': messaging.publicPartners[0].id,
            'partner_name': messaging.publicPartners[0].name,
        });
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Visitor 20 is typing...",
        "Should display that visitor is typing"
    );
});

});
});
