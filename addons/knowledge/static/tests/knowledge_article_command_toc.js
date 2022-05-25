/** @odoo-module */

import FormView from 'web.FormView';
import testUtils from 'web.test_utils';
const { createView } = testUtils;

import { FieldHtmlInjector } from '@knowledge/js/knowledge_field_html_injector';
import { nextTick } from "@web/../tests/helpers/utils";

const getArch = function (){
    return '<form js_class="knowledge_article_view_form">' +
        '<sheet>' +
            '<div class="o_knowledge_editor d-flex flex-grow-1">' +
                '<field name="body" widget="html"/>' +
            '</div>' +
        '</sheet>' +
    '</form>';
};

/**
 * Will make sure that the "Behaviors" are correctly initialized before calling the ToC command.
 * See 'FieldHtmlInjector#start' for details.
 */
const insertTableOfContent = async (form) => {
    const behaviorInitialized = testUtils.makeTestPromise();
    testUtils.mock.patch(FieldHtmlInjector, {
        start: async function () {
            await this._super(...arguments);
            behaviorInitialized.resolve();
        }
    });

    await testUtils.form.clickEdit(form);
    await testUtils.dom.click(form.$("h1:first"));
    const wysiwyg = form.$('.note-editable').data('wysiwyg');
    await nextTick();
    await behaviorInitialized;
    testUtils.mock.unpatch(FieldHtmlInjector);
    wysiwyg._insertTableOfContent();
    await nextTick();
};

const assertHeadings = (assert, $editorEl, expectedHeadings) => {
    const allHeadings = Array.from($editorEl[0].querySelectorAll('a.o_toc_link'));
    for (let index = 0; index < expectedHeadings.length; index++) {
        const { title, depth } = expectedHeadings[index];
        const headingSelector = `a:contains("${title}").o_toc_link_depth_${depth}`;
        // we have the heading in the DOM
        assert.containsOnce($editorEl, headingSelector);

        const $headingEl = $editorEl.find(headingSelector);
        // is has the correct index (as item order is important)
        assert.equal(index, allHeadings.indexOf($headingEl[0]));
    }
};

QUnit.module('Knowledge Table of Content', {
    beforeEach: function () {
        this.data = {
            'knowledge_article': {
                fields: {
                    body: {type: 'html'},
                },
                records: [{
                    id: 1,
                    display_name: "My Article",
                    body: '' +
                    '<h1>Main 1</h1>' +
                        '<h2>Sub 1-1</h2>' +
                            '<h3>Sub 1-1-1</h3>' +
                            '<h3>Sub 1-1-2</h3>' +
                        '<h2>Sub 1-2</h2>' +
                            '<h3>Sub 1-2-1</h3>' +
                    '<h1>Main 2</h1>' +
                        '<h3>Sub 2-1</h3>' +
                        '<h3>Sub 2-2</h3>' +
                            '<h4>Sub 2-2-1</h4>' +
                                '<h5>Sub 2-2-1-1</h5>' +
                        '<h3>Sub 2-3</h3>',
                }, {
                    id: 2,
                    display_name: "My Article",
                    body: '' +
                    '<h2>Main 1</h2>' +
                        '<h3>Sub 1-1</h3>' +
                            '<h4>Sub 1-1-1</h4>' +
                            '<h4>Sub 1-1-2</h4>' +
                    '<h1>Main 2</h1>' +
                        '<h2>Sub 2-1</h2>',
                }]
            },
        };
    }
}, function (){
    QUnit.test('Check Table of Content is correctly built', async function (assert) {
        assert.expect(24);

        const form = await createView({
            View: FormView,
            model: 'knowledge_article',
            data: this.data,
            arch: getArch(),
            res_id: 1,
        });

        await insertTableOfContent(form);

        const $editorEl = form.$(".odoo-editor-editable");
        const expectedHeadings = [
            {title: 'Main 1',      depth: 0},
            {title: 'Sub 1-1',     depth: 1},
            {title: 'Sub 1-1-1',   depth: 2},
            {title: 'Sub 1-1-2',   depth: 2},
            {title: 'Sub 1-2',     depth: 1},
            {title: 'Sub 1-2-1',   depth: 2},
            {title: 'Main 2',      depth: 0},
            // the next <h3>'s should be at depth 1, because we don't have any <h2> in this subtree
            {title: 'Sub 2-1',     depth: 1},
            {title: 'Sub 2-2',     depth: 1},
            {title: 'Sub 2-2-1',   depth: 2},
            {title: 'Sub 2-2-1-1', depth: 3},
            // the next <h3> should be at depth 1, because we don't have any <h2> in this subtree
            {title: 'Sub 2-3',     depth: 1},
        ]

        assertHeadings(assert, $editorEl, expectedHeadings);

        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.test('Check Table of Content is correctly built - starting with H2', async function (assert) {
        assert.expect(12);

        const form = await createView({
            View: FormView,
            model: 'knowledge_article',
            data: this.data,
            arch: getArch(),
            res_id: 2,
        });

        await insertTableOfContent(form);

        const $editorEl = form.$(".odoo-editor-editable");
        const expectedHeadings = [
            // The "Main 1" section is a <h2>, but it should still be at depth 0
            // as there is no <h1> above it
            {title: 'Main 1',      depth: 0},
            {title: 'Sub 1-1',     depth: 1},
            {title: 'Sub 1-1-1',   depth: 2},
            {title: 'Sub 1-1-2',   depth: 2},
            {title: 'Main 2',      depth: 0},
            {title: 'Sub 2-1',     depth: 1},
        ]
        assertHeadings(assert, $editorEl, expectedHeadings);

        await testUtils.form.clickSave(form);

        form.destroy();
    });
});
