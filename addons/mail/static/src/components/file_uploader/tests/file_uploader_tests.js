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
            return createRootMessagingComponent(this, "FileUploader", {
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
    const fileUploader1 = await this.createFileUploaderComponent();
    const fileUploader2 = await this.createFileUploaderComponent();
    const file1 = await createFile({
        name: 'text1.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    inputFiles(
        fileUploader1.el.querySelector('.o_FileUploader_input'),
        [file1]
    );
    await nextAnimationFrame(); // we can't use afterNextRender as fileInput are display:none
    assert.strictEqual(
        this.messaging.models['mail.attachment'].all().length,
        1,
        'Uploaded file should be the only attachment created'
    );

    const file2 = await createFile({
        name: 'text2.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    inputFiles(
        fileUploader2.el.querySelector('.o_FileUploader_input'),
        [file2]
    );
    await nextAnimationFrame();
    assert.strictEqual(
        this.messaging.models['mail.attachment'].all().length,
        2,
        'Uploaded file should be the only attachment added'
    );
});

});
});
});
