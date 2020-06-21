odoo.define('mail/static/src/components/file_uploader/file_uploader_tests.js', function (require) {
"use strict";

const components = {
    FileUploader: require('mail/static/src/components/file_uploader/file_uploader.js'),
};
const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    inputFiles,
    nextAnimationFrame,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const { file: { createFile } } = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('file_uploader', {}, function () {
QUnit.module('file_uploader_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);
        this.components = [];

        this.createFileUploaderComponent = async props => {
            const FileUploaderComponent = components.FileUploader;
            FileUploaderComponent.env = this.env;
            const fileUploader = new FileUploaderComponent(
                null,
                Object.assign({ attachmentLocalIds: [] }, props)
            );
            await fileUploader.mount(this.widget.el);
            this.components.push(fileUploader);
            return fileUploader;
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            const { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        for (const fileUploader of this.components) {
            fileUploader.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        delete components.FileUploader.env;
        this.env = undefined;
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
        this.env.models['mail.attachment'].all().length,
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
        this.env.models['mail.attachment'].all().length,
        2,
        'Uploaded file should be the only attachment added'
    );
});

});
});
});

});
