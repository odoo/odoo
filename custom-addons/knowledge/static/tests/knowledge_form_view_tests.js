/** @odoo-module */

import { onMounted, onPatched, onWillStart, status } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { click, getFixture, makeDeferred, mockSendBeacon, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { renderToElement } from "@web/core/utils/render";
import { patch } from "@web/core/utils/patch";
import { HtmlField } from "@web_editor/js/backend/html_field";
import { parseHTML } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { ArticlesStructureBehavior } from "@knowledge/components/behaviors/articles_structure_behavior/articles_structure_behavior";
import { TableOfContentBehavior } from "@knowledge/components/behaviors/table_of_content_behavior/table_of_content_behavior";
import { TemplateBehavior } from "@knowledge/components/behaviors/template_behavior/template_behavior";
import { KnowledgeArticleFormController } from "@knowledge/js/knowledge_controller";
import { knowledgeCommandsService } from "@knowledge/services/knowledge_commands_service";

const serviceRegistry = registry.category("services");


const articlesStructureSearch = {
    records: [
        { id: 1, display_name: 'My Article', parent_id: false },
        { id: 2, display_name: 'Child 1', parent_id: 1 },
        { id: 3, display_name: 'Child 2', parent_id: 1 },
    ]
};

const articlesIndexSearch = {
    records: articlesStructureSearch.records.concat([
        { id: 4, display_name: 'Grand-child 1', parent_id: 2 },
        { id: 5, display_name: 'Grand-child 2', parent_id: 2 },
        { id: 6, display_name: 'Grand-child 3', parent_id: 3 },
    ])
};

/**
 * Insert an article structure (index or outline) in the target node. This will
 * guarantee that the structure behavior is fully mounted before continuing.
 * @param {HTMLElement} editable
 * @param {HTMLElement} target
 * @param {boolean} childrenOnly
 */
const insertArticlesStructure = async (editable, target, childrenOnly) => {
    const articleStructureMounted = makeDeferred();
    const wysiwyg = $(editable).data('wysiwyg');
    const unpatch = patch(ArticlesStructureBehavior.prototype, {
        setup() {
            super.setup(...arguments);
            onMounted(() => {
                articleStructureMounted.resolve();
                unpatch();
            });
        }
    });
    const selection = document.getSelection();
    selection.removeAllRanges();
    const range = new Range();
    range.setStart(target, 0);
    range.setEnd(target, 0);
    selection.addRange(range);
    await nextTick();
    wysiwyg._insertArticlesStructure(childrenOnly);
    await articleStructureMounted;
    await nextTick();
};

let arch;
let fixture;
let formController;
let htmlField;
let htmlFieldPromise;
let record;
let resModel;
let serverData;
let type;

QUnit.module("Knowledge - Articles Structure Command", (hooks) => {
    hooks.beforeEach(() => {
        fixture = getFixture();
        type = "form";
        resModel = "knowledge.article";
        serverData = {
            models: {
                "knowledge.article": {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                        body: {string: "Body", type: 'html'},
                    },
                    records: [{
                        id: 1,
                        display_name: "My Article",
                        body: '<p class="test_target"><br/></p>',
                    }],
                    methods: {
                        get_sidebar_articles() {
                            return {articles: [], favorite_ids: []};
                        }
                    }
                }
            }
        };
        arch = '<form js_class="knowledge_article_view_form">' +
            '<sheet>' +
                '<div class="o_knowledge_editor">' +
                    '<field name="body" widget="html"/>' +
                '</div>' +
            '</sheet>' +
        '</form>';
        setupViewRegistries();
    });
    QUnit.test('Check Articles Structure is correctly built', async function (assert) {
        assert.expect(3);

        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === 'web_search_read' && args.model === 'knowledge.article') {
                    return Promise.resolve(articlesStructureSearch);
                }
            }
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        const target = editable.querySelector('p.test_target');
        await insertArticlesStructure(editable, target, true);

        // /articles_structure only considers the direct children - "Child 1" and "Child 2"
        assert.containsN(editable, '.o_knowledge_articles_structure_content ol a', 2);
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 1")');
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 2")');
    });
    QUnit.test('Check Articles Index is correctly built - and updated', async function (assert) {
        assert.expect(8);

        let searchReadCallCount = 0;
        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === 'web_search_read' && args.model === 'knowledge.article') {
                    if (searchReadCallCount === 0) {
                        searchReadCallCount++;
                        return Promise.resolve(articlesIndexSearch);
                    } else {
                        // return updated result (called when clicking on the refresh button)
                        return Promise.resolve({
                            records: articlesIndexSearch.records.concat([
                                { id: 7, display_name: 'Grand-child 4', parent_id: 3 },
                            ])
                        });
                    }
                }
            }
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        const target = editable.querySelector('p.test_target');
        await insertArticlesStructure(editable, target, false);

        // /articles_index considers whole children - "Child 1" and "Child 2" and then their respective children
        assert.containsN(editable, '.o_knowledge_articles_structure_content ol a', 5);
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 1")');
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 2")');
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 1") ol a:contains("Grand-child 1")');
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 1") ol a:contains("Grand-child 2")');
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 2") ol a:contains("Grand-child 3")');

        // clicking on update yields an additional Grand-child (see 'mockRPC' here above)
        // make sure our structure is correctly updated
        await click(editable, '.o_knowledge_behavior_type_articles_structure button[title="Update"]');
        await nextTick();

        assert.containsN(editable, '.o_knowledge_articles_structure_content ol a', 6);
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 2") ol a:contains("Grand-child 4")');

    });
});

