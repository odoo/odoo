/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

import { file } from 'web.test_utils';

const { createFile, inputFiles } = file;
QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('file_uploader', {}, function () {
QUnit.module('file_uploader_tests.js', {
    beforeEach() {
        beforeEach(this);
        this.apps = [];

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
            const { apps, env, widget } = res;
            this.env = env;
            this.apps = apps;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('no conflicts between file uploaders', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 100 }, { id: 101 });
    const { afterNextRender, createChatterContainerComponent } = await this.start();
    const firstChatterContainerComponent = await createChatterContainerComponent({
        threadId: 100,
        threadModel: 'res.partner',
    });
    const secondChatterContainerComponent = await createChatterContainerComponent({
        threadId: 101,
        threadModel: 'res.partner',
    });
    await afterNextRender(() => {
        document.querySelectorAll('.o_ChatterTopbar_buttonAttachments')[0].click();
        document.querySelectorAll('.o_ChatterTopbar_buttonAttachments')[1].click();
    });

    const file1 = await createFile({
        name: 'text1.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    await afterNextRender(() => inputFiles(
        firstChatterContainerComponent.chatter.attachmentBoxView.fileUploader.fileInput,
        [file1]
    ));
    assert.strictEqual(
        this.messaging.models['Attachment'].all().length,
        1,
        'Uploaded file should be the only attachment created'
    );

    const file2 = await createFile({
        name: 'text2.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    await afterNextRender(() => inputFiles(
        secondChatterContainerComponent.chatter.attachmentBoxView.fileUploader.fileInput,
        [file2]
    ));
    assert.strictEqual(
        this.messaging.models['Attachment'].all().length,
        2,
        'Uploaded file should be the only attachment added'
    );
});

});
});
});
