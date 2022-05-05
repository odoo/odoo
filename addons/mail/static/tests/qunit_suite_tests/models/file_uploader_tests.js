/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

import { file } from 'web.test_utils';

const { createFile, inputFiles } = file;
QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('file_uploader', {}, function () {
QUnit.module('file_uploader_tests.js');

QUnit.test('no conflicts between file uploaders', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([{}, {}]);
    const { afterNextRender, createChatterContainerComponent, messaging } = await start();
    const firstChatterContainerComponent = await createChatterContainerComponent({
        threadId: resPartnerId1,
        threadModel: 'res.partner',
    });
    const secondChatterContainerComponent = await createChatterContainerComponent({
        threadId: resPartnerId2,
        threadModel: 'res.partner',
    });

    const file1 = await createFile({
        name: 'text1.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    await afterNextRender(() => inputFiles(
        firstChatterContainerComponent.chatter.fileUploader.fileInput,
        [file1]
    ));
    assert.strictEqual(
        messaging.models['Attachment'].all().length,
        1,
        'Uploaded file should be the only attachment created'
    );

    const file2 = await createFile({
        name: 'text2.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    await afterNextRender(() => inputFiles(
        secondChatterContainerComponent.chatter.fileUploader.fileInput,
        [file2]
    ));
    assert.strictEqual(
        messaging.models['Attachment'].all().length,
        2,
        'Uploaded file should be the only attachment added'
    );
});

});
});
});