//==============================================================================
//                                External Views
//==============================================================================

/**
 * Insert an "External" view inside knowledge article.
 * @param {HTMLElement} editable
 */
const testAppendBehavior = async (editable) => {
    const wysiwyg = $(editable).data('wysiwyg');

    const insertedDiv = renderToElement('knowledge.AbstractBehaviorBlueprint', {
        behaviorType: "o_knowledge_behavior_type_template",
    });
    wysiwyg.appendBehaviorBlueprint(insertedDiv);
    await nextTick();
};

QUnit.module("Knowledge - External View Insertion", (hooks) => {
    hooks.beforeEach(() => {
        fixture = getFixture();
        type = "form";
        resModel = "knowledge_article";
        serverData = {
            models: {
                knowledge_article: {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                        body: {string: "Body", type: 'html'},
                    },
                    records: [{
                        id: 1,
                        display_name: "Insertion Article",
                        body: '\n<p>\n<br/>\n</p>\n',
                    }],
                    methods: {
                        get_sidebar_articles() {
                            return {articles: [], favorite_ids: []};
                        }
                    }
                }
            }
        };
        arch = '<form js_class="knowledge_article_view_form">' +
            '<sheet>' +
                '<div class="o_knowledge_editor">' +
                    '<field name="body" widget="html"/>' +
                '</div>' +
            '</sheet>' +
        '</form>';
        setupViewRegistries();
    });
    QUnit.test('Check that the insertion of views goes as expected', async function (assert) {

        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        await testAppendBehavior(editable);

        // We are checking if the anchor has been correctly inserted inside
        // the article.
        assert.containsOnce(editable, '.o_knowledge_behavior_anchor');
        const anchor = editable.querySelector('.o_knowledge_behavior_anchor');
        assert.notOk(anchor.nextSiblingElement, 'The inserted view should be the last element in the article');
    });
});

//==============================================================================
//                                   Macros
//==============================================================================

