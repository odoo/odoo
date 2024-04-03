/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_tests.js');

QUnit.test('livechat: no add attachment button', async function (assert) {
    // Attachments are not yet supported in livechat, especially from livechat
    // visitor PoV. This may likely change in the future with task-2029065.
    assert.expect(2);

    const pyEnv = await startServer();
    const livechatId = pyEnv['mail.channel'].create({ channel_type: 'livechat' });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: livechatId },
        },
    });
    await openDiscuss();
    assert.containsOnce(document.body, '.o_Composer', "should have a composer");
    assert.containsNone(
        document.body,
        '.o_Composer_buttonAttachment',
        "composer linked to livechat should not have a 'Add attachment' button"
    );
});

QUnit.test('livechat: disable attachment upload via drag and drop', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const livechatId = pyEnv['mail.channel'].create({ channel_type: 'livechat' });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: livechatId },
        },
    });
    await openDiscuss();
    assert.containsOnce(document.body, '.o_Composer', "should have a composer");
    assert.containsNone(
        document.body,
        '.o_Composer_dropZone',
        "composer linked to livechat should not have a dropzone"
    );
});

});
});
