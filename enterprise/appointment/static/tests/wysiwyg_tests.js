/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { patchWithCleanup, triggerEvent } from '@web/../tests/helpers/utils';
import { makeFakeDialogService } from '@web/../tests/helpers/mock_services';
import { Wysiwyg } from '@web_editor/js/wysiwyg/wysiwyg';
import { insertText } from '@web_editor/js/editor/odoo-editor/test/utils'
import { setSelection } from '@web_editor/js/editor/odoo-editor/src/utils/utils';

const linkUrl = window.location.origin + '/book/123';
const serviceRegistry = registry.category("services");
let serverData;
let wysiwyg;

function onMount() {
    const editor = wysiwyg.odooEditor;
    const editable = editor.editable;
    editor.clean();
    const originalContent = editable.innerHTML;
    editor.testMode = true;
    return { editor, editable, originalContent };
}

function assertHistorySteps(assert, editable, originalContent) {
    const currentContent = editable.innerHTML;
    wysiwyg.odooEditor.historyUndo();
    wysiwyg.odooEditor.clean();
    assert.strictEqual(editable.innerHTML, originalContent);
    wysiwyg.odooEditor.historyRedo();
    wysiwyg.odooEditor.clean();
    assert.strictEqual(editable.innerHTML, currentContent);
}

QUnit.module('appointment.wysiwyg', {
    before: function () {
        serverData = {
            models: {
                note: {
                    fields: {
                        display_name: {
                            string: "Displayed name",
                            type: "char"
                        },
                        body: {
                            string: "Message",
                            type: "html"
                        },
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
                        body: '<p></p>',
                    }, {
                        id: 2,
                        display_name: "second record",
                        body: '<p><a href="http://odoo.com">Existing link</a></p>',
                    }],
                },
            },
        };
    },
    beforeEach: function () {
        setupViewRegistries();
        serviceRegistry.add(
            'dialog',
            makeFakeDialogService((dialogClass, props) => props.insertLink(linkUrl)),
            { force: true },
        );
        patchWithCleanup(Wysiwyg.prototype, {
            init() {
                super.init(...arguments);
                wysiwyg = this;
            }
        });
    }
}, function () {

    QUnit.test('Insert link with "/Appointment"', async function (assert) {
        assert.expect(3);

        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html_legacy" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable, originalContent } = onMount();

        // Type powerbox command + 'Enter'
        setSelection(editable.querySelector('p'), 0);
        await insertText(editor, '/Appointment');
        await triggerEvent(editable, null, 'keydown', { key: 'Enter' });
        editor.clean();

        assert.strictEqual(editable.innerHTML,
            `<p><a href="${linkUrl}">Schedule an Appointment</a></p>`);

        assertHistorySteps(assert, editable, originalContent);
    });

    QUnit.test('Replace existing link with "/Appointment" link', async function (assert) {
        assert.expect(3);

        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html_legacy"/>' +
                '</form>',
            resId: 2,
        });
        const { editor, editable, originalContent } = onMount();

        // Place cursor at beginning of link's label, after the ZWNBSP.
        const p = editable.querySelector('p');
        setSelection(p.querySelector('a').childNodes[1], 0);

        // Type powerbox command + 'Enter'
        await insertText(editor, '/Appointment');
        await triggerEvent(editable, null, 'keydown', { key: 'Enter' });
        editor.clean();

        assert.strictEqual(editable.innerHTML,
            `<p><a href="${linkUrl}">Schedule an Appointment</a></p>`);

        assertHistorySteps(assert, editable, originalContent);
    });
});