QUnit.module("Knowledge - Enable conditions for Macros", (hooks) => {
    let formController;
    hooks.beforeEach(() => {
        patchWithCleanup(FormController.prototype, {
            setup() {
                super.setup(...arguments);
                formController = this;
            }
        });
        fixture = getFixture();
        serverData = {
            models: {
                'knowledge.article': {
                    fields: {
                        name: {string: "Name", type: "char"},
                        body: {string: "Body", type: "html"},
                    },
                    records: [{
                        id: 1,
                        name: "Article",
                        body: "<p><br></p>",
                    }],
                },
                'product.product': {
                    fields: {
                        note: {string: "Note", type: "html", readonly: true},
                        memo: {string: "Memo", type: "html"},
                        description: {string: "Description", type: "html"},
                        comment: {string: "Comment", type: "html"},
                        narration: {string: "Narration", type: "html"},
                        delivery_instructions: {string: "Delivery instructions", type: "html"},
                        product_details: {string: "Product details", type: "html"},
                        user_feedback: {string: "User feedback", type: "html"},
                    },
                    records: [{
                        id: 1,
                        note: "<p>note</p>",
                        memo: "<p>memo</p>",
                        description: "<p>description</p>",
                        comment: "<p>comment</p>",
                        narration: "<p>narration</p>",
                        delivery_instructions: "<p>delivery instructions</p>",
                        product_details: "<p>product details</p>",
                        user_feedback: "<p>user feedback</p>",
                    }],
                }
            },
        };
        setupViewRegistries();
        // Remove the mock_service (which is a dummy) and replace it with
        // the real KnowledgeCommandsService.
        serviceRegistry.remove("knowledgeCommandsService");
        serviceRegistry.add("knowledgeCommandsService", knowledgeCommandsService);
    });

    QUnit.test("Don't validate a html field candidate from a forbidden model", async function (assert) {
        assert.expect(1);
        arch = `
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                    </group>
                    <notebook>
                        <page string='Test page' name='test_page'>
                            <field name='body'/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `;
        await makeView({
            type: "form",
            resModel: "knowledge.article",
            serverData,
            arch,
            resId: 1,
        });
        formController._evaluateRecordCandidate();
        // Forbidden models are defined in KNOWLEDGE_EXCLUDED_MODELS in the
        // Knowledge form_controller_patch. They typically are models which
        // have a heavily customized form view so a generic macro won't be able
        // to navigate them. `knowledge.article` is one of them.
        assert.equal(
            formController.knowledgeCommandsService.getCommandsRecordInfo(),
            null
        );
    });

    QUnit.test("Validate a visible editable html field with priority", async function (assert) {
        assert.expect(1);
        arch = `
            <form>
                <sheet>
                    <group>
                        <field name="note"/>
                        <field name="memo" readonly="True"/>
                        <div invisible="True">
                            <field name="description"/>
                        </div>
                        <field name="comment" invisible="True"/>
                        <field name="product_details"/>
                        <field name="narration"/>
                    </group>
                </sheet>
            </form>
        `;
        await makeView({
            type: "form",
            resModel: "product.product",
            serverData,
            arch,
            resId: 1,
        });
        formController._evaluateRecordCandidate();
        // Here the selected html field should be `narration`, because
        // every other field declared in the xml view before it is either
        // readonly (on the model or specifically in the view),
        // invisible (the field itself or one of its parent nodes),
        // not in the priority list defined in the Knowledge
        // form_controller_patch (KNOWLEDGE_RECORDED_FIELD_NAMES).
        assert.equal(
            formController.knowledgeCommandsService.getCommandsRecordInfo().fieldInfo.name,
            "narration",
        );
    });

    QUnit.test("Select a candidate in a named page, in order of declaration", async function (assert) {
        assert.expect(1);
        arch = `
            <form>
                <sheet>
                    <notebook>
                        <page string='Unnamed'>
                            <field name='product_details'/>
                        </page>
                        <page string='Named' name='named'>
                            <field name='user_feedback'/>
                            <field name='delivery_instructions'/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `;
        await makeView({
            type: "form",
            resModel: "product.product",
            serverData,
            arch,
            resId: 1,
        });
        formController._evaluateRecordCandidate();
        // Here the selected html field should be `user_feedback`, because
        // it is the first field declared in the first named page of the
        // xml view. This test also demonstrates that the alphabetical order
        // is not considered, since `delivery_instructions` is not chosen.
        assert.equal(
            formController.knowledgeCommandsService.getCommandsRecordInfo().fieldInfo.name,
            "user_feedback",
        );
    });
});

