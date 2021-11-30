/** @odoo-module **/

import {
    afterEach,
    beforeEach,
    createRootMessagingComponent,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

import { file } from 'web.test_utils';

const { createFile, inputFiles } = file;
QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('file_uploader', {}, function () {
QUnit.module('file_uploader_tests.js', {
    beforeEach() {
        beforeEach(this);
        this.components = [];

        this.createFileUploaderComponent = async props => {
            await createRootMessagingComponent(this, "FileUploader", {
                props,
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('no conflicts between file uploaders', async function (assert) {
    assert.expect(2);

    await this.start();
    await this.createFileUploaderComponent();
    await this.createFileUploaderComponent();
    const file1 = await createFile({
        name: 'text1.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    inputFiles(
        document.querySelectorAll('.o_FileUploader_input')[0],
        [file1]
    );
    await nextAnimationFrame(); // we can't use afterNextRender as fileInput are display:none
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
    inputFiles(
        document.querySelectorAll('.o_FileUploader_input')[1],
        [file2]
    );
    await nextAnimationFrame();
    assert.strictEqual(
        this.messaging.models['Attachment'].all().length,
        2,
        'Uploaded file should be the only attachment added'
    );
});

});
});
});
