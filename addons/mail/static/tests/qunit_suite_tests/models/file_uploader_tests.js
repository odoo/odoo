/** @odoo-module **/

import { start, startServer, dropFiles, dragenterFiles } from '@mail/../tests/helpers/test_utils';
import { dom, file } from 'web.test_utils';

const { createFile } = file;
QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('file_uploader', {}, function () {
QUnit.module('file_uploader_tests.js');

QUnit.test('no conflicts between file uploaders', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const channelId =  pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        body: 'not empty',
        model: 'mail.channel',
        res_id: channelId,
    });
    const { afterNextRender, click, messaging, openView } = await start();

    // Uploading file in the first thread: res.partner chatter.
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    const file1 = await createFile({
        name: 'text1.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    await afterNextRender(() =>
        dragenterFiles(document.querySelector('.o_Chatter'))
    );
    await afterNextRender(() =>
        dropFiles(document.querySelector('.o_Chatter_dropZone'), [file1])
    );

    // Uploading file in the second thread: mail.channel in chatWindow.
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_NotificationListItem[data-thread-id="${channelId}"][data-thread-model="mail.channel"]`);
    const file2 = await createFile({
        name: 'text2.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    await afterNextRender(() =>
        dragenterFiles(document.querySelector('.o_ChatWindow'))
    );
    await afterNextRender(() =>
        dropFiles(document.querySelector('.o_ChatWindow .o_DropZone'), [file2])
    );
    await afterNextRender(() =>
        dom.triggerEvent(
            document.querySelector('.o_ChatWindow .o_ComposerTextInput_textarea'),
            'keydown',
            { key: 'Enter' },
        )
    );
    const channelThread = messaging.models['Thread'].findFromIdentifyingData({ id: channelId, model: 'mail.channel' });
    const chatterThread = messaging.models['Thread'].findFromIdentifyingData({ id: resPartnerId1, model: 'res.partner' });
    assert.strictEqual(
        chatterThread.allAttachments.length,
        1,
        'Chatter thread should only have one attachment'
    );
    assert.strictEqual(
        channelThread.allAttachments.length,
        1,
        'Channel thread should only have one attachment'
    );
});

});
});
});