//==============================================================================
//                                Save Scenarios
//==============================================================================

QUnit.module("Knowledge - Ensure body save scenarios", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(KnowledgeArticleFormController.prototype, {
            setup() {
                super.setup(...arguments);
                formController = this;
            }
        });
        htmlFieldPromise = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            async startWysiwyg() {
                await super.startWysiwyg(...arguments);
                await nextTick();
                htmlFieldPromise.resolve(this);
            }
        });
        record = {
            id: 1,
            display_name: "Article",
            body: "<p class='test_target'><br></p>",
        };
        serverData = {
            models: {
                knowledge_article: {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                        body: {string: "Body", type: "html"},
                    },
                    records: [record],
                    methods: {
                        get_sidebar_articles() {
                            return {articles: [], favorite_ids: []};
                        }
                    }
                }
            },
        };
        arch = `
            <form js_class="knowledge_article_view_form">
                <sheet>
                    <div class="o_knowledge_editor">
                        <field name="body" widget="html"/>
                    </div>
                </sheet>
            </form>
        `;
        setupViewRegistries();
    });

    //--------------------------------------------------------------------------
    // TESTS
    //--------------------------------------------------------------------------

    QUnit.test("Ensure save on beforeLeave when Behaviors mutex is not idle and when it is", async function (assert) {
        /**
         * This test forces a call to the beforeLeave function of the KnowledgeFormController. It
         * simulates that we leave the form view.
         *
         * The function will be called 2 times successively:
         * 1- at a controlled time when a Behavior is in the process of being
         *    mounted, but not finished, to ensure that the saved article value is
         *    not corrupted (no missing html node).
         * 2- at a controlled time when every Behavior was successfully mounted and
         *    no other Behavior is being mounted, to ensure that the saved article
         *    value contains information updated from the Behavior nodes.
         */

        assert.expect(4);
        let writeCount = 0;
        await makeView({
            type: "form",
            resModel: "knowledge_article",
            serverData,
            arch,
            resId: 1,
            mockRPC(route, args) {
                if (
                    route === '/web/dataset/call_kw/knowledge_article/web_save' &&
                    args.model === 'knowledge_article'
                ) {
                    if (writeCount === 0) {
                        // The first expected `write` value should be the
                        // unmodified blueprint, since OWL has not finished
                        // mounting the Behavior nodes.
                        assert.notOk(editor.editable.querySelector('[data-prop-name="content"]'));
                        assert.equal(editor.editable.querySelector('.witness').textContent, "WITNESS_ME!");
                    } else if (writeCount === 1) {
                        // Change the expected `write` value, the "witness node"
                        // should have been cleaned since it serves no purpose
                        // for this Behavior in the OWL template.
                        assert.notOk(editor.editable.querySelector('.witness'));
                        assert.equal(editor.editable.querySelector('[data-prop-name="content"]').innerHTML, "<p><br></p>");
                    } else {
                        // This should never be called and will fail if it is.
                        assert.ok(writeCount === 1, "Write should only be called 2 times during this test");
                    }
                    writeCount += 1;
                }
            }
        });
        // Let the htmlField be mounted and recover the Component instance.
        htmlField = await htmlFieldPromise;
        const editor = htmlField.wysiwyg.odooEditor;

        // Patch to control when the next mounting is done.
        const isAtWillStart = makeDeferred();
        const pauseWillStart = makeDeferred();
        const unpatch = patch(TemplateBehavior.prototype, {
            setup() {
                super.setup(...arguments);
                onWillStart(async () => {
                    isAtWillStart.resolve();
                    await pauseWillStart;
                    unpatch();
                });
            }
        });
        // Introduce a Behavior blueprint with an "witness node" that does not
        // serve any purpose except for the fact that it should be left
        // untouched until OWL completely finishes its mounting process
        // and at that point it will be replaced by the rendered OWL template.
        const behaviorHTML = `
            <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_template">
                <div class="witness">WITNESS_ME!</div>
            </div>
        `;
        const anchor = parseHTML(editor.document, behaviorHTML).firstChild;
        const target = editor.editable.querySelector(".test_target");
        // The BehaviorState MutationObserver will try to start the mounting
        // process for the Behavior with the anchor node as soon as it is in
        // the DOM.
        editor.editable.replaceChild(anchor, target);
        // Validate the mutation as a normal user history step.
        editor.historyStep();

        // Wait for the Template Behavior onWillStart lifecycle step.
        await isAtWillStart;

        // Attempt a save when the mutex is not idle. It should save the
        // unchanged blueprint of the Behavior.
        await formController.beforeLeave();

        // Allow the Template Behavior to go past the `onWillStart` lifecycle
        // step.
        pauseWillStart.resolve();

        // Wait for the mount mutex to be idle. The Template Behavior should
        // be fully mounted after this.
        await htmlField.mountBehaviors();

        // Attempt a save when the mutex is idle.
        await formController.beforeLeave();
    });

    QUnit.test("Ensure save on beforeUnload when Behaviors mutex is not idle and when it is", async function (assert) {
        /**
         * This test forces a call to the beforeUnload function of the KnowledgeFormController. It
         * simulates that the close the browser/tab when being on that form view.
         *
         * The function will be called 2 times successively:
         * 1- at a controlled time when a Behavior is in the process of being
         *    mounted, but not finished, to ensure that the saved article value is
         *    not corrupted (no missing html node).
         * 2- at a controlled time when every Behavior was successfully mounted and
         *    no other Behavior is being mounted, to ensure that the saved article
         *    value contains information updated from the Behavior nodes.
         */

        mockSendBeacon((route) => {
            if (route === '/web/dataset/call_kw/knowledge_article/web_save') {
                if (writeCount === 0) {
                    // The first expected `write` value should be the
                    // unmodified blueprint, since OWL has not finished
                    // mounting the Behavior nodes.
                    assert.notOk(editor.editable.querySelector('[data-prop-name="content"]'));
                    assert.equal(editor.editable.querySelector('.witness').textContent, "WITNESS_ME!");
                } else if (writeCount === 1) {
                    // Change the expected `write` value, the "witness node"
                    // should have been cleaned since it serves no purpose
                    // for this Behavior in the OWL template.
                    assert.notOk(editor.editable.querySelector('.witness'));
                    assert.equal(editor.editable.querySelector('[data-prop-name="content"]').innerHTML, "<p><br></p>");
                } else {
                    // This should never be called and will fail if it is.
                    assert.ok(writeCount === 1, "Write should only be called 2 times during this test");
                }
                writeCount += 1;
            }
        });

        assert.expect(4);
        let writeCount = 0;
        await makeView({
            type: "form",
            resModel: "knowledge_article",
            serverData,
            arch,
            resId: 1,
        });
        // Let the htmlField be mounted and recover the Component instance.
        htmlField = await htmlFieldPromise;
        const editor = htmlField.wysiwyg.odooEditor;

        // Patch to control when the next mounting is done.
        const isAtWillStart = makeDeferred();
        const pauseWillStart = makeDeferred();
        const unpatch = patch(TemplateBehavior.prototype, {
            setup() {
                super.setup(...arguments);
                onWillStart(async () => {
                    isAtWillStart.resolve();
                    await pauseWillStart;
                    unpatch();
                });
            }
        });
        // Introduce a Behavior blueprint with an "witness node" that does not
        // serve any purpose except for the fact that it should be left
        // untouched until OWL completely finishes its mounting process
        // and at that point it will be replaced by the rendered OWL template.
        const behaviorHTML = `
            <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_template">
                <div class="witness">WITNESS_ME!</div>
            </div>
        `;
        const anchor = parseHTML(editor.document, behaviorHTML).firstChild;
        const target = editor.editable.querySelector(".test_target");
        // The BehaviorState MutationObserver will try to start the mounting
        // process for the Behavior with the anchor node as soon as it is in
        // the DOM.
        editor.editable.replaceChild(anchor, target);
        // Validate the mutation as a normal user history step.
        editor.historyStep();

        // Wait for the Template Behavior onWillStart lifecycle step.
        await isAtWillStart;

        // Attempt a save when the mutex is not idle. It should save the
        // unchanged blueprint of the Behavior.
        await formController.beforeUnload();

        // Allow the Template Behavior to go past the `onWillStart` lifecycle
        // step.
        pauseWillStart.resolve();

        // Wait for the mount mutex to be idle. The Template Behavior should
        // be fully mounted after this.
        await htmlField.mountBehaviors();

        // Attempt a save when the mutex is idle.
        await formController.beforeUnload();
    });
});

