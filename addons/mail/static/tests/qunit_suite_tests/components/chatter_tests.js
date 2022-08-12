/** @odoo-module **/

import {
    afterNextRender,
    dragenterFiles,
    dropFiles,
    nextAnimationFrame,
    start,
    startServer
} from '@mail/../tests/helpers/test_utils';

import { file } from 'web.test_utils';

const { createFile } = file;

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chatter', {}, function () {
QUnit.module('chatter_tests.js');

QUnit.test('base rendering when chatter has no attachment', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    for (let i = 0; i < 60; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'res.partner',
            res_id: resPartnerId1,
        });
    }
    const { messaging, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_thread`).length,
        1,
        "should have a thread in the chatter"
    );
    assert.strictEqual(
        document.querySelector(`.o_Chatter_thread`).dataset.threadLocalId,
        messaging.models['Thread'].findFromIdentifyingData({
            id: resPartnerId1,
            model: 'res.partner',
        }).localId,
        "thread should have the right thread local id"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        30,
        "the first 30 messages of thread should be loaded"
    );
});

QUnit.test('base rendering when chatter has no record', async function (assert) {
    assert.expect(9);

    const { click, openView } = await start();
    await openView({
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_thread`).length,
        1,
        "should have a thread in the chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        1,
        "should have a message"
    );
    assert.strictEqual(
        document.querySelector(`.o_Message_content`).textContent,
        "Creating a new record...",
        "should have the 'Creating a new record ...' message"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_loadMore',
        "should not have the 'load more' button"
    );

    await click('.o_Message');
    assert.strictEqual(
        document.querySelectorAll(`.o_MessageActionList`).length,
        1,
        "should action list in message"
    );
    assert.containsNone(
        document.body,
        '.o_MessageActionList_action',
        "should not have any action in action list of message"
    );
});

QUnit.test('base rendering when chatter has attachments', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['ir.attachment'].create([
        {
            mimetype: 'text/plain',
            name: 'Blah.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text/plain',
            name: 'Blu.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
    ]);
    const { openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );
});

QUnit.test('show attachment box', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['ir.attachment'].create([
        {
            mimetype: 'text/plain',
            name: 'Blah.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text/plain',
            name: 'Blu.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
    ]);
    const { click, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonToggleAttachments`).length,
        1,
        "should have an attachments button in chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );

    await click(`.o_ChatterTopbar_buttonToggleAttachments`);
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        1,
        "should have an attachment box in the chatter"
    );
});

QUnit.test('chatter: drop attachments', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const { openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    const files = [
        await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        }),
        await createFile({
            content: 'hello, worlduh',
            contentType: 'text/plain',
            name: 'text2.txt',
        }),
    ];
    await afterNextRender(() => dragenterFiles(document.querySelector('.o_Chatter')));
    assert.ok(
        document.querySelector('.o_Chatter_dropZone'),
        "should have a drop zone"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox`).length,
        0,
        "should have no attachment before files are dropped"
    );

    await afterNextRender(() =>
        dropFiles(document.querySelector('.o_Chatter_dropZone'), files)
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_AttachmentCard`).length,
        2,
        "should have 2 attachments in the attachment box after files dropped"
    );

    await afterNextRender(() => dragenterFiles(document.querySelector('.o_Chatter')));
    await afterNextRender(async () =>
        dropFiles(
            document.querySelector('.o_Chatter_dropZone'),
            [
                await createFile({
                    content: 'hello, world',
                    contentType: 'text/plain',
                    name: 'text3.txt',
                })
            ]
        )
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_AttachmentCard`).length,
        3,
        "should have 3 attachments in the attachment box after files dropped"
    );
});

QUnit.test('composer show/hide on log note/send message [REQUIRE FOCUS]', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const { click, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonSendMessage`).length,
        1,
        "should have a send message button"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonLogNote`).length,
        1,
        "should have a log note button"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        0,
        "should not have a composer"
    );

    await click(`.o_ChatterTopbar_buttonSendMessage`);
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        1,
        "should have a composer"
    );
    assert.hasClass(
        document.querySelector('.o_Chatter_composer'),
        'o-focused',
        "composer 'send message' in chatter should have focus just after being displayed"
    );

    await click(`.o_ChatterTopbar_buttonLogNote`);
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        1,
        "should still have a composer"
    );
    assert.hasClass(
        document.querySelector('.o_Chatter_composer'),
        'o-focused',
        "composer 'log note' in chatter should have focus just after being displayed"
    );

    await click(`.o_ChatterTopbar_buttonLogNote`);
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        0,
        "should have no composer anymore"
    );

    await click(`.o_ChatterTopbar_buttonSendMessage`);
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        1,
        "should have a composer"
    );

    await click(`.o_ChatterTopbar_buttonSendMessage`);
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        0,
        "should have no composer anymore"
    );
});

QUnit.test('should display subject when subject is not the same as the thread name', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.partner',
        res_id: resPartnerId1,
        subject: "Salutations, voyageur",
    });
    const { openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    assert.containsOnce(
        document.body,
        '.o_Message_subject',
        "should display subject of the message"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_subject').textContent,
        "Subject: Salutations, voyageur",
        "Subject of the message should be 'Salutations, voyageur'"
    );
});

QUnit.test('should not display subject when subject is the same as the thread name', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Salutations, voyageur" });
    pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.partner',
        res_id: resPartnerId1,
        subject: "Salutations, voyageur",
    });
    const { openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "should not display subject of the message"
    );
});

QUnit.test('should not display user notification messages in chatter', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.message'].create({
        message_type: 'user_notification',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    const { openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    assert.containsNone(
        document.body,
        '.o_Message',
        "should display no messages"
    );
});

QUnit.test('post message with "CTRL-Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const { click, insertText, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in chatter"
    );

    await click('.o_ChatterTopbar_buttonSendMessage');
    await insertText('.o_ComposerTextInput_textarea', "Test");
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { ctrlKey: true, key: "Enter" });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in chatter after posting message from pressing 'CTRL-Enter' in text input of composer"
    );
});

QUnit.test('post message with "META-Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const { click, insertText, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in chatter"
    );

    await click('.o_ChatterTopbar_buttonSendMessage');
    await insertText('.o_ComposerTextInput_textarea', "Test");
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { key: "Enter", metaKey: true });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in channel after posting message from pressing 'META-Enter' in text input of composer"
    );
});

QUnit.test('do not post message with "Enter" keyboard shortcut', async function (assert) {
    // Note that test doesn't assert Enter makes a newline, because this
    // default browser cannot be simulated with just dispatching
    // programmatically crafted events...
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const { click, insertText, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in chatter"
    );

    await click('.o_ChatterTopbar_buttonSendMessage');
    await insertText('.o_ComposerTextInput_textarea', "Test");
    const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
    document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_Message',
        "should still not have any message in mailing channel after pressing 'Enter' in text input of composer"
    );
});

});
});
});
