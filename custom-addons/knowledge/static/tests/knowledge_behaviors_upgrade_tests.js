/** @odoo-module */

// web
import { status } from "@odoo/owl";
import { getFixture, makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { getOrigin } from "@web/core/utils/urls";


// web_editor
import { HtmlField } from "@web_editor/js/backend/html_field";
import { unformat } from "@web_editor/js/editor/odoo-editor/test/utils";
import { parseHTML } from "@web_editor/js/editor/odoo-editor/src/utils/utils";


// knowledge
import {
    decodeDataBehaviorProps,
    getPropNameNodes,
} from "@knowledge/js/knowledge_utils";

//------------------------------------------------------------------------------
// Upgrade utils
//------------------------------------------------------------------------------

/**
 * Assert that the desired attributes are set with the correct value on an
 * anchor element.
 *
 * @param {Object} attributes {name: value} to check for
 * @param {Element} anchor
 * @param {Object} assert assert object from QUnit
 */
function assertAttributes(attributes, anchor, assert) {
    for (const attr in attributes) {
        assert.equal(anchor.getAttribute(attr), attributes[attr], `The value of attribute: ${attr} was not as expected.`);
    }
}

/**
 * Assert that the behavior props registered in `data-behavior-props` attribute
 * of anchor are correct.
 *
 * This function also validates that every prop currently registered on the
 * anchor has been tested.
 *
 * @param {Object} props {name: value} to check for
 * @param {Element} anchor
 * @param {Object} assert assert object from QUnit
 */
function assertBehaviorProps(props, anchor, assert) {
    const behaviorProps = decodeDataBehaviorProps(anchor.dataset.behaviorProps);
    for (const prop in props) {
        assert.deepEqual(behaviorProps[prop], props[prop], `The value of prop: ${prop} in data-behavior-props was not as expected.`);
    }
    assert.deepEqual(new Set(Object.keys(behaviorProps)), new Set(Object.keys(props)), "data-behavior-props should only contain valid props from Behavior props schema");
}

//------------------------------------------------------------------------------
// QUnit setup
//------------------------------------------------------------------------------

let fixture;
let serverData;
let arch;
let record;
let htmlFieldPromise;

function beforeEach() {
    htmlFieldPromise = makeDeferred();
    patchWithCleanup(HtmlField.prototype, {
        async startWysiwyg() {
            await super.startWysiwyg(...arguments);
            await nextTick();
            htmlFieldPromise.resolve(this);
        }
    });
    fixture = getFixture();
    record = {
        id: 1,
        name: "Upgrade Article",
        body: "<p><br></p>",
        sequence: 1,
    };
    serverData = {
        models: {
            knowledge_article: {
                fields: {
                    name: {string: "Name", type: "char"},
                    body: {string: "Body", type: "html"},
                    sequence: {string: "Sequence", type: "integer"},
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
}

//------------------------------------------------------------------------------
// Tests
//------------------------------------------------------------------------------

QUnit.module("Knowledge - Behaviors Full Upgrade from original version", (hooks) => {
    hooks.beforeEach(() => {
        beforeEach();
    });

    QUnit.test("FileBehavior Full Upgrade from original version", async function (assert) {
        // Original most basic form of `/file` blueprint (should be upgraded
        // to current version during the mounting process).
        // This file has an unrecognizable href.
        record.body = unformat(`
            <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_file">
                <div data-prop-name="fileImage">
                    <a href="https://example.com/web/content/1?unique=aaa&access_token=bbb&download=true"
                        data-mimetype="image/jpeg" class="o_image"></a>
                </div>
                <div data-prop-name="fileName">name.jpg</div>
                <div data-prop-name="fileExtension">jpg</div>
            </div>
        `);
        await makeView({
            type: "form",
            resModel: "knowledge_article",
            serverData,
            arch,
            resId: 1,
        });
        const htmlField = await htmlFieldPromise;
        let anchor = fixture.querySelector(".o_knowledge_behavior_type_file");
        // Check that the correct attributes are set
        assertAttributes({
            "contenteditable": "false",
            "data-oe-protected": "true",
        }, anchor, assert);
        // Verify that the behavior props are correctly upgraded
        assertBehaviorProps({
            fileData: {
                extension: "jpg",
                filename: "name.jpg",
                mimetype: "image/jpeg",
                name: "name.jpg",
                type: "url", // type is url because the href was not recognized
                url: "https://example.com/web/content/1",
            },
        }, anchor, assert);
        // Verify that there is no `data-prop-name` left
        let propNameNodes = getPropNameNodes(anchor);
        assert.equal(propNameNodes.length, 0);
        assert.equal(status(anchor.oKnowledgeBehavior.root.component), "mounted");

        // File with an href that can be fully parsed
        const editor = htmlField.wysiwyg.odooEditor;
        const newFileEl = parseHTML(editor.document, unformat(`
            <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_file">
                <div data-prop-name="fileImage">
                    <a href="${getOrigin()}/web/content/1?unique=aaa&access_token=bbb&download=true"
                        data-mimetype="image/jpeg" class="o_image"></a>
                </div>
                <div data-prop-name="fileName">name.jpg</div>
                <div data-prop-name="fileExtension">jpg</div>
            </div>
        `)).firstChild;
        anchor.parentElement.replaceChild(newFileEl, anchor);
        await htmlField.mountBehaviors();
        anchor = fixture.querySelector(".o_knowledge_behavior_type_file");
        assertAttributes({
            "contenteditable": "false",
            "data-oe-protected": "true",
        }, anchor, assert);
        assertBehaviorProps({
            fileData: {
                accessToken: "bbb",
                checksum: "aaa",
                extension: "jpg",
                filename: "name.jpg",
                id: 1,
                mimetype: "image/jpeg",
                name: "name.jpg",
                type: "binary",
            },
        }, anchor, assert);
        propNameNodes = getPropNameNodes(anchor);
        assert.equal(propNameNodes.length, 0);
        assert.equal(status(anchor.oKnowledgeBehavior.root.component), "mounted");
    });
});