//==============================================================================
//                                Table of Contents
//==============================================================================

/**
 * Insert a Table Of Content (TOC) in the target node. This will guarantee that
 * the TOC behavior is fully mounted before continuing.
 * @param {HTMLElement} editable - Root HTMLElement of the editor
 * @param {HTMLElement} target - Target node
 */
const insertTableOfContent = async (editable, target) => {
    const tocMounted = makeDeferred();
    const wysiwyg = $(editable).data('wysiwyg');
    const unpatch = patch(TableOfContentBehavior.prototype, {
        setup() {
            super.setup(...arguments);
            onMounted(() => {
                tocMounted.resolve();
                unpatch();
            });
        }
    });
    const selection = document.getSelection();
    selection.removeAllRanges();
    const range = new Range();
    range.setStart(target, 0);
    range.setEnd(target, 0);
    selection.addRange(range);
    await nextTick();
    wysiwyg._insertTableOfContent();
    await tocMounted;
    await nextTick();
};

/**
 * @param {Object} assert - QUnit assert object used to trigger asserts and exceptions
 * @param {HTMLElement} editable - Root HTMLElement of the editor
 * @param {Array[Object]} expectedHeadings - List of headings that should appear in the toc of the editable
 */
const assertHeadings = (assert, editable, expectedHeadings) => {
    const allHeadings = Array.from(editable.querySelectorAll('a.o_knowledge_toc_link'));
    for (let index = 0; index < expectedHeadings.length; index++) {
        const { title, depth } = expectedHeadings[index];
        const headingSelector = `a:contains("${title}").o_knowledge_toc_link_depth_${depth}`;
        // we have the heading in the DOM
        assert.containsOnce(editable, headingSelector);

        const $headingEl = $(editable).find(headingSelector);
        // it has the correct index (as item order is important)
        assert.equal(index, allHeadings.indexOf($headingEl[0]));
    }
};

