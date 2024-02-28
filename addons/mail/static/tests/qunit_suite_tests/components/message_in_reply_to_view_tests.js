/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function() {
QUnit.module('message_in_reply_to_view_tests');

QUnit.test('click on message in reply to highlights the parent message', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "Hey lol",
        message_type: 'comment',
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const mailMessageId2 = pyEnv['mail.message'].create({
        body: "Response to Hey lol",
        message_type: 'comment',
        model: 'mail.channel',
        parent_id: mailMessageId1,
        res_id: mailChannelId1,
    });
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    await click(`.o_Message[data-id="${mailMessageId2}"] .o_MessageInReplyToView_body`);
    assert.containsOnce(
        document.body,
        `.o-highlighted[data-id="${mailMessageId1}"]`,
        "click on message in reply to should highlight the parent message"
    );
});
});
});
