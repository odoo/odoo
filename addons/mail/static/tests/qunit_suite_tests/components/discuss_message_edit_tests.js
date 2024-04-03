/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_message_edit_tests.js');

QUnit.test('click on message edit button should open edit composer', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'comment',
        model: 'mail.channel',
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
    await click('.o_Message');
    await click('.o_MessageActionView_actionEdit');
    assert.containsOnce(document.body, '.o_Message_composer', 'click on message edit button should open edit composer');
});

});
});