QUnit.module("Knowledge Table of Content", (hooks) => {
    hooks.beforeEach(() => {
        fixture = getFixture();
        type = "form";
        resModel = "knowledge_article";
        serverData = {
            models: {
                knowledge_article: {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                        body: {string: "Body", type: 'html'},
                    },
                    records: [{
                        id: 1,
                        display_name: "My Article",
                        body: '<p class="test_target"><br/></p>' +
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
                        body: '<p class="test_target"><br/></p>' +
                        '<h2>Main 1</h2>' +
                            '<h3>Sub 1-1</h3>' +
                                '<h4>Sub 1-1-1</h4>' +
                                '<h4>Sub 1-1-2</h4>' +
                        '<h1>Main 2</h1>' +
                            '<h2>Sub 2-1</h2>',
                    }, {
                        id: 3,
                        display_name: "My Article",
                        body: `<p class="test_target"><br/></p>
                        <h3>Main 1</h3>
                        <h2>Main 2</h2>`,
                    }],
                    methods: {
                        get_sidebar_articles() {
                            return {articles: [], favorite_ids: []};
                        }
                    },
                },
            }
        };
        arch = '<form js_class="knowledge_article_view_form">' +
            '<sheet>' +
                '<div class="o_knowledge_editor d-flex flex-grow-1">' +
                    '<field name="body" widget="html"/>' +
                '</div>' +
            '</sheet>' +
        '</form>';
        setupViewRegistries();
    });
    QUnit.test("Check Table of Content is correctly built", async function (assert) {
        assert.expect(24);

        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1,
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        const target = editable.querySelector('p.test_target');
        await insertTableOfContent(editable, target);

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
        ];

        assertHeadings(assert, editable, expectedHeadings);
    });

    QUnit.test('Check Table of Content is correctly built - starting with H2', async function (assert) {
        assert.expect(12);

        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 2,
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        const target = editable.querySelector('p.test_target');
        await insertTableOfContent(editable, target);

        const expectedHeadings = [
            // The "Main 1" section is a <h2>, but it should still be at depth 0
            // as there is no <h1> above it
            {title: 'Main 1',      depth: 0},
            {title: 'Sub 1-1',     depth: 1},
            {title: 'Sub 1-1-1',   depth: 2},
            {title: 'Sub 1-1-2',   depth: 2},
            {title: 'Main 2',      depth: 0},
            {title: 'Sub 2-1',     depth: 1},
        ];
        assertHeadings(assert, editable, expectedHeadings);
    });

    QUnit.test('Check Table of Content is correctly built - starting with H3 followed by H2', async function (assert) {
        assert.expect(4);

        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 3,
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        const target = editable.querySelector('p.test_target');
        await insertTableOfContent(editable, target);

        const expectedHeadings = [
            // The "Main 1" section is a <h3> at depth 0, and the next "Main 2" section
            // is  <h2>, which should still be at the 0 depth instead of 1
            {title: 'Main 1',      depth: 0},
            {title: 'Main 2',      depth: 0},
        ];
        assertHeadings(assert, editable, expectedHeadings);
    });
});

