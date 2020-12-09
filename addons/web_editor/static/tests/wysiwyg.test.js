odoo.define('web_editor.wysiwyg.test', function (require) {
"use strict";

var Wysiwyg = require('web_editor.wysiwyg');

QUnit.module('web_editor', {}, function () {

    QUnit.module('wysiwyg');

    QUnit.test('should automatically get the context when calling execCommand inside execCommand', async function (assert) {
        assert.expect(1);

        const div = document.createElement('div');

        const wysiwyg = new Wysiwyg(undefined, { location: [div, 'append'] });
        await wysiwyg.start();
        const calls = [];

        await wysiwyg.execCommand(async () => {
            calls.push(1);
            await wysiwyg.execCommand(() => {
                calls.push(2);
            });
        });
        await wysiwyg.execCommand(() => {
            calls.push(3);
        });

        assert.deepEqual(calls, [1, 2, 3], "all command should have been called in the proper order");
    });
});

});
