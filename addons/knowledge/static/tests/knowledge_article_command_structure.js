/** @odoo-module */

import FormView from 'web.FormView';
import testUtils from 'web.test_utils';
const { createView } = testUtils;

import { ArticlesStructureBehavior, ArticlesStructureToolbar } from '@knowledge/js/knowledge_articles_structure';
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
 * Will make sure that the "Behaviors" are correctly initialized before calling the structure command.
 * See 'FieldHtmlInjector#start' for details.
 */
const insertArticlesStructure = async (form, onlyDirectChildren) => {
    const behaviorInitialized = testUtils.makeTestPromise();

    testUtils.mock.patch(ArticlesStructureBehavior, {
        applyListeners: function () {
            this.minimumWait = 0;
            this._super(...arguments);
        }
    });

    testUtils.mock.patch(ArticlesStructureToolbar, {
        init: function () {
            this._super(...arguments);
            this.minimumWait = 0;
        }
    });

    testUtils.mock.patch(FieldHtmlInjector, {
        start: async function () {
            await this._super(...arguments);
            behaviorInitialized.resolve();
        }
    });

    await testUtils.form.clickEdit(form);
    await testUtils.dom.click(form.$("p:first"));
    const wysiwyg = form.$('.note-editable').data('wysiwyg');
    await nextTick();
    await behaviorInitialized;

    testUtils.mock.unpatch(FieldHtmlInjector);

    wysiwyg._insertArticlesStructure(onlyDirectChildren);
    await nextTick();

    testUtils.mock.unpatch(ArticlesStructureBehavior);
    testUtils.mock.unpatch(ArticlesStructureToolbar);
};

const articlesStructureSearch = [
    { id: 1, display_name: 'My Article', parent_id: false },
    { id: 2, display_name: 'Child 1', parent_id: [1, 'My Article'] },
    { id: 3, display_name: 'Child 2', parent_id: [1, 'My Article'] },
];

const articlesIndexSearch = articlesStructureSearch.concat([
    { id: 4, display_name: 'Grand-child 1', parent_id: [2, 'Child 1'] },
    { id: 5, display_name: 'Grand-child 2', parent_id: [2, 'Child 1'] },
    { id: 6, display_name: 'Grand-child 3', parent_id: [3, 'Child 2'] },
]);

QUnit.module('Knowledge - Articles Structure Command', {
    beforeEach: function () {
        this.data = {
            'knowledge_article': {
                fields: {
                    body: {type: 'html'},
                },
                records: [{
                    id: 1,
                    display_name: "My Article",
                    body: '<p>Initial Content</p>',
                }]
            },
        };
    }
}, function (){
    QUnit.test('Check Articles Structure is correctly built', async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: FormView,
            model: 'knowledge_article',
            data: this.data,
            arch: getArch(),
            res_id: 1,
            mockRPC: function(route, args) {
                if (args.method === 'search_read' && args.model === 'knowledge.article') {
                    return Promise.resolve(articlesStructureSearch);
                }
                return this._super(route, args);
            }
        });

        await insertArticlesStructure(form, true);
        const $editorEl = form.$(".odoo-editor-editable");

        // /articles_structure only considers the direct children - "Child 1" and "Child 2"
        assert.containsN($editorEl, '.o_knowledge_articles_structure_content ol a', 2);
        assert.containsOnce($editorEl, '.o_knowledge_articles_structure_content ol a:contains("Child 1")');
        assert.containsOnce($editorEl, '.o_knowledge_articles_structure_content ol a:contains("Child 2")');

        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.test('Check Articles Index is correctly built - and updated', async function (assert) {
        assert.expect(8);

        let searchReadCallCount = 0;
        const form = await createView({
            View: FormView,
            model: 'knowledge_article',
            data: this.data,
            arch: getArch(),
            res_id: 1,
            mockRPC: function(route, args) {
                if (args.method === 'search_read' && args.model === 'knowledge.article') {
                    if (searchReadCallCount === 0) {
                        searchReadCallCount++;
                        return Promise.resolve(articlesIndexSearch);
                    } else {
                        // return updated result (called when clicking on the refresh button)
                        return Promise.resolve(articlesIndexSearch.concat([
                            { id: 7, display_name: 'Grand-child 4', parent_id: [3, 'Child 2'] },
                        ]));
                    }
                }
                return this._super(route, args);
            }
        });

        await insertArticlesStructure(form, false);
        const $editorEl = form.$(".odoo-editor-editable");

        // /articles_index considers whole children - "Child 1" and "Child 2" and then their respective children
        assert.containsN($editorEl, '.o_knowledge_articles_structure_content ol a', 5);
        assert.containsOnce($editorEl, '.o_knowledge_articles_structure_content ol a:contains("Child 1")');
        assert.containsOnce($editorEl, '.o_knowledge_articles_structure_content ol a:contains("Child 2")');
        assert.containsOnce($editorEl,
            '.o_knowledge_articles_structure_content ol:contains("Child 1") ol a:contains("Grand-child 1")');
        assert.containsOnce($editorEl,
            '.o_knowledge_articles_structure_content ol:contains("Child 1") ol a:contains("Grand-child 2")');
        assert.containsOnce($editorEl,
            '.o_knowledge_articles_structure_content ol:contains("Child 2") ol a:contains("Grand-child 3")');

        // clicking on update yields an additional Grand-child (see 'mockRPC' here above)
        // make sure our structure is correctly updated
        await testUtils.dom.click(form.$('button[data-call="update_articles_structure"]'));
        await nextTick();

        assert.containsN($editorEl, '.o_knowledge_articles_structure_content ol a', 6);
        assert.containsOnce($editorEl,
            '.o_knowledge_articles_structure_content ol:contains("Child 2") ol a:contains("Grand-child 4")');

        await testUtils.form.clickSave(form);

        form.destroy();
    });
});