QUnit.module("Knowledge - Silenced Failure Cases (Recoverable)", (hooks) => {
    hooks.beforeEach(() => {
        htmlFieldPromise = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            async startWysiwyg() {
                await super.startWysiwyg(...arguments);
                await nextTick();
                htmlFieldPromise.resolve(this);
            }
        });
        fixture = getFixture();
        type = "form";
        resModel = "knowledge_article";
        record = {
            id: 1,
            display_name: "Article",
            body: "<p class='test_target'><br></p>",
        };
        serverData = {
            models: {
                knowledge_article: {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                        body: {string: "Body", type: "html"},
                    },
                    records: [record],
                    methods: {
                        get_sidebar_articles() {
                            return {articles: [], favorite_ids: []};
                        }
                    }
                }
            },
        };
        arch = `
            <form js_class="knowledge_article_view_form">
                <sheet>
                    <div class="o_knowledge_editor">
                        <field name="body" widget="html"/>
                    </div>
                </sheet>
            </form>
        `;
        setupViewRegistries();
    });

    QUnit.test("Insertion target node disappeared before mounting and recovery (mount another Behavior afterwards)", async function (assert) {
        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1,
        });
        htmlField = await htmlFieldPromise;
        const editor = htmlField.wysiwyg.odooEditor;

        // Patch to control when the mounting is done
        const isAtWillStart = makeDeferred();
        const pauseWillStart = makeDeferred();
        const unpatch = patch(TemplateBehavior.prototype, {
            setup() {
                super.setup(...arguments);
                onWillStart(async () => {
                    isAtWillStart.resolve();
                    await pauseWillStart;
                    unpatch();
                });
            }
        });

        // Insert a Behavior to mount in the editable
        const behaviorHTML = `
            <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_template">
                <div data-prop-name="content">
                    <p><br></p>
                </div>
            </div>
            <p><br></p>
        `;
        const anchor = parseHTML(editor.document, behaviorHTML).firstChild;
        const target = editor.editable.querySelector(".test_target");
        editor.observerUnactive('test_insert_behavior');
        editor.editable.replaceChild(anchor, target);
        editor.observerActive('test_insert_behavior');

        // Wait for the Behavior mounting process to be almost finished
        await isAtWillStart;

        // Remove the target node from the editable
        editor.observerUnactive('test_insert_behavior');
        editor.editable.replaceChild(target, anchor);
        editor.observerActive('test_insert_behavior');

        // unlock onWillstart so that the mouting can continue
        pauseWillStart.resolve();

        // wait for mount mutex
        await htmlField.mountBehaviors();

        // Ensure that the Behavior is not in the editable but in the Handler
        assert.notOk(editor.editable.querySelector('.o_knowledge_behavior_type_template'), "The Behavior cannot be mounted in the editable since its target anchor was removed.");
        const behavior = htmlField.behaviorState.handlerRef.el.querySelector('.o_knowledge_behavior_type_template');
        assert.equal(status(behavior.oKnowledgeBehavior.root.component), "mounted");

        // Put the anchor blueprint in the editable again, this time we'll allow
        // it to be mounted in the editable
        editor.observerUnactive('test_insert_behavior');
        editor.editable.replaceChild(anchor, target);
        editor.observerActive('test_insert_behavior');

        // wait for mount mutex
        await htmlField.mountBehaviors();

        // Ensure that the obsolete Behavior was destroyed and the new one is
        // mounted in the editable
        assert.notOk(htmlField.behaviorState.handlerRef.el.querySelector('.o_knowledge_behavior_type_template'), "The obsolete Behavior should have been destroyed.");
        const newBehavior = editor.editable.querySelector('.o_knowledge_behavior_type_template');
        assert.equal(status(newBehavior.oKnowledgeBehavior.root.component), "mounted");
        assert.notEqual(behavior, newBehavior);
    });

    QUnit.test("Record changed before mounting (destroy obsolete behaviors)", async function (assert) {
        serverData.models.knowledge_article.records.push({
            id: 2,
            display_name: "Other Article",
            body: "<p class='other_target'><br></p>",
        });
        const htmlFieldPatched = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            setup() {
                super.setup();
                onPatched(() => {
                    if (this.props.record.resId === 2) {
                        htmlFieldPatched.resolve();
                    }
                });
            }
        })
        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1,
        });
        htmlField = await htmlFieldPromise;
        const editor = htmlField.wysiwyg.odooEditor;

        // Patch to control when the mounting is done
        const isAtWillStart = makeDeferred();
        const pauseWillStart = makeDeferred();
        const unpatch = patch(TemplateBehavior.prototype, {
            setup() {
                super.setup(...arguments);
                onWillStart(async () => {
                    isAtWillStart.resolve();
                    await pauseWillStart;
                    unpatch();
                });
            }
        });
        // Insert a Behavior to mount in the editable
        const behaviorHTML = `
            <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_template">
                <div data-prop-name="content">
                    <p><br></p>
                </div>
            </div>
            <p><br></p>
        `;
        const anchor = parseHTML(editor.document, behaviorHTML).firstChild;
        const target = editor.editable.querySelector(".test_target");
        editor.observerUnactive('test_insert_behavior');
        editor.editable.replaceChild(anchor, target);
        editor.observerActive('test_insert_behavior');

        // Wait for the Behavior mounting process to be almost finished
        await isAtWillStart;

        assert.ok(
            htmlField.behaviorState.handlerRef.el.querySelector(
                ".o_knowledge_behavior_type_template"
            ),
            "The Behavior anchor should be in the handler (ongoing mounting process)"
        );

        // open the other article article before the end of the mounting process
        htmlField.env.openArticle(2);
        await htmlFieldPatched;

        // wait for mount mutex
        await htmlField.mountBehaviors();

        // check that the behavior was destroyed and is not present in the
        // handler anymore
        assert.ok(
            editor.editable.querySelector(".other_target"),
            "The new article should have fully loaded"
        );
        assert.notOk(
            editor.editable.querySelector(".o_knowledge_behavior_type_template"),
            "The Behavior cannot be mounted in the editable."
        );
        assert.notOk(
            htmlField.behaviorState.handlerRef.el.querySelector(
                ".o_knowledge_behavior_type_template"
            ),
            "The obsolete Behavior should have been destroyed."
        );

        // allow onWillStart of the obsolete behavior to resolve (to not have
        // pending promises).
        pauseWillStart.resolve();
    });
});
