/** @odoo-module alias=mass_mailing.field_html_tests **/

import * as ajax from "web.ajax";
import weTestUtils from "web_editor.test_utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import {
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import * as legacyTestUtils from "web.test_utils";
import { assets } from "@web/core/assets";

let serverData;
let fixture;

QUnit.module('mass_mailing', {}, function () {
QUnit.module('field html', (hooks) => {
    hooks.beforeEach(() => {
        fixture = getFixture();
        const models = weTestUtils.wysiwygData({
            'mailing.mailing': {
                fields: {
                    display_name: {
                        string: "Displayed name",
                        type: "char"
                    },
                    body_html: {
                        string: "Message Body inline (to send)",
                        type: "html"
                    },
                    body_arch: {
                        string: "Message Body for edition",
                        type: "html"
                    },
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    body_html: "<div class='field_body' style='background-color: red;'><p>code to edit</p></div>",
                    body_arch: "<div class='field_body'><p>code to edit</p></div>",
                }],
            },
        });
        serverData = { models };
        setupViewRegistries();

        legacyTestUtils.mock.patch(ajax, {
            loadAsset: function (xmlId) {
                if (xmlId === 'template.assets') {
                    return Promise.resolve({
                        cssLibs: [],
                        cssContents: ['.field_body {background-color: red;}'],
                        jsContents: ['window.odoo = {define: function(){}}; // inline asset'],
                    });
                }
                if (xmlId === 'template.assets_all_style') {
                    return Promise.resolve({
                        cssLibs: $('link[href]:not([type="image/x-icon"])').map(function () {
                            return $(this).attr('href');
                        }).get(),
                        cssContents: ['.field_body {background-color: red;}']
                    });
                }
                if (xmlId === 'web_editor.wysiwyg_iframe_editor_assets') {
                    return Promise.resolve({});
                }
                throw 'Wrong template';
            },
        });
    });
    hooks.afterEach(() => {
        legacyTestUtils.mock.unpatch(ajax);
    });

    QUnit.test('save arch and html', async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: 'mailing.mailing',
            resId: 1,
            serverData,
            arch: '<form>' +
                '   <field name="body_html" class="oe_read_only"'+
                '       options="{'+
                '                \'cssReadonly\': \'template.assets\','+
                '       }"'+
                '   />'+
                '   <field name="body_arch" class="oe_edit_only" widget="mass_mailing_html"'+
                '       options="{'+
                '                \'snippets\': \'web_editor.snippets\','+
                '                \'cssEdit\': \'template.assets\','+
                '                \'inline-field\': \'body_html\''+
                '       }"'+
                '   />'+
                '</form>',
        });
        await nextTick();
        let fieldReadonly = fixture.querySelector('.o_field_widget[name="body_html"]');
        let fieldEdit = fixture.querySelector('.o_field_widget[name="body_arch"]');

        assert.strictEqual($(fieldReadonly).css('display'), 'none', "should hide the readonly mode");
        assert.strictEqual($(fieldEdit).css('display'), 'block', "should display the edit mode");
    });

    QUnit.test('component destroyed while loading', async function (assert) {
        const def = makeDeferred();
        patchWithCleanup(assets, {
            loadBundle() {
                assert.step("loadBundle");
                return def;
            }
        })

        await makeView({
            type: "form",
            resModel: 'mailing.mailing',
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="display_name"/>
                    <field name="body_arch" widget="mass_mailing_html" attrs="{'invisible': [['display_name', '=', 'hide']]}"/>
                </form>`,
        });

        assert.containsOnce(fixture, ".o_field_widget[name=body_arch]");
        await editInput(fixture, ".o_field_widget[name=display_name] input", "hide");
        assert.containsNone(fixture, ".o_field_widget[name=body_arch]");

        def.resolve();
        await nextTick();
        assert.containsNone(fixture, ".o_field_widget[name=body_arch]");
        assert.verifySteps(["loadBundle"]);
    });
});
});
